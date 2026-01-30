# AGENTS.md

Python tool that scans media libraries and tags TV shows based on audio dubs (Sonarr integration + Kodi/Emby NFO files).

**System dependency:** `mediainfo` (brew install mediainfo / apt-get install mediainfo)

**Run:** `python main.py` with required env vars: `SONARR_API_KEY`, `SONARR_URL`, `ROOT_TV_PATH`

**Package structure:** Code organized in `taggarr/` package:

- `config.py` - Environment variables
- `services/` - Sonarr, Radarr, media analysis
- `storage/` - JSON persistence
- `processors/` - TV and movie scanning logic
- `nfo.py` - NFO file handling
- `languages.py` - Language code utilities

## Tagging Logic

- `dub` - All target languages present in all episodes
- `semi-dub` - Missing some target languages or episodes
- `wrong-dub` - Contains unexpected languages (not original or target)
- No tag - Original language only

## Reference

- [Architecture & Data Flow](.claude/docs/architecture.md)
- [Configuration Reference](.claude/docs/configuration.md)
