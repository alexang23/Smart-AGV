"""
測試 AsyncSerialPort 的 FRAME 模式

這個文件展示如何使用幀格式協議（Header + Length + Checksum）
"""

import asyncio
import logging
from serial_gyro import AsyncSerialPort, ProtocolMode

# 設定 logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

COM_PORT = "COM14"  # 根據實際情況修改
BAUDRATE = 115200

# ==================== 自定義幀解析器 ====================

def custom_frame_parser(frame: bytes):
    """
    自定義幀解析器
    
    幀格式範例: [0xAA, 0x55, cmd_id, data1, data2, data3, data4, checksum]
    - Byte 0-1: Header (0xAA55)
    - Byte 2: Command ID
    - Byte 3-6: Data
    - Byte 7: Checksum (sum of bytes 0-6 % 256)
    
    Returns:
        Tuple[Optional[str], bytes]: (command_id, frame_data)
    """
    if len(frame) >= 8:
        cmd_id = f"CMD_{frame[2]:02X}"  # 第 3 字節是命令 ID
        data = frame[3:7]  # 數據部分（bytes 3-6）
        return cmd_id, data
    return None, frame


# ==================== 測試範例 ====================

async def test_frame_mode_basic():
    """基本 FRAME 模式測試"""
    print("\n" + "="*60)
    print("測試 1: 基本 FRAME 模式")
    print("="*60)
    
    # 創建 FRAME 模式的串口實例
    serial = AsyncSerialPort(
        port=COM_PORT,  # 根據實際情況修改
        baudrate=BAUDRATE,
        protocol_mode=ProtocolMode.FRAME,  # 使用 FRAME 模式
        frame_header=b'\xAA\x55',          # 幀頭標記
        frame_length=8,                     # 幀長度
        checksum_enabled=True,              # 啟用 Checksum
        response_parser=custom_frame_parser # 使用自定義解析器
    )
    
    try:
        # 連線
        success = await serial.connect_async()
        if not success:
            print("❌ 連線失敗")
            return
        
        print("✅ 連線成功")
        
        # 構造一個測試幀
        # [0xAA, 0x55, 0x01, 0x11, 0x22, 0x33, 0x44, checksum]
        cmd_id = 0x01
        data = bytes([0x11, 0x22, 0x33, 0x44])
        frame = b'\xAA\x55' + bytes([cmd_id]) + data
        checksum = sum(frame) % 256
        frame = frame + bytes([checksum])
        
        print(f"\n發送幀: {frame.hex()}")
        
        # 發送幀並等待回應
        try:
            response = await serial.send_command_async(
                command_id="CMD_01",
                data=frame,
                timeout=5.0
            )
            print(f"✅ 收到回應: {response.hex()}")
        except TimeoutError:
            print("⏱️  未在 5 秒內收到回應")
        
        # 查看統計
        stats = serial.statistics
        print(f"\n統計資訊:")
        print(f"  發送字節: {stats['bytes_sent']}")
        print(f"  接收字節: {stats['bytes_received']}")
        print(f"  發送命令: {stats['commands_sent']}")
        print(f"  接收回應: {stats['responses_received']}")
        
    finally:
        await serial.disconnect_async()
        print("\n✅ 測試完成")


async def test_frame_mode_concurrent():
    """並發發送多個幀"""
    print("\n" + "="*60)
    print("測試 2: 並發幀命令")
    print("="*60)
    
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=BAUDRATE,
        protocol_mode=ProtocolMode.FRAME,
        frame_header=b'\xAA\x55',
        frame_length=8,
        checksum_enabled=True,
        response_parser=custom_frame_parser
    )
    
    await serial.connect_async()
    
    try:
        # 構造多個測試幀
        def create_frame(cmd_id: int, data: bytes) -> bytes:
            """創建一個完整的幀"""
            frame = b'\xAA\x55' + bytes([cmd_id]) + data
            checksum = sum(frame) % 256
            return frame + bytes([checksum])
        
        # 同時發送多個命令
        tasks = []
        for i in range(3):
            cmd_id = 0x10 + i
            data = bytes([i, i+1, i+2, i+3])
            frame = create_frame(cmd_id, data)
            
            task = serial.send_command_async(
                command_id=f"CMD_{cmd_id:02X}",
                data=frame,
                timeout=3.0
            )
            tasks.append(task)
        
        # 等待所有命令完成
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"命令 {i} 失敗: {response}")
            else:
                print(f"命令 {i} 回應: {response.hex()}")
        
        # 打印回應時間統計
        serial.print_response_time_stats()
        
    finally:
        await serial.disconnect_async()


async def test_line_mode_compatibility():
    """測試 LINE 模式兼容性（確保現有功能不受影響）"""
    print("\n" + "="*60)
    print("測試 3: LINE 模式兼容性")
    print("="*60)
    
    # 使用預設的 LINE 模式
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=BAUDRATE,
        protocol_mode=ProtocolMode.LINE  # 預設模式
    )
    
    await serial.connect_async()
    
    try:
        # 使用傳統的文本協議
        response = await serial.send_command_async(
            command_id="STATUS_001",
            data=b"GET_STATUS\r\n",
            timeout=3.0
        )
        print(f"✅ LINE 模式回應: {response}")
        
    except TimeoutError:
        print("⏱️  LINE 模式超時")
    finally:
        await serial.disconnect_async()


def test_frame_construction():
    """測試幀構造輔助函數"""
    print("\n" + "="*60)
    print("測試 4: 幀構造輔助")
    print("="*60)
    
    def create_frame(cmd_id: int, data: bytes) -> bytes:
        """
        創建標準幀格式
        
        格式: [0xAA, 0x55, cmd_id, data(4 bytes), checksum]
        """
        if len(data) != 4:
            raise ValueError("Data must be 4 bytes")
        
        frame = b'\xAA\x55' + bytes([cmd_id]) + data
        checksum = sum(frame) % 256
        return frame + bytes([checksum])
    
    def parse_frame(frame: bytes):
        """解析幀"""
        if len(frame) != 8:
            return None
        
        if frame[0:2] != b'\xAA\x55':
            return None
        
        # 驗證 checksum
        checksum_calc = sum(frame[:7]) % 256
        checksum_recv = frame[7]
        
        if checksum_calc != checksum_recv:
            return None
        
        cmd_id = frame[2]
        data = frame[3:7]
        return cmd_id, data
    
    # 測試構造和解析
    test_frames = [
        (0x01, bytes([0x11, 0x22, 0x33, 0x44])),
        (0x02, bytes([0xAA, 0xBB, 0xCC, 0xDD])),
        (0xFF, bytes([0x00, 0x00, 0x00, 0x00])),
    ]
    
    for cmd_id, data in test_frames:
        frame = create_frame(cmd_id, data)
        print(f"\n構造幀 (CMD: 0x{cmd_id:02X}): {frame.hex()}")
        
        result = parse_frame(frame)
        if result:
            parsed_cmd, parsed_data = result
            print(f"  解析成功: CMD=0x{parsed_cmd:02X}, Data={parsed_data.hex()}")
            assert parsed_cmd == cmd_id
            assert parsed_data == data
        else:
            print(f"  ❌ 解析失敗")


# ==================== 主程序 ====================

async def main():
    """運行所有測試"""
    print("\n" + "="*70)
    print(" AsyncSerialPort FRAME 模式測試")
    print("="*70)
    
    # 先測試幀構造（不需要硬件）
    test_frame_construction()
    
    # 以下測試需要實際硬件
    print("\n\n提示: 以下測試需要實際串口硬件")
    print("如需運行，請取消註解並配置正確的串口參數\n")
    
    # await test_frame_mode_basic()
    # await test_frame_mode_concurrent()
    # await test_line_mode_compatibility()


if __name__ == "__main__":
    asyncio.run(main())
