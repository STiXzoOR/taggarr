---
name: taggarr-patterns
description: Coding patterns extracted from taggarr repository
version: 1.0.0
source: local-git-analysis
analyzed_commits: 107
---

# Taggarr Patterns

## Commit Conventions

This project uses **informal, descriptive commits** (no conventional commit prefixes):

| Pattern                 | Examples                                                                  |
| ----------------------- | ------------------------------------------------------------------------- |
| Feature additions       | "Added persistent tagging", "Added option to tag in genre"                |
| Improvements            | "Improved tagging logic", "Improved folder detection logic"               |
| Fixes                   | "Fixed overlapping tags", "Fixed critical regex episode number filtering" |
| Generic updates         | "Update main.py", "Update README.md"                                      |
| Contributor attribution | "current_mtime fix by lavacano"                                           |

**Note:** ~56% of commits are README updates. Code changes tend to be descriptive but don't follow conventional commit format.

## Code Architecture

```
taggarr/
├── main.py              # Single-file application (all logic here)
├── requirements.txt     # Python dependencies
├── dockerfile           # Container build
├── docker-compose.yml   # Deployment config
├── README.md            # User documentation
└── assets/
    ├── images/          # Screenshots for README
    └── logo/            # Branding assets
```

**Key pattern:** This is a single-file Python application. All functionality lives in `main.py` - there is no module structure.

## Development Workflows

### Adding a New Feature

Based on commit history (e.g., "Added option to tag in genre", "Added persistent tagging"):

1. Modify `main.py` directly
2. Add new environment variable if configurable
3. Update `dockerfile` with new ENV default
4. Update `docker-compose.yml` example
5. Update README.md with documentation

### Bug Fixes

Based on commit history (e.g., "Fixed overlapping tags", "Improved handling of broken nfo files"):

1. Identify issue in `main.py`
2. Fix in place (single file)
3. Commit with descriptive message referencing issue if applicable (e.g., "#3")

### External Contributions

Based on merged PRs:

1. Fork and modify `main.py`
2. Submit PR to main branch
3. Attribution in commit message (e.g., "fix by lavacano")

## File Change Patterns

| Files Changed Together                                               | Frequency | Context                  |
| -------------------------------------------------------------------- | --------- | ------------------------ |
| `main.py` alone                                                      | High      | Bug fixes, logic changes |
| `README.md` alone                                                    | Very High | Documentation updates    |
| `main.py` + `docker-compose.yml`                                     | Medium    | New env vars             |
| `main.py` + `dockerfile` + `docker-compose.yml` + `requirements.txt` | Low       | Major version updates    |

## Code Conventions (from main.py)

### Environment Variables

```python
# Pattern: os.getenv with defaults, lowercase comparison for booleans
QUICK_MODE = os.getenv("QUICK_MODE", "false").lower() == "true"
WRITE_MODE = int(os.getenv("WRITE_MODE", 0))
TARGET_LANGUAGES = [lang.strip().lower() for lang in os.getenv("TARGET_LANGUAGES", "en").split(",")]
```

### Logging

```python
# Pattern: Emoji prefixes for visual log scanning
logger.info(f"📺 Processing show: {show}")
logger.info(f"🏷️✅ Tagged as {tag}")
logger.warning(f"⚠️ Audio analysis failed for {video_path}: {e}")
logger.info(f"🚫 Skipping {show} - no new or updated seasons")
```

### Error Handling

```python
# Pattern: Try/except with warning logs, graceful degradation
try:
    # operation
except Exception as e:
    logger.warning(f"⚠️ Operation failed: {e}")
    return default_value
```

### API Interactions

```python
# Pattern: Requests with explicit headers, rate limiting via sleep
requests.get(f"{SONARR_URL}/api/v3/series", headers={"X-Api-Key": SONARR_API_KEY})
time.sleep(0.5)  # Rate limiting after API calls
```

## Testing Patterns

**No automated tests exist.** Testing is manual:

- Use `--dry-run` flag to preview changes
- Use `--quick` flag to scan subset of data
- Check `taggarr.json` output for correctness
- Verify Sonarr tags via Sonarr UI

## Versioning

Version is tracked in `main.py`:

```python
__version__ = "0.4.21"
```

No tags or releases in git - Docker images are tagged with version on Docker Hub.
