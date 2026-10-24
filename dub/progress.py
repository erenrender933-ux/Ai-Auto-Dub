import asyncio
import time

from pyrogram.errors import FloodWait


def bar(done: int, total: int, width: int = 12) -> str:
    ratio = min(done / total, 1.0) if total else 0.0
    filled = int(ratio * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {int(ratio * 100)}%"


class Progress:
    """Edits one Telegram message, throttled to avoid FloodWait."""

    def __init__(self, msg, interval: float = 3.0) -> None:
        self.msg = msg
        self.interval = interval
        self._last = 0.0
        self._text = ""

    async def set(self, stage: str, done: int = 0, total: int = 0, force: bool = False) -> None:
        now = time.monotonic()
        is_final = bool(total) and done >= total
        if not (force or is_final) and now - self._last < self.interval:
            return
        self._last = now

        text = f"🎬 **AI Auto Dub**\n\n{stage}"
        if total:
            text += f"\n{bar(done, total)}  ({done}/{total})"
        if text == self._text:
            return
        self._text = text

        try:
            await self.msg.edit_text(text)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
