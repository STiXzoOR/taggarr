"""Media file analysis using pymediainfo."""

import logging
from pymediainfo import MediaInfo

logger = logging.getLogger("taggarr")


def analyze_audio(video_path):
    """Extract audio language codes from a video file.

    Returns list of language codes found in audio tracks.
    Uses "__fallback_original__" when track has no language but appears to be main audio.
    """
    try:
        media_info = MediaInfo.parse(video_path)
        langs = set()
        fallback_detected = False

        for track in media_info.tracks:
            if track.track_type == "Audio":
                lang = (track.language or "").strip().lower()
                title = (track.title or "").strip().lower()

                if lang:
                    langs.add(lang)
                elif "track 1" in title or "audio 1" in title or title == "":
                    langs.add("__fallback_original__")
                    fallback_detected = True

        logger.debug(f"Analyzed {video_path}, found audio languages: {sorted(langs)}")
        if fallback_detected:
            logger.debug(f"Fallback language detection used in {video_path}")
        return list(langs)
    except Exception as e:
        logger.warning(f"Audio analysis failed for {video_path}: {e}")
        return []
