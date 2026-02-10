---
status: pending
priority: p2
issue_id: "002"
tags: [code-review, data-integrity]
dependencies: []
---

# Non-Atomic JSON File Write

## Problem Statement

`json_store.save()` writes directly to `taggarr.json` with `open(path, 'w')`. A crash mid-write leaves a truncated/corrupted file. The next `load()` renames it to `.bak` and starts fresh — losing all scan history.

## Findings

- **Data Integrity agent**: Medium severity — primary persistence mechanism has crash vulnerability
- Backup overwrite also flagged: repeated corruption overwrites the single `.bak`

## Proposed Solutions

1. **Write-to-temp-then-rename** (Recommended)
   - Write to `taggarr.json.tmp`, flush+fsync, then `os.replace()` (atomic on POSIX)
   - Pros: Industry-standard pattern, eliminates partial-write risk
   - Cons: None significant
   - Effort: Small
   - Risk: Low

## Acceptance Criteria

- [ ] `save()` uses write-to-temp-then-rename pattern
- [ ] All tests pass
