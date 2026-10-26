"""Motion QA: the rules every animated operator has to keep (docs/MOTION_RULES.md), checked frame by frame on the
USD scene itself - so an animation is fixed before anyone has to look at it.

    from ergo_scan import motion_qa as Q
    res = Q.check_stage(stage, "/World", step=2)          # every operator, every 2nd frame
    Q.write_report(res, out_dir)                          # motion_qa.md / .json: what broke, where, how to fix
    res["ok"]                                             # False while any error is left

    issues = Q.check_pose(J)                              # one pose before it is written: {code: (value, limit)}

Positions only (Y-up cm, any rig the scan recognises): the same judge for every character, every tool. Errors are
things no person can or would do; warnings are things to look at.
"""
import json
import math
import os

import numpy as np

from . import scan as S

# code: (severity, what it means, how to fix it in the animation)
RULES = {
    "joint_range": ("error", "a joint past what a person can reach",
                    "keep the pose inside the joint ranges in MOTION_RULES.md; move the target, not the joint"),
    "inside_equipment": ("error", "a body part inside a fixture, bench, panel or machine",
                         "step the operator back or to the side, or bring the work closer so the body need not lean "
                         "into it; legs and feet count as much as the chest"),
    "through_floor": ("error", "a knee, hip or foot below the floor",
                      "kneeling: the knee joint sits a kneecap (~5 cm) above the floor and the hips above the knee"),
    "held_object_in_body": ("error", "a carried or held object (tool, part, box) passing through the trunk or legs",
                            "carry it at the side, turned out, or tipped down; route it around the knee on the way"),
    "arm_behind_back": ("error", "an elbow or wrist drawn behind the back",
                        "nobody works with the arms behind the back: turn the body or move the work in front"),
    "operators_overlap": ("error", "this operator's body passing through another operator's body",
                          "no person ever passes through another: give each station its own floor space, or time "
                          "their moves so they never share the same place"),
    "snap": ("error", "a joint jumps faster than a person moves (a pop between frames)",
             "blend between poses over at least 0.2 s; never switch targets in one frame"),
    "foot_slide": ("warning", "a planted foot sliding along the floor",
                   "keep a standing foot fixed until it steps; step instead of gliding"),
    "arm_held_up": ("warning", "an idle arm held up and bent at rest",
                    "a free arm hangs relaxed (elbow ~20-30 deg), hand by the thigh"),
}
LIMITS = {"knee_floor_cm": 3.0,       # knee joint lowest (its kneecap ~5 cm above the floor; 2 cm of slack)
          "hip_floor_cm": 20.0, "foot_below_cm": 4.0,
          "behind_elbow_cm": 19.0, "behind_wrist_cm": 10.0,
          "held_in_body_cm": 2.0, "inside_cm": 2.0, "overlap_cm": 2.0,
          "snap_cm_s": {"hand": 650.0, "foot": 650.0, "head": 400.0, "pelvis": 350.0},
          "slide_cm_s": (4.0, 40.0), "slide_s": 0.3,
          "idle_elbow_deg": 60.0, "idle_still_cm_s": 8.0}
BODY_CAPSULES = [c for c in S.ROLE_CAPSULES if not c[0].startswith(("upperarm", "forearm", "head"))]   # (the hands
# hold things; a hard hat or glasses modelled as a separate mesh moves with the head)


def check_pose(J, rest=None, floor=0.0, ankle=8.0):
    """Rules one pose breaks on its own (no scene needed): {code_part: (value, limit)}. J: role -> Y-up cm positions
    (scan.map_joints roles); floor: the floor's height (cm); ankle: the ankle joint's height when standing (cm)."""
    out = {f"joint_range:{k}": v for k, v in S.anatomy(J, rest).items()}
    for s in "lr":
        kn = float(J[f"calf_{s}"][1]) - floor
        if kn < LIMITS["knee_floor_cm"]:
            out[f"through_floor:knee_{s}"] = (round(kn, 1), LIMITS["knee_floor_cm"])
        ft = float(J[f"foot_{s}"][1]) - floor
        if ft < ankle - LIMITS["foot_below_cm"] - 6.0:          # (a tucked toe drops the ankle a little)
            out[f"through_floor:foot_{s}"] = (round(ft, 1), round(ankle - LIMITS["foot_below_cm"] - 6.0, 1))
    hp = float(J["pelvis"][1]) - floor
    if hp < LIMITS["hip_floor_cm"]:
        out["through_floor:pelvis"] = (round(hp, 1), LIMITS["hip_floor_cm"])
    hip, ch = J["pelvis"], J["chest"]
    up_t = S._unit(ch - hip)
    left = J["thigh_l"] - J["thigh_r"]
    left = S._unit(np.array([left[0], 0.0, left[2]]))
    fwd = S._unit(S._perp(np.cross(left, S.UP), up_t))                 # the chest's forward, level with the trunk
    for s in "lr":
        sh = J[f"upperarm_{s}"]
        be = -float(np.dot(J[f"forearm_{s}"] - sh, fwd))
        bw = -float(np.dot(J[f"hand_{s}"] - sh, fwd))
        if be > LIMITS["behind_elbow_cm"] or bw > LIMITS["behind_wrist_cm"]:
            out[f"arm_behind_back:arm_{s}"] = (round(max(be, bw), 1), LIMITS["behind_wrist_cm"])
    return out


def _capsule_pen(pts, J, capsules=BODY_CAPSULES):
    """{part: cm} the points reach into the body's capsules."""
    out = {}
    if not len(pts):
        return out
    for a, b, r, n, frac in capsules:
        if a not in J or b not in J:
            continue
        pa, pb = np.asarray(J[a], float), np.asarray(J[b], float)
        if a == b:
            pa = pb = pa + np.array([0.0, 8.0, 0.0])
        ab = (pb - pa) * frac
        u = np.clip(((pts - pa) @ ab) / max(float(ab @ ab), 1e-9), 0.0, 1.0)
        pen = r - float(np.min(np.linalg.norm(pts - (pa + np.outer(u, ab)), axis=1)))
        if pen > 0.0:
            q = a.rsplit("_", 1)[0] if a.endswith(("_l", "_r")) else a
            out[q] = max(out.get(q, 0.0), pen)
    return out


def check_stage(stage, root="/World", step=2, frames=None, mapping=None, only=None, floor=None, log=print):
    """Every operator under root, frame by frame. floor: the floor height in cm (default: the stage's 0)."""
    from pxr import Usd, UsdGeom, UsdSkel
    from .collide import SceneGeometry, body_points, region_around
    conv, k, zup = S._to_cm_yup(stage)
    t0, t1 = frames or (stage.GetStartTimeCode(), stage.GetEndTimeCode())
    fps = stage.GetTimeCodesPerSecond() or 24.0
    times = list(np.arange(t0, max(t0, t1) + 1e-6, step))
    dt = step / fps
    fl = float(floor or 0.0)
    found = [f for f in S.find_operators(stage, root) if not only or f[0] in only]
    start = stage.GetPrimAtPath(root) if root else stage.GetPseudoRoot()

    def top_of(prim):
        p = prim
        while p.GetParent() and p.GetParent().GetPath() != start.GetPath():
            p = p.GetParent()
        return p.GetPath().pathString
    exclude = tuple(top_of(sr) for _, sr, _ in found)
    cache = UsdSkel.Cache()
    xc = UsdGeom.XformCache()
    ops, tracks = [], {}
    for name, sr, sk in found:
        cache.Populate(UsdSkel.Root(sr), Usd.TraverseInstanceProxies())
        q = cache.GetSkelQuery(UsdSkel.Skeleton(sk))
        joints = [str(j) for j in q.GetJointOrder()]
        ov = mapping.get(name, mapping) if mapping else None
        ov = ov if isinstance(ov, dict) and all(isinstance(v, str) for v in ov.values()) else None
        idx = S.map_joints(joints, ov)
        missing = [r for r in S.REQUIRED if r not in idx]
        op = {"name": name, "skelroot": str(sr.GetPath()), "missing": missing, "issues": [], "frames": 0}
        ops.append(op)
        if missing:
            log(f"{name}: skipped - joints not recognised: {missing}")
            continue
        bind = q.GetJointWorldBindTransforms()
        Jb = {r: conv(np.array(bind[i].ExtractTranslation())) for r, i in idx.items()}
        arest = S.anatomy_rest(Jb)
        ankle = float(np.clip(min(Jb["foot_l"][1], Jb["foot_r"][1]), 4.0, 15.0))
        seq = []
        for t in times:
            xc.SetTime(Usd.TimeCode(float(t)))
            W = q.ComputeJointWorldTransforms(xc)
            seq.append({r: conv(np.array(W[i].ExtractTranslation())) for r, i in idx.items()})
        tracks[name] = seq
        region = region_around([J["pelvis"] for J in seq[::max(1, len(seq) // 40)]])
        geo = SceneGeometry(stage, region, exclude)
        own = top_of(sr)                                             # what this operator carries can sit under its
        props = SceneGeometry(stage, region, tuple(e for e in exclude if e != own))   # own branch (not the body)
        fields, rows = {}, []
        for n, (t, J) in enumerate(zip(times, seq)):
            hits = dict(check_pose(J, arest, fl, ankle))
            b = 2.0 * fps                                            # the equipment where it stands around now
            key = int(t // b) * b + b / 2
            if key not in fields:
                fields.clear()
                fields[key] = geo.field_at(key)
            pts, rad, part = body_points(J, capsules=S.ROLE_CAPSULES)
            pen = fields[key].penetration((pts, rad, part))
            worst = {}
            for p_, q_ in zip(pen, part):
                if p_ > LIMITS["inside_cm"]:
                    worst[q_] = max(worst.get(q_, 0.0), float(p_))
            for q_, p_ in worst.items():
                hits[f"inside_equipment:{q_}"] = (round(p_, 1), LIMITS["inside_cm"])
            for q_, p_ in _held(props, t, J, fps).items():                # what the hands carry, against the body
                if p_ > LIMITS["held_in_body_cm"]:
                    hits[f"held_object_in_body:{q_}"] = (round(p_, 1), LIMITS["held_in_body_cm"])
            if n:                                                    # snaps and sliding feet
                P = seq[n - 1]
                for r_, lim in (("hand_l", "hand"), ("hand_r", "hand"), ("foot_l", "foot"), ("foot_r", "foot"),
                                ("head", "head"), ("pelvis", "pelvis")):
                    v = float(np.linalg.norm(J[r_] - P[r_])) / dt
                    if v > LIMITS["snap_cm_s"][lim]:
                        hits[f"snap:{r_}"] = (round(v), LIMITS["snap_cm_s"][lim])
                for s in "lr":
                    f0, f1 = P[f"foot_{s}"], J[f"foot_{s}"]
                    low = max(f0[1], f1[1]) - fl < ankle + 3.0 and abs(f1[1] - f0[1]) / dt < 5.0
                    vh = float(np.hypot(*(f1 - f0)[[0, 2]])) / dt
                    if low and LIMITS["slide_cm_s"][0] < vh < LIMITS["slide_cm_s"][1]:
                        hits[f"foot_slide:foot_{s}"] = (round(vh, 1), LIMITS["slide_cm_s"][0])
                for s in "lr":                                       # an idle arm held up: still, bent, not working
                    e = S._ang(J[f"forearm_{s}"] - J[f"upperarm_{s}"], J[f"hand_{s}"] - J[f"forearm_{s}"])
                    still = float(np.linalg.norm(J[f"hand_{s}"] - J["pelvis"] - (P[f"hand_{s}"] - P["pelvis"]))) / dt
                    low_hand = J[f"hand_{s}"][1] < J["pelvis"][1] + 25.0
                    if e > LIMITS["idle_elbow_deg"] and still < LIMITS["idle_still_cm_s"] and low_hand and                             not _near(fields[key], J[f"hand_{s}"]) and not _holding(props, t, J[f"hand_{s}"]):
                        hits[f"arm_held_up:arm_{s}"] = (round(e), LIMITS["idle_elbow_deg"])
            rows.append((float(t), hits))
        op["frames"] = len(rows)
        op["issues"] = _ranges(rows, fps, dt)
        log(f"{name}: {len(rows)} frames, {sum(1 for i in op['issues'] if i['severity'] == 'error')} errors, "
            f"{sum(1 for i in op['issues'] if i['severity'] == 'warning')} warnings")
    names = [n for n in tracks]                                      # operators in each other's space
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            A, B = tracks[names[a]], tracks[names[b]]
            rows = []
            for t, Ja, Jb_ in zip(times, A, B):
                d = _bodies_overlap(Ja, Jb_) if float(np.linalg.norm(Ja["pelvis"] - Jb_["pelvis"])) < 250.0 else 0.0
                rows.append((float(t), {f"operators_overlap:{names[b]}": (round(d, 1), LIMITS["overlap_cm"])}
                             if d > LIMITS["overlap_cm"] else {}))
            for i in _ranges(rows, fps, dt):
                next(o for o in ops if o["name"] == names[a])["issues"].append(i)
    n_err = sum(1 for o in ops for i in o["issues"] if i["severity"] == "error")
    return {"stage": os.path.basename(stage.GetRootLayer().identifier), "fps": fps, "step": step, "range": [t0, t1],
            "floor_cm": fl, "operators": ops, "errors": n_err,
            "warnings": sum(1 for o in ops for i in o["issues"] if i["severity"] == "warning"), "ok": n_err == 0}


def _bodies_overlap(Ja, Jb):
    """cm two bodies' outlines (every capsule, arms and legs included) reach into each other (<= 0: apart)."""
    from .collide import body_points
    pts, rad, _ = body_points(Ja, capsules=S.ROLE_CAPSULES)
    worst = 0.0
    for a, b, r, n, frac in S.ROLE_CAPSULES:
        pa, pb = np.asarray(Jb[a], float), np.asarray(Jb[b], float)
        if a == b:
            pa = pb = pa + np.array([0.0, 8.0, 0.0])
        ab = (pb - pa) * frac
        u = np.clip(((pts - pa) @ ab) / max(float(ab @ ab), 1e-9), 0.0, 1.0)
        pen = r + rad - np.linalg.norm(pts - (pa + np.outer(u, ab)), axis=1)
        worst = max(worst, float(pen.max()))
    return worst


def _near(field, p, cm=14.0):
    """Whether a hand (its wrist joint) is at a surface: resting on a bench or bracing a panel is not 'held up'."""
    return float(field.distance(np.array([p]))[0]) < cm


def _holding(geo, t, hand, cm=14.0):
    """Whether a hand is on something that moves in the scene (a tool, a part, a hoisted load)."""
    for p, v, tri, moving in geo.prims:
        if moving:
            w, _ = geo._world(p, v[::max(1, len(v) // 400)], t)
            if len(w) and float(np.min(np.linalg.norm(w - hand, axis=1))) < cm:
                return True
    return False


def _held(geo, t, J, fps, still_s=0.4):
    """{body part: cm} the objects moving with the operator right now (carried, held) reach into the trunk / legs."""
    out = {}
    hands = [J["hand_l"], J["hand_r"]]
    for p, v, tri, moving in geo.prims:
        if not moving:
            continue
        w, M = geo._world(p, v[::max(1, len(v) // 400)], t)
        if not len(w) or min(float(np.min(np.linalg.norm(w - h, axis=1))) for h in hands) > 25.0:
            continue                                                 # (only what a hand is on)
        _, Ma = geo._world(p, v[:1], t - still_s * fps)
        if np.abs(Ma - M).max() < 1e-3:
            continue                                                 # standing still: the equipment field has it
        for q_, pen in _capsule_pen(w, J).items():
            out[q_] = max(out.get(q_, 0.0), pen)
    return out


def _ranges(rows, fps, dt):
    """Per-frame hits -> [{code, part, severity, frames (from, to), seconds, worst, limit, meaning, fix}]: one entry
    per run of consecutive frames."""
    runs, open_ = [], {}
    for n, (t, hits) in enumerate(rows):
        for key, (v, lim) in hits.items():
            r = open_.get(key)
            if r and r["last"] == n - 1:
                r["last"], r["to"] = n, t
                r["worst"] = v if abs(v) > abs(r["worst"]) and key.split(":")[0] != "through_floor" else \
                    (min(v, r["worst"]) if key.split(":")[0] == "through_floor" else r["worst"])
            else:
                r = open_[key] = {"key": key, "from": t, "to": t, "last": n, "worst": v, "limit": lim}
                runs.append(r)
    out = []
    for r in runs:
        code, part = r["key"].split(":", 1)
        sev, meaning, fix = RULES[code]
        secs = (r["last"] - next(i for i, (t, _) in enumerate(rows) if t == r["from"]) + 1) * dt
        if code == "foot_slide" and secs < LIMITS["slide_s"]:
            continue
        if code == "arm_held_up" and secs < 1.0:
            continue
        out.append({"code": code, "part": part, "severity": sev, "frames": [r["from"], r["to"]],
                    "seconds": round(secs, 2), "worst": r["worst"], "limit": r["limit"], "meaning": meaning,
                    "fix": fix})
    return out


def write_report(res, out_dir):
    """motion_qa.json (all of it) and motion_qa.md (what to fix, worst first)."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "motion_qa.json"), "w") as f:
        json.dump(res, f, indent=1)
    L = [f"# Motion QA - {res['stage']}", "",
         f"**{'PASS' if res['ok'] else 'FAIL'}**: {res['errors']} errors, {res['warnings']} warnings over "
         f"{len(res['operators'])} operators (every {res['step']} frame(s), frames {res['range'][0]:g}-{res['range'][1]:g}).",
         "", "Rules: docs/MOTION_RULES.md. Fix every error before the animation is reviewed or scored.", "",
         "| operator | errors | warnings | worst problem |", "|---|---|---|---|"]
    for o in sorted(res["operators"], key=lambda o: -sum(i["severity"] == "error" for i in o["issues"])):
        e = [i for i in o["issues"] if i["severity"] == "error"]
        w = [i for i in o["issues"] if i["severity"] == "warning"]
        top = max(e or w, key=lambda i: i["seconds"], default=None)
        txt = "skipped: " + ", ".join(o["missing"]) if o["missing"] else \
            (f"{top['code']} ({top['part']}) frames {top['frames'][0]:g}-{top['frames'][1]:g}" if top else "clean")
        L.append(f"| {o['name']} | {len(e)} | {len(w)} | {txt} |")
    for o in res["operators"]:
        if not o["issues"]:
            continue
        L += ["", f"## {o['name']}", ""]
        for i in sorted(o["issues"], key=lambda i: (i["severity"] != "error", -i["seconds"])):
            L.append(f"- **{i['severity']}** `{i['code']}` {i['part']}: frames {i['frames'][0]:g}-{i['frames'][1]:g} "
                     f"({i['seconds']} s), worst {i['worst']} (limit {i['limit']}). {i['meaning']}. Fix: {i['fix']}.")
    with open(os.path.join(out_dir, "motion_qa.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return os.path.join(out_dir, "motion_qa.md")
