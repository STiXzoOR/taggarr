---
status: pending
priority: p3
issue_id: "006"
tags: [code-review, bug, pattern]
dependencies: []
---

# Video Extension List Mismatch (Potential Bug)

## Problem Statement

`movies.py:46` uses a 4-element tuple for mtime detection:

```python
('.mkv', '.mp4', '.m4v', '.avi')
```

But `movies.py:142` uses a 7-element list for scanning:

```python
['.mkv', '.mp4', '.m4v', '.avi', '.webm', '.mov', '.mxf']
```

This means `.webm`, `.mov`, `.mxf` files would NOT trigger change detection but WOULD be scanned, causing potential missed re-scans.

## Findings

- **Pattern Recognition agent**: Identified as MEDIUM — inconsistency likely a bug

## Proposed Solutions

1. **Extract shared constant** (Recommended)
   - Define `VIDEO_EXTENSIONS` at module level, used by both mtime check and scanning
   - Pros: Single source of truth, fixes the bug
   - Effort: Small
   - Risk: Low

## Acceptance Criteria

- [ ] Single video extension constant used in both places
- [ ] Same constant shared between tv.py and movies.py
