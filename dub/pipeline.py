import asyncio
import logging
import os

from config import settings
from dub import ffmpeg
from dub.gemini_client import transcribe_chunk
from dub.mixer import mix_dub
from dub.progress import Progress
from dub.subtitles import build_srt
from dub.tts import synthesize_segment
from dub.voices import VoiceAssigner

log = logging.getLogger(__name__)
SR = settings.sample_rate


async def process_video(video_path: str, job_dir: str, progress: Progress) -> tuple[str, str]:
    # 0. Check length
    duration = await ffmpeg.probe_duration(video_path)
    if duration / 60 > settings.max_video_minutes:
        raise ValueError(f"Video too long. Max {settings.max_video_minutes:.0f} minutes.")

    # 1. Extract audio
    await progress.set("🎧 Extracting audio", force=True)
    full_wav = os.path.join(job_dir, "full.wav")
    await ffmpeg.extract_audio(video_path, full_wav, SR)

    # 2. Split into chunks so Gemini output stays reliable and parallel
    chunks_dir = os.path.join(job_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)
    chunks = await ffmpeg.split_audio(full_wav, chunks_dir, settings.chunk_seconds)

    # 3. Transcribe + translate with Gemini (parallel, limited)
    stage = "🧠 Listening & translating"
    await progress.set(stage, 0, len(chunks), force=True)
    sem = asyncio.Semaphore(settings.transcribe_concurrency)
    done = 0

    async def do_chunk(i: int, path: str) -> list[dict]:
        nonlocal done
        async with sem:
            result = await transcribe_chunk(path, i * settings.chunk_seconds)
        done += 1
        await progress.set(stage, done, len(chunks))
        return result

    parts = await asyncio.gather(*(do_chunk(i, p) for i, p in enumerate(chunks)))
    segments = sorted((s for part in parts for s in part), key=lambda s: s["start"])
    if not segments:
        raise RuntimeError("No speech found in this video.")

    # 4. Subtitles (English + Tamil)
    srt_path = os.path.join(job_dir, "subtitles.srt")
    build_srt(segments, srt_path, include_english=settings.subtitle_english)

    # 5. Voice per speaker, then TTS per segment (parallel, limited)
    assigner = VoiceAssigner()
    plan = [assigner.get(s["gender"], s["speaker"]) for s in segments]

    stage = "🎙️ Generating Tamil voice"
    await progress.set(stage, 0, len(segments), force=True)
    tts_sem = asyncio.Semaphore(settings.tts_concurrency)
    done = 0

    async def do_tts(i: int, s: dict, voice: str, pitch: str) -> tuple[float, str]:
        nonlocal done
        slot = max(0.3, s["end"] - s["start"])
        out = os.path.join(job_dir, f"seg_{i:05d}.wav")
        async with tts_sem:
            wav = await synthesize_segment(s["tamil"], voice, pitch, slot, out)
        done += 1
        await progress.set(stage, done, len(segments))
        return s["start"], wav

    timeline = await asyncio.gather(
        *(do_tts(i, s, v, p) for i, (s, (v, p)) in enumerate(zip(segments, plan)))
    )

    # 6. Mix all voice segments with quiet original audio
    await progress.set("🎚️ Mixing voice with background", force=True)
    dub_wav = os.path.join(job_dir, "dub.wav")
    await asyncio.to_thread(mix_dub, full_wav, timeline, dub_wav, settings.original_volume, SR)

    # 7. Render final video with dub audio + soft subtitles
    await progress.set("🎬 Rendering final video", force=True)
    out_path = os.path.join(job_dir, "dubbed.mp4")
    await ffmpeg.mux(video_path, dub_wav, srt_path, out_path)

    return out_path, srt_path
