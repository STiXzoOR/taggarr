# Taggarr UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full admin web interface for taggarr with monitoring, configuration, and data exploration capabilities.

**Architecture:** FastAPI backend serving a TanStack Start/React frontend. SQLite database replaces JSON files. Single process deployment with background workers for scans, notifications, and backups.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, TanStack Start, React 18, TypeScript, Tailwind CSS, shadcn/ui

---

## Phase 1: Backend Foundation

### Task 1.1: SQLite Database Setup

**Files:**

- Create: `taggarr/db/__init__.py`
- Create: `taggarr/db/models.py`
- Create: `taggarr/db/database.py`
- Test: `tests/unit/db/test_database.py`

**Step 1: Create db package structure**

```bash
mkdir -p taggarr/db tests/unit/db
touch taggarr/db/__init__.py tests/unit/db/__init__.py
```

**Step 2: Write failing test for database connection**

Create `tests/unit/db/test_database.py` with tests for:

- `test_create_engine_creates_sqlite_file` - Engine creation should create SQLite database file
- `test_get_session_returns_session` - get_session should yield a working database session

**Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_database.py -v`
Expected: FAIL with "No module named 'taggarr.db.database'"

**Step 4: Write minimal implementation**

Create `taggarr/db/database.py` with:

- `create_engine(url)` - Create SQLAlchemy engine
- `get_session(engine)` - Yield database session with cleanup

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_database.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add taggarr/db/ tests/unit/db/
git commit -m "feat(db): add database connection and session management"
```

---

### Task 1.2: Core Database Models - Users and Auth

**Files:**

- Modify: `taggarr/db/models.py`
- Test: `tests/unit/db/test_models.py`

**Step 1: Write failing test for User model**

Create `tests/unit/db/test_models.py` with tests for:

- `test_user_model_create` - User model should store username and password hash
- `test_session_model_create` - Session model should link to user with expiration
- `test_api_key_model_create` - ApiKey model should store label and hashed key

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_models.py -v`
Expected: FAIL with "cannot import name 'User' from 'taggarr.db.models'"

**Step 3: Write minimal implementation**

Create models in `taggarr/db/models.py`:

- `User` - id, identifier (GUID), username, password, salt, iterations
- `Session` - id, identifier (token), user_id, expires_at
- `ApiKey` - id, label, key (hashed), last_used_at

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/db/models.py tests/unit/db/test_models.py
git commit -m "feat(db): add User, Session, and ApiKey models"
```

---

### Task 1.3: Database Models - Config and Instances

**Files:**

- Modify: `taggarr/db/models.py`
- Modify: `tests/unit/db/test_models.py`

**Step 1: Write failing tests for Config and Instance models**

Add tests:

- `test_config_model_key_value` - Config model should store key-value pairs
- `test_config_key_unique` - Config keys must be unique
- `test_instance_model_create` - Instance model should store Sonarr/Radarr connection info

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_models.py::test_config_model_key_value -v`
Expected: FAIL with "cannot import name 'Config'"

**Step 3: Write minimal implementation**

Add models:

- `Config` - id, key (unique), value
- `Instance` - id, name, type, url, api_key, root_path, target_languages (JSON), tags (JSON), etc.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/db/models.py tests/unit/db/test_models.py
git commit -m "feat(db): add Config and Instance models"
```

---

### Task 1.4: Database Models - Media and Tags

**Files:**

- Modify: `taggarr/db/models.py`
- Modify: `tests/unit/db/test_models.py`

**Step 1: Write failing tests for Tag and Media models**

Add tests:

- `test_tag_model_create` - Tag model should store label
- `test_media_model_create` - Media model should link to instance and tag
- `test_season_model_create` - Season model should link to media with episode data

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_models.py::test_tag_model_create -v`
Expected: FAIL with "cannot import name 'Tag'"

**Step 3: Write minimal implementation**

Add models:

- `Tag` - id, label (unique)
- `Media` - id, instance_id, path, title, clean_title, media_type, original_language, tag_id, added, last_scanned, etc.
- `Season` - id, media_id, season_number, episode_count, status, dub (JSON), missing_dub (JSON), etc.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/db/models.py tests/unit/db/test_models.py
git commit -m "feat(db): add Tag, Media, and Season models"
```

---

### Task 1.5: Database Models - History and Notifications

**Files:**

- Modify: `taggarr/db/models.py`
- Modify: `tests/unit/db/test_models.py`

**Step 1: Write failing tests for History and Notification models**

Add tests:

- `test_history_model_create` - History model should store events with flexible data
- `test_notification_model_create` - Notification model should store provider config and triggers

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_models.py::test_history_model_create -v`
Expected: FAIL with "cannot import name 'History'"

**Step 3: Write minimal implementation**

Add models:

- `History` - id, date, event_type, media_id, instance_id, data (JSON)
- `Notification` - id, name, implementation, settings (JSON), on\_\* flags
- `NotificationStatus` - id, notification_id, last_sent_at, last_error, consecutive_failures

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/db/models.py tests/unit/db/test_models.py
git commit -m "feat(db): add History, Notification, and NotificationStatus models"
```

---

### Task 1.6: Database Models - Commands, Tasks and Backups

**Files:**

- Modify: `taggarr/db/models.py`
- Modify: `tests/unit/db/test_models.py`

**Step 1: Write failing tests for Command, ScheduledTask, and Backup models**

Add tests:

- `test_command_model_create` - Command model should store async command queue
- `test_scheduled_task_model_create` - ScheduledTask model should track recurring jobs
- `test_backup_model_create` - Backup model should store backup metadata

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_models.py::test_command_model_create -v`
Expected: FAIL with "cannot import name 'Command'"

**Step 3: Write minimal implementation**

Add models:

- `Command` - id, name, body (JSON), status, queued_at, started_at, ended_at, duration, exception, trigger
- `ScheduledTask` - id, type_name (unique), last_execution, last_start_time, interval
- `Backup` - id, filename, path, type, size_bytes, created_at

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/db/models.py tests/unit/db/test_models.py
git commit -m "feat(db): add Command, ScheduledTask, and Backup models"
```

---

### Task 1.7: Database Migration System

**Files:**

- Create: `taggarr/db/migrations.py`
- Test: `tests/unit/db/test_migrations.py`

**Step 1: Write failing test for migration system**

Create `tests/unit/db/test_migrations.py` with tests:

- `test_init_db_creates_all_tables` - init_db should create all required tables
- `test_init_db_creates_default_tags` - init_db should create default dub tags

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/db/test_migrations.py -v`
Expected: FAIL with "No module named 'taggarr.db.migrations'"

**Step 3: Write minimal implementation**

Create `taggarr/db/migrations.py` with:

- `init_db(engine)` - Create all tables and seed default tags

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/db/test_migrations.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/db/migrations.py tests/unit/db/test_migrations.py
git commit -m "feat(db): add database initialization and migrations"
```

---

### Task 1.8: Update db package exports

**Files:**

- Modify: `taggarr/db/__init__.py`

**Step 1: Update package exports**

Export all models and functions from `taggarr/db/__init__.py`

**Step 2: Run all db tests**

Run: `uv run pytest tests/unit/db/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add taggarr/db/__init__.py
git commit -m "feat(db): export all models from db package"
```

---

## Phase 2: Authentication System

### Task 2.1: Password Hashing Service

**Files:**

- Create: `taggarr/auth/__init__.py`
- Create: `taggarr/auth/password.py`
- Test: `tests/unit/auth/test_password.py`

**Step 1: Create auth package structure**

```bash
mkdir -p taggarr/auth tests/unit/auth
touch taggarr/auth/__init__.py tests/unit/auth/__init__.py
```

**Step 2: Write failing tests for password hashing**

Create `tests/unit/auth/test_password.py` with tests:

- `test_hash_password_returns_hash_and_salt`
- `test_hash_password_different_salts`
- `test_verify_password_correct`
- `test_verify_password_incorrect`

**Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/auth/test_password.py -v`
Expected: FAIL

**Step 4: Write minimal implementation**

Create `taggarr/auth/password.py` with PBKDF2-SHA256:

- `hash_password(password)` - Returns hash, salt, iterations
- `verify_password(password, stored_hash, salt, iterations)` - Returns bool

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/auth/test_password.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add taggarr/auth/ tests/unit/auth/
git commit -m "feat(auth): add password hashing with PBKDF2"
```

---

### Task 2.2: Session Token Management

**Files:**

- Create: `taggarr/auth/session.py`
- Test: `tests/unit/auth/test_session.py`

**Step 1: Write failing tests for session management**

Create `tests/unit/auth/test_session.py` with tests:

- `test_create_session_token_returns_token`
- `test_create_session_token_unique`
- `test_get_session_expiry_returns_future_date`
- `test_is_session_expired_false_for_future`
- `test_is_session_expired_true_for_past`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/auth/test_session.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `taggarr/auth/session.py`:

- `create_session_token()` - Generate secure random token
- `get_session_expiry(hours)` - Get ISO timestamp for expiry
- `is_session_expired(expires_at)` - Check if session expired

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/auth/test_session.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/auth/session.py tests/unit/auth/test_session.py
git commit -m "feat(auth): add session token management"
```

---

### Task 2.3: API Key Generation

**Files:**

- Create: `taggarr/auth/apikey.py`
- Test: `tests/unit/auth/test_apikey.py`

**Step 1: Write failing tests for API key generation**

Create `tests/unit/auth/test_apikey.py` with tests:

- `test_generate_api_key_returns_key`
- `test_hash_api_key_returns_hash`
- `test_verify_api_key_correct`
- `test_verify_api_key_incorrect`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/auth/test_apikey.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `taggarr/auth/apikey.py`:

- `generate_api_key()` - Generate 32-char key
- `hash_api_key(key)` - SHA256 hash
- `verify_api_key(key, stored_hash)` - Verify key

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/auth/test_apikey.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add taggarr/auth/apikey.py tests/unit/auth/test_apikey.py
git commit -m "feat(auth): add API key generation and verification"
```

---

### Task 2.4: Update auth package exports

**Files:**

- Modify: `taggarr/auth/__init__.py`

**Step 1: Update package exports**

Export all auth functions from `taggarr/auth/__init__.py`

**Step 2: Run all auth tests**

Run: `uv run pytest tests/unit/auth/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add taggarr/auth/__init__.py
git commit -m "feat(auth): export all auth functions from package"
```

---

## Phase 3: FastAPI Backend

### Task 3.1: FastAPI Application Setup

**Files:**

- Create: `taggarr/api/__init__.py`
- Create: `taggarr/api/app.py`
- Test: `tests/unit/api/test_app.py`

**Step 1: Create api package and add dependencies**

```bash
mkdir -p taggarr/api tests/unit/api
touch taggarr/api/__init__.py tests/unit/api/__init__.py
uv add fastapi uvicorn[standard]
```

**Step 2: Write failing tests for FastAPI app**

Create `tests/unit/api/test_app.py` with tests:

- `test_health_endpoint_returns_ok`
- `test_app_serves_root`

**Step 3: Run test to verify it fails**

Run: `uv run pytest tests/unit/api/test_app.py -v`
Expected: FAIL

**Step 4: Write minimal implementation**

Create `taggarr/api/app.py`:

- `create_app(base_url)` - Factory function with CORS and health endpoint

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/api/test_app.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add taggarr/api/ tests/unit/api/ pyproject.toml uv.lock
git commit -m "feat(api): add FastAPI application factory with health endpoint"
```

---

## Remaining Phases (Summary)

### Phase 3 (continued): API Routes

- Task 3.2: Auth routes (login, logout, status, initialize)
- Task 3.3: API key routes (list, create, delete)
- Task 3.4: Config routes (get, set)
- Task 3.5: Instance routes (CRUD)
- Task 3.6: Media routes (list, get, update)
- Task 3.7: Tag routes (list)
- Task 3.8: Command routes (list, create, cancel)
- Task 3.9: History routes (list)
- Task 3.10: Notification routes (CRUD, test)
- Task 3.11: Backup routes (list, create, download, restore, delete)
- Task 3.12: Stats routes (dashboard data)
- Task 3.13: Log routes (list, stream via WebSocket)

### Phase 4: Background Workers

- Task 4.1: Command queue processor
- Task 4.2: Scan scheduler
- Task 4.3: Notification dispatcher
- Task 4.4: Backup scheduler

### Phase 5: Frontend Setup

- Task 5.1: TanStack Start project initialization
- Task 5.2: Tailwind and shadcn/ui setup
- Task 5.3: API client with TanStack Query
- Task 5.4: Auth context and protected routes
- Task 5.5: Layout components (header, sidebar, etc.)

### Phase 6: Frontend Pages

- Task 6.1: Setup wizard page
- Task 6.2: Login page
- Task 6.3: Dashboard page
- Task 6.4: Library browser page
- Task 6.5: Media detail page
- Task 6.6: Settings pages (general, instances, notifications, backup, security)
- Task 6.7: Activity pages (history, queue, logs)
- Task 6.8: System page

### Phase 7: Migration and Integration

- Task 7.1: JSON to SQLite data migration
- Task 7.2: YAML config migration
- Task 7.3: CLI integration (serve command)
- Task 7.4: Docker image updates

### Phase 8: Testing and Polish

- Task 8.1: Integration tests
- Task 8.2: E2E tests with Playwright
- Task 8.3: Security audit
- Task 8.4: Documentation

---

## Skills Reference

Use these skills during implementation:

| Phase          | Skills                                                                                                                     |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Database       | `superpowers:test-driven-development`                                                                                      |
| Auth           | `superpowers:test-driven-development`, `everything-claude-code:security-review`                                            |
| API            | `api-contracts-and-zod-validation:api-contracts-and-zod-validation`, `superpowers:test-driven-development`                 |
| Frontend Setup | `tailwind-shadcn-ui-setup:tailwind-shadcn-ui-setup`                                                                        |
| Frontend Pages | `frontend-design:frontend-design`, `form-generator-rhf-zod:form-generator-rhf-zod`                                         |
| Security       | `security-hardening-checklist:security-hardening-checklist`, `auth-route-protection-checker:auth-route-protection-checker` |
| Final Review   | `superpowers:verification-before-completion`, `superpowers:requesting-code-review`                                         |
