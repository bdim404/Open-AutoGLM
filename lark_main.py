import asyncio
import json
import logging
from typing import Dict

from lark_oapi import Client
from lark_oapi.event import EventDispatcherHandler, MessageReceiveEvent, CardActionEvent

from phone_agent.config.bot_config import BotConfig
from phone_agent.interfaces.lark import LarkInterface
from phone_agent.interfaces.task_runner import TaskRunner

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

config = BotConfig()

client = Client.builder() \
    .app_id(config.lark_app_id) \
    .app_secret(config.lark_app_secret) \
    .build()

active_tasks: Dict[str, LarkInterface] = {}
event_loop = asyncio.new_event_loop()


def check_lark_auth(user_id: str) -> bool:
    return user_id in config.lark_allowed_users


class MessageHandler(EventDispatcherHandler):
    def __init__(self):
        super().__init__()

    def do(self, event: MessageReceiveEvent) -> None:
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(handle_message_event(event))


class CardActionHandler(EventDispatcherHandler):
    def __init__(self):
        super().__init__()

    def do(self, event: CardActionEvent) -> None:
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(handle_card_action_event(event))


async def handle_message_event(event: MessageReceiveEvent):
    try:
        sender = event.event.sender
        user_id = sender.sender_id.open_id

        if not check_lark_auth(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            interface = LarkInterface(client, user_id)
            await interface.send_message("未授权用户")
            return

        message = event.event.message
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


async def handle_card_action_event(event: CardActionEvent):
    try:
        action = event.event.action
        value_str = action.value

        try:
            value = json.loads(value_str)
        except json.JSONDecodeError:
            logger.error(f"Invalid action value JSON: {value_str}")
            return

        msg_id = value.get("msg_id")
        action_type = value.get("action")

        user_id = event.event.operator.open_id

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
    from lark_oapi.event import EventDispatcher

    logger.info("Starting Lark bot with long connection...")
    logger.info(f"App ID: {config.lark_app_id}")
    logger.info(f"Allowed users: {config.lark_allowed_users}")

    event_dispatcher = EventDispatcher.builder(
        verification_token=config.lark_verification_token,
        encrypt_key=""
    ).build()

    event_dispatcher.register("im.message.receive_v1", MessageHandler())
    event_dispatcher.register("card.action.trigger", CardActionHandler())

    logger.info("Starting event listener...")

    client.ws.start(event_dispatcher)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
