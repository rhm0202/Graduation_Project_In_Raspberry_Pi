# Spotlight Cam — Raspberry Pi Server

> Spotlight Cam 프로젝트의 Raspberry Pi 측 서버.
> 카메라 영상 스트리밍 및 팬·틸트 서보 모터 제어를 담당한다.

---

## 역할

| 기능 | 설명 |
|---|---|
| 영상 스트리밍 | picamera2로 캡처한 프레임을 JPEG 바이너리로 PC에 실시간 전송 |
| 모터 제어 수신 | PC(spotlight_core.py)에서 계산한 서보 절대 각도를 수신해 팬·틸트 구동 |
| 통신 방식 | WebSocket (ws://0.0.0.0:8000) |

---

## 하드웨어

| 항목 | 사양 |
|---|---|
| 보드 | Raspberry Pi |
| 카메라 | Raspberry Pi Camera Module |
| 모터 드라이버 | PCA9685 I2C 16채널 PWM 보닛 (Adafruit) |
| 서보 채널 | Pan: CH0 / Tilt: CH1 |

---

## 프로젝트 구조

```
Graduation_Project_In_Raspberry_Pi/
├── Server/
│   └── rpi_server.py            # WebSocket 서버 진입점
├── modules/
│   ├── camera_module.py         # picamera2 백그라운드 캡처 모듈
│   ├── motor_module_pca9685.py  # PCA9685 기반 Pan/Tilt 서보 제어
│   ├── logger.py                # 공통 로거 (RotatingFileHandler)
│   └── legacy/
│       ├── motor_module.py      # 구버전 RPi.GPIO PWM 방식
│       └── motor_module_pigpio.py  # 구버전 pigpio 하드웨어 PWM 방식
├── active/
│   └── run.sh                   # 서버 실행 스크립트
└── setup/
    ├── install.sh               # 환경 설치 스크립트
    └── requirements.txt         # Python 의존성 목록
```

---

## 설치

```bash
bash setup/install.sh
```

Python 가상환경 생성 및 의존 패키지를 자동으로 설치한다.

### 사전 조건

- I2C 활성화: `sudo raspi-config` → Interface Options → I2C → Enable
- 의존 패키지: `numpy`, `opencv-python`, `websockets`, `adafruit-circuitpython-servokit`

---

## 실행

```bash
bash active/run.sh
```

가상환경을 활성화하고 `Server/rpi_server.py`를 실행한다.

---

## 통신 프로토콜

### RPi → PC (영상 전송)

- 형식: Binary JPEG bytes
- 프레임레이트: 최대 50fps

### PC → RPi (모터 제어)

```json
{ "type": "servo_angle", "pan_angle": 95.0, "tilt_angle": 88.5 }
```

PC의 PID 연산 결과인 절대 각도를 수신해 서보를 부드럽게 이동시킨다.

---

## 주요 모듈

### `CameraModule`
- `picamera2` 기반 1280×720 캡처
- 백그라운드 스레드에서 지속 캡처 → asyncio 블로킹 방지
- RGB → BGR 변환 후 최신 프레임 반환

### `PanTiltController`
- PCA9685 I2C PWM으로 서보 2축 제어
- 각 축 전용 워커 스레드가 목표 각도까지 보간 이동 (STEP_SIZE: 3°/스텝)
- `handle_command()` 로 JSON 명령 파싱 및 모터 구동

---

## 관련 레포지토리

- PC 서버 (spotlight_core.py): [Graduation_Project](https://github.com/rhm0202/Graduation_Project)
