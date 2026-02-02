# AGENTS.md

Python tool that scans media libraries and tags TV shows/movies based on audio dubs via Sonarr/Radarr APIs.

## Essentials

| Item              | Value                          |
| ----------------- | ------------------------------ |
| Package manager   | `uv`                           |
| System dependency | `mediainfo`                    |
| Run tests         | `./test.sh` or `uv run pytest` |
| Coverage minimum  | 99% (enforced)                 |

## Tagging Logic

| Tag         | Meaning                                                |
| ----------- | ------------------------------------------------------ |
| `dub`       | All target languages present in all episodes           |
| `semi-dub`  | Missing some target languages or episodes              |
| `wrong-dub` | Contains unexpected languages (not original or target) |
| _(no tag)_  | Original language only                                 |

## Reference

- [Architecture & Data Flow](.claude/docs/architecture.md) - Package structure, data flow, key classes
- [Configuration](.claude/docs/configuration.md) - YAML structure, CLI options, env vars
- [Testing](.claude/docs/testing.md) - TDD approach, coverage requirements, mocking patterns
- [Example Config](taggarr.example.yaml)

---

## Maintaining This File

This file follows **progressive disclosure**. When modifying:

1. **Root file (this file)** - Only include what applies to _every single task_:
   - One-line project description
   - Package manager, system deps, test command
   - Hard constraints (coverage minimum)
   - Core domain concepts (tagging logic)

2. **Separate files** - Move everything else to `.claude/docs/`:
   - Detailed patterns → `testing.md`, `architecture.md`
   - Configuration details → `configuration.md`
   - New topic areas → create new `<topic>.md`

3. **Don't include**:
   - Instructions the agent already knows (e.g., "write clean code")
   - Information discoverable from code (e.g., "use pytest-mock" - visible in tests)
   - User-facing docs (installation guides belong in README)

4. **Link, don't inline** - If content exceeds 5 lines, put it in a separate file and link to it.
