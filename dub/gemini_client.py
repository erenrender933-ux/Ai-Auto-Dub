import asyncio
import json
import logging

from google import genai
from google.genai import types

from config import settings

log = logging.getLogger(__name__)
client = genai.Client(api_key=settings.gemini_api_key)

PROMPT = """You are a professional dubbing transcriber and translator.
Listen to this audio and return ONLY a JSON array. Each item must be:
{"start": seconds, "end": seconds, "speaker": "S1", "gender": "male" or "female" or "unknown",
 "original": "original speech in English or source language", "tamil": "Tamil translation"}

Rules:
- Times are relative to the start of THIS audio clip.
- Keep speaker labels consistent inside this clip. Detect gender from the voice.
- Split at natural sentence or pause boundaries. Each segment under 12 seconds.
- Skip silence, music and sound effects (no entry for them).
- "tamil": write spoken Chennai Tamil (Madras bashai) like local people talk daily.
  Casual and colloquial. Keep common English words naturally (bro, ok, time, phone).
  Do NOT use formal or literary Tamil.
- Keep the Tamil text short enough to be spoken in the same time as the original.
- Output only the JSON array. No markdown, no commentary."""


async def _wait_active(file):
    while getattr(file.state, "name", str(file.state)) == "PROCESSING":
        await asyncio.sleep(1)
        file = await client.aio.files.get(name=file.name)
    return file


async def transcribe_chunk(path: str, offset: float) -> list[dict]:
    uploaded = await client.aio.files.upload(file=path)
    try:
        uploaded = await _wait_active(uploaded)
        last_err = None
        for attempt in range(3):
            try:
                resp = await client.aio.models.generate_content(
                    model=settings.gemini_model,
                    contents=[uploaded, PROMPT],
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                    ),
                )
                raw_segments = json.loads(resp.text)
                break
            except Exception as e:
                last_err = e
                log.warning("Gemini attempt %s failed: %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)
        else:
            raise RuntimeError(f"Gemini failed after retries: {last_err}")
    finally:
        try:
            await client.aio.files.delete(name=uploaded.name)
        except Exception:
            pass

    segments = []
    for s in raw_segments:
        try:
            tamil = str(s.get("tamil", "")).strip()
            if not tamil:
                continue
            segments.append({
                "start": float(s["start"]) + offset,
                "end": float(s["end"]) + offset,
                "speaker": str(s.get("speaker", "S1")),
                "gender": str(s.get("gender", "unknown")).lower(),
                "original": str(s.get("original", "")).strip(),
                "tamil": tamil,
            })
        except (KeyError, TypeError, ValueError):
            continue
    return segments
