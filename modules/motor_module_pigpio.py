import logging
import time
import pigpio

logger = logging.getLogger("motor_module_pigpio")


def _angle_to_pulsewidth(angle: float) -> int:
    """각도(0~180)를 펄스폭(500~2500 μs)으로 변환."""
    return int(500 + (angle / 180.0) * 2000)


class ServoMotor:
    """단일 서보 모터 제어 (pigpio 하드웨어 PWM)."""

    def __init__(self, pi: "pigpio.pi", pin: int,
                 min_angle: float = 0, max_angle: float = 180,
                 initial_angle: float = 90):
        self.pi = pi
        self.pin = pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.current_angle = initial_angle

        self.pi.set_mode(pin, pigpio.OUTPUT)
        self.set_angle(initial_angle)

    def set_angle(self, angle: float, steps: int = 20, step_delay: float = 0.015):
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
            self.current_angle += step_size
            self.pi.set_servo_pulsewidth(self.pin, _angle_to_pulsewidth(self.current_angle))
            time.sleep(step_delay)
        self.current_angle = target

    def move_by(self, delta: float):
        self.set_angle(self.current_angle + delta)

    def stop(self):
        self.pi.set_servo_pulsewidth(self.pin, 0)


class PanTiltController:
    """Pan/Tilt 서보 두 축 제어 (pigpio 하드웨어 PWM).

    pigpio 데몬이 실행 중이어야 합니다: sudo pigpiod
    """

    PAN_PIN  = 18  # BCM 18 (물리 핀 12) — PWM0
    TILT_PIN = 13  # BCM 13 (물리 핀 33) — PWM1

    def __init__(self, threshold: float = 5.0, gain: float = 0.1):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpio 데몬에 연결할 수 없습니다. 'sudo pigpiod'를 먼저 실행하세요.")

        self.pan  = ServoMotor(self.pi, self.PAN_PIN)
        self.tilt = ServoMotor(self.pi, self.TILT_PIN)
        self.threshold = threshold
        self.gain = gain

    def apply_correction(self, pan_correction: float, tilt_correction: float):
        if abs(pan_correction) >= self.threshold:
            self.pan.move_by(pan_correction * self.gain)
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
        self.pi.stop()
