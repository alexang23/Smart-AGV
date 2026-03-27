"""
AsyncSerialPort 簡單測試

這個文件展示最基本的使用方式，可以用於快速測試串口通訊
"""

import asyncio
import logging
from serial_gyro import AsyncSerialPort

# 設定 logging 查看詳細信息
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

COM_PORT = "COM14"  # 根據實際情況修改
PORT_BAUDRATE = 115200

async def simple_test():
    """簡單測試"""
    print("="*60)
    print("AsyncSerialPort 簡單測試")
    print("="*60)
    
    # 配置串口參數（請根據實際情況修改）
    PORT = COM_PORT
    BAUDRATE = PORT_BAUDRATE

    print(f"\n正在連線到 {PORT} (波特率: {BAUDRATE})...")
    
    # 創建串口實例
    serial = AsyncSerialPort(
        port=PORT,
        baudrate=BAUDRATE,
        auto_reconnect=True,
        reconnect_interval=2.0,
        response_timeout=5.0,
        # 回調函數
        on_connected=lambda: print("✅ 連線成功!"),
        on_disconnected=lambda: print("❌ 連線中斷!"),
        on_reconnecting=lambda: print("🔄 正在嘗試重連...")
    )
    
    try:
        # 方式 1: Async 連線
        success = await serial.connect_async()
        if not success:
            print("❌ 連線失敗，請檢查:")
            print("   1. 串口名稱是否正確")
            print("   2. 串口是否已被其他程序占用")
            print("   3. 波特率等參數是否正確")
            return
        
        print("\n" + "="*60)
        print("測試 1: 發送簡單命令（不等待回應）")
        print("="*60)
        
        # 發送不需要回應的數據
        await serial.write_async(b"HELLO WORLD\r\n")
        print("✅ 已發送: HELLO WORLD")
        
        print("\n" + "="*60)
        print("測試 2: 發送命令並等待回應")
        print("="*60)
        
        # 發送需要回應的命令
        # 注意: 這裡使用預設的協議格式 "RESPONSE:command_id:data"
        # 您需要根據實際設備的協議格式調整
        print("發送命令: GET_STATUS")
        print("期待回應格式: RESPONSE:STATUS_001:data")
        
        try:
            response = await serial.send_command_async(
                command_id="STATUS_001",
                data=b"GET_STATUS\r\n",
                timeout=5.0
            )
            print(f"✅ 收到回應: {response}")
            
        except TimeoutError:
            print("⏱️  未在 5 秒內收到回應")
            print("   提示: 檢查設備是否正確回應，或調整 response_parser")
        
        print("\n" + "="*60)
        print("測試 3: 查看統計信息")
        print("="*60)
        
        stats = serial.statistics
        print(f"發送字節數: {stats['bytes_sent']}")
        print(f"接收字節數: {stats['bytes_received']}")
        print(f"發送命令數: {stats['commands_sent']}")
        print(f"接收回應數: {stats['responses_received']}")
        print(f"超時次數: {stats['timeouts']}")
        print(f"重連次數: {stats['reconnects']}")
        
        # 回應時間統計
        if stats['response_times']['count'] > 0:
            print("\n回應時間統計:")
            serial.print_response_time_stats()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n正在斷線...")
        await serial.disconnect_async()
        print("✅ 測試完成")


def simple_sync_test():
    """同步方式測試"""
    print("="*60)
    print("AsyncSerialPort 同步測試")
    print("="*60)
    
    PORT = COM_PORT
    BAUDRATE = PORT_BAUDRATE

    print(f"\n正在連線到 {PORT} (波特率: {BAUDRATE})...")
    
    serial = AsyncSerialPort(
        port=PORT,
        baudrate=BAUDRATE,
        auto_reconnect=True
    )
    
    try:
        # 方式 2: Sync 連線
        success = serial.connect()
        if not success:
            print("❌ 連線失敗")
            return
        
        print("✅ 連線成功")
        
        # Sync 寫入
        serial.write(b"HELLO FROM SYNC\r\n")
        print("✅ 已發送數據")
        
        # Sync 命令（等待回應）
        try:
            response = serial.send_command(
                command_id="SYNC_CMD_001",
                data=b"GET_DATA\r\n",
                timeout=5.0
            )
            print(f"✅ 收到回應: {response}")
        except TimeoutError:
            print("⏱️  超時未收到回應")
        
        # 查看統計
        print(f"\n統計: 發送 {serial.statistics['commands_sent']} 個命令")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    finally:
        serial.disconnect()
        print("✅ 測試完成")


# 自定義協議解析器範例
def custom_parser(response: bytes):
    """
    自定義協議解析器
    
    根據您的實際協議格式修改此函數
    
    例如:
    - 如果回應格式是 "CMD_ID:DATA\r\n"
    - 如果回應格式是 JSON: {"id": "xxx", "data": "yyy"}
    - 如果回應格式是固定長度，前 4 字節是 ID
    
    Returns:
        Tuple[Optional[str], bytes]: (command_id, response_data)
    """
    try:
        # 範例: 假設格式是 "CMD_ID:DATA\r\n"
        response = response.rstrip(b'\r\n')
        parts = response.split(b':', 1)
        if len(parts) == 2:
            cmd_id = parts[0].decode('utf-8')
            data = parts[1]
            return cmd_id, data
    except:
        pass
    
    # 如果無法解析，返回 None
    return None, response


async def test_with_custom_parser():
    """使用自定義協議解析器的測試"""
    print("="*60)
    print("使用自定義協議解析器")
    print("="*60)
    
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=PORT_BAUDRATE,
        response_parser=custom_parser  # 使用自定義解析器
    )
    
    await serial.connect_async()
    
    try:
        # 使用自定義格式發送命令
        response = await serial.send_command_async(
            command_id="MY_CMD_001",
            data=b"SOME_COMMAND\r\n",
            timeout=5.0
        )
        print(f"收到回應: {response}")
    finally:
        await serial.disconnect_async()


if __name__ == "__main__":
    print("\n選擇測試模式:")
    print("1. Async 測試 (推薦)")
    print("2. Sync 測試")
    print("3. 自定義協議測試")
    
    choice = input("\n請輸入選項 (1-3, 直接按 Enter 執行 Async 測試): ").strip()
    
    if choice == "2":
        simple_sync_test()
    elif choice == "3":
        asyncio.run(test_with_custom_parser())
    else:
        asyncio.run(simple_test())
