"""Media file analysis using pymediainfo."""

import logging
from pymediainfo import MediaInfo

logger = logging.getLogger("taggarr")


VIDEO_EXTENSIONS = frozenset({'.mkv', '.mp4', '.m4v', '.avi', '.webm', '.mov', '.mxf'})

_COMMENTARY_KEYWORDS = {"commentary", "director", "isolated"}


def analyze_audio(video_path):
    """Extract audio language codes from a video file.

    Returns list of language codes found in audio tracks.
    Uses "__fallback_original__" when the first audio track has no language
    and doesn't appear to be a commentary/special track.
    """
    try:
        media_info = MediaInfo.parse(video_path)
        langs = set()
        fallback_detected = False
        audio_index = 0

        for track in media_info.tracks:
            if track.track_type == "Audio":
                lang = (track.language or "").strip().lower()
                title = (track.title or "").strip().lower()

                if lang:
                    langs.add(lang)
                elif audio_index == 0 and not _is_commentary(title):
                    langs.add("__fallback_original__")
                    fallback_detected = True

                audio_index += 1

        logger.debug(f"Analyzed {video_path}, found audio languages: {sorted(langs)}")
        if fallback_detected:
            logger.debug(f"Fallback language detection used in {video_path}")
        return list(langs)
    except (OSError, RuntimeError, ValueError) as e:
        logger.warning(f"Audio analysis failed for {video_path}: {e}")
        return []


def _is_commentary(title):
    """Check if a track title indicates commentary or special audio."""
    return any(kw in title for kw in _COMMENTARY_KEYWORDS)
