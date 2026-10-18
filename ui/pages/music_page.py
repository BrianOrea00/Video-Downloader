# ui/pages/music_page.py
"""Music library: metadata list over the download folder."""
from __future__ import annotations

from ui.pages.media_page import AUDIO_EXT, MediaBrowser

TITLE = "Music Library"


class MusicPage(MediaBrowser):
    title = TITLE
    extensions = AUDIO_EXT
    kind = "music"
    icon_mode = False
    empty_title = "No music yet"
    empty_hint = "Download audio and it will appear here."

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(settings, parent)
