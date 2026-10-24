import asyncio
import logging
import os
import shutil

from pyrogram import Client, filters
from pyrogram.types import Message

from config import settings
from dub.pipeline import process_video
from dub.progress import Progress

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("dubbot")

app = Client(
    "ai_auto_dub",
    api_id=settings.api_id,
    api_hash=settings.api_hash,
    bot_token=settings.bot_token,
    workdir="data",
)

job_slots = asyncio.Semaphore(settings.max_concurrent_jobs)


@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message: Message):
    await message.reply_text(
        "👋 **AI Auto Dub Bot**\n\n"
        "Video anuppunga. Tamil (Chennai style) voice dub, "
        "English + Tamil subtitles kedaikum."
    )


@app.on_message(filters.private & (filters.video | filters.document))
async def dub_handler(client: Client, message: Message):
    media = message.video or message.document

    if message.document and not (message.document.mime_type or "").startswith("video/"):
        return await message.reply_text("❌ Video file mattum anuppunga.")

    size_mb = (media.file_size or 0) / 1024 / 1024
    if size_mb > settings.max_file_mb:
        return await message.reply_text(f"❌ File too big. Max {settings.max_file_mb} MB.")

    status = await message.reply_text("⏳ Queue-la irukku...")
    progress = Progress(status)
    job_dir = os.path.join(settings.work_dir, f"{message.chat.id}_{message.id}")
    os.makedirs(job_dir, exist_ok=True)

    async with job_slots:
        try:
            # Download
            await progress.set("📥 Downloading video", force=True)
            video_path = await client.download_media(
                media,
                file_name=os.path.join(job_dir, "input.mp4"),
                progress=lambda cur, tot: asyncio.ensure_future(
                    progress.set("📥 Downloading video", cur, tot)
                ),
            )

            # Dub
            out_video, srt = await process_video(video_path, job_dir, progress)

            # Upload
            await progress.set("📤 Uploading dubbed video", force=True)
            await message.reply_video(
                out_video,
                caption="✅ Tamil AI dub ready",
                supports_streaming=True,
                progress=lambda cur, tot: asyncio.ensure_future(
                    progress.set("📤 Uploading dubbed video", cur, tot)
                ),
            )
            await message.reply_document(srt, caption="📝 Subtitles (English + Tamil)")
            await status.delete()

        except Exception as e:
            log.exception("Dub job failed")
            try:
                await status.edit_text(f"❌ Failed: {str(e)[:300]}")
            except Exception:
                pass
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)


if __name__ == "__main__":
    os.makedirs(settings.work_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    app.run()
