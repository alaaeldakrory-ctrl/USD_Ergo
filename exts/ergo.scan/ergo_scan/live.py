"""Window > Ergo Live: the score panel live in Kit. One card per operator, updated while the timeline plays (or when
you scrub). Each card shows:
- the RULA badge and band;
- back, neck, arm, elbow and knee angles;
- the body parts coloured by their score;
- the last 20 s as a chart.

It scores the pose in the stage at the current time, so no scan is needed first.
"""
import omni.kit.app
import omni.timeline
import omni.ui as ui
import omni.usd

from . import scan as E

TITLE = "Ergo Live"
BAND = {"acceptable": 0xFF50AA2E, "investigate": 0xFF1EC8F0, "change soon": 0xFF1E78F5, "change now": 0xFF2828D7}
GREEN, YELLOW, RED = 0xFF50AA2E, 0xFF1EC8F0, 0xFF2828D7
PARTS = (("back", "trunk_s"), ("neck", "neck_s"), ("arms", "upper_arm_s"), ("legs", "legs_s"))
DIM = 0xFF9AA0A6
HISTORY = 60                                    # chart bars (about 20 s: one bar every ~8 frames at 24 fps)


def part_color(key, s):
    g, y = E.PART_LIMITS[key]
    return GREEN if s <= g else YELLOW if s <= y else RED


class LiveWindow:
    def __init__(self, root="/World", loads=None, repeated=()):
        self.root, self.loads, self.repeated = root, loads or {}, repeated
        self.live = None
        self.cards, self.hist = {}, {}
        self._last = None
        self._tick = 0
        self.window = ui.Window(TITLE, width=1000, height=760)
        self.window.frame.set_build_fn(self._build)
        self._sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="ergo live")

    def reset(self, root=None, loads=None, repeated=None):
        """Pick up the operators of the stage now open (another scene, other loads)."""
        if root is not None:
            self.root = root
        if loads is not None:
            self.loads = loads
        if repeated is not None:
            self.repeated = repeated
        self.live = None
        self._last = None
        self.window.frame.rebuild()

    def _build(self):
        st = omni.usd.get_context().get_stage()
        self.cards, self.hist = {}, {}
        with ui.VStack(spacing=4):
            with ui.HStack(height=26, spacing=6):
                ui.Label("Ergonomics (RULA) - live", style={"font_size": 20})
                ui.Button("Re-read operators", width=140, clicked_fn=lambda: self.reset())
            self.sub = ui.Label("", height=18, style={"color": DIM})
            if not st:
                self.sub.text = "No stage open."
                return
            try:
                self.live = E.LiveScorer(st, self.root, self.loads, self.repeated)
            except Exception as e:
                self.sub.text = f"Could not read operators: {e}"
                return
            if not self.live.ops:
                self.sub.text = "No animated characters (UsdSkel skeletons) under " + self.root
                return
            with ui.ScrollingFrame():
                with ui.VGrid(column_width=320, row_height=176, spacing=6):
                    for op in self.live.ops:
                        self._card(op["name"])
        self._last = None

    def _card(self, name):
        c = {}
        with ui.ZStack(width=314, height=170):
            ui.Rectangle(style={"background_color": 0xFF2B2522, "border_radius": 8, "border_width": 1,
                                "border_color": 0xFF48403C})
            with ui.VStack(spacing=2):
                ui.Spacer(height=4)
                with ui.HStack(height=20):
                    ui.Spacer(width=8)
                    ui.Label(name, elided_text=True, style={"font_size": 16})
                with ui.HStack(height=56, spacing=6):
                    ui.Spacer(width=6)
                    with ui.ZStack(width=52, height=52):
                        c["badge"] = ui.Rectangle(style={"background_color": GREEN, "border_radius": 8})
                        c["score"] = ui.Label("-", alignment=ui.Alignment.CENTER, style={"font_size": 30})
                    with ui.VStack(spacing=0):
                        c["band"] = ui.Label("", height=18, style={"font_size": 14})
                        c["ang1"] = ui.Label("", height=16, style={"color": DIM, "font_size": 13})
                        c["ang2"] = ui.Label("", height=16, style={"color": DIM, "font_size": 13})
                with ui.HStack(height=16, spacing=4):
                    ui.Spacer(width=6)
                    c["parts"] = {}
                    for label, key in PARTS:
                        with ui.ZStack(width=68):
                            c["parts"][key] = ui.Rectangle(style={"background_color": GREEN, "border_radius": 3})
                            ui.Label(label, alignment=ui.Alignment.CENTER,
                                     style={"color": 0xFF111111, "font_size": 12})
                with ui.HStack(height=60):
                    ui.Spacer(width=6)
                    c["plot"] = ui.Plot(ui.Type.HISTOGRAM, 0.0, 7.0, *([0.0] * HISTORY), width=298, height=56,
                                        style={"color": GREEN, "background_color": 0xFF161412})
                ui.Label("   last 20 s", height=12, style={"color": DIM, "font_size": 11})
        self.cards[name] = c
        self.hist[name] = []

    def _on_update(self, e):
        if not self.live or not self.window or not self.window.visible:
            return
        self._tick += 1
        tl = omni.timeline.get_timeline_interface()
        tc = tl.get_current_time() * tl.get_time_codes_per_seconds()
        if self._last is not None and abs(tc - self._last) < 1e-6:
            return
        if tl.is_playing() and self._tick % 2:                 # every other app frame while playing is plenty
            return
        back = self._last is not None and tc < self._last
        step = 1.0 if self._last is None else abs(tc - self._last)
        self._last = tc
        try:
            rows = self.live.at(tc)
        except Exception as ex:
            self.sub.text = f"Scoring failed at frame {tc:g}: {ex}"
            return
        worst = 0
        every = max(1, int(round(20.0 * self.live.fps / HISTORY / max(step, 1.0))))
        for name, r in rows.items():
            c = self.cards.get(name)
            if not c:
                continue
            s = r["score"]
            worst = max(worst, s)
            b = E.band(s)
            c["badge"].set_style({"background_color": BAND[b], "border_radius": 8})
            c["score"].text = str(s)
            c["score"].set_style({"font_size": 30, "color": 0xFFFFFFFF if s >= 5 else 0xFF111111})
            c["band"].text = b.upper() + ("  (walking)" if r["walking"] else "")
            c["band"].set_style({"font_size": 14, "color": BAND[b]})
            g = lambda v: f"{round(v) + 0:d}"                   # noqa: E731
            c["ang1"].text = f"back {g(r['trunk_deg'])}°   neck {g(r['neck_deg'])}°"
            c["ang2"].text = f"arm {g(r['upper_arm_deg'])}°  elbow {g(r['elbow_deg'])}°  knee {g(r['knee_deg'])}°"
            for key, rect in c["parts"].items():
                rect.set_style({"background_color": part_color(key, r[key]), "border_radius": 3})
            h = self.hist[name]
            if back:
                h.clear()
            if not h or self._tick % every == 0 or back:
                h.append(float(s))
                del h[:-HISTORY]
            c["plot"].set_data(*([0.0] * (HISTORY - len(h)) + h))
            c["plot"].set_style({"color": BAND[b], "background_color": 0xFF161412})
        fps = self.live.fps
        self.sub.text = (f"t = {tc / fps:6.1f} s   frame {tc:g}   {len(rows)} operators   worst now: {worst}"
                         + (f"   skipped (joints not recognised): {', '.join(self.live.skipped)}"
                            if self.live.skipped else ""))

    def destroy(self):
        self._sub = None
        if self.window:
            self.window.destroy()
            self.window = None
