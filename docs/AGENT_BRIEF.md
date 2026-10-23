# Brief for an AI agent: ergonomic assessment (RULA) of the operators in a scene

This repository is everything you need. Download it from GitHub (clone, or **Code > Download ZIP**). Nothing else
can be copied to this PC, and you do not need internet beyond that download.

---

## Your task

Assess the ergonomics of every operator in the scene `<SCENE>` (about 15 animated people) with RULA. Then:

- install the **Ergo Scan** Kit extension in our Kit app so people can run it from the window;
- produce the report and dashboards;
- show the risk markers in the viewport;
- tell me which operators and moments need changing, and why.

You are not writing the assessment. It is in this repository:

- the scan, in `exts/ergo.scan/ergo_scan/`;
- the window, in `extension.py`;
- the command lines, in `tools/`.

Use them as they are. Do not write your own angle maths or RULA tables, and do not edit the code to change a
score. If something does not work, fix the cause and tell me what you changed. If the scene's animation code
needs changing, that is a separate job: ask me first.

`<ERGO>` below is the folder where you put this repository.

## 1. Install the extension in our Kit app

The folder `<ERGO>/exts/ergo.scan` is a complete Kit extension. There is nothing to compile.

- **Quick:** in the Kit app, go to **Window > Extensions**, then the gear icon, then **Extension Search Paths**.
  Add `<ERGO>/exts`, search "Ergo Scan" and enable it (tick **Autoload** to keep it).
- **Permanent in our app:** add `"ergo.scan" = {}` to the `[dependencies]` of our app's `.kit` file, and add
  `<ERGO>/exts` to its `[settings.app.exts] folders`. If our app is built from kit-app-template, you can instead
  copy `exts/ergo.scan` into `source/extensions/` and rebuild.
- **Check:** **Window > Ergo Scan** appears. In the Script Editor, `from ergo_scan import scan` works.
- **Dependencies:** USD, numpy and the UI come with Kit. Pillow (PNG dashboards only) is usually in Kit too. If it
  is missing, the extension installs it from `<ERGO>/wheels` by itself, with no internet.

## 2. Find the operators

Open `<SCENE>` in the Kit app, then go to **Window > Ergo Scan** and click **List operators**.

- The window lists every character found. "ok" means all the joints the scan needs were recognised.
- Check the count matches the operators you expect.
- If an operator shows `missing ...`, its rig uses unusual joint names. Write a mapping (see section 6) and use
  the Python route.

## 3. Gather what a skeleton cannot show

Loads and repeated work don't appear in a skeleton.

- Read the animation code and the scene: which operators carry or hold weight (kg), and which do repeated cycles
  (ratcheting, drilling, more than ~4 times a minute)?
- Put them in the window: **Loads** `Operator_03:12, Operator_07:5` and **Repeated work** `Operator_02, Operator_09`.
- Leave a field empty if you don't know, and say so in your report. Do not guess weights.

## 4. Run the scan

1. Set **Every Nth frame** to 2 (plenty). Set **Frames from / to** if only part of the timeline matters.
2. Set **Output folder** (default: next to the scene).
3. Click **Run scan**. The window stays usable and shows progress per operator.
4. When it finishes, the table lists the operators worst first, with max, p90, time at 5+ and main driver.

Then use the other buttons:

- **go to worst** moves the timeline to that operator's worst moment and selects them. The tooltip says why and
  what to change.
- **Markers on / off** shows a sphere above each head, coloured by risk over time, plus dots on the back,
  shoulders and knees. The markers go on the session layer, so they are never saved into the scene.
- **Open dashboard** opens `ergo_dashboard.html` in the browser. **Open folder** opens all the outputs.
- **Live panel** (also **Window > Ergo Live**) shows one card per operator that updates while the timeline plays or
  is scrubbed. Each card has the RULA badge, band, angles, body parts coloured by score, and the last 20 s chart.
  It needs no scan first. It scores the pose in the stage at the current time, so it also follows animation your
  Python writes into USD while playing. It takes about 3 ms per frame for 15 operators.

### Without the window

From the Script Editor:

```python
import omni.usd
from ergo_scan import scan
res = scan.scan(omni.usd.get_context().get_stage(), "/World", step=2,
                loads={"Operator_03": 12}, repeated={"Operator_02"})
scan.write_report(res, r"<OUT>")
```

Headless from a terminal with Kit's own Python: see `tools/kit_scan.py`. It uses environment variables
`ERGO_SCENE`, `ERGO_OUT`, and so on.

A standalone Python 3.10-3.12 also works:

1. Install the packages: `pip install --no-index --find-links <ERGO>/wheels usd-core numpy pillow`.
2. Run `python <ERGO>/tools/ergo_scan.py "<SCENE>" --list`.
3. Then run `python <ERGO>/tools/ergo_scan.py "<SCENE>" --out="<OUT>" --step=2 --loads=... --repeated=...`.

## 5. Check the output is real before reporting

- **Static operators.** No operator should be marked **NOT MOVING** in the window, or "Not moving in the USD file"
  in the report. That marker means the motion is not stored as USD time samples.

  Our animation is written by Python scripts. If a script moves the characters while the timeline plays, instead
  of writing time samples, the scan sees one frozen pose. In that case:
  1. Make the script bake its result into USD time samples, or record a playback with Kit's Stage Recorder
     (Window > Stage Recorder), into a copy of the scene.
  2. Scan that copy.

  Never report a static operator's scores as an assessment.
- **Spot check.** Click **go to worst** for the top 2 operators and look at the viewport. Confirm the posture
  described ("trunk bent 50 deg, right arm raised 95 deg") is what you see. If it isn't, the joint mapping is
  wrong (section 6).
- **Skipped operators.** Explain any operator marked `skipped`.

## 6. Unusual rigs (only if List operators showed `missing`)

Find the operator's joint names: they are in the Skeleton prim's `joints` attribute. Then write the mapping for
the missing roles:

```python
mapping = {"Operator_07": {"pelvis": "Bip_Pelvis", "chest": "Bip_Spine2", "upperarm_l": "Bip_L_UpperArm"}}
res = scan.scan(stage, "/World", step=2, mapping=mapping)
```

The roles are:

- `pelvis`, `chest` (top of the spine), `neck`, `head`;
- `upperarm_l/r`, `forearm_l/r`, `hand_l/r`, `mid_l/r` (middle finger base; optional);
- `thigh_l/r`, `calf_l/r`, `foot_l/r`.

The command line takes the same mapping as a JSON file: `--mapping=map.json`.

## 7. What you get in the output folder (the dashboards)

| file | what it is |
|---|---|
| `ergo_dashboard.html` | **Main dashboard.** One file, works offline in any browser. It has: KPI tiles; the ranking (click an operator); RULA over time; body angles; the body part at risk; the worst moments with fixes; the floor map of where risky work happens. |
| `ergo_panel_worst.png` | Score panel at the worst moment. One card per operator with the score badge, band, angles, a body figure coloured by part, and the last 20 s chart. |
| `ergo_timeline.png` | Every operator's RULA over time, worst first. |
| `ergo_floor.png` | Plan view of where RULA 5-7 happens. |
| `ergo_report.md` / `.json` | Overview table, and worst moments with fixes. |
| `ergo_frames.csv` | Every scored frame: score, part scores, angles. |
| `ergo_overlay.usda` | The viewport markers. The window's **Markers on / off** loads them. |

Optional movie with the score panel beside each frame:

1. Render frames with Movie Capture (PNG, frame number in the name).
2. Run `scan`, then:

```python
from ergo_scan import dash
dash.composite_frames(res, r"<render folder>", r"<OUT>/frames_with_panel")
```

## 8. Reading the scores (RULA 1-7)

- **Bands:** 1-2 acceptable · 3-4 investigate · 5-6 change soon · 7 change now.
- **Walking empty-handed** is not a task posture, so it is capped at 2.
- **Main driver and fix:**

  | driver | fix |
  |---|---|
  | trunk bent | bring the work up or closer |
  | neck | raise or tilt the work |
  | arm raised | lower the work, or raise the operator |
  | deep knee bend | raise the part, or give a stool or creeper |
  | twist | rotate the fixture, or move the bin in front |

- **Rank by time as well as peak.** A long stretch at 5-6 matters more than a short spike to 7. Use "time at 5+"
  and the "lasts" seconds of each worst moment.

## 9. Report back to me

- The overview table from `ergo_report.md`.
- The 3 to 5 most important findings. For each: operator, time and frame, score, what the body is doing, and the
  fix in workplace terms.
- Which operators are fine (max 4 or below).
- Where the files are.
- The caveats:
  - loads and repetition you assumed or left out;
  - the scores describe the animated method, not measured people;
  - any skipped or static operators, and what you did about them.

## Rules

- Report the tool's numbers; never round a 5 down to "acceptable".
- Say plainly when something failed.
- Use red only for the risk markers and for E-stops and fire equipment. Never colour equipment red or orange: in
  our plant red means a quality issue.
