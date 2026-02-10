# Taggarr v1.0 Release Roadmap

**Date:** 2026-02-10
**Status:** Brainstorm complete
**Context:** Pre-release prep for public open-source, large library (2000+ items), no rush

---

## What We're Building

A bottom-up roadmap to take Taggarr from v0.8.0 (functional but rough) to a v1.0 public release. The work is sequenced in 5 phases: stability fixes, test coverage, gap completion, performance, and release features.

## Why This Approach

- **Bottom-up sequencing** -- Fix foundations before building on them. Every test written validates correct behavior, not buggy behavior.
- **No rush timeline** -- Quality over speed. The codebase is ~6,500 lines Python + ~33 React components -- small enough to get right.
- **Public open-source audience** -- Needs hardening, docs, changelog, polished UX. Can't ship with permissive CORS (`allow_origins=["*"]` in `api/app.py`).
- **Large library (2000+ items)** -- Performance (parallel scanning, pagination) is a real need, not premature optimization.

---

## Phase 1: Stability Fixes

Fix the 6 high-priority bugs that would embarrass a public release.

### 1.1 Non-atomic tag operations

- **Problem:** Tag add/remove across 3 API calls. If middle call fails, tags are inconsistent. See `_apply_tags()` in `processors/tv.py` (lines 240-257) and the equivalent block in `processors/movies.py` (lines 99-107). Each tag operation makes separate add/remove calls with a 0.5s sleep between them in the underlying client methods.
- **Decision:** Collect-then-apply pattern. Calculate ALL tag changes first (which tags to add, which to remove), then apply in a single batch per media item. Fewer API calls, naturally atomic.
- **Files:** `processors/tv.py`, `processors/movies.py`, `services/sonarr.py` (`_modify_series_tags`), `services/radarr.py` (`_modify_movie_tags`)

### 1.2 Broad exception catching

- **Problem:** `except Exception` everywhere masks real problems (missing mediainfo, permission errors). Confirmed in `services/media.py` (line 36), `services/sonarr.py` (lines 31, 81, 112), `services/radarr.py` (lines 29, 74, 106), and `api/websocket.py` (line 39).
- **Decision:** Replace with specific exceptions. Network errors (retry), config errors (fail fast), mediainfo errors (log clearly), permission errors (surface to user).
- **Files:** `services/media.py`, `services/sonarr.py`, `services/radarr.py`, `api/websocket.py`

### 1.3 No retry logic on API calls

- **Problem:** Transient Sonarr/Radarr network failures cause silent scan failures. No `requests` calls currently specify a timeout except `refresh_series` (10s timeout in `services/sonarr.py` line 65). Radarr client has no timeouts at all.
- **Decision:** Simple retry -- 3 attempts with exponential backoff. Use `tenacity` or `urllib3.util.retry`. Also add explicit timeouts (30s) on all `requests` calls.
- **Files:** `services/sonarr.py`, `services/radarr.py`

### 1.4 Path matching by basename only

- **Problem:** `os.path.basename(s['path']) == os.path.basename(path)` -- two folders named "Breaking Bad" in different paths would collide. Present in both `services/sonarr.py` (`get_series_by_path`, line 29) and `services/radarr.py` (`get_movie_by_path`, line 41).
- **Decision:** Match by full path from Sonarr/Radarr API response. Fall back to basename only if full path match fails (backwards compat).
- **Files:** `services/sonarr.py`, `services/radarr.py`

### 1.5 Fragile audio fallback detection

- **Problem:** Track title heuristic (`"track 1" in title or "audio 1" in title or title == ""`) can misidentify commentary tracks as original audio. See `services/media.py` line 27.
- **Decision:** Use track position (first audio track = default) and codec metadata instead of title string matching. Only fall back to title heuristic as last resort.
- **Files:** `services/media.py`

### 1.6 JSON state grows unbounded

- **Problem:** Deleted media entries never cleaned up from `taggarr.json`. The `storage/json_store.py` `save()` function writes whatever is passed to it with no pruning. Neither `processors/tv.py` nor `processors/movies.py` remove entries for shows/movies that no longer exist on disk (only write_mode=2 deletes entries explicitly).
- **Decision:** Add a cleanup step at the end of each scan cycle. Compare entries against current folder listing, remove any that no longer exist on disk.
- **Files:** `storage/json_store.py`, `processors/tv.py`, `processors/movies.py`

---

## Phase 2: Test Coverage (97.6% -> 99%)

Coverage is currently at 97.64% with 642 tests (693 including integration). The remaining gap to hit the enforced 99% minimum is small but specific. Priority order based on actual coverage gaps:

### Priority 1: Lowest coverage files

- `workers/providers/base.py` (75% -- missing lines 22, 34)
- `api/websocket.py` (78% -- missing lines 85-101, the live WebSocket loop)
- `api/routes/backups.py` (84% -- missing lines 80-81, 93-99, 236-237, 245-256)
- `workers/providers/__init__.py` (87% -- missing line 34)
- `workers/handlers/base.py` (89% -- missing line 30)

### Priority 2: 90-96% coverage files

- `api/routes/stats.py` (92%)
- `workers/notification_dispatcher.py` (92%)
- `workers/providers/pushover.py` (93%)
- `api/routes/notifications.py` (95%)
- `api/routes/instances.py` (96%)
- `workers/handlers/backup.py` (96%)

### Priority 3: 97-98% coverage files

- `api/app.py` (97%)
- `workers/providers/email.py` (97%)
- `workers/providers/telegram.py` (97%)
- `nfo.py` (98%)

### Testing Strategy

- Write tests for Phase 1 bug fixes as they land (TDD where practical)
- Use existing patterns: `responses` for HTTP mocking, `pytest-mock` for general mocking
- Mock external services (Sonarr/Radarr/notification providers), test business logic
- Estimated: ~30-50 new tests to close the remaining 1.4% gap

---

## Phase 3: Complete the Gaps

Finish incomplete work to make Taggarr release-ready.

### 3.1 Log REST endpoints

- Implement file listing and download in `api/routes/logs.py` (currently stubs returning empty lists / 501 Not Implemented)
- WebSocket streaming already works via `api/websocket.py` (`websocket_logs` function)

### 3.2 Security hardening

- Rate limiting on auth endpoints (e.g., `slowapi` or custom middleware)
- CSRF protection for session-based auth (currently using cookie-based sessions in `api/deps.py`)
- Restrict CORS to configured origins (currently `allow_origins=["*"]` in `api/app.py` line 45)
- Secure cookie flags (`secure=True`, `httponly=True`, `samesite=strict`) for HTTPS
- Input validation on all API endpoints (some routes already use Pydantic models with validation, e.g., `api/routes/notifications.py`)

### 3.3 Frontend CI

- Add `npm run build && npm run typecheck` step to GitHub Actions (`.github/workflows/test.yml`)
- Current CI only runs Python tests across Python 3.9-3.13 -- no frontend validation
- Run alongside Python tests (parallel jobs)

### 3.4 Release documentation

- Create CHANGELOG.md (no CHANGELOG currently exists in the project root)
- Review and polish README.md for public audience
- Verify example config (`taggarr.example.yaml`) covers all options

### 3.5 Medium-priority bug fixes

- Add timeouts on all API calls (currently only `refresh_series` in `services/sonarr.py` has a 10s timeout; no other `requests` calls specify timeouts)
- Fix NFO update running even when API call fails (gate on success) -- in `processors/tv.py` the NFO update at line 82 runs regardless of whether `_apply_tags` succeeded
- Fix timezone mismatch (`datetime.utcnow()` used in `processors/tv.py` line 283 and `processors/movies.py` line 118 vs `os.path.getmtime()` which returns local time)
- Fix `dockerfile` casing (file is lowercase `dockerfile` at project root; convention is `Dockerfile` for Docker tooling compatibility)
- Add semi-dub tag support for movies (consistency with TV logic -- `processors/movies.py` only applies `dub` or `wrong-dub`, never `semi-dub`)
- Improve episode regex to handle more formats (current regex in `processors/tv.py` line 167 only matches `E\d{2}` pattern -- misses `s01e01`, `01.mkv`, multi-episode)

---

## Phase 4: Performance

Critical for the 2000+ item library.

### 4.1 Parallel scanning

- **Decision:** `concurrent.futures.ThreadPoolExecutor`
- Parallelize at instance level (scan multiple instances simultaneously) -- currently sequential in `taggarr/__init__.py` `run()` loop
- Optionally parallelize within an instance (scan multiple shows/movies concurrently)
- Configurable thread pool size (default: 4)
- No async rewrite needed -- simple, compatible with existing `requests`-based code
- Note: the `ScanHandler` in `workers/handlers/scan.py` is already async but calls synchronous code; ThreadPoolExecutor wrapping is natural here

### 4.2 Pagination for Sonarr/Radarr APIs

- Fetch series/movies in pages instead of loading all at once
- Currently `get_series_by_path()` in `services/sonarr.py` fetches the entire series list on every call to find one show -- this is O(n) per show lookup, O(n^2) overall for n shows
- Same pattern in `services/radarr.py` (`get_movie_by_path` and `get_movies`)
- Consider caching the full list per scan cycle rather than per-item fetching, or using Sonarr/Radarr lookup-by-path endpoints if available

### 4.3 Resume/checkpoint scanning

- Save scan progress so a crashed/interrupted scan can resume
- Store last-processed index in database (the `Command` model in `db/models.py` with its `status` field could be extended for this)
- Important for large libraries where full scans take hours

---

## Phase 5: Release Features

Polish and differentiation for public release.

### 5.1 Scan progress indicator

- Real-time progress in the UI (current instance, current item, X/Y complete)
- WebSocket-based updates (infrastructure already exists in `api/websocket.py`)

### 5.2 Health checks

- Sonarr/Radarr connectivity status in system page (`api/routes/stats.py` already has a `SystemStatusResponse` model -- extend it)
- mediainfo binary availability check
- Database health and size

### 5.3 Dashboard analytics

- Tag distribution chart (how many items per tag) -- `api/routes/stats.py` already returns `media_by_tag` counts in `StatsResponse`; the UI needs to visualize this
- Scan history trends
- Instance coverage overview

### 5.4 Dark/light theme toggle

- Currently dark-only. Add theme switching support.

### 5.5 Config validation at load time

- Verify paths exist and are accessible
- Test Sonarr/Radarr URL reachability
- Validate language codes against pycountry
- Detect duplicate instance names
- Note: `config_loader.py` already validates env var interpolation and basic structure; this extends it with runtime checks

---

## Key Decisions

| Decision      | Choice                          | Rationale                                    |
| ------------- | ------------------------------- | -------------------------------------------- |
| Sequencing    | Bottom-up                       | Fix foundations before building features     |
| Tag atomicity | Collect-then-apply              | Fewer API calls, naturally atomic            |
| Retry logic   | 3 retries, exponential backoff  | Simple, handles transient failures           |
| Parallelism   | concurrent.futures              | No async rewrite needed, good enough for I/O |
| Test strategy | Close remaining ~1.4% gap       | Most modules already well-covered at 97.6%   |
| Security      | Rate limit + CSRF + strict CORS | Required for public open-source release      |

## Open Questions

1. **Version numbering:** Should the next release be v0.9.0 (after stability) and v1.0.0 (after all phases)? Or jump straight to v1.0.0?
2. **Thread pool sizing:** Should parallel scanning defaults be auto-tuned based on library size or always configurable?
3. **Backwards compatibility:** Should the collect-then-apply tag pattern maintain the same Sonarr/Radarr API call structure for users who might have monitoring on those calls?
4. **Feature flags:** Should new features (parallel scanning, etc.) be behind config flags for gradual rollout?
5. **API call caching per scan cycle:** Should `get_series_by_path`/`get_movie_by_path` cache the full series/movie list once per scan cycle instead of fetching it on every lookup? This is both a performance fix (Phase 4) and a stability improvement (fewer API calls = fewer failure points).

## Deferred (v1.1+)

These ideas from the audit are valuable but not needed for v1.0:

- Webhook events for external automation
- User-configurable scan profiles
- Media exclusion rules via UI
- Bulk tag management in UI
- E2E tests (Playwright)
- API key authentication for routes (infrastructure exists in `api/routes/apikeys.py` and `auth/apikey.py` but not widely adopted)
