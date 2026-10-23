"""Run the scan inside Kit without the window (Kit has its own Python, USD and numpy: nothing to install).

    set ERGO_SCENE=C:/scenes/line.usd
    set ERGO_OUT=C:/scenes/line_ergo
    rem optional: ERGO_STEP=2  ERGO_ROOT=/World  ERGO_RANGE=0,1800  ERGO_LOADS=Operator_03:12  ERGO_REPEATED=Operator_02
    <kit app folder>\\kit\\kit.exe <kit app folder>\\apps\\<your app>.kit --no-window ^
        --ext-folder <repo>\\exts --enable ergo.scan --exec <repo>\\tools\\kit_scan.py

Writes the same report and dashboards as tools/ergo_scan.py, plus <ERGO_OUT>/kit_scan_done.json (summary or the
error), then quits Kit.
"""
import asyncio
import json
import os
import traceback

import omni.kit.app
import omni.usd


async def _frames(n):
    for _ in range(n):
        await omni.kit.app.get_app().next_update_async()


async def main():
    out = os.environ.get("ERGO_OUT") or os.path.join(os.path.expanduser("~"), "Documents", "ergo_scan")
    os.makedirs(out, exist_ok=True)
    done = {"out": out}
    try:
        from ergo_scan import scan as E
        from ergo_scan.extension import _parse_list, _parse_pairs
        await _frames(30)
        scene = os.environ["ERGO_SCENE"]
        ok, err = await omni.usd.get_context().open_stage_async(scene)
        if not ok:
            raise RuntimeError(f"could not open {scene}: {err}")
        await _frames(30)
        st = omni.usd.get_context().get_stage()
        rng = os.environ.get("ERGO_RANGE")
        res = E.scan(st, os.environ.get("ERGO_ROOT", "/World"), step=float(os.environ.get("ERGO_STEP", 2)),
                     frames=tuple(float(v) for v in rng.split(",")) if rng else None,
                     loads=_parse_pairs(os.environ.get("ERGO_LOADS", "")),
                     repeated=_parse_list(os.environ.get("ERGO_REPEATED", "")))
        summ = E.write_report(res, out)
        done["operators"] = [{k: s.get(k) for k in ("operator", "max", "p90", "main_driver", "skipped", "static")}
                             for s in summ]
    except Exception:
        done["error"] = traceback.format_exc()
    with open(os.path.join(out, "kit_scan_done.json"), "w") as f:
        json.dump(done, f, indent=1)
    omni.kit.app.get_app().post_quit()
    await _frames(60)
    os._exit(0)


asyncio.ensure_future(main())
