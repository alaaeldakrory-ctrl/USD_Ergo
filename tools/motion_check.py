"""Motion QA of every animated operator in a USD scene: the rules in docs/MOTION_RULES.md, frame by frame
(exts/ergo.scan/ergo_scan/motion_qa.py). Run it after every animation change, before anyone looks at the result.

    python tools/motion_check.py C:/scenes/line.usd [--out=C:/scenes/line_motion_qa] [--root=/World] [--step=2]
        [--range=0,1800] [--only=Operator_01,Operator_02] [--mapping=mapping.json] [--floor=0]

Writes motion_qa.md (what to fix, worst first) and motion_qa.json, prints the summary, and exits with code 1 while
any error is left (0 when the scene passes) - so a script or an agent can loop until it is clean.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "exts", "ergo.scan"))


def main():
    from pxr import Usd

    from ergo_scan import motion_qa as Q
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = {}
    for a in sys.argv[1:]:
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            opt[k] = v
    if not args:
        print(__doc__)
        sys.exit(2)
    st = Usd.Stage.Open(args[0])
    root = opt.get("root", "/World")
    if not st.GetPrimAtPath(root):
        root = str(st.GetDefaultPrim().GetPath()) if st.GetDefaultPrim() else "/"
    mapping = json.load(open(opt["mapping"])) if opt.get("mapping") else None
    rng = tuple(float(v) for v in opt["range"].split(",")) if opt.get("range") else None
    only = opt["only"].split(",") if opt.get("only") else None
    res = Q.check_stage(st, root, step=float(opt.get("step", 2)), frames=rng, mapping=mapping, only=only,
                        floor=float(opt["floor"]) if opt.get("floor") else None)
    out = opt.get("out") or os.path.splitext(args[0])[0] + "_motion_qa"
    md = Q.write_report(res, out)
    print(json.dumps({"ok": res["ok"], "errors": res["errors"], "warnings": res["warnings"], "report": md,
                      "operators": {o["name"]: {"errors": sum(i["severity"] == "error" for i in o["issues"]),
                                                "warnings": sum(i["severity"] == "warning" for i in o["issues"]),
                                                "skipped": o["missing"] or None} for o in res["operators"]}},
                     indent=1))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
