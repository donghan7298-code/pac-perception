"""Render boxes seen by a straight-down depth camera (top faces and rollers only)."""
import math

import numpy as np

from pac_perception import CameraModel

CAMERA_HEIGHT_M = 1.5
WIDTH, HEIGHT_PX = 320, 240
F = 300.0


def camera() -> CameraModel:
    # optical x -> conveyor x, optical y -> -conveyor y, optical z (forward) -> -conveyor z
    t = np.eye(4)
    t[:3, :3] = np.diag([1.0, -1.0, -1.0])
    t[2, 3] = CAMERA_HEIGHT_M
    return CameraModel(F, F, WIDTH / 2, HEIGHT_PX / 2, t)


def render(length, width, height, x=0.0, y=0.0, yaw=0.0, dent_m=0.0, crushed_corner_m=0.0,
           hole_ratio=0.0, seed=0):
    return render_scene([dict(length=length, width=width, height=height, x=x, y=y, yaw=yaw, dent_m=dent_m,
                              crushed_corner_m=crushed_corner_m, hole_ratio=hole_ratio)], seed)


def render_scene(boxes, seed=0):
    """``boxes``: dicts with length, width, height and optional x, y, yaw, dent_m,
    crushed_corner_m, hole_ratio. The nearest top face wins per pixel."""
    v, u = np.mgrid[0:HEIGHT_PX, 0:WIDTH].astype(float)
    depth = np.full(u.shape, CAMERA_HEIGHT_M)
    rng = np.random.default_rng(seed)
    for b in boxes:
        length, width, height = b["length"], b["width"], b["height"]
        x, y, yaw = b.get("x", 0.0), b.get("y", 0.0), b.get("yaw", 0.0)
        z_top = CAMERA_HEIGHT_M - height
        px, py = (u - WIDTH / 2) / F * z_top, -(v - HEIGHT_PX / 2) / F * z_top
        c, s = math.cos(yaw), math.sin(yaw)
        a, bb = c * (px - x) + s * (py - y), -s * (px - x) + c * (py - y)
        on_top = (np.abs(a) <= length / 2) & (np.abs(bb) <= width / 2)
        if b.get("crushed_corner_m"):
            on_top &= (length / 2 - a) + (width / 2 - bb) > b["crushed_corner_m"]
        top = np.full(on_top.shape, height)
        if b.get("dent_m"):
            r = min(length, width) / 4
            top -= b["dent_m"] * np.clip(1 - np.hypot(a, bb) / r, 0, None)
        box_depth = np.where(on_top, CAMERA_HEIGHT_M - top, np.inf)
        if b.get("hole_ratio"):
            box_depth[on_top & (rng.random(box_depth.shape) < b["hole_ratio"])] = np.nan
        nearer = on_top & ~(box_depth > depth)  # NaN holes also replace the background
        depth = np.where(nearer, box_depth, depth)
    return depth
