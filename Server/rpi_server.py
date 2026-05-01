import asyncio
import json
import sys
import os
import cv2
import websockets

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from modules.motor_module_pigpio import PanTiltController
from modules.camera_module import CameraModule
from modules.logger import get_logger

# ==========================================
# 설정
# ==========================================
HOST = "0.0.0.0"  # 모든 IP에서 접속 허용
PORT = 8000       # spotlight_core.py의 RPI_WS_URL 포트와 일치해야 함

JPEG_QUALITY = 80  # 전송용 JPEG 압축 품질

# ==========================================
# 로거
# ==========================================
logger = get_logger("rpi_server")

# ==========================================
# 카메라 초기화
# ==========================================
camera = CameraModule()
logger.info("카메라 시작")

# ==========================================
# 모터 초기화
# ==========================================
pan_tilt = PanTiltController(threshold=0.5, gain=1.0)
pan_tilt.center()
logger.info("Pan/Tilt 서보 초기화 완료 (중앙 복귀)")

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
                frame = camera.capture_bgr()
                if frame is None:
                    await asyncio.sleep(0)
                    continue

                ret, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if ret:
                    await websocket.send(encoded.tobytes())
                    frame_count += 1
                    if frame_count % 100 == 0:
                        logger.debug(f"프레임 전송: {frame_count}장")

                await asyncio.sleep(0)  # 이벤트 루프 양보 (최대 속도)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def receive_commands():
        """PC에서 오는 JSON 제어 명령 수신.
        보정이 적용된 경우 보정값을 0으로 초기화한 완료 응답을 PC로 전송한다.
        """
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    loop = asyncio.get_event_loop()
                    applied = await loop.run_in_executor(None, pan_tilt.handle_command, data)
                    if applied:
                        await websocket.send(json.dumps({
                            "type": "motor_corrected",
                            "control": {"pan": 0, "tilt": 0}
                        }))
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
        camera.stop()
        pan_tilt.cleanup()
