# AGENTS.md

Python tool that scans media libraries and tags TV shows/movies based on audio dubs. Supports multiple Sonarr/Radarr instances via YAML configuration.

## Quick Start

**System dependency:** `mediainfo` (brew install mediainfo / apt-get install mediainfo)

**Install & Run (Native):**
```bash
git clone https://github.com/STiXzoOR/taggarr.git
cd taggarr
uv sync
uv run taggarr --loop
```

**Run (Docker):**
```bash
docker run -p 8191:8191 ghcr.io/stixzoor/taggarr:latest
```

**Config locations:**
- `./taggarr.yaml` (current directory)
- `$XDG_CONFIG_HOME/taggarr/config.yaml` (Linux/macOS)
- `~/.config/taggarr/config.yaml` (Linux/macOS fallback)
- `%APPDATA%\taggarr\config.yaml` (Windows)

## Tagging Logic

- `dub` - All target languages present in all episodes
- `semi-dub` - Missing some target languages or episodes
- `wrong-dub` - Contains unexpected languages (not original or target)
- No tag - Original language only

## Development

**Setup:**
```bash
uv sync --group test
```

**Run tests:**
```bash
./test.sh
# or
uv run pytest
```

**Current coverage:** 99%+ (262 tests)

## Testing Requirements

**IMPORTANT:** All new features and bug fixes MUST include tests.

- **Target:** 100% code coverage for new code
- **Minimum:** 99% overall coverage must be maintained
- **Approach:** Write tests first (TDD) when possible
- Follow existing test patterns in `tests/unit/`
- Use `pytest-mock` for mocking external services
- Use `responses` for mocking HTTP requests

**Before committing:**
```bash
uv run pytest --cov=taggarr --cov-fail-under=99
```

## Reference

- [Architecture & Data Flow](.claude/docs/architecture.md)
- [Configuration Reference](.claude/docs/configuration.md)
- [Example Config](taggarr.example.yaml)
- [Native Installation](README.md#native-installation)
