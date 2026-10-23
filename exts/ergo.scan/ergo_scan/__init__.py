"""Ergonomic scan (RULA) of every animated operator in a USD scene, with report and dashboards.

    from ergo_scan import scan
    res = scan.scan(stage, "/World", step=2)
    scan.write_report(res, "C:/out/ergo")

Inside Kit the extension also adds Window > Ergo Scan (extension.py).
"""
__version__ = "0.1.0"

try:                                    # Kit: the extension class must be importable from the package
    import omni.ext  # noqa: F401
    from .extension import ErgoScanExtension  # noqa: F401
except ImportError:                     # plain Python: scan / dash only
    pass
