---
title: "feat: Taggarr v1.0 Release Roadmap"
type: feat
date: 2026-02-10
source: docs/brainstorms/2026-02-10-v1-release-roadmap-brainstorm.md
deepened: 2026-02-10
---

# Taggarr v1.0 Release Roadmap

## Enhancement Summary

**Deepened on:** 2026-02-10
**Review agents used:** Security Sentinel, Architecture Strategist, Performance Oracle, Code Simplicity Reviewer, Kieran Python Reviewer
**External research:** tenacity retry patterns, FastAPI security (slowapi/CSRF), Python ThreadPoolExecutor best practices

### Key Improvements

1. **Move API caching from Phase 4.2 to Phase 1.1** -- the O(n^2) fetch pattern wastes 6,000 redundant calls for 2,000 items; fixing alongside tag atomicity cuts scan time from 6-10 hours to 20-40 minutes
2. **Reorder Phase 3 critical items**: 3.8 (Alembic) -> 3.7 (state storage) -> 3.6 (wire ScanHandler) -- Alembic must exist before model changes, state storage before ScanHandler wiring
3. **4 critical security gaps not in original plan**: API key exposure in Instance responses, path traversal in log download, LIKE wildcard injection in media search, notification credential storage
4. **Exception hierarchy**: `TaggarrError -> ApiError -> ApiTransientError/ApiPermanentError` in new `exceptions.py` -- enables tenacity to retry only transient errors
5. **BaseArrClient extraction**: DRY up Sonarr/Radarr clients into shared base with `_request()` + tenacity decorator
6. **ScanResultSink protocol**: Clean adapter pattern for JSON-vs-DB state divergence with `JsonScanSink` and `DbScanSink`

### New Considerations Discovered

- `Instance.api_key` stored in plaintext in DB -- must mask in API responses, consider encryption at rest
- `allow_credentials=True` + `allow_origins=["*"]` = credential theft vector (not just permissive CORS)
- `time.sleep(0.5)` after each tag modification wastes 50 minutes for 2,000 items -- remove in Phase 1.1
- `/initialize` endpoint has TOCTOU race condition allowing duplicate admin creation
- `datetime.utcnow()` deprecated since Python 3.12 -- use `datetime.now(timezone.utc)`
- `threading.Event` pattern for graceful shutdown (replaces signal + flag approach)

---

## Overview

Bottom-up roadmap to take Taggarr from v0.8.0 (functional but rough) to a v1.0 public open-source release. The work is sequenced across 5 phases: stability fixes, test coverage, gap completion, performance, and release features. Each phase builds on the previous -- foundations first, polish last.

**Scope:** ~6,500 lines Python (57 files), ~14,160 lines tests (53 files), ~33 React components. 642 tests at 97.67% coverage. Dual architecture: CLI mode (processors -> JSON) and Server mode (FastAPI + SQLAlchemy + workers -> DB).

**Audience:** Public open-source users with large media libraries (2000+ items).

## Problem Statement

Taggarr v0.8.0 works but isn't release-ready:

1. **Stability:** Non-atomic tag operations, bare `except Exception` everywhere (9 instances), no retry logic, path collisions, fragile audio detection, unbounded JSON state
2. **Coverage:** 97.67% vs enforced 99% minimum -- CI fails
3. **Incomplete:** Log endpoints are stubs, CORS wide open (`allow_origins=["*"]`), no frontend CI, ScanHandler is a placeholder, no CHANGELOG
4. **Performance:** Sequential scanning, O(n^2) API lookups for n media items, no resume on interrupted scans
5. **Polish:** No scan progress UI, no health checks, no theme toggle, no config validation

## Proposed Solution

Five sequential phases, bottom-up: fix foundations before building features. Each phase includes tests for new code (TDD where practical).

**Critical additions from flow analysis** (not in original brainstorm):

- Wire ScanHandler to processors (server mode can't scan without this)
- Resolve JSON-vs-DB state divergence
- WebSocket authentication
- Merge timeout work into retry phase
- Alembic migration framework

## Technical Approach

### Architecture Context

```
CLI Mode (working):
  main.py scan -> taggarr.run() -> processors/tv.py|movies.py
    -> SonarrClient/RadarrClient -> json_store persistence

Server Mode (partially built):
  FastAPI app -> api/routes/commands.py (queue) -> workers/handlers/scan.py
    -> PLACEHOLDER (does not call processors/) -> DB persistence

Frontend:
  React + TanStack Router -> API calls -> Auth (cookie sessions)
    -> Dashboard/Library/Activity/System/Settings -> WebSocket logs
```

### Dependency Graph

```
Phase 1 (Stability) ──> Phase 2 (Tests) ──> Phase 3 (Gaps) ──> Phase 4 (Performance) ──> Phase 5 (Features)

Key cross-phase dependencies:
  1.2 (exceptions) ──> 1.3 (retry) -- tenacity retries ApiTransientError only
  1.2 (exceptions) ──> 4.1 (parallel scanning) -- silent failures in threads
  1.1 (tag atomicity + caching) absorbs former 4.2 -- critical perf fix moved early
  3.6 (Alembic) ──> 3.7 (sink protocol) ──> 3.8 (wire ScanHandler)
  3.8 (ScanHandler bridge) ──> 4.3 (resume), 5.1 (progress)
  3.7 (state storage) ──> 5.3 (dashboard analytics)
```

### Implementation Phases

#### Phase 1: Stability Fixes

Fix 7 high-priority bugs that would embarrass a public release.

##### 1.1 Non-atomic tag operations + API caching (EXPANDED)

- **Problem:** `_apply_tags()` makes separate add/remove API calls. Middle call failure leaves inconsistent state. Additionally, `get_series_by_path()` fetches the entire series list on every call -- O(n^2) for n items. The `time.sleep(0.5)` after each tag modification wastes ~50 minutes for 2,000 items.
- **Solution:** Collect-then-apply pattern. New `apply_tag_changes(media_id, add_tags=[], remove_tags=[])` method: one GET, modify tags array, one PUT. **Also** cache the full series/movie list once per scan cycle (moved from Phase 4.2) and cache tag ID mappings. Remove `time.sleep(0.5)`.
- **Files:** `processors/tv.py:240-257`, `processors/movies.py:99-107`, `services/sonarr.py` (new `apply_tag_changes` + `_series_cache`), `services/radarr.py` (same)
- **Tests:** Mock the GET/PUT cycle, verify single PUT with correct tag set, test partial failure recovery, verify cache populated once per cycle

> **Performance insight (from Performance Oracle):** Moving API caching here (from Phase 4.2) is critical. For 2,000 items: 6,000 redundant tag-list fetches + 2,000 series-list fetches = ~8,000 wasted HTTP calls. Combined with removing `time.sleep(0.5)`, projected scan time drops from 6-10 hours to 20-40 minutes.

##### 1.2 Broad exception catching + exception hierarchy

- **Problem:** 9 bare `except Exception` handlers mask real problems.
- **Solution:** Create `taggarr/exceptions.py` with hierarchy, then replace bare handlers:

```
TaggarrError (base)
├── ConfigError          -- invalid config, missing keys
├── ApiError             -- all Sonarr/Radarr API errors
│   ├── ApiTransientError  -- 5xx, timeouts, connection errors (retryable)
│   └── ApiPermanentError  -- 4xx, auth failures (not retryable)
├── MediaAnalysisError   -- mediainfo failures
└── StorageError         -- JSON/DB write failures
```

- **Files:** New `taggarr/exceptions.py`, `services/media.py:35`, `services/sonarr.py:31,67,80,112`, `services/radarr.py:29,43,74,106`, `api/websocket.py:39`
- **Tests:** Verify each exception type surfaces correctly, `ApiTransientError` triggers retry (1.3), `ApiPermanentError` fails fast
- **Note:** Also fix unhandled `_get_or_create_tag()` POST error in both Sonarr/Radarr clients -- `KeyError`/`JSONDecodeError` propagates unwrapped
- **Pre-requisite for:** Phase 1.3 (tenacity retries on `ApiTransientError` only), Phase 4.1 (exceptions in threads must not silently vanish)

> **Python patterns insight:** Use `from __future__ import annotations` in all new/modified files for modern type hint syntax. Extract `BaseArrClient` from `SonarrClient`/`RadarrClient` during this phase to DRY up the 90%+ identical code.

##### 1.3 Retry logic + timeouts (merged with former 3.5)

- **Problem:** Transient failures cause silent scan failures. No timeouts on most requests (only `refresh_series` has 10s).
- **Solution:** Use `tenacity` (not `urllib3.util.retry` -- matches bare `requests` pattern). Add `_request()` helper on `BaseArrClient` with tenacity decorator. 30s timeout on all calls.

```python
# On BaseArrClient._request():
@retry(
    retry=retry_if_exception_type(ApiTransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _request(self, method, endpoint, **kwargs):
    kwargs.setdefault("timeout", 30)
    try:
        resp = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError as e:
        raise ApiTransientError(str(e)) from e
    except requests.HTTPError as e:
        if e.response.status_code >= 500:
            raise ApiTransientError(str(e)) from e
        raise ApiPermanentError(str(e)) from e
```

- **Files:** New `services/base_client.py` (or inline in existing), `services/sonarr.py`, `services/radarr.py`
- **Tests:** Mock transient 503 -> verify 3 attempts, mock permanent 404 -> verify 1 attempt, verify timeout triggers
- **Depends on:** 1.2 (exception hierarchy must exist first)

##### 1.4 Path matching by basename only

- **Problem:** `os.path.basename()` comparison causes collisions for folders with same name in different paths.
- **Solution:** Match by full path first. Fall back to basename only if no full path match (backwards compat).
- **Files:** `services/sonarr.py:29` (`get_series_by_path`), `services/radarr.py:41` (`get_movie_by_path`)
- **Tests:** Two items with same basename but different full paths, verify correct match

##### 1.5 Fragile audio fallback detection

- **Problem:** Track title heuristic misidentifies commentary tracks as original audio.
- **Solution:** Use track position (first audio track = default) and codec metadata. Title heuristic as last resort only.
- **Files:** `services/media.py:27`
- **Tests:** Commentary track with "Audio 1" title, track with no language but first position, multi-audio files

##### 1.6 JSON state grows unbounded

- **Problem:** Deleted media entries never cleaned from `taggarr.json`.
- **Solution:** Cleanup step at end of each scan cycle. Compare entries against current folder listing, remove orphans.
- **Files:** `storage/json_store.py`, `processors/tv.py`, `processors/movies.py`
- **Tests:** Add entries for non-existent paths, verify cleanup removes them

##### 1.7 Graceful shutdown (NEW -- from flow analysis)

- **Problem:** `run_loop()` has no signal handling. SIGTERM during scan = partially-written JSON state.
- **Solution:** Use `threading.Event` pattern instead of raw signal flag. Scan loop checks `shutdown_event.is_set()` between items. JSON writes use atomic rename (`write to .tmp` then `os.replace()`).

```python
# In taggarr/__init__.py:
shutdown_event = threading.Event()

def _signal_handler(signum, frame):
    logger.info("Shutdown requested, finishing current item...")
    shutdown_event.set()

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)

# In run_loop:
while not shutdown_event.is_set():
    for item in items:
        process_item(item)
        if shutdown_event.is_set():
            break
    if not shutdown_event.is_set():
        shutdown_event.wait(timeout=scan_interval)  # replaces time.sleep()
```

- **Files:** `taggarr/__init__.py:96-98`, `storage/json_store.py` (atomic writes)
- **Tests:** Simulate SIGTERM during scan loop, verify clean exit after current item, verify `.tmp` rename pattern

> **Python patterns insight:** `threading.Event.wait(timeout=N)` replaces `time.sleep(N)` -- it's interruptible by the shutdown event, so the process stops promptly instead of sleeping through the full interval.

---

#### Phase 2: Test Coverage (97.67% -> 99%)

Close the remaining ~1.4% gap. Priority by coverage distance from 100%.

##### Priority 1: Lowest coverage files

| File                            | Current | Missing Lines                  |
| ------------------------------- | ------- | ------------------------------ |
| `workers/providers/base.py`     | 75%     | 22, 34                         |
| `api/websocket.py`              | 78%     | 85-101 (live WebSocket loop)   |
| `api/routes/backups.py`         | 84%     | 80-81, 93-99, 236-237, 245-256 |
| `workers/providers/__init__.py` | 87%     | 34                             |
| `workers/handlers/base.py`      | 89%     | 30                             |

##### Priority 2: 90-96% coverage files

| File                                 | Current |
| ------------------------------------ | ------- |
| `api/routes/stats.py`                | 92%     |
| `workers/notification_dispatcher.py` | 92%     |
| `workers/providers/pushover.py`      | 93%     |
| `api/routes/notifications.py`        | 95%     |
| `api/routes/instances.py`            | 96%     |
| `workers/handlers/backup.py`         | 96%     |

##### Priority 3: 97-98% coverage files

| File                            | Current |
| ------------------------------- | ------- |
| `api/app.py`                    | 97%     |
| `workers/providers/email.py`    | 97%     |
| `workers/providers/telegram.py` | 97%     |
| `nfo.py`                        | 98%     |

**Strategy:** Write tests for Phase 1 bug fixes as they land (TDD). Use existing patterns: `responses` for HTTP mocking, `pytest-mock` for general mocking. Estimated ~30-50 new tests.

---

#### Phase 3: Complete the Gaps

Finish incomplete work for release readiness.

##### 3.1 Log REST endpoints + rotation

- Implement file listing and download in `api/routes/logs.py` (currently stubs returning empty lists)
- Add `RotatingFileHandler` or `TimedRotatingFileHandler` to `logging_setup.py`
- WebSocket streaming already works via `api/websocket.py`
- **Files:** `api/routes/logs.py:1-94`, `logging_setup.py`

> **Security insight:** Path traversal protection is critical for log download. Validate that requested filename resolves within the log directory: `resolved = Path(log_dir, filename).resolve(); assert resolved.is_relative_to(log_dir)`. Never pass user input directly to `open()`.

##### 3.2 Security hardening (expanded from flow analysis + security review)

- Rate limiting on auth endpoints using `slowapi`: `Limiter(key_func=get_remote_address)`, 5/min on login, 3/min on initialize
- CSRF protection: double-submit cookie pattern (`X-CSRF-Token` header must match `csrf_token` cookie)
- Restrict CORS to configured origins (replace `allow_origins=["*"]` in `api/app.py:45`)
- Fix `allow_credentials=True` + wildcard origin combination (CRITICAL: enables credential theft)
- Secure cookie flags: `samesite="strict"` (upgrade from `"lax"`), auto-detect `secure=True` from `X-Forwarded-Proto`
- Input validation on all API endpoints
- **WebSocket authentication** (NEW): check session cookie during handshake in `api/websocket.py:85`
- **`/initialize` race protection** (NEW): DB-level UNIQUE constraint on admin user, not just Python check
- **Session cleanup** (NEW): scheduled task to prune expired sessions
- **API key masking** (NEW -- from security review): `Instance` API responses must NEVER return raw `api_key`. Mask to `"****<last4>"` in `InstanceResponse`. Consider Fernet encryption at rest.
- **Notification credential masking** (NEW): Same for webhook URLs, SMTP passwords, Pushover/Telegram tokens
- **Security headers middleware** (NEW): Add `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Strict-Transport-Security`
- **LIKE wildcard escape** (NEW): Escape `%` and `_` in user-supplied search terms for media search endpoints
- **Command name validation** (NEW): Validate `command_type` against allowlist in command creation
- **Files:** `api/app.py`, `api/websocket.py`, `api/routes/auth.py:101,219`, `api/deps.py`, `api/routes/instances.py` (mask keys), `api/routes/notifications.py` (mask credentials)

##### 3.3 Frontend CI

- Add `typecheck` script to `frontend/package.json` first: `"typecheck": "tsc --noEmit"`
- Add `npm run build && npm run typecheck` step to `.github/workflows/test.yml`
- Run alongside Python tests (parallel jobs)
- **Files:** `frontend/package.json`, `.github/workflows/test.yml`

##### 3.4 Release documentation

- Create `CHANGELOG.md`
- Review and polish `README.md` for public audience
- Verify `taggarr.example.yaml` covers all options

##### 3.5 Medium-priority bug fixes (timeouts merged into 1.3)

- Fix NFO update running even when API call fails -- gate on success in `processors/tv.py:82`
- Fix timezone mismatch: create `utc_now_iso()` helper in a utils module, replace all `datetime.utcnow()` calls (`processors/tv.py:283`, `processors/movies.py:118`). Uses `datetime.now(timezone.utc)` (deprecated in Python 3.12)
- Fix `dockerfile` casing -> `Dockerfile`
- Add semi-dub tag support for movies: update `_determine_tag()`, `_apply_tags()` three-way exclusion, and `write_mode==2` removal list in `processors/movies.py`
- Improve episode regex to handle `s01e01`, `01.mkv`, multi-episode formats in `processors/tv.py:167`

##### 3.6 Add Alembic migration framework (REORDERED -- was 3.8)

- Initialize Alembic for the 14 SQLAlchemy models
- Generate baseline migration from current schema
- **Must come first:** 3.7 and 3.8 below add/modify models, which need migrations
- Configure with `render_as_batch=True` for SQLite ALTER TABLE compatibility
- **Files:** New `alembic/`, `alembic.ini`, `db/migrations.py` update

> **Architecture insight:** SQLite doesn't support `ALTER TABLE DROP COLUMN` natively. Alembic's `render_as_batch=True` uses the copy-and-rename workaround automatically.

##### 3.7 Resolve JSON-vs-DB state storage (REORDERED -- was 3.7)

- Decision: Server mode processors write to DB models directly (not JSON)
- Implement `ScanResultSink` protocol with two implementations:

```python
# processors/sink.py
from typing import Protocol

class ScanResultSink(Protocol):
    def save_media_result(self, instance: str, path: str, tags: list[str], metadata: dict) -> None: ...
    def remove_orphan(self, instance: str, path: str) -> None: ...
    def on_progress(self, current: int, total: int) -> None: ...  # for Phase 5.1

class JsonScanSink:
    """Wraps json_store for CLI mode."""

class DbScanSink:
    """Writes to Media/Season/Tag/History tables for server mode."""
```

- Add JSON-to-DB import utility for users migrating from CLI to server mode
- Add unique composite index on `(instance_id, path)` in `Media` table (prevents duplicates)
- **Requires:** 3.6 (Alembic for the new index migration)
- **Files:** New `processors/sink.py`, `storage/json_store.py` (wrap as `JsonScanSink`), `workers/handlers/scan.py`

##### 3.8 Wire ScanHandler to processors (REORDERED -- was 3.6, CRITICAL)

- Replace placeholder in `workers/handlers/scan.py:103,143` with actual processor calls
- Create `ScanOptions` dataclass to replace untyped `opts` namespace:

```python
@dataclass(frozen=True)
class ScanOptions:
    write_mode: int = 0     # 0=dry, 1=write, 2=overwrite
    dry_run: bool = False
    quick: bool = False
    instance_name: str = ""
```

- Processors accept `ScanOptions` + `ScanResultSink` instead of `opts`
- Use `asyncio.to_thread()` to bridge async ScanHandler -> sync processors
- **Requires:** 3.7 (sink protocol must exist), 1.1 + 1.2 (fixed tag ops + exceptions)
- **Files:** `workers/handlers/scan.py`, `processors/tv.py`, `processors/movies.py`, new `processors/scan_options.py`

---

#### Phase 4: Performance

Critical for 2000+ item libraries.

**Prerequisites:** Phase 1 complete (especially 1.2 exceptions, 1.4 path matching), Phase 3.7/3.8 (state storage + ScanHandler bridge)

> **Performance projection (from Performance Oracle):** With Phase 1.1 caching + sleep removal, Phase 4.1 parallelism, and Phase 4.2 optimizations: 2,000-item library scan drops from 6-10 hours to 20-40 minutes.

##### 4.1 Parallel scanning

- `concurrent.futures.ThreadPoolExecutor` -- no async rewrite needed
- Dual-level pool sizing:
  - Instance level: 2-3 threads (external API rate limiting is the bottleneck)
  - Item level within instance: 4-8 threads (mediainfo analysis is CPU-bound)
- Configurable via config YAML: `scanning.instance_threads: 2`, `scanning.item_threads: 4`
- **Files:** `taggarr/__init__.py`, `workers/handlers/scan.py`, `config_schema.py`

> **Performance insight:** Don't oversubscribe instance-level threads. Sonarr/Radarr APIs typically rate-limit or slow down with concurrent requests. 2-3 instance threads is optimal; more causes contention without speedup.

##### 4.2 Additional API optimizations (caching moved to 1.1)

- **Note:** Core API caching (series/movie list + tag IDs) moved to Phase 1.1
- This phase handles remaining optimizations:
  - Batch tag creation: create all needed tags in one pass at scan start instead of per-item `_get_or_create_tag()`
  - Connection pooling: `requests.Session` with `HTTPAdapter(pool_maxsize=N)` matching thread count
  - Profile and optimize any remaining hot paths
- **Files:** `services/sonarr.py`, `services/radarr.py`

##### 4.3 Resume/checkpoint scanning

- Save scan progress so interrupted scans can resume
- Use per-item checkpointing (not linear index): store set of completed `(instance, path)` tuples
- Extend `Command` model in `db/models.py` with `checkpoint_data` JSON field
- On resume: load completed set, skip already-processed items
- **Requires:** 3.8 (ScanHandler bridge), 3.6 (Alembic for model changes)
- **Files:** `db/models.py`, `workers/handlers/scan.py`

> **Architecture insight:** Per-item checkpointing is more robust than linear index. If items are processed in parallel or the item list changes between runs, a linear index would skip wrong items or re-process. A set of completed paths handles both cases correctly.

---

#### Phase 5: Release Features

Polish and differentiation for public release.

**Prerequisites:** Phase 3.6 (ScanHandler bridge for scan data), Phase 3.7 (state storage for analytics)

##### 5.1 Scan progress indicator

- Real-time progress in UI (current instance, current item, X/Y complete)
- WebSocket-based updates (infrastructure exists in `api/websocket.py`)
- Uses `ScanResultSink.on_progress()` callback (added in Phase 3.7) -- `DbScanSink` broadcasts via WebSocket
- **Requires:** 3.8 (ScanHandler must actually scan for progress to report)

##### 5.2 Health checks

- Sonarr/Radarr connectivity status (extend `SystemStatusResponse` in `api/routes/stats.py`)
- mediainfo binary availability check
- Database health and size

##### 5.3 Dashboard analytics

- Tag distribution chart (data exists: `media_by_tag` in `StatsResponse`)
- Scan history trends
- Instance coverage overview
- **Requires:** 3.7 (state storage resolution -- data must be in DB)

##### 5.4 Dark/light theme toggle

- Currently dark-only. Add CSS custom properties for theme switching.

##### 5.5 Config validation at load time

- Verify paths exist and are accessible
- Test Sonarr/Radarr URL reachability
- Validate language codes against pycountry
- Detect duplicate instance names
- **Files:** `config_loader.py`

---

## Acceptance Criteria

### Functional Requirements

- [ ] **Phase 1:** All 7 stability bugs fixed with tests
- [ ] **Phase 1.1:** Tag operations use single GET-modify-PUT per media item; API list cached per scan cycle; `time.sleep(0.5)` removed
- [ ] **Phase 1.2:** Zero bare `except Exception` in services/ and api/; `taggarr/exceptions.py` with full hierarchy; `BaseArrClient` extracted
- [ ] **Phase 1.3:** All `requests` calls have 30s timeout + tenacity retry (3 attempts, exponential backoff) on `ApiTransientError`
- [ ] **Phase 1.4:** Full path matching with basename fallback
- [ ] **Phase 1.5:** Audio detection uses track position, not title heuristic
- [ ] **Phase 1.6:** Orphaned JSON entries cleaned each scan cycle
- [ ] **Phase 1.7:** SIGTERM during scan exits cleanly after current item
- [ ] **Phase 2:** Test coverage >= 99% (enforced by CI)
- [ ] **Phase 3.1:** Log files listable and downloadable via REST API
- [ ] **Phase 3.2:** CORS restricted, WebSocket authenticated, rate limiting on auth, CSRF protection, API keys masked in responses, security headers middleware
- [ ] **Phase 3.3:** Frontend build + typecheck passes in CI
- [ ] **Phase 3.5:** Movies support semi-dub tag, datetime.utcnow() replaced, Dockerfile casing fixed
- [ ] **Phase 3.6:** Alembic initialized with baseline migration, `render_as_batch=True`
- [ ] **Phase 3.7:** `ScanResultSink` protocol with `JsonScanSink` + `DbScanSink`; composite index on `(instance_id, path)`
- [ ] **Phase 3.8:** Server mode scans actually invoke processors via ScanHandler; `ScanOptions` dataclass replaces `opts`
- [ ] **Phase 4.1:** Parallel scanning configurable (default 4 threads)
- [ ] **Phase 4.2:** Batch tag creation at scan start; connection pooling matches thread count
- [ ] **Phase 5.1:** Scan progress visible in real-time via WebSocket
- [ ] **Phase 5.5:** Invalid config fails fast with clear error messages

### Non-Functional Requirements

- [ ] 99% test coverage maintained across all phases
- [ ] No `except Exception` in new code -- use exception hierarchy
- [ ] All new `requests` calls include timeout + tenacity retry
- [ ] CORS restricted to configured origins; `allow_credentials` only with explicit origins
- [ ] Python 3.9-3.13 compatibility maintained
- [ ] Frontend builds without TypeScript errors
- [ ] `from __future__ import annotations` in all new/modified files
- [ ] API keys and credentials never exposed in API responses
- [ ] Security headers on all responses

### Quality Gates

- [ ] Each phase passes full test suite before next phase starts
- [ ] Security items reviewed before v1.0 tag
- [ ] CHANGELOG.md documents all changes
- [ ] README.md updated for public audience

## Dependencies & Prerequisites

| Phase     | Depends On                         | Reason                                                                  |
| --------- | ---------------------------------- | ----------------------------------------------------------------------- |
| Phase 1.3 | Phase 1.2                          | Retry logic uses exception hierarchy to distinguish transient/permanent |
| Phase 2   | Phase 1                            | Tests should validate correct behavior, not buggy behavior              |
| Phase 3.3 | `typecheck` script in package.json | CI step requires the script to exist                                    |
| Phase 3.6 | (none)                             | Alembic init is standalone, baseline from current schema                |
| Phase 3.7 | Phase 3.6                          | Sink protocol + composite index need Alembic for migration              |
| Phase 3.8 | Phase 3.7, 1.1, 1.2                | ScanHandler wiring needs sink protocol + fixed tag ops + exceptions     |
| Phase 4.1 | Phase 1.2                          | Parallel scanning with silent exception swallowing = invisible failures |
| Phase 4.3 | Phase 3.8, 3.6                     | Resume needs ScanHandler bridge + Alembic for model changes             |
| Phase 5.1 | Phase 3.8                          | Progress reporting needs actual scan execution via ScanResultSink       |
| Phase 5.3 | Phase 3.7                          | Dashboard analytics needs data in DB via DbScanSink                     |

## Risk Analysis & Mitigation

| Risk                                                                | Impact | Probability | Mitigation                                                          |
| ------------------------------------------------------------------- | ------ | ----------- | ------------------------------------------------------------------- |
| Phase 1.1 collect-then-apply breaks existing monitoring             | Medium | Low         | Log tag changes before and after, same visible behavior             |
| Phase 3.6 ScanHandler bridge creates processor refactor scope creep | High   | Medium      | Create thin adapter, don't rewrite processors                       |
| Phase 3.7 JSON-to-DB migration data loss                            | High   | Medium      | Add validation step, backup before import, dry-run mode             |
| Phase 4.1 thread safety issues in processors                        | High   | Medium      | Processors are stateless (all state in args), thread-safe by design |
| Coverage regression during Phase 1 changes                          | Medium | High        | Write Phase 1 tests in Phase 2 cadence, maintain TDD                |

## Open Questions (from brainstorm)

1. **Version numbering:** v0.9.0 after stability, then v1.0.0 after all phases? Or jump to v1.0.0?
2. **Thread pool sizing:** Auto-tune based on library size or always configurable?
3. **Feature flags:** New features behind config flags for gradual rollout?
4. **API call caching:** Cache full list once per scan cycle vs per-item fetch? (Recommendation: cache per cycle)

## References & Research

### Internal References

- Brainstorm: `docs/brainstorms/2026-02-10-v1-release-roadmap-brainstorm.md`
- Architecture docs: `.claude/docs/architecture.md`
- Testing patterns: `.claude/docs/testing.md`
- Configuration: `.claude/docs/configuration.md`
- Past plans: `docs/plans/2026-02-01-test-coverage-design.md`, `docs/plans/2026-02-02-ui-design.md`

### Key Files

- Tag operations: `processors/tv.py:240-257`, `processors/movies.py:99-107`
- API clients: `services/sonarr.py`, `services/radarr.py`
- Audio detection: `services/media.py:27`
- State storage: `storage/json_store.py`
- CORS config: `api/app.py:45`
- WebSocket: `api/websocket.py:85`
- ScanHandler placeholder: `workers/handlers/scan.py:103,143`
- Log stubs: `api/routes/logs.py`
- CI: `.github/workflows/test.yml`
- DB models: `db/models.py` (14 models)
- Frontend: `frontend/src/` (42 source files, React + TanStack Router)
