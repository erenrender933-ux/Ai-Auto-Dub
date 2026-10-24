import wave

import numpy as np


def _read(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def mix_dub(
    original_wav: str,
    timeline: list[tuple[float, str]],
    out_wav: str,
    bg_volume: float,
    sample_rate: int,
) -> None:
    """Place each Tamil segment at its start time over the quieter original audio."""
    track = _read(original_wav) * bg_volume

    for start, seg_path in timeline:
        voice = _read(seg_path)
        i = int(start * sample_rate)
        if i >= len(track):
            continue
        end = min(i + len(voice), len(track))
        track[i:end] += voice[: end - i]

    np.clip(track, -1.0, 1.0, out=track)
    pcm = (track * 32767).astype(np.int16)

    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
