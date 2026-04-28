import logging
import time
import RPi.GPIO as GPIO

logger = logging.getLogger("motor_module")


class ServoMotor:
    """단일 서보 모터 제어 (PWM 50Hz 기준)."""

    def __init__(self, pin: int, min_angle: float = 0, max_angle: float = 180, initial_angle: float = 90):
        self.pin = pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.current_angle = initial_angle

        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, 50)  # 50Hz
        self.pwm.start(0)
        self.set_angle(initial_angle)

    def _to_duty(self, angle: float) -> float:
        """각도(0~180)를 듀티 사이클(2.5~12.5%)로 변환."""
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle: float):
        """절대 각도로 이동 (범위 초과 시 클램프)."""
        self.current_angle = max(self.min_angle, min(self.max_angle, angle))
        self.pwm.ChangeDutyCycle(self._to_duty(self.current_angle))
        time.sleep(0.3)

    def move_by(self, delta: float):
        """현재 위치에서 delta만큼 상대 이동."""
        self.set_angle(self.current_angle + delta)

    def stop(self):
        self.pwm.stop()


class PanTiltController:
    """Pan/Tilt 서보 두 축 제어.

    PC에서 보정값(pan, tilt)을 수신하면 apply_correction() 또는 handle_command()를 호출한다.
    보정값의 절댓값이 threshold 미만이면 움직이지 않는다 (흔들림 방지).
    """

    PAN_PIN  = 12  # GPIO 12 (PWM0)
    TILT_PIN = 33  # GPIO 13 (PWM1)

    def __init__(self, threshold: float = 5.0, gain: float = 0.1):
        """
        threshold : 보정값이 이 값 이상일 때만 모터 작동 (단위: 픽셀 or degree)
        gain      : 보정값 → 이동 각도 변환 비율
        """
        GPIO.setmode(GPIO.BCM)

        self.pan  = ServoMotor(self.PAN_PIN)
        self.tilt = ServoMotor(self.TILT_PIN)

        self.threshold = threshold
        self.gain = gain

    def apply_correction(self, pan_correction: float, tilt_correction: float):
        """보정값(pan, tilt)을 받아 서보 이동.
        절댓값이 threshold 미만이면 흔들림으로 간주하고 무시한다.
        """
        if abs(pan_correction) >= self.threshold:
            self.pan.move_by(pan_correction * self.gain)
        if abs(tilt_correction) >= self.threshold:
            self.tilt.move_by(tilt_correction * self.gain)

    def handle_command(self, data: dict) -> bool:
        """PC에서 수신한 제어 명령 딕셔너리를 파싱해 모터를 구동한다.

        예상 포맷:
            {
                "tracking": "on" | "off",
                "control": {"pan": <float>, "tilt": <float>},
                "status": "tracking" | "lost" | "searching"   # 선택
            }

        - tracking == "on" 이고 control 키가 있을 때만 모터를 움직인다.
        - status 필드는 로그 출력에만 사용한다.
        - 보정이 실제로 적용된 경우 True를 반환한다 (호출자가 완료 응답을 보낼 수 있도록).
        """
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
        """두 축을 정중앙(90°)으로 복귀."""
        self.pan.set_angle(90)
        self.tilt.set_angle(90)

    def cleanup(self):
        self.pan.stop()
        self.tilt.stop()
        GPIO.cleanup()
