"""Group word timings into on-screen caption cues.

Implemented rather than stubbed: it is pure logic over the voiceover's word
timings, so it needs no credentials and none of the open requirements questions
change it. Captions are assumed mandatory - most social video is watched muted.
"""

from __future__ import annotations

from owp.models import CaptionCue, WordTiming

# Short cues suit vertical video: a couple of words at a time, large on screen.
MAX_WORDS_PER_CUE = 4
MAX_CUE_SECONDS = 2.0
# A pause longer than this reads as a beat change, so break the cue there even
# if it is still short.
PAUSE_BREAK_SECONDS = 0.35


def cues_from_word_timings(
    words: list[WordTiming],
    *,
    max_words: int = MAX_WORDS_PER_CUE,
    max_seconds: float = MAX_CUE_SECONDS,
    pause_break_seconds: float = PAUSE_BREAK_SECONDS,
) -> list[CaptionCue]:
    """Chunk `words` into cues, breaking on length, duration, or a pause.

    Args:
        words: Word timings in ascending order, as reported by the TTS provider.
        max_words: Hard cap on words per cue.
        max_seconds: Hard cap on cue duration.
        pause_break_seconds: Gap between consecutive words that forces a break.

    Returns:
        Cues in order. Empty when `words` is empty.
    """
    cues: list[CaptionCue] = []
    buffer: list[WordTiming] = []

    def flush() -> None:
        if buffer:
            cues.append(
                CaptionCue(
                    text=" ".join(w.word for w in buffer),
                    start_s=buffer[0].start_s,
                    end_s=buffer[-1].end_s,
                )
            )
            buffer.clear()

    for word in words:
        if buffer:
            gap = word.start_s - buffer[-1].end_s
            spans = word.end_s - buffer[0].start_s
            if gap >= pause_break_seconds or len(buffer) >= max_words or spans > max_seconds:
                flush()
        buffer.append(word)

    flush()
    return cues
