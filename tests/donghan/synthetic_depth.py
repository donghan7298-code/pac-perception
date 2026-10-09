"""Render a box seen by a straight-down depth camera (top face and rollers only)."""
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
    v, u = np.mgrid[0:HEIGHT_PX, 0:WIDTH].astype(float)
    z_top = CAMERA_HEIGHT_M - height
    px, py = (u - WIDTH / 2) / F * z_top, -(v - HEIGHT_PX / 2) / F * z_top
    c, s = math.cos(yaw), math.sin(yaw)
    a, b = c * (px - x) + s * (py - y), -s * (px - x) + c * (py - y)
    on_top = (np.abs(a) <= length / 2) & (np.abs(b) <= width / 2)
    if crushed_corner_m:
        on_top &= (length / 2 - a) + (width / 2 - b) > crushed_corner_m
    top = np.full(on_top.shape, height)
    if dent_m:
        r = min(length, width) / 4
        top -= dent_m * np.clip(1 - np.hypot(a, b) / r, 0, None)
    depth = np.where(on_top, CAMERA_HEIGHT_M - top, CAMERA_HEIGHT_M)
    if hole_ratio:
        rng = np.random.default_rng(seed)
        depth[on_top & (rng.random(depth.shape) < hole_ratio)] = np.nan
    return depth
