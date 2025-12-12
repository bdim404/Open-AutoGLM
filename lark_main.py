import asyncio
import json
import logging
from typing import Dict

import lark_oapi as lark

from phone_agent.config.bot_config import BotConfig
from phone_agent.interfaces.lark import LarkInterface
from phone_agent.interfaces.task_runner import TaskRunner

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

config = BotConfig()

client = lark.Client.builder() \
    .app_id(config.lark_app_id) \
    .app_secret(config.lark_app_secret) \
    .build()

active_tasks: Dict[str, LarkInterface] = {}


def check_lark_auth(user_id: str) -> bool:
    return user_id in config.lark_allowed_users


def do_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    logger.info(f"do_p2_im_message_receive_v1 called with data: {data}")
    asyncio.create_task(handle_message_event(data))


async def handle_message_event(data: lark.im.v1.P2ImMessageReceiveV1):
    try:
        event = data.event
        sender = event.sender
        user_id = sender.sender_id.open_id

        logger.info(f"Received message from user: {user_id}")

        if not check_lark_auth(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            logger.warning(f"Please add this user to allowed_users in config: '{user_id}'")
            interface = LarkInterface(client, user_id)
            await interface.send_message(f"未授权用户\n\n请将以下 ID 添加到配置文件的 allowed_users 中：\n{user_id}")
            return

        message = event.message
        msg_type = message.message_type

        if msg_type != "text":
            logger.info(f"Ignoring non-text message type: {msg_type}")
            return

        content = json.loads(message.content)
        text = content.get("text", "").strip()

        if not text:
            return

        if user_id in active_tasks:
            interface = LarkInterface(client, user_id)
            await interface.send_message("另一个任务正在运行中，请先取消或等待完成。")
            return

        interface = LarkInterface(client, user_id)
        active_tasks[user_id] = interface

        try:
            runner = TaskRunner(
                interface=interface,
                model_config=config.model_config,
                agent_config=config.agent_config
            )

            await interface.send_message(f"开始执行任务: {text}")
            result = await runner.run_task(text)
            logger.info(f"Task completed for user {user_id}: {result}")

        except Exception as e:
            logger.error(f"Task error for user {user_id}: {e}", exc_info=True)
            await interface.send_message(f"错误: {str(e)}")

        finally:
            if user_id in active_tasks:
                del active_tasks[user_id]

    except Exception as e:
        logger.error(f"Error handling message event: {e}", exc_info=True)


def do_card_action_event(data: lark.CustomizedEvent) -> None:
    asyncio.create_task(handle_card_action_event(data))


async def handle_card_action_event(data: lark.CustomizedEvent):
    try:
        event_data = json.loads(data.event)
        action = event_data.get("action", {})
        value_str = action.get("value", "{}")

        try:
            value = json.loads(value_str)
        except json.JSONDecodeError:
            logger.error(f"Invalid action value JSON: {value_str}")
            return

        msg_id = value.get("msg_id")
        action_type = value.get("action")

        operator = event_data.get("operator", {})
        user_id = operator.get("open_id")

        if user_id not in active_tasks:
            logger.warning(f"No active task for user {user_id} when handling card action")
            return

        interface = active_tasks[user_id]

        if action_type == "confirm":
            interface.handle_card_action(msg_id, action_type, confirmed=True)
        elif action_type == "cancel":
            interface.handle_card_action(msg_id, action_type, confirmed=False)
        elif action_type == "takeover_done":
            interface.handle_card_action(msg_id, action_type, confirmed=True)

    except Exception as e:
        logger.error(f"Error handling card action event: {e}", exc_info=True)


def main():
    logger.info("Starting Lark bot with long connection...")
    logger.info(f"App ID: {config.lark_app_id}")
    logger.info(f"Allowed users: {config.lark_allowed_users}")

    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
        .register_p1_customized_event("card.action.trigger", do_card_action_event) \
        .build()

    logger.info("Starting WebSocket client...")

    ws_client = lark.ws.Client(
        config.lark_app_id,
        config.lark_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )

    ws_client.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
