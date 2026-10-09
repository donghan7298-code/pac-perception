# pac-perception

AHEAD 런타임 흐름의 **1단계 인식** 중 통합 저장소에 아직 없는 부분을 채우는 모듈입니다.
통합 저장소: [dlwotjd1289-cloud/dlwotjd1289-cloud](https://github.com/dlwotjd1289-cloud/dlwotjd1289-cloud)
(`docs/flow/01_perception.md`, `docs/flow/KNOWN_ISSUES.md` 3절 "1 인식: 깊이(RGB-D) 처리" 미구현 항목)

## 흐름에서의 위치

```
1 인식                                                      2 State Validator (태현, 기존)
 무게 측정 ── AutoScaleCycle.measured_kg (재성, 기존) ─┐
 ID·라벨 ──── 판독 결과 또는 None ───────────────────┼─► RawObservation ─► StateValidator.validate
 Top-view RGB-D ─ measure_box (이 저장소) ────────────┤    (pac_runtime.perception)   OK / DAMAGED /
 라벨 미판독 시 ─ resolve_sku (이 저장소) ────────────┘                               SPEC_MISMATCH /
                                                                                      RECOGNITION_FAIL
```

- 이 모듈은 **관측만** 만듭니다. 이상 판정(파손 → Reject, 규격 불일치 → 재측정, 인식 실패 → Base-view·Inspection)은 2단계 `StateValidator`가 합니다.
- 출력은 1→2단계 계약인 `pac_runtime.perception.RawObservation` 그대로이며, 상태 변경은 State Manager만 합니다 (공통 기준서 12.1).
- 박스 ID는 도착 시 부여되는 추적 ID이고, 주문 목록은 SKU 단위(`order.json`: 규격, 무게 범위, 수량)입니다.

## 구성

| 파일 | 내용 |
|---|---|
| `pac_perception/depth_measurement.py` | 깊이 이미지 → `conveyor` frame 점군 → 박스 크기(긴 변·짧은 변·높이), 위치·yaw, 파손 단서(윗면 눌림, 기울어짐, 모서리 찌그러짐: 면적 비율 + 박스 크기와 무관한 모서리 빈 거리), 확신도 |
| `pac_perception/sku_resolver.py` | 라벨을 못 읽었을 때 측정 크기·무게로 SKU 추정. 허용오차는 `ValidatorConfig`와 같은 의미. 후보가 둘 이상이거나 없으면 라벨 없음으로 둠 |
| `pac_perception/raw_observation.py` | 저울 무게 + 깊이 측정 (+ 라벨) → `RawObservation` |
| `config/donghan/perception_depth.yaml` | 위 두 설정 (SI 단위). `load_perception_config()`로 읽음 |
| `viewer/perception_sim.html` | 브라우저 시뮬레이터 (아래) |

`conveyor` frame은 통합 저장소에 원점 정의가 없어 **픽업 구역 중심 (-1.08, 1.20)의 롤러 윗면(z 0.895), 축은 world와 같음**으로 가정했습니다. 팀 확정이 필요합니다.

## 시뮬레이터 (`viewer/perception_sim.html`)

파일을 브라우저로 바로 열면 됩니다 (서버 불필요, three.js는 CDN). 재성 님 Gazebo V4.4 작업셀의 배치를 그대로 씁니다:
컨베이어·인라인 저울(x −3.80)·PICK 스토퍼(x −0.845)·기둥 CCTV(위치·자세·화각 1.40 rad는 `ahead_workcell_v4_4_suction.sdf`)·HDR50-22 받침대·팔레트(1.10 m, 데크 0.15 m)·버퍼 테이블, 도착 흔들림(±80 mm, ±10°, `ARRIVAL_JITTER` 기본값).

- 박스마다: 저울 안정화 → 라벨 판독 → 깊이 이미지 렌더링(기둥 카메라에서 광선 추적) → `measure_box` → `resolve_sku` → `StateValidator` → 팔레트 또는 Hold/NG.
- 이상 주입: 라벨 미판독, 윗면 눌림, 모서리 찌그러짐, 내용물 손실, 규격 불량, 깊이 결측, 미등록 박스 (확률 조절, 시드 고정).
- 결과: 주입 이상 → 판정 분포 표, 박스별 상세, JSONL 내보내기 (공통 기준서 21절 필드 일부).
- URL 옵션: `?order=demo_original10&seed=7&repeat=3&speed=inf&autorun`
- 계산부(`<script id="core">`)는 DOM 없이 node로도 돌아갑니다: `node viewer/check_core.js demo_original10 7 15` (판정 분포와 크기 오차 출력).

시뮬레이터 전용 가정: 기둥 CCTV를 RGB-D로 가정(현재 Gazebo는 RGB만), 로봇 팔 형상과 팔레트 배치 규칙은 시각화용 단순화(실제 배치는 5단계 플래너), Hold/NG 위치는 임시, Base-view는 `PerceptionSim.base_view`와 같은 가상 동작.

판정 연결:

| 측정 결과 | `RawObservation` | 2단계 처리 |
|---|---|---|
| 정상, 라벨 판독 | `confidence = 1.0` | OK → 계획 |
| 정상, 라벨 미판독, SKU 하나로 추정 | 추정 라벨, `confidence = 0.9` | OK, 불확실(δ) 적용 |
| SKU 후보 여럿 / 없음 | `label_sku = None` | Base-view → Inspection/NG |
| 윗면 눌림·기울어짐·모서리 찌그러짐 | `visual_damage = True` | DAMAGED → Reject (또는 상부 하중 0) |
| 깊이 결측 많음 (반사·가림) | `confidence = 0.6` | 불확실(δ) 적용 |

## 개발 환경과 테스트

공통 계약(`pac_common`, `pac_runtime`)은 통합 저장소에 있으므로, 테스트는 통합 저장소 사본을 사용합니다.
`PAC_INTEGRATED_ROOT`를 지정하거나 이 저장소 옆에 `dlwotjd1289-cloud` 이름으로 clone 하세요.

```
git clone https://github.com/dlwotjd1289-cloud/dlwotjd1289-cloud ../dlwotjd1289-cloud
pip install numpy PyYAML Shapely pytest
pytest
```

- `tests/donghan/test_depth_measurement.py`: 합성 깊이 이미지로 크기·위치·yaw·파손·결측 검증
- `tests/donghan/test_sku_resolver.py`: `demo_original6` 주문 목록 기준 SKU 추정
- `tests/donghan/test_stage1_to_stage2_contract.py`: 출력이 통합 저장소의 `StateValidator`를 그대로 통과하는지 (계약 테스트)

## 통합 저장소로 옮길 때

- 폴더 구조를 통합 저장소와 같게 두었습니다. `ros2_ws/src/pac_perception/pac_perception/`의 파일 4개, `config/donghan/`, `tests/donghan/`을 그대로 복사하면 됩니다.
- `pac_perception` 패키지는 재성 님 담당 폴더이므로, 옮기기 전에 확인이 필요합니다. 기존 `observation_generator.py`와 파일 이름은 겹치지 않지만 `__init__.py`는 합쳐야 합니다.
- 통합 저장소 `config/camera.yaml`의 `optional_3d_camera`는 현재 `enabled: false`이고, Gazebo 월드에 깊이 카메라가 없습니다. 카메라 추가와 `conveyor` frame 외부 파라미터 확정이 필요합니다.

## 한계

- 합성 이미지는 수직으로 내려다보는 카메라와 윗면만 그립니다. 기울어진 카메라, 옆면, 실제 센서 잡음은 Gazebo 깊이 카메라로 검증해야 합니다.
- 픽업 구역(ROI)에 박스가 하나만 있다고 가정합니다 (현재 Gazebo 셀은 스토퍼에서 한 개씩 정지).
- 파손·결측 임계값은 임시값이며 Gazebo 데이터로 조정해야 합니다.
- ROS 2 노드(깊이 토픽 구독 → `RawObservation`)는 아직 없습니다. 핵심 계산과 노드를 분리하는 공통 기준에 따라 계산부만 먼저 만들었습니다.
