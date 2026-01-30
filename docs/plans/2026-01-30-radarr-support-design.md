# Radarr Support Design

Add full Radarr support to taggarr, enabling the same audio dub tagging functionality for movies that currently exists for TV shows via Sonarr.

## Configuration

### New Environment Variables

| Variable              | Required | Description                                       |
| --------------------- | -------- | ------------------------------------------------- |
| `RADARR_URL`          | No\*     | Radarr server URL (e.g., `http://localhost:7878`) |
| `RADARR_API_KEY`      | No\*     | Radarr API key                                    |
| `ROOT_MOVIE_PATH`     | No\*     | Path to movie library root                        |
| `TARGET_GENRE_MOVIES` | No       | Genre filter for movies (e.g., "Anime")           |

\*Required only if you want Radarr support.

### Service Detection Behavior

- If only Sonarr vars are set → process TV shows only (current behavior)
- If only Radarr vars are set → process movies only
- If both are set → process both in the same run

### Shared Settings (Apply to Both)

- `TARGET_LANGUAGES` - Same language targets
- `WRITE_MODE` - Same NFO behavior
- `DRY_RUN`, `QUICK_MODE`, `RUN_INTERVAL_SECONDS` - Apply globally
- `TAG_DUB`, `TAG_WRONG_DUB` - Same tag names

## Movie Processing Logic

### Tagging Rules

| Condition                                         | Tag Applied                  |
| ------------------------------------------------- | ---------------------------- |
| All target languages present                      | `dub`                        |
| Missing target languages                          | No tag (original audio only) |
| Has unexpected languages (not original or target) | `wrong-dub`                  |

Note: No `semi-dub` for movies since there's only one file.

### Processing Flow

1. Fetch all movies from Radarr API
2. Filter by `TARGET_GENRE_MOVIES` (if set)
3. For each movie:
   - Check if movie folder/file mtime changed since last scan
   - If unchanged, skip (use cached result)
   - If changed, scan video file(s) with mediainfo
   - Detect audio languages present
   - Compare against `TARGET_LANGUAGES` + original language
   - Determine appropriate tag
   - Update Radarr via API
   - Update NFO file (if `WRITE_MODE` enabled)
   - Save state to `ROOT_MOVIE_PATH/taggarr.json`

### Original Language Detection

Radarr API provides `originalLanguage` for each movie, used to distinguish expected vs unexpected audio tracks.

## Code Architecture

### New Functions

| Function                | Purpose                                           |
| ----------------------- | ------------------------------------------------- |
| `load_taggarr_movies()` | Load state from `ROOT_MOVIE_PATH/taggarr.json`    |
| `save_taggarr_movies()` | Save movie state                                  |
| `scan_movie()`          | Analyze single movie file, return languages found |
| `determine_movie_tag()` | Decide tag based on languages vs targets          |
| `tag_radarr()`          | Apply/remove tags via Radarr API                  |
| `get_radarr_id()`       | Fetch movie ID from Radarr                        |
| `update_movie_nfo()`    | Update movie NFO file with tag                    |
| `process_movies()`      | Main loop for movie processing                    |

### Modified Functions

| Function     | Change                                                              |
| ------------ | ------------------------------------------------------------------- |
| `run_loop()` | Call both `process_series()` and `process_movies()` based on config |
| `main()`     | Validate Radarr config alongside Sonarr config                      |

### Reused As-Is

- `get_language_aliases()` - Language normalization
- `analyze_audio()` - Mediainfo extraction
- Logging setup, argument parsing

### State File Structure

Separate `taggarr.json` in `ROOT_MOVIE_PATH`:

```json
{
  "version": "0.5.0",
  "movies": {
    "Movie Name (2024)": {
      "tag": "dub",
      "last_modified": 1234567890,
      "languages": ["en", "ja"]
    }
  }
}
```

## Edge Cases & Error Handling

### Multi-File Movies

- Scan the largest video file in each movie folder (the main feature)
- Ignore extras/samples based on naming patterns (`-sample`, `extras/`, `featurettes/`)

### Radarr Connection Failures

- If Radarr unreachable but Sonarr works, log warning and continue with TV only
- Don't fail entire run because one service is down

### Missing ROOT_MOVIE_PATH

- If `RADARR_URL` set but `ROOT_MOVIE_PATH` missing, log error and skip movies
- Clear error message: "RADARR_URL set but ROOT_MOVIE_PATH missing"

### Movies Not Yet Downloaded

- Skip movies where `hasFile: false` in Radarr API response

### Tag Conflicts

- Remove old tags before applying new one
- If movie has `dub` but now qualifies for `wrong-dub`, remove `dub` first
