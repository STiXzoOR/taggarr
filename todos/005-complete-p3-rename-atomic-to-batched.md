---
status: pending
priority: p3
issue_id: "005"
tags: [code-review, documentation, data-integrity]
dependencies: []
---

# Rename "Atomic" to "Batched" in apply_tag_changes

## Problem Statement

`apply_tag_changes()` docstring and comments call the operation "atomic" but it's a GET-modify-PUT with a TOCTOU window. Concurrent modifications between GET and PUT will be silently overwritten.

## Findings

- **Security agent**: MEDIUM — TOCTOU race identified
- **Data Integrity agent**: MEDIUM — misleading "atomic" claim, documented concrete scenario
- This is inherent to Sonarr/Radarr API design (no ETag/conditional updates)

## Proposed Solutions

1. **Update documentation** (Recommended)
   - Change "atomic" to "batched" or "consolidated" in docstrings and comments
   - Add a note about the TOCTOU limitation
   - Pros: Sets correct expectations
   - Effort: Small
   - Risk: None

## Acceptance Criteria

- [ ] No references to "atomic" in `apply_tag_changes` docstring
- [ ] TOCTOU limitation documented
