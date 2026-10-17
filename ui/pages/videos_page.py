# ui/pages/videos_page.py
"""Video library: thumbnail grid over the download folder."""
from __future__ import annotations

from ui.pages.media_page import VIDEO_EXT, MediaBrowser

TITLE = "Video Library"


class VideosPage(MediaBrowser):
    title = TITLE
    extensions = VIDEO_EXT
    kind = "video"
    icon_mode = True
    empty_title = "No videos yet"
    empty_hint = "Download a video and it will appear here."

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(settings, parent)
