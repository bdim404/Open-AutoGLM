import asyncio
import json
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from phone_agent.interfaces.base import BaseInterface, ProgressUpdate


class TelegramInterface(BaseInterface):
    def __init__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.update = update
        self.context = context
        self.chat_id = update.effective_chat.id
        self._cancelled = False
        self._confirmation_event: Optional[asyncio.Event] = None
        self._confirmation_result: Optional[bool] = None

    async def send_message(self, text: str) -> None:
        await self.context.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode='Markdown'
        )

    async def send_image(self, image_path: str, caption: str = "") -> None:
        with open(image_path, 'rb') as photo:
            await self.context.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo,
                caption=caption
            )

    async def send_progress(self, update: ProgressUpdate) -> None:
        thinking_preview = update.thinking[:200] + "..." if len(update.thinking) > 200 else update.thinking
        action_name = update.action.get('action', 'Unknown')

        progress_text = (
            f"Step {update.step_num}/{update.total_steps}\n\n"
            f"*Thinking:*\n{thinking_preview}\n\n"
            f"*Action:* {action_name}"
        )

        try:
            await self.context.bot.send_message(
                chat_id=self.chat_id,
                text=progress_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Failed to send progress message: {e}")

        if update.screenshot_path:
            try:
                await self.send_image(update.screenshot_path, f"Step {update.step_num}")
            except Exception as e:
                print(f"Failed to send screenshot: {e}")

    async def ask_confirmation(self, message: str) -> bool:
        self._confirmation_event = asyncio.Event()
        self._confirmation_result = None

        keyboard = [[
            InlineKeyboardButton("Confirm", callback_data="confirm_yes"),
            InlineKeyboardButton("Cancel", callback_data="confirm_no")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.context.bot.send_message(
            chat_id=self.chat_id,
            text=f"*Confirmation Required*\n\n{message}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        await self._confirmation_event.wait()
        return self._confirmation_result or False

    def handle_confirmation_callback(self, confirmed: bool):
        self._confirmation_result = confirmed
        if self._confirmation_event:
            self._confirmation_event.set()

    async def ask_takeover(self, message: str) -> None:
        keyboard = [[
            InlineKeyboardButton("Done", callback_data="takeover_done")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        self._confirmation_event = asyncio.Event()
        await self.context.bot.send_message(
            chat_id=self.chat_id,
            text=f"*Manual Operation Required*\n\n{message}\n\nPress 'Done' when finished.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        await self._confirmation_event.wait()

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        self._cancelled = True
