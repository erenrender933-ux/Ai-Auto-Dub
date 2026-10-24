import asyncio
import glob
import os
from asyncio.subprocess import DEVNULL, PIPE


async def _run(*args: str) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        *args, stdin=DEVNULL, stdout=PIPE, stderr=PIPE
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {err.decode(errors='ignore')[-400:]}")
    return _


async def probe_duration(path: str) -> float:
    out = await _run(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", path,
    )
    return float(out.decode().strip())


async def extract_audio(video: str, wav_out: str, sample_rate: int) -> None:
    await _run(
        "ffmpeg", "-y", "-loglevel", "error", "-i", video,
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le", wav_out,
    )


async def split_audio(wav: str, out_dir: str, chunk_seconds: int) -> list[str]:
    pattern = os.path.join(out_dir, "chunk_%03d.wav")
    await _run(
        "ffmpeg", "-y", "-loglevel", "error", "-i", wav,
        "-f", "segment", "-segment_time", str(chunk_seconds),
        "-c", "copy", pattern,
    )
    return sorted(glob.glob(os.path.join(out_dir, "chunk_*.wav")))


async def mp3_to_wav(src: str, dst: str, sample_rate: int, tempo: float = 1.0) -> None:
    args = ["ffmpeg", "-y", "-loglevel", "error", "-i", src]
    if tempo > 1.01:
        args += ["-filter:a", f"atempo={tempo:.3f}"]
    args += ["-ar", str(sample_rate), "-ac", "1", "-c:a", "pcm_s16le", dst]
    await _run(*args)


async def mux(video: str, audio: str, srt: str, out: str) -> None:
    await _run(
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", video, "-i", audio, "-i", srt,
        "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-c:s", "mov_text", "-metadata:s:s:0", "language=tam",
        "-movflags", "+faststart", out,
    )
