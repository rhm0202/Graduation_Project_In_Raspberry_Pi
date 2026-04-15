import cv2
from picamera2 import Picamera2

FRAME_WIDTH  = 640
FRAME_HEIGHT = 480

class CameraModule:
    def __init__(self, width=FRAME_WIDTH, height=FRAME_HEIGHT):
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_preview_configuration(
                main={"size": (width, height)}
            )
        )
        self.picam2.start()

    def capture_bgr(self):
        """RGB 프레임을 캡처해 OpenCV용 BGR로 변환해 반환."""
        frame = self.picam2.capture_array()
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def stop(self):
        self.picam2.stop()
