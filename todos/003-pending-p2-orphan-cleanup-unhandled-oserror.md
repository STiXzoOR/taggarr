---
status: pending
priority: p2
issue_id: "003"
tags: [code-review, data-integrity, reliability]
dependencies: []
---

# Orphan Cleanup OSError Can Prevent Saving

## Problem Statement

The orphan cleanup in `tv.py:104` and `movies.py:127` calls `os.listdir(instance.root_path)` without error handling. On network storage (NFS/CIFS), a temporary mount failure would throw `OSError`, preventing `json_store.save()` from being called and losing all scan progress.

## Findings

- **Data Integrity agent**: Medium severity — can prevent saving current scan progress
- **Pattern Recognition agent**: Also flagged the duplicated cleanup block between tv.py and movies.py

## Proposed Solutions

1. **Wrap in try/except** (Recommended)
   - Catch `OSError` around the orphan cleanup block, log warning, skip cleanup
   - Pros: Graceful degradation, scan progress preserved
   - Cons: Orphan cleanup skipped on that cycle
   - Effort: Small
   - Risk: Low

2. **Extract to helper and wrap**
   - Move path-gathering + cleanup into `json_store.cleanup_orphans_for_root(data, key, root_path)`
   - Also eliminates the duplication between tv.py and movies.py
   - Pros: DRY + error handling in one fix
   - Effort: Small
   - Risk: Low

## Acceptance Criteria

- [ ] OSError during orphan cleanup does not prevent save
- [ ] Cleanup logic is deduplicated between tv.py and movies.py
- [ ] All tests pass
