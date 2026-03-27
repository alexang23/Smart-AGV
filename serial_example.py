"""
AsyncSerialPort 使用範例

展示如何使用 AsyncSerialPort 類別的各種功能：
1. Async 和 Sync 使用方式
2. Context Manager
3. 命令發送與回應匹配
4. 自動重連
5. 回應時間統計
"""

import asyncio
import logging
from serial_gyro import AsyncSerialPort, ConnectionState

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

COM_PORT = "COM14"  # 根據實際情況修改
BAUDRATE = 115200


# ==================== 範例 1: Async 使用方式 ====================

async def example_async_basic():
    """基本 async 使用範例"""
    print("\n" + "="*60)
    print("範例 1: 基本 Async 使用")
    print("="*60)
    
    # 創建實例
    serial = AsyncSerialPort(
        port=COM_PORT,  # 根據實際情況修改
        baudrate=BAUDRATE,
        auto_reconnect=True,
        reconnect_interval=2.0,
        response_timeout=3.0
    )
    
    # 連線
    success = await serial.connect_async()
    if not success:
        print("連線失敗")
        return
    
    try:
        # 發送不需要回應的命令
        await serial.write_async(b"PING\r\n")
        print("已發送 PING 命令")
        
        # 發送需要回應的命令
        response = await serial.send_command_async(
            command_id="STATUS_001",
            data=b"RESPONSE:STATUS_001:OK\r\n",  # 模擬回應格式
            timeout=3.0
        )
        print(f"收到回應: {response}")
        
    finally:
        # 斷線
        await serial.disconnect_async()


# ==================== 範例 2: Sync 使用方式 ====================

def example_sync_basic():
    """基本 sync 使用範例"""
    print("\n" + "="*60)
    print("範例 2: 基本 Sync 使用")
    print("="*60)
    
    # 創建實例
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=BAUDRATE,
        auto_reconnect=True
    )
    
    # 連線
    success = serial.connect()
    if not success:
        print("連線失敗")
        return
    
    try:
        # Sync 寫入
        serial.write(b"HELLO\r\n")
        print("已發送 HELLO 命令")
        
        # Sync 命令並等待回應
        response = serial.send_command(
            command_id="GET_DATA_001",
            data=b"GET_DATA\r\n",
            timeout=3.0
        )
        print(f"收到回應: {response}")
        
    finally:
        # 斷線
        serial.disconnect()


# ==================== 範例 3: Context Manager ====================

async def example_async_context_manager():
    """使用 async context manager"""
    print("\n" + "="*60)
    print("範例 3: Async Context Manager")
    print("="*60)
    
    # 自動連線和斷線
    async with AsyncSerialPort(COM_PORT, baudrate=BAUDRATE) as serial:
        response = await serial.send_command_async(
            command_id="CMD_001",
            data=b"RESPONSE:CMD_001:DATA\r\n"
        )
        print(f"收到回應: {response}")
    # 離開 with 區塊時自動斷線


def example_sync_context_manager():
    """使用 sync context manager"""
    print("\n" + "="*60)
    print("範例 4: Sync Context Manager")
    print("="*60)
    
    # 自動連線和斷線
    with AsyncSerialPort(COM_PORT, baudrate=BAUDRATE) as serial:
        response = serial.send_command(
            command_id="CMD_002",
            data=b"GET_STATUS\r\n"
        )
        print(f"收到回應: {response}")
    # 離開 with 區塊時自動斷線


# ==================== 範例 5: 事件回調 ====================

async def example_callbacks():
    """使用事件回調"""
    print("\n" + "="*60)
    print("範例 5: 事件回調")
    print("="*60)
    
    def on_connected():
        print("✅ 已連線!")
    
    def on_disconnected():
        print("❌ 已斷線!")
    
    def on_reconnecting():
        print("🔄 正在重連...")
    
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=BAUDRATE,
        auto_reconnect=True,
        on_connected=on_connected,
        on_disconnected=on_disconnected,
        on_reconnecting=on_reconnecting
    )
    
    await serial.connect_async()
    
    # 模擬一些操作
    await asyncio.sleep(2)
    
    await serial.disconnect_async()


# ==================== 範例 6: 並發命令 ====================

async def example_concurrent_commands():
    """同時發送多個命令"""
    print("\n" + "="*60)
    print("範例 6: 並發命令")
    print("="*60)
    
    async with AsyncSerialPort(COM_PORT, baudrate=BAUDRATE) as serial:
        # 同時發送多個命令
        tasks = [
            serial.send_command_async("CMD_001", b"RESPONSE:CMD_001:POS_X\r\n"),
            serial.send_command_async("CMD_002", b"RESPONSE:CMD_002:POS_Y\r\n"),
            serial.send_command_async("CMD_003", b"RESPONSE:CMD_003:SPEED\r\n"),
        ]
        
        # 等待所有命令完成
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses, 1):
            if isinstance(response, Exception):
                print(f"命令 {i} 失敗: {response}")
            else:
                print(f"命令 {i} 回應: {response}")


# ==================== 範例 7: 混合 Async/Sync 使用 ====================

async def example_mixed_async_sync():
    """混合使用 async 和 sync API"""
    print("\n" + "="*60)
    print("範例 7: 混合 Async/Sync")
    print("="*60)
    
    serial = AsyncSerialPort(COM_PORT, baudrate=BAUDRATE)
    serial.connect()  # Sync 連線
    
    try:
        # 在 async 函數中發送 async 命令
        response1 = await serial.send_command_async(
            "ASYNC_CMD",
            b"RESPONSE:ASYNC_CMD:DATA1\r\n"
        )
        print(f"Async 回應: {response1}")
        
        # 也可以在同一個 async 函數中調用 sync 方法（不推薦，僅示範）
        # response2 = serial.send_command("SYNC_CMD", b"GET_DATA\r\n")
        # print(f"Sync 回應: {response2}")
        
    finally:
        await serial.disconnect_async()  # Async 斷線


# ==================== 範例 8: 自定義協議解析器 ====================

def custom_json_parser(response: bytes):
    """
    自定義 JSON 協議解析器
    假設格式: {"cmd_id": "xxx", "data": "yyy"}
    """
    import json
    try:
        data = json.loads(response.decode('utf-8'))
        cmd_id = data.get("cmd_id")
        return cmd_id, response
    except:
        return None, response


async def example_custom_parser():
    """使用自定義協議解析器"""
    print("\n" + "="*60)
    print("範例 8: 自定義協議解析器")
    print("="*60)
    
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=BAUDRATE,
        response_parser=custom_json_parser
    )
    
    await serial.connect_async()
    
    try:
        # 發送 JSON 格式的命令
        response = await serial.send_command_async(
            command_id="JSON_CMD_001",
            data=b'{"cmd": "get_status"}\n'
        )
        print(f"JSON 回應: {response}")
        
    finally:
        await serial.disconnect_async()


# ==================== 範例 9: 回應時間統計 ====================

async def example_response_time_stats():
    """回應時間統計"""
    print("\n" + "="*60)
    print("範例 9: 回應時間統計")
    print("="*60)
    
    async with AsyncSerialPort(COM_PORT, baudrate=BAUDRATE) as serial:
        # 發送多個命令來收集統計數據
        for i in range(10):
            try:
                response = await serial.send_command_async(
                    command_id=f"PERF_TEST_{i:03d}",
                    data=f"RESPONSE:PERF_TEST_{i:03d}:OK\r\n".encode(),
                    timeout=5.0
                )
                print(f"命令 {i} 完成")
                await asyncio.sleep(0.1)  # 模擬間隔
            except TimeoutError:
                print(f"命令 {i} 超時")
        
        # 打印統計報告
        serial.print_response_time_stats()
        
        # 獲取統計數據
        stats = serial.get_response_time_stats()
        print(f"\n平均回應時間: {stats['avg_ms']:.2f} ms")
        print(f"最小回應時間: {stats['min_ms']:.2f} ms")
        print(f"最大回應時間: {stats['max_ms']:.2f} ms")


# ==================== 範例 10: 錯誤處理 ====================

async def example_error_handling():
    """錯誤處理範例"""
    print("\n" + "="*60)
    print("範例 10: 錯誤處理")
    print("="*60)
    
    serial = AsyncSerialPort(COM_PORT, baudrate=BAUDRATE)
    
    try:
        # 嘗試連線
        if not await serial.connect_async():
            print("連線失敗，請檢查串口設定")
            return
        
        try:
            # 發送命令
            response = await serial.send_command_async(
                command_id="TEST_CMD",
                data=b"GET_DATA\r\n",
                timeout=2.0
            )
            print(f"成功: {response}")
            
        except TimeoutError as e:
            print(f"超時錯誤: {e}")
        except ValueError as e:
            print(f"參數錯誤: {e}")
        except ConnectionError as e:
            print(f"連線錯誤: {e}")
            
    finally:
        if serial.is_connected:
            await serial.disconnect_async()


# ==================== 範例 11: 實際應用場景 ====================

async def example_real_world_agv():
    """
    實際應用：AGV 控制
    大部分命令用 async，少數關鍵命令用 sync
    """
    print("\n" + "="*60)
    print("範例 11: 實際 AGV 應用場景")
    print("="*60)
    
    # 初始化串口
    serial = AsyncSerialPort(
        port=COM_PORT,
        baudrate=BAUDRATE,
        auto_reconnect=True,
        reconnect_interval=1.0,
        response_timeout=3.0
    )
    
    serial.connect()
    
    try:
        # 背景任務：持續發送狀態更新（async）
        async def status_updater():
            cmd_count = 0
            while serial.is_connected:
                try:
                    await serial.send_command_async(
                        command_id=f"STATUS_{cmd_count:04d}",
                        data=b"RESPONSE:STATUS:OK\r\n",
                        expect_response=False  # 不需要回應
                    )
                    cmd_count += 1
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"狀態更新錯誤: {e}")
        
        # 啟動背景任務
        status_task = asyncio.create_task(status_updater())
        
        # 主程序：定期檢查關鍵參數（sync）
        for i in range(5):
            await asyncio.sleep(2)
            
            # 使用 sync 方法獲取關鍵位置信息
            try:
                position = serial.send_command(
                    command_id=f"GET_POS_{i:03d}",
                    data=b"GET_POSITION\r\n",
                    timeout=2.0
                )
                print(f"[主程序] 位置: {position}")
            except TimeoutError:
                print(f"[主程序] 位置查詢超時")
        
        # 停止背景任務
        status_task.cancel()
        try:
            await status_task
        except asyncio.CancelledError:
            pass
        
        # 打印統計
        print(f"\n總計發送: {serial.statistics['commands_sent']} 個命令")
        print(f"總計接收: {serial.statistics['responses_received']} 個回應")
        print(f"超時次數: {serial.statistics['timeouts']}")
        
    finally:
        serial.disconnect()


# ==================== 主程序 ====================

async def main():
    """運行所有範例"""
    print("\n" + "="*70)
    print(" AsyncSerialPort 使用範例集")
    print("="*70)
    
    # 選擇要運行的範例（取消註解來運行）
    
    # await example_async_basic()
    example_sync_basic()
    # await example_async_context_manager()
    # example_sync_context_manager()
    # await example_callbacks()
    # await example_concurrent_commands()
    # await example_mixed_async_sync()
    # await example_custom_parser()
    # await example_response_time_stats()
    # await example_error_handling()
    # await example_real_world_agv()
    
    print("\n提示: 請根據實際串口配置修改 port 參數")
    print("範例代碼需要根據實際協議調整 response_parser")
    print("部分範例需要實際硬件才能運行\n")


if __name__ == "__main__":
    # 運行範例
    asyncio.run(main())
