import logging
import time
from adafruit_servokit import ServoKit

logger = logging.getLogger("motor_module_pca9685")


class ServoMotor:
    """단일 서보 모터 제어 (PCA9685 I2C PWM)."""

    def __init__(self, kit: ServoKit, channel: int,
                 min_angle: float = 0, max_angle: float = 180,
                 initial_angle: float = 90):
        self.kit = kit
        self.channel = channel
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.current_angle = max(min_angle, min(max_angle, initial_angle))

        self.kit.servo[channel].set_pulse_width_range(500, 2500)
        self.kit.servo[channel].angle = self.current_angle
        time.sleep(0.5)

    def set_angle(self, angle: float, steps: int = 20, step_delay: float = 0.05):
        """절대 각도로 부드럽게 이동 (보간, 범위 초과 시 클램프).

        steps * step_delay 가 총 이동 시간. 기본값: 20 * 0.015s = 0.3s
        이동 거리가 작을수록 자동으로 steps 수를 줄여 지연을 최소화한다.
        """
        target = max(self.min_angle, min(self.max_angle, angle))
        delta = target - self.current_angle
        if abs(delta) < 0.5:
            return

        actual_steps = max(1, min(steps, int(abs(delta) / 0.5)))
        step_size = delta / actual_steps
        for _ in range(actual_steps):
            self.current_angle = max(self.min_angle, min(self.max_angle, self.current_angle + step_size))
            self.kit.servo[self.channel].angle = self.current_angle
            time.sleep(step_delay)
        self.current_angle = target

    def move_by(self, delta: float):
        self.set_angle(self.current_angle + delta)

    def stop(self):
        # duty_cycle=0 으로 PWM 신호 중단 (서보를 자유 상태로)
        self.kit._pca.channels[self.channel].duty_cycle = 0


class PanTiltController:
    """Pan/Tilt 서보 두 축 제어 (PCA9685 I2C PWM).

    사전 준비:
        1. I2C 활성화: sudo raspi-config → Interface Options → I2C → Enable
        2. 라이브러리 설치: pip install adafruit-circuitpython-servokit
    """

    PAN_CHANNEL  = 1  # PCA9685 채널 1
    TILT_CHANNEL = 0  # PCA9685 채널 0

    def __init__(self, threshold: float = 5.0, gain: float = 0.1):
        self.kit = ServoKit(channels=16)
        self.pan  = ServoMotor(self.kit, self.PAN_CHANNEL)
        self.tilt = ServoMotor(self.kit, self.TILT_CHANNEL, min_angle=20, max_angle=160)
        self.threshold = threshold
        self.gain = gain

    def apply_correction(self, pan_correction: float, tilt_correction: float):
        # if abs(pan_correction) >= self.threshold:
        #     self.pan.move_by(pan_correction * self.gain)
        if abs(tilt_correction) >= self.threshold:
            self.tilt.move_by(tilt_correction * self.gain)

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
