def _ts(sec: float) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{s:06.3f}".replace(".", ",")


def build_srt(segments: list[dict], path: str, include_english: bool = True) -> None:
    blocks = []
    for i, s in enumerate(segments, 1):
        lines = []
        if include_english and s["original"]:
            lines.append(s["original"])
        lines.append(s["tamil"])
        blocks.append(
            f"{i}\n{_ts(s['start'])} --> {_ts(s['end'])}\n" + "\n".join(lines)
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + "\n")
