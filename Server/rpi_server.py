import asyncio
import json
import sys
import os
import websockets

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from modules.motor_module_pca9685 import PanTiltController
from modules.logger import get_logger

# ==========================================
# 설정
# ==========================================
HOST = "0.0.0.0"  # 모든 IP에서 접속 허용
PORT = 8765       # 포트 충돌 방지 (MediaMTX가 8000 사용)

# ==========================================
# 로거
# ==========================================
logger = get_logger("rpi_server")

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
    """PC 접속 시 제어 명령 수신 처리.
    영상 송신은 MediaMTX WebRTC(WHEP)로 전환되어 이 서버에서 담당하지 않음.
    """
    logger.info("PC 연결됨")

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

    receiver = asyncio.create_task(receive_commands())

    try:
        await receiver
    finally:
        receiver.cancel()
        logger.info("PC 연결 해제됨")

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
        pan_tilt.cleanup()
