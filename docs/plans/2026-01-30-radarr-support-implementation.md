# Radarr Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add full Radarr support to taggarr, enabling audio dub tagging for movies alongside existing Sonarr/TV functionality.

**Architecture:** Extend main.py with parallel movie-specific functions that mirror the existing TV/Sonarr patterns. Auto-detect which services to process based on configured environment variables.

**Tech Stack:** Python, requests (Radarr API), pymediainfo (audio analysis), xml.etree (NFO files)

---

## Task 1: Add Radarr Configuration Variables

**Files:**
- Modify: `main.py:21-38` (CONFIG section)

**Step 1: Add new environment variables after existing config**

Add these lines after `ADD_TAG_TO_GENRE` (line 38):

```python
# Radarr config
RADARR_API_KEY = os.getenv("RADARR_API_KEY")
RADARR_URL = os.getenv("RADARR_URL")
ROOT_MOVIE_PATH = os.getenv("ROOT_MOVIE_PATH")
TARGET_GENRE_MOVIES = os.getenv("TARGET_GENRE_MOVIES")
TAGGARR_MOVIES_JSON_PATH = os.path.join(ROOT_MOVIE_PATH, "taggarr.json") if ROOT_MOVIE_PATH else None
```

**Step 2: Add service detection helper**

Add after the new config variables:

```python
# Service detection
SONARR_ENABLED = all([SONARR_API_KEY, SONARR_URL, ROOT_TV_PATH])
RADARR_ENABLED = all([RADARR_API_KEY, RADARR_URL, ROOT_MOVIE_PATH])
```

**Step 3: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add Radarr configuration variables"
```

---

## Task 2: Add Movie State Management Functions

**Files:**
- Modify: `main.py` (after JSON STORAGE section, around line 123)

**Step 1: Add load_taggarr_movies function**

Add after `save_taggarr()`:

```python
# === MOVIE JSON STORAGE ===
def load_taggarr_movies():
    if not TAGGARR_MOVIES_JSON_PATH:
        return {"movies": {}}
    if os.path.exists(TAGGARR_MOVIES_JSON_PATH):
        try:
            logger.info(f"📍 taggarr.json (movies) found at {TAGGARR_MOVIES_JSON_PATH}")
            with open(TAGGARR_MOVIES_JSON_PATH, 'r') as f:
                data = json.load(f)
                logger.debug(f"✅ Loaded taggarr.json (movies) with {len(data.get('movies', {}))} entries.")
                return data
        except Exception as e:
            logger.warning(f"⚠️ taggarr.json (movies) is corrupted: {e}")
            backup_path = TAGGARR_MOVIES_JSON_PATH + ".bak"
            os.rename(TAGGARR_MOVIES_JSON_PATH, backup_path)
            logger.warning(f"❌ Corrupted file moved to: {backup_path}")

    logger.info("❌ No taggarr.json (movies) found — starting fresh.")
    return {"movies": {}}
```

**Step 2: Add save_taggarr_movies function**

Add after `load_taggarr_movies()`:

```python
def save_taggarr_movies(data):
    if not TAGGARR_MOVIES_JSON_PATH:
        return
    try:
        data["version"] = __version__
        ordered_data = {"version": data["version"]}
        for k, v in data.items():
            if k != "version":
                ordered_data[k] = v
        raw_json = json.dumps(ordered_data, indent=2, ensure_ascii=False)

        # compact language lists
        compact_json = re.sub(
            r'("languages": )\[\s*\n\s*((?:\s*"[^"]+",?\s*\n?)+)(\s*\])',
            lambda m: '{}[{}]'.format(
                m.group(1),
                ', '.join(f'"{x}"' for x in re.findall(r'"([^"]+)"', m.group(2)))
            ),
            raw_json
        )

        with open(TAGGARR_MOVIES_JSON_PATH, 'w') as f:
            f.write(compact_json)
        logger.debug("✅ taggarr.json (movies) saved successfully.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save taggarr.json (movies): {e}")
```

**Step 3: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add movie state management functions"
```

---

## Task 3: Add Radarr API Functions

**Files:**
- Modify: `main.py` (after Sonarr section, around line 370)

**Step 1: Add get_radarr_movies function**

Add after `get_sonarr_series()`:

```python
# === RADARR ===
def get_radarr_movies():
    """Fetch all movies from Radarr API."""
    try:
        resp = requests.get(f"{RADARR_URL}/api/v3/movie", headers={"X-Api-Key": RADARR_API_KEY})
        return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Radarr movies: {e}")
        return []


def get_radarr_movie_by_path(path):
    """Find a specific movie by its folder path."""
    try:
        resp = requests.get(f"{RADARR_URL}/api/v3/movie", headers={"X-Api-Key": RADARR_API_KEY})
        for m in resp.json():
            if os.path.basename(m['path']) == os.path.basename(path):
                return m
    except Exception as e:
        logger.warning(f"Radarr lookup failed: {e}")
    return None
```

**Step 2: Add tag_radarr function**

```python
def tag_radarr(movie_id, tag, remove=False, dry_run=False):
    """Add or remove a tag from a movie in Radarr."""
    if dry_run:
        logger.info(f"[Dry Run] Would {'remove' if remove else 'add'} tag '{tag}' for movie ID {movie_id}")
        return
    try:
        tag_id = None
        r = requests.get(f"{RADARR_URL}/api/v3/tag", headers={"X-Api-Key": RADARR_API_KEY})
        for t in r.json():
            if t["label"].lower() == tag.lower():
                tag_id = t["id"]
        if tag_id is None and not remove:
            r = requests.post(f"{RADARR_URL}/api/v3/tag", headers={"X-Api-Key": RADARR_API_KEY}, json={"label": tag})
            tag_id = r.json()["id"]
            logger.debug(f"Created new Radarr tag '{tag}' with ID {tag_id}")

        m_url = f"{RADARR_URL}/api/v3/movie/{movie_id}"
        m_data = requests.get(m_url, headers={"X-Api-Key": RADARR_API_KEY}).json()
        if remove and tag_id in m_data["tags"]:
            m_data["tags"].remove(tag_id)
            logger.debug(f"Removing Radarr tag ID {tag_id} from movie {movie_id}")
        elif not remove and tag_id not in m_data["tags"]:
            m_data["tags"].append(tag_id)
            logger.debug(f"Adding Radarr tag ID {tag_id} to movie {movie_id}")
        requests.put(m_url, headers={"X-Api-Key": RADARR_API_KEY}, json=m_data)
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Failed to tag Radarr: {e}")
```

**Step 3: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add Radarr API functions"
```

---

## Task 4: Add Movie Scanning Function

**Files:**
- Modify: `main.py` (after MEDIA TOOLS section)

**Step 1: Add scan_movie function**

Add after `analyze_audio()`:

```python
def scan_movie(movie_path, movie_meta):
    """
    Scan a movie folder and return language analysis.
    Finds the largest video file (main feature) and analyzes its audio tracks.
    """
    video_exts = ['.mkv', '.mp4', '.m4v', '.avi', '.webm', '.mov', '.mxf']
    ignore_patterns = ['-sample', 'sample.', 'extras', 'featurettes', 'behind the scenes', 'deleted scenes']

    # Find all video files in movie folder
    video_files = []
    for root, dirs, files in os.walk(movie_path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if not any(p in d.lower() for p in ignore_patterns)]
        for f in files:
            if os.path.splitext(f)[1].lower() in video_exts:
                # Skip sample files
                if any(p in f.lower() for p in ignore_patterns):
                    continue
                full_path = os.path.join(root, f)
                video_files.append((full_path, os.path.getsize(full_path)))

    if not video_files:
        logger.warning(f"No video files found in {movie_path}")
        return None

    # Get the largest file (main feature)
    main_file = max(video_files, key=lambda x: x[1])[0]
    logger.debug(f"Scanning main movie file: {os.path.basename(main_file)}")

    langs = analyze_audio(main_file)

    # Get original language from Radarr metadata
    original_lang = movie_meta.get("originalLanguage", {})
    if isinstance(original_lang, dict):
        original_lang_name = original_lang.get("name", "").lower()
    else:
        original_lang_name = str(original_lang).lower()

    ORIGINAL_LANGUAGE_CODES = get_language_aliases(original_lang_name)

    return {
        "file": os.path.basename(main_file),
        "languages": langs,
        "original_language": original_lang_name,
        "original_codes": ORIGINAL_LANGUAGE_CODES,
        "last_modified": os.path.getmtime(main_file)
    }
```

**Step 2: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add movie scanning function"
```

---

## Task 5: Add Movie Tag Determination Function

**Files:**
- Modify: `main.py` (after scan_movie)

**Step 1: Add determine_movie_tag function**

```python
def determine_movie_tag(scan_result):
    """
    Determine the appropriate tag for a movie based on audio analysis.
    Returns: TAG_DUB, TAG_WRONG_DUB, or None (original only)
    """
    if scan_result is None:
        return None

    langs = set(scan_result["languages"])
    original_codes = scan_result["original_codes"]

    # Handle fallback audio track
    if "__fallback_original__" in langs:
        logger.info("⚠️🔊 Audio track not labelled — assuming original language")
        return None

    # Build language aliases for detected tracks
    langs_aliases = set()
    for l in langs:
        langs_aliases.update(get_language_aliases(l))

    # Check for target languages
    has_all_targets = True
    for target in TARGET_LANGUAGES:
        target_aliases = get_language_aliases(target)
        if not langs_aliases.intersection(target_aliases):
            has_all_targets = False
            break

    # Check for unexpected languages
    unexpected = []
    for l in langs:
        if l not in LANGUAGE_CODES and l not in original_codes:
            unexpected.append(l)

    if unexpected:
        return TAG_WRONG_DUB
    elif has_all_targets:
        return TAG_DUB

    return None  # Original only
```

**Step 2: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add movie tag determination function"
```

---

## Task 6: Add Movie NFO Update Function

**Files:**
- Modify: `main.py` (after update_nfo_tag)

**Step 1: Add update_movie_nfo function**

```python
def update_movie_nfo(nfo_path, tag_value, dry_run=False):
    """
    Updates <tag> in a movie NFO file.
    Movie NFOs use <movie> as root element instead of <tvshow>.
    """
    try:
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        # Tags to manage
        known_tags = {"dub", "semi-dub", "wrong-dub"}

        # Remove any existing known tags
        old_tags = root.findall("tag")
        for t in old_tags:
            if t.text and t.text.strip().lower() in known_tags:
                root.remove(t)

        # Add new tag as first tag
        new_tag = ET.Element("tag")
        new_tag.text = tag_value
        insert_index = 0

        # Insert before existing <tag> if any
        for i, elem in enumerate(root):
            if elem.tag == "tag":
                insert_index = i
                break
        root.insert(insert_index, new_tag)

        if not dry_run:
            ET.indent(tree, space="  ")
            tree.write(nfo_path, encoding="utf-8", xml_declaration=False)
            logger.info(f"🏷️ Updated <tag>{tag_value}</tag> in movie NFO: {os.path.basename(nfo_path)}")
        else:
            logger.info(f"[Dry Run] Would update <tag>{tag_value}</tag> in movie NFO: {os.path.basename(nfo_path)}")
    except Exception as e:
        logger.warning(f"❌ Failed to update <tag> in movie NFO: {e}")
```

**Step 2: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add movie NFO update function"
```

---

## Task 7: Add Main Movie Processing Function

**Files:**
- Modify: `main.py` (before run_loop)

**Step 1: Add process_movies function**

```python
def process_movies(opts, taggarr_movies):
    """Process all movies in the Radarr library."""
    quick_mode = opts.quick or QUICK_MODE
    dry_run = opts.dry_run or DRY_RUN
    write_mode = opts.write_mode or WRITE_MODE

    logger.info("🎬 Starting movie scan...")

    for movie_folder in sorted(os.listdir(ROOT_MOVIE_PATH)):
        movie_path = os.path.join(ROOT_MOVIE_PATH, movie_folder)
        movie_path = os.path.abspath(movie_path)
        if not os.path.isdir(movie_path):
            continue

        # Skip non-movie folders (like taggarr.json)
        if movie_folder.startswith('.') or movie_folder.endswith('.json'):
            continue

        saved_movie = taggarr_movies["movies"].get(movie_path, {})
        saved_mtime = saved_movie.get("last_modified", 0)

        # Check if movie folder has changed
        try:
            current_mtime = max(
                os.path.getmtime(os.path.join(root, f))
                for root, dirs, files in os.walk(movie_path)
                for f in files if f.endswith(('.mkv', '.mp4', '.m4v', '.avi'))
            )
        except ValueError:
            current_mtime = 0

        is_new_movie = movie_path not in taggarr_movies["movies"]
        changed = current_mtime > saved_mtime

        if write_mode == 0 and not (changed or is_new_movie):
            logger.info(f"🚫 Skipping {movie_folder} - no changes")
            continue

        # Get movie metadata from Radarr
        movie_meta = get_radarr_movie_by_path(movie_path)
        if not movie_meta:
            logger.warning(f"No Radarr metadata for {movie_folder}")
            continue

        # Skip movies not yet downloaded
        if not movie_meta.get("hasFile", False):
            logger.debug(f"Skipping {movie_folder} - not yet downloaded")
            continue

        # Genre filtering
        if TARGET_GENRE_MOVIES:
            genres = [g.lower() for g in movie_meta.get("genres", [])]
            if TARGET_GENRE_MOVIES.lower() not in genres:
                logger.info(f"🚫⛔ Skipping {movie_folder}: genre mismatch")
                continue

        logger.info(f"🎬 Processing movie: {movie_folder}")

        movie_id = movie_meta.get("id")
        if not movie_id:
            logger.warning(f"No Radarr ID for {movie_folder}")
            continue

        if write_mode == 2:
            logger.info(f"Removing tags for {movie_folder}")
            for tag in [TAG_DUB, TAG_WRONG_DUB]:
                tag_radarr(movie_id, tag, remove=True, dry_run=dry_run)
            if movie_path in taggarr_movies["movies"]:
                del taggarr_movies["movies"][movie_path]
            continue

        # Scan movie
        scan_result = scan_movie(movie_path, movie_meta)
        if scan_result is None:
            continue

        # Determine tag
        tag = determine_movie_tag(scan_result)
        logger.info(f"🏷️✅ Tagged as {tag if tag else 'no tag (original)'}")

        # Apply tags to Radarr
        if tag:
            tag_radarr(movie_id, tag, dry_run=dry_run)
            if tag == TAG_WRONG_DUB:
                tag_radarr(movie_id, TAG_DUB, remove=True, dry_run=dry_run)
            elif tag == TAG_DUB:
                tag_radarr(movie_id, TAG_WRONG_DUB, remove=True, dry_run=dry_run)
        else:
            # Remove all tags if original only
            for t in [TAG_DUB, TAG_WRONG_DUB]:
                tag_radarr(movie_id, t, remove=True, dry_run=dry_run)

        # Update NFO if enabled
        nfo_patterns = ['movie.nfo', f"{movie_folder}.nfo"]
        nfo_path = None
        for pattern in nfo_patterns:
            potential_nfo = os.path.join(movie_path, pattern)
            if os.path.exists(potential_nfo):
                nfo_path = potential_nfo
                break

        if nfo_path and tag in [TAG_DUB, TAG_WRONG_DUB]:
            update_movie_nfo(nfo_path, tag, dry_run=dry_run)

        # Save state
        taggarr_movies["movies"][movie_path] = {
            "display_name": movie_folder,
            "tag": tag or "none",
            "last_scan": datetime.utcnow().isoformat() + "Z",
            "original_language": scan_result["original_language"],
            "languages": scan_result["languages"],
            "last_modified": current_mtime
        }

    return taggarr_movies
```

**Step 2: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main movie processing function"
```

---

## Task 8: Integrate Movie Processing into Main Loop

**Files:**
- Modify: `main.py:422-618` (main function)

**Step 1: Refactor main() to process both services**

Replace the `main()` function with updated version that:
1. Checks which services are enabled
2. Processes TV shows if Sonarr is enabled
3. Processes movies if Radarr is enabled

Add at the start of `main()` after mode logging:

```python
    # Process TV shows (Sonarr)
    if SONARR_ENABLED:
        logger.info("📺 Sonarr enabled - processing TV shows...")
        # ... existing TV processing code ...
    else:
        logger.info("📺 Sonarr not configured - skipping TV shows")

    # Process movies (Radarr)
    if RADARR_ENABLED:
        logger.info("🎬 Radarr enabled - processing movies...")
        taggarr_movies = load_taggarr_movies()
        taggarr_movies = process_movies(opts, taggarr_movies)
        save_taggarr_movies(taggarr_movies)
    else:
        logger.info("🎬 Radarr not configured - skipping movies")
```

**Step 2: Wrap existing TV processing in SONARR_ENABLED check**

The existing loop `for show in sorted(os.listdir(ROOT_TV_PATH)):` should only run if `SONARR_ENABLED` is True.

**Step 3: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (success)

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: integrate movie processing into main loop"
```

---

## Task 9: Update Version and Documentation

**Files:**
- Modify: `main.py:3` (version)
- Modify: `CLAUDE.md`
- Modify: `.claude/docs/configuration.md`

**Step 1: Bump version**

Change line 3 from:
```python
__version__ = "0.4.21"
```
To:
```python
__version__ = "0.5.0"
```

**Step 2: Update CLAUDE.md**

Add Radarr to the description and env vars section.

**Step 3: Update configuration.md**

Add new Radarr environment variables to the reference.

**Step 4: Commit**

```bash
git add main.py CLAUDE.md .claude/docs/configuration.md
git commit -m "docs: update version and add Radarr configuration docs"
```

---

## Task 10: Manual Integration Test

**Files:** None (testing only)

**Step 1: Create test .env file**

```bash
cat > .env.test << 'EOF'
SONARR_API_KEY=your_sonarr_key
SONARR_URL=http://localhost:8989
ROOT_TV_PATH=/path/to/tv
RADARR_API_KEY=your_radarr_key
RADARR_URL=http://localhost:7878
ROOT_MOVIE_PATH=/path/to/movies
TARGET_LANGUAGES=en
DRY_RUN=true
EOF
```

**Step 2: Test with dry-run mode**

Run: `python main.py --dry-run`

Expected output should show:
- Both Sonarr and Radarr being processed
- Movies being scanned
- Tags being determined (but not applied due to dry-run)

**Step 3: Test Radarr-only mode**

Comment out Sonarr vars in .env.test and run again. Should only process movies.

**Step 4: Test Sonarr-only mode (backwards compatibility)**

Comment out Radarr vars in .env.test and run again. Should behave exactly like before.

---

## Summary

After completing all tasks, taggarr will:
1. Auto-detect which services are configured (Sonarr, Radarr, or both)
2. Process TV shows via Sonarr API (existing behavior)
3. Process movies via Radarr API (new behavior)
4. Apply consistent tagging (`dub`, `wrong-dub`) across both
5. Maintain separate state files per library
6. Support independent genre filtering for movies
