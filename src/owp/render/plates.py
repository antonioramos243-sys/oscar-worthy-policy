"""The reusable background plate library.

This is what makes the hybrid approach fit a firm $25/week cap (Q2.10).

Generated video is billed per second, so generating backgrounds per video makes
that a permanent recurring cost - about $12/week at four 60-second videos, half
the cap, forever. Generating them once into a reusable library turns it into a
one-off: roughly $12 for 30 eight-second plates, after which the steady-state
cost of a video is TTS plus one LLM call, around $0.16.

Plates carry no characters. Characters are drawn assets composited on top (see
`owp.cast`), which is what keeps them consistent across videos (Q2.4) - the one
thing generative video is worst at.

The manifest is checked in, so the library is reproducible and its cost is
visible. Plate *generation* is stubbed; everything about selecting, budgeting
and auditing the library is implemented.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from owp.budget import Charge, remaining
from owp.models import VisualStyle

PLATES_FILE = Path(__file__).with_name("plates.json")

#: Veo-class models generate in short clips; plates are sized to one clip.
PLATE_SECONDS = 8.0
#: Veo 3.1 Lite 720p. Verify against Google's pricing page before relying on it.
DEFAULT_USD_PER_SECOND = 0.05


class Plate(BaseModel):
    """One reusable background clip."""

    id: str
    style: VisualStyle
    prompt: str = Field(description="Generation prompt; kept so a plate can be regenerated.")
    seconds: float = PLATE_SECONDS
    path: str | None = Field(default=None, description="Set once generated; None means pending.")
    cost_usd: float | None = Field(default=None, description="What this plate actually cost.")

    @property
    def generated(self) -> bool:
        return self.path is not None


class NoPlatesForStyle(LookupError):
    """Raised when a style has no generated plates to draw on."""


class PlateLibrary:
    """Selects, budgets and audits the plate manifest."""

    def __init__(self, plates: list[Plate]) -> None:
        self._plates = plates

    @classmethod
    def load(cls, path: Path = PLATES_FILE) -> PlateLibrary:
        return cls([Plate.model_validate(entry) for entry in json.loads(path.read_text())])

    @property
    def plates(self) -> list[Plate]:
        return list(self._plates)

    def generated(self, style: VisualStyle | None = None) -> list[Plate]:
        """Plates that exist on disk, optionally filtered by style."""
        out = [p for p in self._plates if p.generated]
        if style is not None:
            out = [p for p in out if p.style is style]
        return out

    def pending(self) -> list[Plate]:
        """Plates in the manifest that have not been generated yet."""
        return [p for p in self._plates if not p.generated]

    def cover(self, style: VisualStyle, seconds: float) -> list[Plate]:
        """Pick enough plates of `style` to cover `seconds` of video.

        Plates are cycled in manifest order, so the same script always gets the
        same backgrounds - repeatable renders, and a diff that means something
        when a video is regenerated.

        Raises:
            NoPlatesForStyle: if the style has no generated plates.
            ValueError: if `seconds` is negative.
        """
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        available = self.generated(style)
        if not available:
            raise NoPlatesForStyle(
                f"no generated plates for style {style.value!r}; "
                f"{len(self.pending())} plates are pending generation"
            )

        chosen: list[Plate] = []
        covered = 0.0
        index = 0
        while covered < seconds:
            plate = available[index % len(available)]
            chosen.append(plate)
            covered += plate.seconds
            index += 1
        return chosen

    def generation_cost(
        self, plates: list[Plate], *, usd_per_second: float = DEFAULT_USD_PER_SECOND
    ) -> float:
        """What generating `plates` would cost."""
        return sum(p.seconds for p in plates) * usd_per_second

    def affordable_batch(
        self,
        charges: list[Charge],
        now: object,
        *,
        usd_per_second: float = DEFAULT_USD_PER_SECOND,
        reserve_usd: float = 0.0,
    ) -> list[Plate]:
        """The longest prefix of pending plates that fits this week's budget.

        Building the library is deliberately incremental: a batch that would
        breach the cap is truncated rather than rejected, so the library grows
        every week instead of waiting for a week with room for all of it.

        Args:
            charges: Spend already booked.
            now: The moment whose ISO week is being budgeted.
            usd_per_second: Generation rate.
            reserve_usd: Budget to hold back for the week's videos.

        Returns:
            Plates to generate now, in manifest order. May be empty.
        """
        budget = max(0.0, remaining(charges, now) - reserve_usd)  # type: ignore[arg-type]
        per_plate = PLATE_SECONDS * usd_per_second
        batch: list[Plate] = []
        for plate in self.pending():
            cost = plate.seconds * usd_per_second
            if sum(p.seconds for p in batch) * usd_per_second + cost > budget:
                break
            batch.append(plate)
        if not batch and per_plate > budget:
            return []
        return batch
