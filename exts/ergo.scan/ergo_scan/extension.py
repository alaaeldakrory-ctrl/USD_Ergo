"""Kit extension: Window > Ergo Scan. Scores every animated operator in the open stage (RULA), lists them worst
first, jumps to each one's worst moment, shows the risk markers in the viewport and opens the dashboards.

Everything the window does is also plain Python (ergo_scan.scan / ergo_scan.dash), so scripts and agents can run
the same scan without the window.
"""
import asyncio
import os
import webbrowser

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd

from . import scan as E

TITLE = "Ergo Scan"
BAND_COLOR = {"acceptable": 0xFF50AA2E, "investigate": 0xFF1EC8F0, "change soon": 0xFF1E78F5,
              "change now": 0xFF2828D7}          # ABGR


def _parse_pairs(text):
    out = {}
    for part in (text or "").replace(";", ",").split(","):
        if ":" in part:
            k, v = part.rsplit(":", 1)
            try:
                out[k.strip()] = float(v)
            except ValueError:
                carb.log_warn(f"[ergo.scan] load '{part}' is not name:kg")
    return out


def _parse_list(text):
    return [p.strip() for p in (text or "").replace(";", ",").split(",") if p.strip()]


def default_out_dir(stage):
    path = stage.GetRootLayer().realPath if stage else ""
    if path and os.path.isfile(path):
        return os.path.splitext(path)[0] + "_ergo"
    return os.path.join(os.path.expanduser("~"), "Documents", "ergo_scan")


class ErgoWindow:
    def __init__(self):
        self.res = None
        self.summary = []
        self.out_dir = ""
        self._task = None
        self.window = ui.Window(TITLE, width=700, height=720)
        self.window.frame.set_build_fn(self._build)

    # ------------------------------------------------------------------------------------------------ layout
    def _build(self):
        st = omni.usd.get_context().get_stage()
        with ui.ScrollingFrame():
            with ui.VStack(spacing=6, height=0):
                ui.Label("Ergonomic scan (RULA) of every animated operator in the open stage", height=20)
                with ui.HStack(height=22):
                    ui.Label("Root prim", width=130)
                    self.m_root = ui.StringField().model
                    self.m_root.set_value(str(st.GetDefaultPrim().GetPath()) if st and st.GetDefaultPrim() else "/World")
                with ui.HStack(height=22):
                    ui.Label("Every Nth frame", width=130)
                    self.m_step = ui.IntField(width=60).model
                    self.m_step.set_value(2)
                    ui.Label("  Frames from / to (empty = whole stage)", width=250)
                    self.m_from = ui.StringField(width=60).model
                    self.m_to = ui.StringField(width=60).model
                with ui.HStack(height=22):
                    ui.Label("Loads (name:kg, ...)", width=130)
                    self.m_loads = ui.StringField().model
                with ui.HStack(height=22):
                    ui.Label("Repeated work (names)", width=130)
                    self.m_rep = ui.StringField().model
                with ui.HStack(height=22):
                    ui.Label("Output folder", width=130)
                    self.m_out = ui.StringField().model
                    self.m_out.set_value(default_out_dir(st))
                with ui.HStack(height=28, spacing=6):
                    ui.Button("List operators", clicked_fn=self.list_operators)
                    ui.Button("Run scan", clicked_fn=self.run)
                    ui.Button("Markers on / off", clicked_fn=self.toggle_markers)
                    ui.Button("Open dashboard", clicked_fn=self.open_dashboard)
                    ui.Button("Open folder", clicked_fn=self.open_folder)
                    ui.Button("Live panel", clicked_fn=self.open_live)
                self.progress = ui.ProgressBar(height=14).model
                self.status = ui.Label("", height=40, word_wrap=True)
                self.table = ui.VStack(spacing=2, height=0)
                self._fill_table()

    def _fill_table(self):
        self.table.clear()
        with self.table:
            if not self.summary:
                ui.Label("No scan yet. 'List operators' shows who was found; 'Run scan' scores them.", height=20)
                return
            with ui.HStack(height=20):
                for t, w in (("operator", 190), ("max", 40), ("p90", 40), ("time at 5+", 80), ("main driver", 140)):
                    ui.Label(t, width=w, style={"color": 0xFF9AA0A6})
            for s in self.summary:
                with ui.HStack(height=24, spacing=4):
                    ui.Label(s["operator"], width=180, elided_text=True, tooltip=s.get("path", ""))
                    if "skipped" in s:
                        ui.Label(f"skipped: {s['skipped']}", style={"color": 0xFF1EC8F0})
                        continue
                    b = E.band(s["max"])
                    with ui.ZStack(width=34):
                        ui.Rectangle(style={"background_color": BAND_COLOR[b], "border_radius": 4})
                        ui.Label(str(s["max"]), alignment=ui.Alignment.CENTER,
                                 style={"color": 0xFFFFFFFF if s["max"] >= 5 else 0xFF111111})
                    ui.Spacer(width=6)
                    ui.Label(str(s["p90"]), width=40)
                    hi = s["band_pct"]["change soon"] + s["band_pct"]["change now"]
                    ui.Label(f"{hi:.0f}%", width=80)
                    ui.Label(("NOT MOVING " if s.get("static") else "") + s["main_driver"], width=140, elided_text=True)
                    w = s["worst"][0] if s["worst"] else None
                    ui.Button("go to worst", width=96, enabled=w is not None,
                              tooltip=f"{w['t']:.1f} s: {w['why']}. Fix: {w['fix']}" if w else "",
                              clicked_fn=lambda s=s, w=w: self.go_to(s, w))

    # ------------------------------------------------------------------------------------------------ actions
    def _opts(self):
        def num(m):
            try:
                return float(m.get_value_as_string())
            except ValueError:
                return None
        a, b = num(self.m_from), num(self.m_to)
        return dict(root=self.m_root.get_value_as_string() or "/World", step=max(1, self.m_step.get_value_as_int()),
                    frames=(a, b) if a is not None and b is not None else None,
                    loads=_parse_pairs(self.m_loads.get_value_as_string()),
                    repeated=_parse_list(self.m_rep.get_value_as_string()))

    def list_operators(self):
        st = omni.usd.get_context().get_stage()
        if not st:
            self.status.text = "No stage open."
            return
        from pxr import Usd, UsdSkel
        cache = UsdSkel.Cache()
        lines = []
        for name, sr, sk in E.find_operators(st, self._opts()["root"]):
            cache.Populate(UsdSkel.Root(sr), Usd.TraverseInstanceProxies())
            q = cache.GetSkelQuery(UsdSkel.Skeleton(sk))
            idx = E.map_joints([str(j) for j in q.GetJointOrder()])
            miss = [r for r in E.REQUIRED if r not in idx]
            lines.append(f"{name}: {'ok' if not miss else 'missing ' + ', '.join(miss)}")
        self.status.text = (f"{len(lines)} operators found. " + "; ".join(lines))[:1500] if lines else \
            "No animated characters (UsdSkel skeletons) under the root prim."

    def run(self):
        if self._task and not self._task.done():
            self.status.text = "A scan is already running."
            return
        self._task = asyncio.ensure_future(self._run())

    async def _run(self):
        st = omni.usd.get_context().get_stage()
        if not st:
            self.status.text = "No stage open."
            return
        o = self._opts()
        self.out_dir = self.m_out.get_value_as_string() or default_out_dir(st)
        app = omni.kit.app.get_app()
        res = None
        try:
            for ev in E.scan_iter(st, o["root"], o["step"], o["frames"], o["loads"], o["repeated"],
                                  log=lambda m: carb.log_info(f"[ergo.scan] {m}")):
                if ev[0] == "done":
                    res = ev[1]
                    break
                _, name, i, n, frac = ev
                self.progress.set_value((i + frac) / max(1, n))
                self.status.text = f"Scoring {name} ({i + 1} of {n}) ..."
                await app.next_update_async()
            self.status.text = "Writing the report and dashboards ..."
            await app.next_update_async()
            self.res = res
            self.summary = E.write_report(res, self.out_dir)
        except Exception as e:                                       # shown in the window, full trace in the log
            import traceback
            carb.log_error(f"[ergo.scan] {traceback.format_exc()}")
            self.status.text = f"Scan failed: {e}"
            return
        self.progress.set_value(1.0)
        scored = [s for s in self.summary if "skipped" not in s]
        bad = [s["operator"] for s in scored if s["max"] >= 5]
        warn = [s["operator"] for s in self.summary if "skipped" in s or s.get("static")]
        self.status.text = (f"{len(scored)} operators scored; {len(bad)} reach 5+ (change soon / now). "
                            + (f"Check: {', '.join(warn)} (skipped or not moving). " if warn else "")
                            + f"Report: {self.out_dir}")
        self._fill_table()

    def go_to(self, s, w):
        """Timeline to the worst moment, the operator selected."""
        import omni.timeline
        st = omni.usd.get_context().get_stage()
        tl = omni.timeline.get_timeline_interface()
        tl.pause()
        tl.set_current_time(w["frame"] / (st.GetTimeCodesPerSecond() or 24.0))
        omni.usd.get_context().get_selection().set_selected_prim_paths([s["path"]], True)
        self.status.text = (f"{s['operator']} at {w['t']:.1f} s (frame {w['frame']:g}): RULA {w['rula']} - {w['why']}. "
                            f"Fix: {w['fix']}.")

    def toggle_markers(self):
        """The overlay layer on the session layer: seen in the viewport, never saved into the scene file."""
        st = omni.usd.get_context().get_stage()
        path = os.path.join(self.out_dir or self.m_out.get_value_as_string(), "ergo_overlay.usda").replace("\\", "/")
        if not st:
            return
        sess = st.GetSessionLayer()
        subs = list(sess.subLayerPaths)
        if path in subs:
            sess.subLayerPaths.remove(path)
            self.status.text = "Markers off."
        elif os.path.isfile(path):
            sess.subLayerPaths.append(path)
            self.status.text = "Markers on: sphere above each operator coloured by RULA band, dots on back / shoulders / knees."
        else:
            self.status.text = "No markers yet - run the scan first."

    def open_dashboard(self):
        p = os.path.join(self.out_dir or self.m_out.get_value_as_string(), "ergo_dashboard.html")
        if os.path.isfile(p):
            webbrowser.open("file:///" + p.replace("\\", "/"))
        else:
            self.status.text = "No dashboard yet - run the scan first."

    def open_live(self):
        """Window > Ergo Live, with this window's root prim, loads and repeated work."""
        o = self._opts()
        w = show_live()
        if w is not None:
            w.reset(o["root"], o["loads"], o["repeated"])

    def open_folder(self):
        p = self.out_dir or self.m_out.get_value_as_string()
        if os.path.isdir(p):
            os.startfile(p)

    def destroy(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self.window.destroy()
        self.window = None


class ErgoScanExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._window = None
        self._menu = None
        try:
            import omni.kit.menu.utils as mu
            from omni.kit.menu.utils import MenuItemDescription
            self._menu = [MenuItemDescription(name=TITLE, onclick_fn=self.show),
                          MenuItemDescription(name="Ergo Live", onclick_fn=self.show_live)]
            mu.add_menu_items(self._menu, "Window")
        except ImportError:                                           # an app without the menu: E.show() from a script
            carb.log_warn("[ergo.scan] no omni.kit.menu.utils: open the window with ergo_scan.extension.show()")
        ui.Workspace.set_show_window_fn(TITLE, lambda visible: self.show() if visible else None)
        self._live = None
        global _EXT
        _EXT = self

    def show(self, *_):
        if self._window is None:
            self._window = ErgoWindow()
        self._window.window.visible = True
        self._window.window.focus()
        return self._window

    def show_live(self, *_):
        from .live import LiveWindow
        if self._live is None:
            self._live = LiveWindow()
        self._live.window.visible = True
        self._live.window.focus()
        return self._live

    def on_shutdown(self):
        global _EXT
        _EXT = None
        if self._menu:
            import omni.kit.menu.utils as mu
            mu.remove_menu_items(self._menu, "Window")
        ui.Workspace.set_show_window_fn(TITLE, None)
        if self._window:
            self._window.destroy()
            self._window = None
        if self._live:
            self._live.destroy()
            self._live = None


_EXT = None


def show():
    """Open the window from a script: ergo_scan.extension.show() -> the ErgoWindow."""
    return _EXT.show() if _EXT else None


def show_live():
    """Open the live panel from a script: ergo_scan.extension.show_live() -> the LiveWindow."""
    return _EXT.show_live() if _EXT else None
