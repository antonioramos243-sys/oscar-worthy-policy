"""Component 2d: assembling audio, captions and visuals into a video."""

from owp.render.base import Renderer
from owp.render.ffmpeg_renderer import FfmpegRenderer

__all__ = ["Renderer", "FfmpegRenderer"]
