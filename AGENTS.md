# AGENTS.md

This repository scores the ergonomics (RULA) of animated operators in a USD scene and writes a report and
dashboards. If you are an AI agent asked to assess operators, follow **`docs/AGENT_BRIEF.md`** step by step.

**If you create or change operator animation, read `docs/MOTION_RULES.md` first and keep every rule in mind while
you build each step.** No person passes through an object, the floor or another person. After every animation
change, run `tools/motion_check.py` on the baked scene and fix every error before anyone sees it.

| What | Where |
|---|---|
| Command line | `tools/ergo_scan.py` (`--list` first; prints JSON) |
| Motion QA (animation gate) | `tools/motion_check.py` (exit code 1 while errors are left); rules in `docs/MOTION_RULES.md`; Python: `ergo_scan/motion_qa.py` (`check_stage`, `check_pose`) |
| Python | `exts/ergo.scan/ergo_scan/scan.py`: `scan()` and `write_report()`; dashboards in `dash.py`; RULA tables in `rula.py` |
| Kit | extension `ergo.scan` (search path `<repo>/exts`): Window > Ergo Scan; scripts: `from ergo_scan import scan`; headless: `tools/kit_scan.py` |
| Offline installs | `wheels/` (usd-core, numpy, Pillow for Python 3.10-3.12, Windows) |
| Tests | `python -m pytest tests` |

Rules:
- Never show or score an animation that fails `motion_check.py`. The person reviewing must not have to point out
  clipping, impossible joints, arms behind the back or tools through the body.
- Use the tool's numbers. Don't edit the scoring to change a result.
- Report skipped or static operators plainly.
- Use red only for risk markers, E-stops and fire equipment. Never on equipment.
