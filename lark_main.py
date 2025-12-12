import asyncio
import json
import logging
from typing import Dict

from fastapi import FastAPI, Request
from lark_oapi import Client

from phone_agent.config.bot_config import BotConfig
from phone_agent.interfaces.lark import LarkInterface
from phone_agent.interfaces.task_runner import TaskRunner

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

config = BotConfig()
app = FastAPI()

client = Client.builder() \
    .app_id(config.lark_app_id) \
    .app_secret(config.lark_app_secret) \
    .build()

active_tasks: Dict[str, LarkInterface] = {}


def check_lark_auth(user_id: str) -> bool:
    return user_id in config.lark_allowed_users


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/webhook/event")
async def handle_event(request: Request):
    body = await request.json()

    if body.get("type") == "url_verification":
        logger.info("URL verification challenge received")
        return {"challenge": body.get("challenge")}

    asyncio.create_task(process_event_async(body))
    return {"code": 0}


async def process_event_async(body: dict):
    try:
        event_type = body.get("header", {}).get("event_type")

        if event_type == "im.message.receive_v1":
            await handle_message_event(body.get("event", {}))
        elif event_type == "card.action.trigger":
            await handle_card_action_event(body.get("event", {}))
        else:
            logger.warning(f"Unknown event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)


async def handle_message_event(event: dict):
    sender = event.get("sender", {})
    user_id = sender.get("sender_id", {}).get("open_id")

    if not check_lark_auth(user_id):
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        interface = LarkInterface(client, user_id)
        await interface.send_message("未授权用户")
        return

    message = event.get("message", {})
    msg_type = message.get("message_type")

    if msg_type != "text":
        logger.info(f"Ignoring non-text message type: {msg_type}")
        return

    content = json.loads(message.get("content", "{}"))
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


async def handle_card_action_event(event: dict):
    action = event.get("action", {})
    value_str = action.get("value", "{}")

    try:
        value = json.loads(value_str)
    except json.JSONDecodeError:
        logger.error(f"Invalid action value JSON: {value_str}")
        return

    msg_id = value.get("msg_id")
    action_type = value.get("action")

    user_id = event.get("operator", {}).get("open_id")

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


def main():
    import uvicorn

    logger.info("Starting Lark bot server...")
    logger.info(f"App ID: {config.lark_app_id}")
    logger.info(f"Allowed users: {config.lark_allowed_users}")
    logger.info(f"Webhook URL: http://{config.lark_webhook_host}:{config.lark_webhook_port}/webhook/event")

    uvicorn.run(
        app,
        host=config.lark_webhook_host,
        port=config.lark_webhook_port,
        log_level="info"
    )


if __name__ == '__main__':
    main()
