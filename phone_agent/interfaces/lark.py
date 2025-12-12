import asyncio
import json
import logging
from typing import Optional, Dict
from pathlib import Path

from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateImageRequest,
    CreateImageRequestBody
)
from lark_oapi import Client

from phone_agent.interfaces.base import BaseInterface, ProgressUpdate

logger = logging.getLogger(__name__)


class LarkInterface(BaseInterface):
    def __init__(self, client: Client, receive_id: str, receive_id_type: str = "open_id"):
        self.client = client
        self.receive_id = receive_id
        self.receive_id_type = receive_id_type
        self._cancelled = False
        self._confirmation_events: Dict[str, asyncio.Event] = {}
        self._confirmation_results: Dict[str, bool] = {}

    async def send_message(self, text: str) -> None:
        request = CreateMessageRequest.builder() \
            .receive_id_type(self.receive_id_type) \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(self.receive_id)
                .msg_type("text")
                .content(json.dumps({"text": text}))
                .build()
            ) \
            .build()

        response = self.client.im.v1.message.create(request)
        if not response.success():
            logger.error(f"Failed to send message: {response.msg}")

    async def send_image(self, image_path: str, caption: str = "") -> None:
        logger.info(f"Sending image: {image_path}")
        image_key = await self.upload_image(image_path)

        if image_key:
            logger.info(f"Image uploaded successfully, image_key: {image_key}")
            request = CreateMessageRequest.builder() \
                .receive_id_type(self.receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(self.receive_id)
                    .msg_type("image")
                    .content(json.dumps({"image_key": image_key}))
                    .build()
                ) \
                .build()

            response = self.client.im.v1.message.create(request)
            if not response.success():
                logger.error(f"Failed to send image: {response.msg}")
            else:
                logger.info("Image sent successfully")

            if caption:
                await self.send_message(caption)
        else:
            logger.error("Failed to upload image, image_key is None")

    async def send_progress(self, update: ProgressUpdate) -> None:
        logger.info(f"Sending progress update for step {update.step_num}/{update.total_steps}")

        thinking_preview = update.thinking[:200] + "..." if len(update.thinking) > 200 else update.thinking
        action_name = update.action.get('action', 'Unknown')

        card = self._build_progress_card(
            step_num=update.step_num,
            total_steps=update.total_steps,
            thinking=thinking_preview,
            action=action_name
        )

        try:
            request = CreateMessageRequest.builder() \
                .receive_id_type(self.receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(self.receive_id)
                    .msg_type("interactive")
                    .content(json.dumps(card))
                    .build()
                ) \
                .build()

            response = self.client.im.v1.message.create(request)
            if not response.success():
                logger.error(f"Failed to send progress card: {response.msg}")
            else:
                logger.info("Progress card sent successfully")
        except Exception as e:
            logger.error(f"Failed to send progress message: {e}", exc_info=True)

    async def ask_confirmation(self, message: str) -> bool:
        event = asyncio.Event()
        msg_id = f"confirm_{id(event)}"
        self._confirmation_events[msg_id] = event
        self._confirmation_results[msg_id] = False

        card = self._build_confirmation_card(message, msg_id)

        request = CreateMessageRequest.builder() \
            .receive_id_type(self.receive_id_type) \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(self.receive_id)
                .msg_type("interactive")
                .content(json.dumps(card))
                .build()
            ) \
            .build()

        response = self.client.im.v1.message.create(request)
        if not response.success():
            logger.error(f"Failed to send confirmation card: {response.msg}")
            return False

        await event.wait()
        result = self._confirmation_results.get(msg_id, False)

        del self._confirmation_events[msg_id]
        del self._confirmation_results[msg_id]

        return result

    async def ask_takeover(self, message: str) -> None:
        event = asyncio.Event()
        msg_id = f"takeover_{id(event)}"
        self._confirmation_events[msg_id] = event

        card = self._build_takeover_card(message, msg_id)

        request = CreateMessageRequest.builder() \
            .receive_id_type(self.receive_id_type) \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(self.receive_id)
                .msg_type("interactive")
                .content(json.dumps(card))
                .build()
            ) \
            .build()

        response = self.client.im.v1.message.create(request)
        if not response.success():
            logger.error(f"Failed to send takeover card: {response.msg}")
            return

        await event.wait()

        del self._confirmation_events[msg_id]

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        self._cancelled = True

    def handle_card_action(self, msg_id: str, action: str, confirmed: bool = False):
        if msg_id in self._confirmation_events:
            if action in ["confirm", "cancel"]:
                self._confirmation_results[msg_id] = confirmed
            self._confirmation_events[msg_id].set()

    async def upload_image(self, image_path: str) -> Optional[str]:
        try:
            logger.info(f"Uploading image from path: {image_path}")
            with open(image_path, 'rb') as f:
                image_data = f.read()
            logger.info(f"Image file size: {len(image_data)} bytes")

            request = CreateImageRequest.builder() \
                .request_body(
                    CreateImageRequestBody.builder()
                    .image_type("message")
                    .image(image_data)
                    .build()
                ) \
                .build()

            response = self.client.im.v1.image.create(request)
            if response.success():
                logger.info(f"Image uploaded successfully: {response.data.image_key}")
                return response.data.image_key
            else:
                logger.error(f"Failed to upload image: {response.msg}")
                return None
        except Exception as e:
            logger.error(f"Error uploading image: {e}", exc_info=True)
            return None

    def _build_progress_card(self, step_num: int, total_steps: int, thinking: str, action: str) -> dict:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": f"步骤 {step_num}/{total_steps}"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**思考：**\n{thinking}"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**操作：** {action}"
                            }
                        }
                    ]
                }
            ]
        }

    def _build_confirmation_card(self, message: str, msg_id: str) -> dict:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "orange",
                "title": {
                    "tag": "plain_text",
                    "content": "需要确认"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": message
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "确认"
                            },
                            "type": "primary",
                            "value": json.dumps({"action": "confirm", "msg_id": msg_id})
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "取消"
                            },
                            "type": "default",
                            "value": json.dumps({"action": "cancel", "msg_id": msg_id})
                        }
                    ]
                }
            ]
        }

    def _build_takeover_card(self, message: str, msg_id: str) -> dict:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "red",
                "title": {
                    "tag": "plain_text",
                    "content": "需要手动操作"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"{message}\n\n完成后请点击下方按钮。"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "已完成"
                            },
                            "type": "primary",
                            "value": json.dumps({"action": "takeover_done", "msg_id": msg_id})
                        }
                    ]
                }
            ]
        }
