# ✅ TODO.md — Documentation Spiral Plan

## Current Focus
- [ ] Document `bezier_interpolate()` and `scale_handle()` in `interpolation.py`
- [ ] Add full class-level docstrings to `TimelineMobSlot` and `StaticMobSlot` in `mobslots.py`

## Next Modules
- [ ] `mobs.py` → focus on `CompositionMob`, `MasterMob`, `SourceMob`
- [ ] `file.py` → document `open()`, `save()`, and how metadata is handled

## Cleanup
- [ ] Filter built-ins from Critic warnings
- [ ] Archive `fastapi_summary.json`, `pyaaf2_callgraph.dot` if not in use

## Guidelines
- Use crisp, descriptive docstrings
- Do not alter logic (doc pass only)
- Each session should update this file

🧠 Use Codex to Modify It Between Sessions
At the end of every run, Codex can:

✅ Check off what it just documented

➕ Add new tasks based on critic suggestions

🧠 Reflect: “I saw a function used 20× but not documented — should I add that to TODO.md?”

🔁 Then Codex Updates AGENTS.md for Traceability
Every time Codex edits something, it appends:

### Session July 21
- Documented: `scale_handle()` and `bezier_interpolate()` in `interpolation.py`
- Updated: `TODO.md` to reflect completion
