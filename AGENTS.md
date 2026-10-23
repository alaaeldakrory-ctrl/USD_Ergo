# AGENTS.md

This repository scores the ergonomics (RULA) of animated operators in a USD scene and writes a report and
dashboards. If you are an AI agent asked to assess operators, follow **`docs/AGENT_BRIEF.md`** step by step.

| What | Where |
|---|---|
| Command line | `tools/ergo_scan.py` (`--list` first; prints JSON) |
| Python | `exts/ergo.scan/ergo_scan/scan.py`: `scan()` and `write_report()`; dashboards in `dash.py`; RULA tables in `rula.py` |
| Kit | extension `ergo.scan` (search path `<repo>/exts`): Window > Ergo Scan; scripts: `from ergo_scan import scan`; headless: `tools/kit_scan.py` |
| Offline installs | `wheels/` (usd-core, numpy, Pillow for Python 3.10-3.12, Windows) |
| Tests | `python -m pytest tests` |

Rules:
- Use the tool's numbers. Don't edit the scoring to change a result.
- Report skipped or static operators plainly.
- Use red only for risk markers, E-stops and fire equipment. Never on equipment.
