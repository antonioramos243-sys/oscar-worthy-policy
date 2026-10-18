"""Serialize cues to SRT, which ffmpeg can burn in directly."""

from __future__ import annotations

from owp.models import CaptionCue


def _timestamp(seconds: float) -> str:
    """Format seconds as SRT's HH:MM:SS,mmm."""
    if seconds < 0:
        raise ValueError(f"negative timestamp: {seconds}")
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def to_srt(cues: list[CaptionCue]) -> str:
    """Render cues as an SRT document."""
    blocks = [
        f"{index}\n{_timestamp(cue.start_s)} --> {_timestamp(cue.end_s)}\n{cue.text}"
        for index, cue in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")
