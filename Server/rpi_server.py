import asyncio
import json
import sys
import os
import cv2
import websockets
import queue

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from modules.motor_module_pca9685 import PanTiltController
from modules.camera_module import CameraModule
from modules.logger import get_logger

# ==========================================
# 설정
# ==========================================
HOST = "0.0.0.0"  # 모든 IP에서 접속 허용
PORT = 8000       # spotlight_core.py의 RPI_WS_URL 포트와 일치해야 함

# ==========================================
# 로거
# ==========================================
logger = get_logger("rpi_server")

# ==========================================
# H.264 버퍼 클래스
# ==========================================
class H264StreamOutput:
    """하드웨어 인코더에서 실시간으로 생성된 바이트 스트림을 버퍼링하는 클래스"""
    def __init__(self):
        self.q = queue.Queue(maxsize=30)  # 네트워크 지연 대비 버퍼 큐

    def write(self, buf):
        try:
            # 큐가 가득 차면 새 프레임을 드롭하여 메모리 누수 방지 및 최신 상태 유지
            self.q.put_nowait(buf)
        except queue.Full:
            pass

    def flush(self):
        pass

# ==========================================
# 카메라 초기화
# ==========================================
camera = CameraModule()
logger.info("카메라 시작")

# ==========================================
# 모터 초기화
# ==========================================
pan_tilt = PanTiltController(threshold=0.5, gain=0.3)
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
        """하드웨어 인코딩된 H.264 바이트 스트림을 PC로 전송."""
        nonlocal frame_count
        
        output = H264StreamOutput()
        camera.start_h264_stream(output)
        
        loop = asyncio.get_running_loop()
        try:
            while True:
                # 큐에서 바이트 데이터를 대기하여 가져옴 (blocking I/O 처리를 비동기로 수행)
                buf = await loop.run_in_executor(None, output.q.get)
                await websocket.send(buf)
                
                frame_count += 1
                if frame_count % 100 == 0:
                    logger.debug(f"H.264 패킷 전송: {frame_count}개")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            camera.stop_h264_stream()

    async def receive_commands():
        """PC에서 오는 JSON 제어 명령 수신.

        ★ PID 방식 (신규):
            { "type": "servo_angle", "pan_angle": float, "tilt_angle": float }
            → 절대 각도로 서보 이동, 응답 없음 (일방향)

        ★ 구버전 방식 (하위 호환):
            { "tracking": "on", "control": { "pan": float, "tilt": float } }
            → 델타 보정 적용
        """
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, pan_tilt.handle_command, data)
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
