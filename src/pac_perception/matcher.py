"""Identify arriving boxes against the order list using scale weight and measured size."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Status(str, Enum):
    OK = "OK"
    CANDIDATE = "CANDIDATE"  # only one sensor available so far, not consumed
    AMBIGUOUS = "AMBIGUOUS"
    SUSPECT = "SUSPECT"
    DAMAGED = "DAMAGED"
    DUPLICATE = "DUPLICATE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class OrderBox:
    box_id: str
    sku: str
    size_m: tuple[float, float, float]
    weight_kg: float


@dataclass(frozen=True)
class Observation:
    weight_kg: float | None = None
    size_m: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class MatchResult:
    status: Status
    box_id: str | None
    reason: str
    margin: float | None = None
    candidates: tuple[str, ...] = field(default_factory=tuple)


def load_fixture(path: str | Path) -> list[OrderBox]:
    """Read the per-box list from a fixture.json (the `boxes` array)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        OrderBox(b["box_id"], b["sku"], tuple(b["size_m"]), float(b["weight_kg"]))
        for b in data["boxes"]
    ]


class BoxMatcher:
    """Matches observations to order boxes one-to-one.

    Sizes are compared as sorted triples so box orientation does not matter.
    A sensor value fits an entry when it is within `gate` sigmas of it.
    """

    def __init__(
        self,
        boxes: list[OrderBox],
        sigma_weight_abs_kg: float = 0.05,
        sigma_weight_rel: float = 0.02,
        sigma_size_m: float = 0.01,
        gate: float = 3.0,
        margin_min: float = 1.0,
    ) -> None:
        self._remaining = {b.box_id: b for b in boxes}
        self._consumed: dict[str, OrderBox] = {}
        self._sw_abs = sigma_weight_abs_kg
        self._sw_rel = sigma_weight_rel
        self._sd = sigma_size_m
        self._gate = gate
        self._margin_min = margin_min

    def missing(self) -> list[str]:
        return sorted(self._remaining)

    def _zw(self, weight: float, box: OrderBox) -> float:
        return (weight - box.weight_kg) / max(self._sw_abs, self._sw_rel * box.weight_kg)

    def _zd(self, size: tuple[float, float, float], box: OrderBox) -> float:
        a, b = sorted(size), sorted(box.size_m)
        return max(abs(x - y) for x, y in zip(a, b)) / self._sd

    def _fits(self, obs: Observation, box: OrderBox) -> tuple[bool, bool, float]:
        zw = self._zw(obs.weight_kg, box) if obs.weight_kg is not None else 0.0
        zd = self._zd(obs.size_m, box) if obs.size_m is not None else 0.0
        return abs(zw) <= self._gate, zd <= self._gate, math.hypot(zw, zd)

    def identify(self, obs: Observation) -> MatchResult:
        if obs.weight_kg is None and obs.size_m is None:
            return MatchResult(Status.UNKNOWN, None, "no_measurement")

        scored = [(self._fits(obs, b), b) for b in self._remaining.values()]
        fit = sorted(
            ((score, b) for (wf, df, score), b in scored if wf and df), key=lambda t: t[0]
        )
        if fit:
            return self._resolve_fit(obs, fit)
        return self._diagnose(obs, scored)

    def _resolve_fit(self, obs: Observation, fit: list[tuple[float, OrderBox]]) -> MatchResult:
        best_score, best = fit[0]
        margin = fit[1][0] - best_score if len(fit) > 1 else None
        if margin is not None and margin < self._margin_min:
            return MatchResult(
                Status.AMBIGUOUS, None, "close_candidates", margin,
                tuple(b.box_id for _, b in fit),
            )
        if obs.weight_kg is None or obs.size_m is None:
            only = "weight_only" if obs.size_m is None else "size_only"
            return MatchResult(Status.CANDIDATE, best.box_id, only, margin,
                               tuple(b.box_id for _, b in fit))
        self._consume(best.box_id)
        return MatchResult(Status.OK, best.box_id, "matched", margin)

    def _diagnose(self, obs: Observation, scored) -> MatchResult:
        if obs.weight_kg is not None and obs.size_m is not None:
            if any(all(self._fits(obs, b)[:2]) for b in self._consumed.values()):
                return MatchResult(Status.DUPLICATE, None, "already_matched")
            size_fit = [(abs(self._zw(obs.weight_kg, b)), b) for (_, df, _), b in scored if df]
            if size_fit:
                _, nearest = min(size_fit, key=lambda t: t[0])
                z = self._zw(obs.weight_kg, nearest)
                if z < 0:
                    self._consume(nearest.box_id)
                    return MatchResult(Status.DAMAGED, nearest.box_id, "weight_deficit")
                return MatchResult(Status.SUSPECT, nearest.box_id, "weight_excess")
            weight_fit = [b for (wf, _, _), b in scored if wf]
            if weight_fit:
                return MatchResult(Status.SUSPECT, None, "size_mismatch",
                                   candidates=tuple(b.box_id for b in weight_fit))
        return MatchResult(Status.UNKNOWN, None, "no_order_entry")

    def _consume(self, box_id: str) -> None:
        self._consumed[box_id] = self._remaining.pop(box_id)
