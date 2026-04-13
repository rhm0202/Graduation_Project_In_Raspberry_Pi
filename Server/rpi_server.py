import asyncio
import json
import logging
import os
import sys
import cv2
import websockets
from logging.handlers import RotatingFileHandler
from picamera2 import Picamera2

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from modules.motor_module import PanTiltController

# ==========================================
# 설정
# ==========================================
HOST = "0.0.0.0"  # 모든 IP에서 접속 허용
PORT = 8000       # spotlight_core.py의 RPI_WS_URL 포트와 일치해야 함

FRAME_WIDTH  = 640
FRAME_HEIGHT = 480
JPEG_QUALITY = 80  # 전송용 JPEG 압축 품질

# ==========================================
# 로거
# ==========================================
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("rpi_server")
logger.setLevel(logging.DEBUG)

_formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_file_handler = RotatingFileHandler("logs/rpi_server.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
_file_handler.setFormatter(_formatter)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)

logger.addHandler(_file_handler)
logger.addHandler(_console_handler)

# ==========================================
# 카메라 초기화
# ==========================================
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (FRAME_WIDTH, FRAME_HEIGHT)}))
picam2.start()
logger.info(f"카메라 시작 ({FRAME_WIDTH}x{FRAME_HEIGHT})")

# ==========================================
# 모터 초기화
# ==========================================
pan_tilt = PanTiltController(threshold=5.0, gain=0.1)
pan_tilt.center()
logger.info("Pan/Tilt 서보 초기화 완료 (중앙 복귀)")

# ==========================================
# 제어 명령 처리
# ==========================================
async def handle_control(data: dict):
    """PC에서 수신한 제어 명령 처리.
    예: {"control": {"pan": -12.3, "tilt": 5.6}, "status": "tracking"}
    """
    control = data.get("control")
    status  = data.get("status")

    if status:
        logger.debug(f"추적 상태: {status}")

    if control:
        pan  = control.get("pan", 0)
        tilt = control.get("tilt", 0)
        logger.debug(f"모터 제어 수신 — pan: {pan}, tilt: {tilt}")
        pan_tilt.update(pan, tilt)

# ==========================================
# WebSocket 핸들러
# ==========================================
async def stream_handler(websocket):
    """PC 접속 시 영상 송신과 제어 명령 수신을 동시 처리."""
    logger.info("PC 연결됨")
    frame_count = 0

    async def send_frames():
        """카메라 프레임을 JPEG 바이너리로 인코딩해 PC로 전송."""
        nonlocal frame_count
        try:
            while True:
                frame = picam2.capture_array()

                ret, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if ret:
                    await websocket.send(encoded.tobytes())
                    frame_count += 1
                    if frame_count % 100 == 0:
                        logger.debug(f"프레임 전송: {frame_count}장")

                await asyncio.sleep(0)  # 이벤트 루프 양보
        except websockets.exceptions.ConnectionClosed:
            pass

    async def receive_commands():
        """PC에서 오는 JSON 제어 명령 수신."""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await handle_control(data)
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass

    sender   = asyncio.create_task(send_frames())
    receiver = asyncio.create_task(receive_commands())

    try:
        await asyncio.gather(sender, receiver)
    finally:
        sender.cancel()
        receiver.cancel()
        logger.info(f"PC 연결 해제됨 (전송 프레임: {frame_count}장)")

# ==========================================
# 진입점
# ==========================================
async def main():
    logger.info(f"RPi WebSocket 서버 시작: ws://{HOST}:{PORT}")
    async with websockets.serve(stream_handler, HOST, PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("서버 종료")
    finally:
        picam2.stop()
        pan_tilt.cleanup()
