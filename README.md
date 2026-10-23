# Ergo Scan

An ergonomic assessment (RULA) of every animated operator in an Omniverse / USD scene, with dashboards. It works
with one operator or dozens, on any common rig, in any up axis, units and frame rate.

```
python tools/ergo_scan.py C:/scenes/line.usd --list                  # who was found, joints recognised
python tools/ergo_scan.py C:/scenes/line.usd --out=C:/scenes/line_ergo --step=2 \
       --loads=Operator_03:12 --repeated=Operator_02                 # what the skeleton can't show
```

## What you get

- **`ergo_dashboard.html`**: one offline file with:
  - KPI tiles and an operator ranking (click one);
  - RULA over time and the body angles;
  - which body part is at risk;
  - the worst moments, with fixes;
  - a floor map of where risky work happens.
- **`ergo_panel_worst.png`**: a card per operator with the score badge, angles, a body figure coloured by body
  part, and the last 20 s chart. `--frames-dir=<rendered frames>` puts this panel beside every movie frame.
- **`ergo_timeline.png`** and **`ergo_floor.png`**.
- **`ergo_overlay.usda`**: sublayer it into the scene. It adds a marker above each head coloured by risk over time,
  and dots on the back, shoulders and knees.
- **`ergo_report.md` / `.json` / `ergo_frames.csv`**.

## How it scores

- **Operators.** Every `UsdSkel` skeleton under the root is an operator. Names are taken from the scene, for
  example `/World/Operator_07`.
- **Joints.** Joint names are recognised for Unreal-style, Mixamo, Reallusion CC / NVIDIA characters and SMPL
  rigs. For any other rig, use `--mapping=map.json`.
- **Angles.** They come from joint positions:
  - trunk flexion, side bend and twist;
  - neck;
  - upper arm (raised, abducted, shoulder up);
  - elbow, and the hand across the midline;
  - wrist against the bind pose;
  - knees (squatting or kneeling).
- **Bands.** RULA 1-7: 1-2 acceptable, 3-4 investigate, 5-6 change soon, 7 change now. Walking empty-handed is
  capped at 2.
- **Loads and repetition** are given per operator.

Scores describe the animated method, not measured people: use them to compare methods and find the bad steps.
Animation driven at runtime (Animation Graph, omni.anim.people behaviour scripts) is not stored in USD. The scan
flags those operators as not moving; record the motion first.

## Install

- **Outside Kit:** Python 3.10+ with `pip install usd-core numpy pillow`.
- **Inside Kit:** add `<repo>/exts` to the extension search paths and enable **ergo.scan**. Then open
  **Window > Ergo Scan**:
  - **List operators** and **Run scan**;
  - the ranking, worst first;
  - **go to worst**, which moves the timeline to the moment and selects the operator;
  - **Markers on / off**, on the session layer, so they are never saved into the scene;
  - **Open dashboard**.

  The same scan from the Script Editor:

  ```python
  import omni.usd
  from ergo_scan import scan
  res = scan.scan(omni.usd.get_context().get_stage(), "/World", step=2)
  scan.write_report(res, r"C:/out/ergo")
  ```

- **Headless with Kit's own Python:** use `tools/kit_scan.py`. Nothing needs installing.
- **Offline PCs:** everything is in this repository. `wheels/` holds usd-core, numpy and Pillow for Python
  3.10-3.12 on Windows: `pip install --no-index --find-links wheels usd-core numpy pillow`. Kit installs Pillow
  from there by itself if it is missing.

An AI agent doing an assessment should follow `docs/AGENT_BRIEF.md`.
