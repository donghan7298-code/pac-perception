"""Put this repo's package and the integrated monorepo's team packages on sys.path.

The shared contract (``pac_common``, ``pac_runtime.perception.RawObservation``,
``StateValidator``) lives in the integrated repository, so tests run against a
local clone of it: set ``PAC_INTEGRATED_ROOT`` or clone it next to this repo
as ``pac-integrated-main`` (clean origin/main checkout, preferred),
``dlwotjd1289-cloud`` or ``pac-integrated-ref``.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _integrated_root():
    candidates = [os.environ.get("PAC_INTEGRATED_ROOT")]
    candidates += [str(ROOT.parent / name) for name in ("pac-integrated-main", "dlwotjd1289-cloud", "pac-integrated-ref")]
    for c in candidates:
        if c and (Path(c) / "ros2_ws" / "src" / "pac_common" / "pac_common").is_dir():
            return Path(c)
    raise RuntimeError("integrated repo not found: set PAC_INTEGRATED_ROOT to a clone of "
                       "https://github.com/dlwotjd1289-cloud/dlwotjd1289-cloud")


INTEGRATED = _integrated_root()
PATHS = [
    ROOT / "ros2_ws" / "src" / "pac_perception",  # ours first: shadows the integrated pac_perception
    ROOT / "ros2_ws" / "src" / "pac_reinspection",
    *(p for p in sorted((INTEGRATED / "ros2_ws" / "src").glob("pac_*"))
      if (p / p.name).is_dir() and p.name != "pac_perception"),
    INTEGRATED / "tools" / "virtual_data",
    INTEGRATED / "scripts",
]
for path in reversed(PATHS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
