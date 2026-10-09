from pathlib import Path

import pytest

from pac_perception import BoxMatcher, Observation, Status, load_fixture

FIXTURE = Path(__file__).parent.parent / "data" / "fixture_demo6.json"

K08 = (0.34, 0.25, 0.21)
K13 = (0.52, 0.48, 0.40)
K03 = (0.27, 0.18, 0.15)


@pytest.fixture
def matcher():
    return BoxMatcher(load_fixture(FIXTURE))


def test_loads_fixture():
    assert len(load_fixture(FIXTURE)) == 6


def test_same_sku_is_told_apart_by_weight(matcher):
    first = matcher.identify(Observation(4.80, K08))
    second = matcher.identify(Observation(1.74, K08))
    assert (first.status, first.box_id) == (Status.OK, "S0001-B001")
    assert (second.status, second.box_id) == (Status.OK, "S0001-B005")


def test_orientation_does_not_matter(matcher):
    result = matcher.identify(Observation(28.49, (0.40, 0.52, 0.48)))
    assert (result.status, result.box_id) == (Status.OK, "S0001-B003")


def test_weight_only_is_candidate_and_not_consumed(matcher):
    result = matcher.identify(Observation(weight_kg=0.86))
    assert (result.status, result.box_id) == (Status.CANDIDATE, "S0001-B006")
    assert "S0001-B006" in matcher.missing()


def test_weight_deficit_is_damaged_and_consumed(matcher):
    result = matcher.identify(Observation(10.0, K13))
    assert (result.status, result.box_id, result.reason) == (
        Status.DAMAGED, "S0001-B002", "weight_deficit")
    assert "S0001-B002" not in matcher.missing()


def test_size_mismatch_is_suspect(matcher):
    result = matcher.identify(Observation(1.39, (0.27, 0.18, 0.05)))
    assert (result.status, result.reason) == (Status.SUSPECT, "size_mismatch")
    assert "S0001-B004" in matcher.missing()


def test_unknown_box(matcher):
    result = matcher.identify(Observation(60.0, (1.0, 1.0, 1.0)))
    assert result.status == Status.UNKNOWN


def test_duplicate_after_match(matcher):
    assert matcher.identify(Observation(1.39, K03)).status == Status.OK
    assert matcher.identify(Observation(1.39, K03)).status == Status.DUPLICATE


def test_close_weights_are_ambiguous():
    boxes = load_fixture(FIXTURE)
    twin = type(boxes[0])("X-B001", "K08", boxes[0].size_m, boxes[0].weight_kg + 0.02)
    result = BoxMatcher(boxes + [twin]).identify(Observation(4.81, K08))
    assert result.status == Status.AMBIGUOUS
    assert set(result.candidates) == {"S0001-B001", "X-B001"}


def test_missing_reports_unmatched_entries(matcher):
    matcher.identify(Observation(4.80, K08))
    assert len(matcher.missing()) == 5
