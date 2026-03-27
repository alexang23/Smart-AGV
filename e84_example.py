"""
E84 Protocol 使用範例

展示如何使用 E84Client 類別的各種功能：
1. 基本使用方式
2. 事件處理（Callbacks + Queue）
3. 完整的 Load/Unload 流程
4. 錯誤處理
5. 進階功能
"""

import asyncio
import logging
from e84 import E84Client, E84Event

COM_PORT = "COM14"  # 根據實際情況修改
BAUDRATE = 115200

# 設定 logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ==================== 範例 1: 基本使用 ====================

async def example_basic():
    """範例 1: 基本使用方式"""
    print("\n" + "=" * 60)
    print("範例 1: 基本使用方式")
    print("=" * 60)
    
    # 創建 E84 客戶端
    e84 = E84Client(
        port=COM_PORT,  # 根據實際情況修改
        baudrate=BAUDRATE,
        auto_reconnect=True
    )
    
    # 連線
    success = await e84.connect_async()
    if not success:
        print("❌ 連線失敗")
        return
    
    try:
        # 讀取韌體版本
        version = await e84.read_firmware_version()
        if version:
            print(f"✅ 韌體版本: {version[0]}.{version[1]}")

        await e84.disconnect_async()
        return
        
        # 初始化 TA 參數
        print("\n初始化 Timeout 參數...")
        if await e84.initialize_timeout_params():
            print("✅ TA 參數初始化成功")
        
    finally:
        # 斷線
        await e84.disconnect_async()


# ==================== 範例 2: 使用 Context Manager ====================

async def example_context_manager():
    """範例 2: 使用 Context Manager"""
    print("\n" + "=" * 60)
    print("範例 2: Context Manager 使用")
    print("=" * 60)
    
    # 使用 async with 自動管理連線
    async with E84Client(COM_PORT, baudrate=BAUDRATE) as e84:
        version = await e84.read_firmware_version()
        if version:
            print(f"韌體版本: {version[0]}.{version[1]}")


# ==================== 範例 3: 事件處理 - Callbacks ====================

async def example_callbacks():
    """範例 3: 使用 Callbacks 處理事件"""
    print("\n" + "=" * 60)
    print("範例 3: Callbacks 事件處理")
    print("=" * 60)
    
    # 定義回調函數
    def on_sensor_event(signal: str, state: bool):
        """感測器事件回調"""
        state_str = "🟢 ON " if state else "🔴 OFF"
        print(f"[感測器] {signal:10s}: {state_str}")
    
    def on_state_event(code: int, description: str):
        """狀態事件回調"""
        print(f"[狀態] {description}")
    
    # 創建帶回調的客戶端
    e84 = E84Client(
        port=COM_PORT,
        baudrate=BAUDRATE,
        on_sensor_event=on_sensor_event,
        on_state_event=on_state_event
    )
    
    await e84.connect_async()
    
    try:
        # 執行 Load 流程，事件會自動觸發回調
        print("\n開始 Load 流程...")
        success = await e84.load_async()
        if success:
            print("✅ Load 完成")
        else:
            print("❌ Load 失敗")
            
    finally:
        await e84.disconnect_async()


# ==================== 範例 4: 事件處理 - Event Queue ====================

async def example_event_queue():
    """範例 4: 使用 Event Queue 處理事件"""
    print("\n" + "=" * 60)
    print("範例 4: Event Queue 事件處理")
    print("=" * 60)
    
    # 創建帶事件佇列的客戶端
    e84 = E84Client(
        port=COM_PORT,
        baudrate=BAUDRATE,
        event_queue_size=100  # 啟用事件佇列
    )
    
    await e84.connect_async()
    
    try:
        # 啟動事件處理協程
        async def event_processor():
            """事件處理器"""
            print("事件處理器啟動...")
            while True:
                try:
                    # 從佇列獲取事件（阻塞）
                    event: E84Event = await e84.get_event(timeout=1.0)
                    
                    if event.series == 0x70:
                        # 感測器事件
                        print(f"[事件] {event.signal_name}: {event.description}")
                    elif event.series == 0x71:
                        # 狀態事件
                        print(f"[狀態] {event.description}")
                        
                except asyncio.TimeoutError:
                    # 無事件，繼續等待
                    continue
                except Exception as e:
                    print(f"事件處理錯誤: {e}")
                    break
        
        # 啟動事件處理器
        processor_task = asyncio.create_task(event_processor())
        
        # 執行 Load 流程
        print("\n開始 Load 流程...")
        success = await e84.load_async()
        if success:
            print("✅ Load 完成")
        
        # 取消事件處理器
        processor_task.cancel()
        
    finally:
        await e84.disconnect_async()


# ==================== 範例 5: 混合模式 (Callbacks + Queue) ====================

async def example_hybrid():
    """範例 5: 混合模式 - Callbacks + Event Queue"""
    print("\n" + "=" * 60)
    print("範例 5: 混合模式 (Callbacks + Queue)")
    print("=" * 60)
    
    # Callback 用於即時監控
    def quick_monitor(signal: str, state: bool):
        print(f"[即時] {signal}: {'ON' if state else 'OFF'}")
    
    # 創建混合模式客戶端
    e84 = E84Client(
        port=COM_PORT,
        baudrate=BAUDRATE,
        on_sensor_event=quick_monitor,  # Callback 即時通知
        event_queue_size=100             # Queue 處理複雜邏輯
    )
    
    await e84.connect_async()
    
    try:
        # 複雜的事件處理邏輯
        async def complex_event_handler():
            """複雜的事件處理邏輯"""
            l_req_count = 0
            while True:
                try:
                    event = await e84.get_event(timeout=1.0)
                    
                    # 複雜的狀態機處理
                    if event.signal_name == "L_REQ":
                        l_req_count += 1
                        print(f"[分析] L_REQ 觸發次數: {l_req_count}")
                    
                    # 其他複雜邏輯...
                    
                except asyncio.TimeoutError:
                    continue
        
        handler_task = asyncio.create_task(complex_event_handler())
        
        # 執行 Load
        success = await e84.load_async()
        print(f"Load 結果: {'成功' if success else '失敗'}")
        
        handler_task.cancel()
        
    finally:
        await e84.disconnect_async()


# ==================== 範例 6: 完整的 Load 流程 ====================

async def example_load_process():
    """範例 6: 完整的 Load 流程"""
    print("\n" + "=" * 60)
    print("範例 6: 完整的 Load 流程")
    print("=" * 60)
    
    async with E84Client(COM_PORT, baudrate=BAUDRATE) as e84:
        # 初始化
        await e84.initialize_timeout_params()
        
        # 執行 Load
        success = await e84.load_async(timeout_per_step=5.0)
        
        if success:
            print("\n✅ Load 流程成功完成！")
            print("可以進行下一步操作...")
        else:
            print("\n❌ Load 流程失敗！")
            print("請檢查設備狀態和日誌")


# ==================== 範例 7: 完整的 Unload 流程 ====================

async def example_unload_process():
    """範例 7: 完整的 Unload 流程"""
    print("\n" + "=" * 60)
    print("範例 7: 完整的 Unload 流程")
    print("=" * 60)
    
    async with E84Client(COM_PORT, baudrate=BAUDRATE) as e84:
        # 初始化
        await e84.initialize_timeout_params()
        
        # 執行 Unload
        success = await e84.unload_async(timeout_per_step=5.0)
        
        if success:
            print("\n✅ Unload 流程成功完成！")
            print("貨物已取出")
        else:
            print("\n❌ Unload 流程失敗！")
            print("請檢查設備狀態和日誌")


# ==================== 範例 8: 錯誤處理 ====================

async def example_error_handling():
    """範例 8: 錯誤處理"""
    print("\n" + "=" * 60)
    print("範例 8: 錯誤處理")
    print("=" * 60)
    
    e84 = E84Client(COM_PORT, baudrate=BAUDRATE, auto_reconnect=True)
    
    try:
        # 嘗試連線
        if not await e84.connect_async():
            print("❌ 連線失敗，可能原因：")
            print("   1. 串口不存在或已被占用")
            print("   2. 串口權限不足")
            print("   3. 波特率不正確")
            return
        
        # 執行操作
        try:
            success = await e84.load_async(timeout_per_step=5.0)
            if not success:
                print("⚠️  Load 流程失敗，可能原因：")
                print("   1. 設備未回應")
                print("   2. 訊號超時")
                print("   3. 設備處於錯誤狀態")
                
                # 嘗試重置
                print("嘗試 Alarm Reset...")
                await e84.alarm_reset()
                
        except asyncio.TimeoutError:
            print("❌ 操作超時")
        except Exception as e:
            print(f"❌ 操作異常: {e}")
            
    finally:
        # 確保斷線
        if e84._state.value == "connected":
            await e84.disconnect_async()


# ==================== 範例 9: 手動控制步驟 ====================

async def example_manual_control():
    """範例 9: 手動控制每個步驟"""
    print("\n" + "=" * 60)
    print("範例 9: 手動控制步驟")
    print("=" * 60)
    
    async with E84Client(COM_PORT, baudrate=BAUDRATE, event_queue_size=50) as e84:
        # 初始化
        await e84.initialize_timeout_params()
        
        # 手動執行每個步驟
        print("\n[步驟 1] DB25 Port Open")
        if not await e84.db25_port_control(open=True):
            print("失敗")
            return
        input("按 Enter 繼續...")
        
        print("\n[步驟 2] SELECT ON")
        if not await e84.select_control(select_on=True):
            print("失敗")
            return
        input("按 Enter 繼續...")
        
        print("\n[步驟 3] SELECT OFF")
        if not await e84.select_control(select_on=False):
            print("失敗")
            return
        input("按 Enter 繼續...")
        
        print("\n[步驟 4] 發送 LOAD 命令")
        if not await e84.send_load_command():
            print("失敗")
            return
        
        print("\n等待設備回應...")
        print("（監控事件佇列）")
        
        # 監控幾個事件
        for i in range(10):
            try:
                event = await e84.get_event(timeout=2.0)
                print(f"  事件: {event.signal_name} = {event.description}")
            except asyncio.TimeoutError:
                break
        
        print("\n後續步驟省略...")


# ==================== 範例 10: 生產環境使用模式 ====================

async def example_production():
    """範例 10: 生產環境使用模式"""
    print("\n" + "=" * 60)
    print("範例 10: 生產環境使用模式")
    print("=" * 60)
    
    # 統計資訊
    stats = {
        "total_loads": 0,
        "successful_loads": 0,
        "failed_loads": 0,
    }
    
    def on_state(code: int, desc: str):
        """記錄重要狀態"""
        logging.info(f"狀態變更: {desc}")
    
    # 創建生產級客戶端
    e84 = E84Client(
        port=COM_PORT,
        baudrate=BAUDRATE,
        auto_reconnect=True,
        reconnect_interval=2.0,
        on_state_event=on_state,
        event_queue_size=200
    )
    
    await e84.connect_async()
    
    try:
        # 初始化一次
        await e84.initialize_timeout_params()
        
        # 模擬連續操作
        for i in range(3):
            print(f"\n--- 第 {i+1} 次 Load ---")
            stats["total_loads"] += 1
            
            try:
                success = await e84.load_async(timeout_per_step=5.0)
                if success:
                    stats["successful_loads"] += 1
                    print(f"✅ Load #{i+1} 成功")
                else:
                    stats["failed_loads"] += 1
                    print(f"❌ Load #{i+1} 失敗")
                    # 嘗試恢復
                    await e84.alarm_reset()
                    await asyncio.sleep(2.0)
                    
            except Exception as e:
                stats["failed_loads"] += 1
                print(f"❌ Load #{i+1} 異常: {e}")
            
            # 間隔
            await asyncio.sleep(1.0)
        
        # 顯示統計
        print("\n" + "=" * 60)
        print("統計資訊:")
        print(f"  總計: {stats['total_loads']}")
        print(f"  成功: {stats['successful_loads']}")
        print(f"  失敗: {stats['failed_loads']}")
        print(f"  成功率: {stats['successful_loads']/stats['total_loads']*100:.1f}%")
        
    finally:
        await e84.disconnect_async()


# ==================== 主程式 ====================

async def main():
    """主程式 - 選擇要執行的範例"""
    print("\n" + "=" * 60)
    print("E84 Protocol 使用範例")
    print("=" * 60)
    print("\n請選擇要執行的範例：")
    print("1. 基本使用")
    print("2. Context Manager")
    print("3. Callbacks 事件處理")
    print("4. Event Queue 事件處理")
    print("5. 混合模式 (Callbacks + Queue)")
    print("6. 完整 Load 流程")
    print("7. 完整 Unload 流程")
    print("8. 錯誤處理")
    print("9. 手動控制步驟")
    print("10. 生產環境模式")
    print("0. 執行所有範例（需要設備連接）")
    
    choice = input("\n請輸入選項 (0-10): ").strip()
    
    examples = {
        "1": example_basic,
        "2": example_context_manager,
        "3": example_callbacks,
        "4": example_event_queue,
        "5": example_hybrid,
        "6": example_load_process,
        "7": example_unload_process,
        "8": example_error_handling,
        "9": example_manual_control,
        "10": example_production,
    }
    
    if choice == "0":
        # 執行所有範例
        for key in sorted(examples.keys()):
            try:
                await examples[key]()
                await asyncio.sleep(1.0)
            except Exception as e:
                print(f"範例 {key} 執行錯誤: {e}")
                continue
    elif choice in examples:
        # 執行選定的範例
        try:
            await examples[choice]()
        except Exception as e:
            print(f"執行錯誤: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("無效的選項")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程式已中止")
