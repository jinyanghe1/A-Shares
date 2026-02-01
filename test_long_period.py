"""测试长周期数据获取功能"""
import asyncio
from app.utils.eastmoney import eastmoney_api
from app.services.analysis_service import analysis_service


async def test_kline_data_periods():
    """测试不同周期的K线数据获取"""
    test_code = "000001"  # 平安银行
    periods = [60, 120, 250, 500, 750, 1250, 2500]

    print("=" * 80)
    print("测试不同周期的K线数据获取")
    print("=" * 80)

    for days in periods:
        print(f"\n测试周期: {days}天")
        try:
            data = await eastmoney_api.get_kline_data(test_code, days)
            if data:
                print(f"✓ 成功获取 {len(data)} 条数据")
                print(f"  起始日期: {data[0]['date']}")
                print(f"  结束日期: {data[-1]['date']}")
                print(f"  收盘价范围: {min(d['close'] for d in data):.2f} - {max(d['close'] for d in data):.2f}")

                # 验证数据类型
                sample = data[0]
                assert isinstance(sample['close'], (int, float)), "close应该是数字类型"
                assert isinstance(sample['volume'], (int, float)), "volume应该是数字类型"
                print(f"  ✓ 数据类型验证通过")
            else:
                print(f"✗ 未获取到数据")
        except Exception as e:
            print(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()


async def test_correlation_analysis():
    """测试相关性分析在不同周期下的表现"""
    code1 = "000001"  # 平安银行
    code2 = "600000"  # 浦发银行
    periods = [250, 500, 750, 1250]

    print("\n" + "=" * 80)
    print("测试不同周期的相关性分析")
    print("=" * 80)

    for days in periods:
        print(f"\n测试周期: {days}天 ({code1} vs {code2})")
        try:
            result = await analysis_service.analyze_correlation(
                code1, code2, days,
                indicators=["ma5", "turnover_rate", "amplitude"]
            )

            if result:
                print(f"✓ 分析成功")
                print(f"  {result['name1']} vs {result['name2']}")
                print(f"  实际分析天数: {result['days']}天")
                print(f"  时间序列数据点: {len(result['time_series'])}")

                # 显示相关系数
                for indicator, data in result['correlation_matrix'].items():
                    print(f"  {data['description']}: {data['value']:.4f} ({data['level']})")

                # 验证数据
                assert result['days'] > 0, "分析天数应大于0"
                assert len(result['time_series']) > 0, "时间序列不应为空"
                print(f"  ✓ 数据验证通过")
            else:
                print(f"✗ 分析失败，返回None")
        except Exception as e:
            print(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()


async def test_macro_correlation():
    """测试宏观数据相关性分析"""
    print("\n" + "=" * 80)
    print("测试宏观数据相关性分析")
    print("=" * 80)

    test_cases = [
        ("000001", "MACRO_CPI", 500),  # 股票 vs 宏观
        ("MACRO_CPI", "MACRO_PMI", 500),  # 宏观 vs 宏观
    ]

    for code1, code2, days in test_cases:
        print(f"\n测试: {code1} vs {code2}, {days}天")
        try:
            result = await analysis_service.analyze_correlation(
                code1, code2, days,
                indicators=["ma5"]
            )

            if result:
                print(f"✓ 分析成功")
                print(f"  {result['name1']} vs {result['name2']}")
                print(f"  时间序列数据点: {len(result['time_series'])}")

                for indicator, data in result['correlation_matrix'].items():
                    print(f"  {data['description']}: {data['value']:.4f} ({data['level']})")

                # 验证时间序列数据
                if result['time_series']:
                    sample = result['time_series'][0]
                    print(f"  样本数据: {sample['date']}")
                    assert 'code1' in sample, "时间序列应包含code1数据"
                    assert 'code2' in sample, "时间序列应包含code2数据"
                    print(f"  ✓ 数据验证通过")
            else:
                print(f"✗ 分析失败，返回None")
        except Exception as e:
            print(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试长周期数据功能\n")

    # 测试1: K线数据获取
    await test_kline_data_periods()

    # 测试2: 相关性分析
    await test_correlation_analysis()

    # 测试3: 宏观数据相关性
    await test_macro_correlation()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
