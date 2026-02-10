---
status: pending
priority: p2
issue_id: "001"
tags: [code-review, architecture, bug]
dependencies: []
---

# Duplicate ConfigError Classes

## Problem Statement

Two separate `ConfigError` classes exist with different base classes:

- `taggarr/exceptions.py:10` — `ConfigError(TaggarrError)`
- `taggarr/config_loader.py:15` — `ConfigError(Exception)`

The entry point imports from `config_loader`, making the `exceptions.py` version dead code. Code catching `TaggarrError` will miss config errors.

## Findings

- **Pattern Recognition agent**: Identified as HIGH priority — class identity bug waiting to happen
- **Simplicity agent**: Confirmed the `exceptions.py` version is never imported

## Proposed Solutions

1. **Unify into exceptions.py**: Make `config_loader.py` import from `exceptions.py`
   - Pros: Single source of truth, enables `except TaggarrError` to catch config errors
   - Cons: Minor import restructuring needed
   - Effort: Small
   - Risk: Low

2. **Remove from exceptions.py**: Delete the unused `ConfigError` from `exceptions.py`
   - Pros: Simplest fix
   - Cons: Breaks the exception hierarchy design
   - Effort: Small
   - Risk: Low

## Acceptance Criteria

- [ ] Only one `ConfigError` class exists
- [ ] `except TaggarrError` catches config errors
- [ ] All tests pass
