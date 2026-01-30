# AGENTS.md

Python tool that scans media libraries and tags TV shows/movies based on audio dubs. Supports multiple Sonarr/Radarr instances via YAML configuration.

**System dependency:** `mediainfo` (brew install mediainfo / apt-get install mediainfo)

**Run:** `python main.py` (requires `taggarr.yaml` config file)

## Tagging Logic

- `dub` - All target languages present in all episodes
- `semi-dub` - Missing some target languages or episodes
- `wrong-dub` - Contains unexpected languages (not original or target)
- No tag - Original language only

## Reference

- [Architecture & Data Flow](.claude/docs/architecture.md)
- [Configuration Reference](.claude/docs/configuration.md)
- [Example Config](taggarr.example.yaml)
