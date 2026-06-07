# Progress Log

## How to use this file
At the end of every work block, append a new session entry below.
The next session MUST read the most recent entry before doing anything.

---

## Session 0 — Project initialized
**Date**: 2025-06-07 (night before hackathon)
**Status**: Files created, no code written yet.

### What exists
- `CLAUDE.md` — full project spec, stack, contracts, scoring rubric
- `GOALS.md` — 7 phases, 25 goal items, ordered
- `PROGRESS.md` — this file
- `src/`, `assets/` directory structure created

### What does NOT exist yet
- No Python code
- No frontend code
- No MuJoCo Menagerie clone
- No H1 GLB asset
- No splat file (captured tomorrow morning at Fordham)

### Next session must start here
Read GOALS.md. Begin at **Goal 1.1**. Do not skip ahead.

### Known decisions made before coding started
- Stack is finalized: MuJoCo + SB3 PPO + FastAPI WS + Three.js
- H1 joint order is locked (see CLAUDE.md)
- Observation space is 47-dim (see CLAUDE.md)
- Splat file won't exist until morning — all code must gracefully handle its absence
- If `assets/h1.glb` is missing, frontend shows capsule placeholder — do not block on asset

### Blockers
None yet.

---

<!-- New sessions: append below this line -->
