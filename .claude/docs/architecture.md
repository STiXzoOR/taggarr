# Architecture

Single-file application (`main.py`) organized into these sections:

1. **Configuration** - Environment variable loading via `python-dotenv`
2. **JSON Storage** (`load_taggarr`/`save_taggarr`) - Persistent scan state in `taggarr.json` at media root
3. **Language Handling** (`get_language_aliases`) - Uses `pycountry` to normalize language codes (ISO 639-1/2)
4. **Audio Analysis** (`analyze_audio`) - Extracts audio track languages via `pymediainfo`
5. **Season Scanning** (`scan_season`) - Analyzes episodes, compares against target languages
6. **Tag Determination** (`determine_tag_and_stats`) - Aggregates season results into final show tag
7. **Sonarr Integration** (`tag_sonarr`, `get_sonarr_id`) - REST API calls to manage Sonarr tags
8. **NFO Updates** (`update_nfo_tag`) - XML manipulation for Kodi/Emby metadata files
9. **Main Loop** (`run_loop`/`main`) - Periodic scanning with change detection

## Data Flow

```
Media files -> pymediainfo -> language detection -> compare with targets ->
determine tag -> update Sonarr API + NFO files -> save state to taggarr.json
```

## Change Detection

Compares `last_modified` timestamps of season folders against saved JSON to skip unchanged shows.
