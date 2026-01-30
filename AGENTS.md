# AGENTS.md

Python tool that scans media libraries and tags TV shows based on audio dubs (Sonarr integration + Kodi/Emby NFO files).

**System dependency:** `mediainfo` (brew install mediainfo / apt-get install mediainfo)

**Run:** `python main.py` with required env vars: `SONARR_API_KEY`, `SONARR_URL`, `ROOT_TV_PATH`

**Single-file app:** All code lives in `main.py`

## Tagging Logic

- `dub` - All target languages present in all episodes
- `semi-dub` - Missing some target languages or episodes
- `wrong-dub` - Contains unexpected languages (not original or target)
- No tag - Original language only

## Reference

- [Architecture & Data Flow](.claude/docs/architecture.md)
- [Configuration Reference](.claude/docs/configuration.md)
