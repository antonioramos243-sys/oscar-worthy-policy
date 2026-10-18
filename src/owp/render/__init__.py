"""Component 2d: assembling audio, captions, characters and backgrounds.

`HybridRenderer` is the chosen approach: drawn characters over reused generated
background plates. `AssetAnimationRenderer` remains as the fallback for before
the plate library exists, or if generated backgrounds are dropped entirely.

There is no full-generative renderer. The firm $25/week cap (Q2.10) rules out
every Veo tier above Lite, and Lite is exactly where `animation_quality` and
`character_consistency` - two of the four quality dimensions in Q2.6 - score
worst. See docs/requirements-decisions.md.
"""

from owp.render.asset_renderer import AssetAnimationRenderer
from owp.render.base import REEL_HEIGHT, REEL_WIDTH, Renderer
from owp.render.hybrid_renderer import HybridRenderer, RenderPlan
from owp.render.plates import (
    DEFAULT_USD_PER_SECOND,
    PLATE_SECONDS,
    NoPlatesForStyle,
    Plate,
    PlateLibrary,
)

__all__ = [
    "DEFAULT_USD_PER_SECOND",
    "PLATE_SECONDS",
    "REEL_HEIGHT",
    "REEL_WIDTH",
    "AssetAnimationRenderer",
    "HybridRenderer",
    "NoPlatesForStyle",
    "Plate",
    "PlateLibrary",
    "RenderPlan",
    "Renderer",
]
