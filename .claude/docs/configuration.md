# Configuration Reference

## Environment Variables

| Variable           | Required | Description                                    |
| ------------------ | -------- | ---------------------------------------------- |
| `SONARR_API_KEY`   | Yes      | Sonarr API key                                 |
| `SONARR_URL`       | Yes      | Sonarr base URL                                |
| `ROOT_TV_PATH`     | Yes      | Path to TV media (maps to `/tv` in Docker)     |
| `TARGET_LANGUAGES` | No       | Comma-separated languages (default: `english`) |
| `TARGET_GENRE`     | No       | Filter to specific genre (e.g., `Anime`)       |
| `DRY_RUN`          | No       | Preview mode without writes                    |
| `QUICK_MODE`       | No       | Scan first episode only per season             |
| `WRITE_MODE`       | No       | 0=normal, 1=rewrite all, 2=remove all          |
| `ADD_TAG_TO_GENRE` | No       | Add "Dub" to NFO genre for fully dubbed shows  |

## CLI Options

```bash
python main.py --dry-run           # Preview changes without writing
python main.py --quick             # Scan only first episode per season
python main.py --write-mode 1      # Rewrite all tags and JSON
python main.py --write-mode 2      # Remove all tags and JSON
```
