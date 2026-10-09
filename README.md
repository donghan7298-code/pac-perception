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

**연속 흐름**
- 박스가 투입 간격(평균·변동 설정)을 두고 계속 들어옵니다. 컨베이어는 존(zone) 축적식으로 가정했습니다: 앞 박스와 최소 50 mm 간격, 저울은 한 번에 한 박스만 올라가 정지 계량(1.9 s), PICK 스토퍼에서 대기.
- **연산 중 정지**: PICK 박스 분류(기본 0.5 s)와 적재 결정(기본 1.0 s = `planning.timeout_sec`) 동안 컨베이어 전체를 멈춥니다(끌 수 있음). 정지 시간 비율이 결과에 나옵니다.
- **버퍼**: 태현 님 `RulePolicy` 이식 (PLACE_CURRENT / BUFFER_CURRENT / RETRIEVE_BUFFER / PALLET_CLOSE, 지지율 0.95, 보관 12회 초과 시 인출, 2 cm 더 낮으면 버퍼 우선). 버퍼 칸은 재성 님 V4.4 2칸 테이블(칸당 ≤ 0.37 × 0.56 m), 팔레트 교체 60 s(`SupervisorConfig`). 주문이 끝나면 버퍼 박스를 마저 적재합니다.
- 로봇은 박스를 들어 올린 순간부터 다음 박스가 PICK으로 들어와 분류됩니다(재성 님 V4.4 파이프라이닝과 같은 개념).

**초입 기둥 카메라 (위치 가정: (−4.30, 1.78, 2.40), 초입 (−4.48, 1.20)을 향함. Gazebo 파일이 공개되면 교체)**

| 기능 | 시뮬레이터 | 효과 |
|---|---|---|
| 붙어서 들어온 박스 감지 → 갭 생성 (뒤 박스 정지) | 구현 | 저울에 두 박스가 함께 올라가는 것을 막음 |
| 측면 라벨 2차 판독 | 구현 | 상단 라벨 미판독을 PICK 전에 보완 |
| Base-view 대체 (흐름도의 보조 카메라) | 구현 | 이상 시 재확인에 초입 기록 사용 (Gazebo에 없는 Base-view 카메라 대신) |
| 초입/PICK 크기 비교 (운송 중 변화) | 구현 | 15 mm 넘게 다르면 확신도 0.6 (δ) |
| Look-ahead 대기열 (도착 전 SKU·크기·파손 단서) | 표시 | 플래너·버퍼 결정에 미리 쓸 수 있음 (알고리즘 연결은 아직) |
| 넘어진 박스(높이 ≠ SKU) 조기 정지, 유입량 감시·MISSING 보조, 무게/부피 밀도 교차검증 | 아이디어 | – |

같은 시드로 "초입 카메라 유무 비교" 버튼을 누르면 두 번 실행해 비교합니다. 예 (`demo_original8 ×6`, 붙어서 투입 30%): 판정 오류 0 vs 8, 함께 계량 0 vs 19. 붙어서 투입 0%이면 두 경우가 같습니다.

**그 밖에**
- 이상 주입: 라벨 미판독, 윗면 눌림, 모서리 찌그러짐, 내용물 손실, 규격 불량, 깊이 결측, 미등록 박스, 붙어서 투입 (확률 조절, 시드 고정).
- 결과: 주입 이상 → 판정 분포 표, 처리량, 정지 비율, 로봇 가동률, 팔레트 수·적재율, 버퍼 보관/인출, 박스별 상세, JSONL.
- URL 옵션: `?order=demo_original10&seed=7&repeat=3&speed=inf&autorun&compare&touch=0.3&interval=5&inlet=0&tab=inlet&advance=120`
- 계산부(`<script id="core">`)는 DOM 없이 node로 돌아갑니다: `node viewer/check_core.js demo_original8 3 6 0.3 5` (초입 카메라 켬/끔 두 번 실행, 판정 분포와 흐름 지표 출력).

시뮬레이터 전용 가정: 기둥 CCTV를 RGB-D로 가정(현재 Gazebo는 RGB만), 초입 카메라 위치, 존 축적 컨베이어와 갭 생성 구동, 로봇 팔 형상과 이동 시간, 팔레트 배치 규칙(2 cm 높이맵, 최저 높이 우선, 지지율 ≥ 0.70: 실제는 5단계 플래너), Hold/NG 위치. 초입 카메라를 끄면 Base-view는 `PerceptionSim.base_view`와 같은 가상 동작입니다.

**시뮬레이터로 찾아 `measure_box`에 반영한 것**: 큰 박스의 모서리 찌그러짐 누락(모서리 빈 거리 추가), PICK ROI에 들어온 다음 박스와 합쳐 측정(컨베이어 방향 분리, `target_x`, 앞뒤 간격), ROI·이미지 경계에서 잘린 박스를 파손으로 오판(`in_full_view`가 거짓이면 파손 판단 생략, 확신도 0.6).

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
