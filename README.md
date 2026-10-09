# pac-perception

컨베이어 벨트로 들어오는 박스를 **저울 무게**와 **탑뷰 깊이 카메라 치수**로 주문 목록(order)과 대조해 식별하고, 손상/미확인 박스를 가려내는 모듈입니다.

## 구성 개념

```
[투입] → [저울] ───────벨트───────→ [깊이 카메라 + 로봇 픽업]
          무게 후보 좁히기             치수로 식별·이상 판정
```

- 주문 목록은 [pac-mission1-shared](https://github.com/yang8988/pac-mission1-shared)의 `config/*/fixture.json` 형식(`boxes` 배열)을 그대로 읽습니다. (`data/fixture_demo6.json`은 예시 사본)
- 박스를 목록과 **1:1로 매칭**합니다. 같은 SKU라도 무게가 달라 구분됩니다.
- 치수는 정렬한 세 값으로 비교하므로 박스 방향과 무관합니다.

## 판정 상태

| 상태 | 의미 |
|---|---|
| `OK` | 무게·치수 모두 목록의 한 항목과 일치 (항목 소진) |
| `CANDIDATE` | 센서 한쪽만 있어 후보만 정해짐 (항목 소진 안 함) |
| `AMBIGUOUS` | 후보 간 차이가 작아 하나로 정할 수 없음 |
| `SUSPECT` | 센서 간 불일치 (치수 불일치, 무게 초과 등) → 재측정 |
| `DAMAGED` | 치수는 맞고 무게가 부족 (내용물 손실 의심) |
| `DUPLICATE` | 이미 매칭된 항목과 같은 값 |
| `UNKNOWN` | 어떤 항목과도 맞지 않음 |

`missing()`은 작업 종료 후 매칭되지 않은 항목(누락)을 돌려줍니다.

## 사용

```python
from pac_perception import BoxMatcher, Observation, load_fixture

matcher = BoxMatcher(load_fixture("data/fixture_demo6.json"))
matcher.identify(Observation(weight_kg=4.80))                       # 저울 단계: CANDIDATE
matcher.identify(Observation(weight_kg=4.80, size_m=(0.34, 0.25, 0.21)))  # OK
matcher.missing()
```

## 테스트

```
pip install -e .[dev]
pytest
```

## 한계와 다음 단계

- 센서 노이즈(`sigma_*`)와 `gate`, `margin_min`은 임시 기본값이며 Gazebo 센서 구성 후 조정해야 합니다.
- 같은 규격 박스의 무게 손실이 다른 박스의 무게와 겹치면 오식별될 수 있습니다.
- 아직 없는 것: 저울 무게 계단(step) 검출, 깊이 이미지 기반 치수/높이 측정, 저울-카메라 트랙 매칭, ROS2 노드와 Gazebo 연동.
