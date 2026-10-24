import asyncio
import os

import edge_tts

from config import settings
from dub import ffmpeg


async def synthesize_segment(
    text: str, voice: str, pitch: str, slot_sec: float, out_wav: str
) -> str:
    mp3 = out_wav[:-4] + ".mp3"

    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, pitch=pitch).save(mp3)
            break
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))

    raw_len = await ffmpeg.probe_duration(mp3)
    # Speed up only if the voice is longer than its time slot
    tempo = min(max(raw_len / slot_sec, 1.0), settings.max_tempo)
    await ffmpeg.mp3_to_wav(mp3, out_wav, settings.sample_rate, tempo)
    os.remove(mp3)
    return out_wav
