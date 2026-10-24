import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.environ["BOT_TOKEN"]
    api_id: int = int(os.environ["API_ID"])
    api_hash: str = os.environ["API_HASH"]
    gemini_api_key: str = os.environ["GEMINI_API_KEY"]

    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    max_file_mb: int = int(os.getenv("MAX_FILE_MB", "500"))
    max_video_minutes: float = float(os.getenv("MAX_VIDEO_MINUTES", "30"))
    chunk_seconds: int = int(os.getenv("CHUNK_SECONDS", "300"))
    transcribe_concurrency: int = int(os.getenv("TRANSCRIBE_CONCURRENCY", "2"))
    tts_concurrency: int = int(os.getenv("TTS_CONCURRENCY", "6"))
    max_concurrent_jobs: int = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
    original_volume: float = float(os.getenv("ORIGINAL_VOLUME", "0.12"))
    subtitle_english: bool = os.getenv("SUBTITLE_ENGLISH", "1") == "1"
    work_dir: str = os.getenv("WORK_DIR", "work")

    sample_rate: int = 24000
    max_tempo: float = 1.6  # never speed up a voice more than this


settings = Settings()
