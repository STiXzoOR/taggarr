---
status: pending
priority: p3
issue_id: "004"
tags: [code-review, simplicity, cleanup]
dependencies: []
---

# Remove Dead Code From Phase 1

## Problem Statement

Several pieces of code introduced in Phase 1 are unused:

1. `MediaAnalysisError` and `StorageError` in `exceptions.py` — never raised or caught
2. `add_tag()` / `remove_tag()` legacy wrappers in `base_client.py` — no production callers
3. `_media_id_field` class attribute in `base_client.py` — never referenced
4. Unused imports in `radarr.py` — `ApiTransientError`, `ApiPermanentError`

## Findings

- **Simplicity agent**: 3 of 6 exception classes are dead, legacy wrappers born dead
- **Pattern Recognition agent**: Confirmed unused attribute and imports

## Proposed Solutions

1. **Remove all dead code**
   - Delete unused exceptions, wrappers, attribute, imports
   - Update tests that only test the legacy wrappers
   - Pros: Cleaner codebase, no misleading code
   - Effort: Small
   - Risk: Low

## Acceptance Criteria

- [ ] No unused exception classes in `exceptions.py`
- [ ] No unused wrappers in `base_client.py`
- [ ] No unused imports in `radarr.py`
- [ ] Coverage remains >= 99%
