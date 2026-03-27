import asyncio
import sys
import pathlib

# 將專案根目錄加入 sys.path，使測試模組可被直接 import
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.test_e84_client_queue_cross_loop import (
    test_put_from_different_loop_thread,
    test_put_from_same_loop,
)


async def main():
    await test_put_from_different_loop_thread()
    await test_put_from_same_loop()
    print("All tests passed")


if __name__ == "__main__":
    asyncio.run(main())
