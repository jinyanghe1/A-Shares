"""简单的东财API测试 - 不依赖app模块"""
import asyncio
import httpx
from datetime import datetime


class SimpleEastMoneyTest:
    """简单的东财API测试类"""

    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    def get_market_code(self, code: str) -> str:
        """获取市场代码"""
        if len(code) == 5:
            return f"116.{code}"
        elif code.startswith("00") or code.startswith("30"):
            return f"0.{code}"
        elif code.startswith("60") or code.startswith("68"):
            return f"1.{code}"
        elif code.startswith("8") or code.startswith("4"):
            return f"0.{code}"
        else:
            return f"1.{code}"

    async def test_kline(self, code: str, days: int):
        """测试K线数据获取"""
        secid = self.get_market_code(code)

        # 测试单次请求
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": 101,
            "fqt": 1,
            "beg": 0,
            "end": 20500101,
            "lmt": min(days, 1000),
            "_": int(datetime.now().timestamp() * 1000)
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(self.KLINE_URL, params=params)
                data = resp.json()

                if data.get("rc") != 0 or not data.get("data"):
                    print(f"  ✗ API返回错误: rc={data.get('rc')}")
                    return None

                klines = data["data"].get("klines", [])
                print(f"  ✓ 成功获取 {len(klines)} 条K线数据")

                if klines:
                    # 解析第一条和最后一条
                    first = klines[0].split(",")
                    last = klines[-1].split(",")
                    print(f"  起始: {first[0]}, 收盘: {first[2]}")
                    print(f"  结束: {last[0]}, 收盘: {last[2]}")

                return klines
            except Exception as e:
                print(f"  ✗ 请求失败: {e}")
                return None


async def main():
    """主测试函数"""
    tester = SimpleEastMoneyTest()

    print("=" * 80)
    print("测试东财API K线数据获取功能")
    print("=" * 80)

    test_cases = [
        ("000001", 60, "平安银行 - 60天"),
        ("000001", 250, "平安银行 - 250天"),
        ("000001", 500, "平安银行 - 500天"),
        ("000001", 1000, "平安银行 - 1000天"),
        ("600000", 500, "浦发银行 - 500天"),
        ("00700", 250, "腾讯控股(港股) - 250天"),
    ]

    for code, days, desc in test_cases:
        print(f"\n测试: {desc}")
        result = await tester.test_kline(code, days)

        if result:
            print(f"  ✓ 测试通过")
        else:
            print(f"  ✗ 测试失败")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
