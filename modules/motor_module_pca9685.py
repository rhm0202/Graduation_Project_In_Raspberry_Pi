import time
import threading
from adafruit_servokit import ServoKit
from modules.logger import get_logger

logger = get_logger("motor_module_pca9685")


class ServoMotor:
    """단일 서보 모터 제어 (PCA9685 I2C PWM).

    전용 워커 스레드가 목표각을 향해 부드럽게 이동한다.
    move_by/set_angle은 목표각만 갱신하고 즉시 반환한다.
    """

    STEP_SIZE  = 1.5   # 한 스텝당 최대 이동 각도
    STEP_DELAY = 0.03  # 스텝 간격 (초)

    def __init__(self, kit: ServoKit, channel: int,
                 min_angle: float = 0, max_angle: float = 180,
                 initial_angle: float = 90):
        self.kit = kit
        self.channel = channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.current_angle = max(min_angle, min(max_angle, initial_angle))
        self._target_angle = self.current_angle

        self._lock = threading.Lock()
        self._event = threading.Event()
        self._running = True

        self.kit.servo[channel].set_pulse_width_range(500, 2500)
        self.kit.servo[channel].angle = self.current_angle
        time.sleep(0.5)

        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def _run(self):
        while self._running:
            self._event.wait()
            self._event.clear()
            while self._running:
                with self._lock:
                    target = self._target_angle
                    delta = target - self.current_angle
                    if abs(delta) < 0.5:
                        break
                    step = min(abs(delta), self.STEP_SIZE) * (1 if delta > 0 else -1)
                    self.current_angle = max(self.min_angle, min(self.max_angle, self.current_angle + step))
                    angle = self.current_angle
                self.kit.servo[self.channel].angle = angle
                time.sleep(self.STEP_DELAY)

    def set_angle(self, angle: float):
        with self._lock:
            self._target_angle = max(self.min_angle, min(self.max_angle, angle))
        self._event.set()

    MAX_LOOKAHEAD = 8.0  # 현재 위치보다 최대 이 각도만큼만 앞서서 목표 설정

    def move_by(self, delta: float):
        with self._lock:
            new_target = self.current_angle + delta
            # 목표가 현재 위치보다 MAX_LOOKAHEAD 이상 앞서지 않도록 제한
            new_target = max(self.current_angle - self.MAX_LOOKAHEAD,
                             min(self.current_angle + self.MAX_LOOKAHEAD, new_target))
        self.set_angle(new_target)

    def stop(self):
        self._running = False
        self._event.set()
        self.kit._pca.channels[self.channel].duty_cycle = 0


class PanTiltController:
    """Pan/Tilt 서보 두 축 제어 (PCA9685 I2C PWM).

    사전 준비:
        1. I2C 활성화: sudo raspi-config → Interface Options → I2C → Enable
        2. 라이브러리 설치: pip install adafruit-circuitpython-servokit
    """

    PAN_CHANNEL  = 0  # PCA9685 채널 0
    TILT_CHANNEL = 1  # PCA9685 채널 1

    def __init__(self, threshold: float = 5.0, gain: float = 0.1):
        self.kit = ServoKit(channels=16)
        self.pan  = ServoMotor(self.kit, self.PAN_CHANNEL)
        self.tilt = ServoMotor(self.kit, self.TILT_CHANNEL, min_angle=20, max_angle=160)
        self.threshold = threshold
        self.gain = gain

    def apply_correction(self, pan_correction: float, tilt_correction: float):
        if abs(pan_correction) >= self.threshold:
            self.pan.move_by(pan_correction * self.gain)
        if abs(tilt_correction) >= self.threshold:
            self.tilt.move_by(tilt_correction * self.gain)
        logger.debug(f"서보 현재 각도 — pan: {self.pan.current_angle:.1f}°, tilt: {self.tilt.current_angle:.1f}°")

    def handle_command(self, data: dict) -> bool:
        status  = data.get("status")
        control = data.get("control")

        if status:
            logger.debug(f"추적 상태: {status}")

        if data.get("tracking") == "on" and control:
            pan  = float(control.get("pan",  0))
            tilt = float(control.get("tilt", 0))
            logger.debug(f"모터 보정값 수신 — pan: {pan:.2f}, tilt: {tilt:.2f}")
            self.apply_correction(pan, tilt)
            return True

        return False

    def center(self):
        self.pan.set_angle(90)
        self.tilt.set_angle(90)

    def cleanup(self):
        self.pan.stop()
        self.tilt.stop()
