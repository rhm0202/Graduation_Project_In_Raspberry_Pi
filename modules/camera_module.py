import cv2
import threading
from picamera2 import Picamera2

FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720

class CameraModule:
    def __init__(self, width=FRAME_WIDTH, height=FRAME_HEIGHT):
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_preview_configuration(
                main={"size": (width, height)}
            )
        )
        self.picam2.start()

        # 백그라운드 스레드에서 계속 캡처해 최신 프레임 유지
        self._frame = None
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        while self._running:
            frame = self.picam2.capture_array()
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            with self._lock:
                self._frame = bgr

    def capture_bgr(self):
        """최신 BGR 프레임 반환. 아직 프레임이 없으면 None 반환."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self):
        self._running = False
        self._thread.join(timeout=2)
        self.picam2.stop()
