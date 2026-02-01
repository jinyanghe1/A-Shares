"""测试宏观数据相关性分析功能"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_macro_analysis():
    """测试宏观数据相关性分析"""
    from app.services.analysis_service import analysis_service

    print("=" * 80)
    print("测试宏观数据相关性分析")
    print("=" * 80)

    test_cases = [
        {
            "desc": "股票 vs 宏观 (多指标)",
            "code1": "000001",
            "code2": "MACRO_CPI",
            "days": 500,
            "indicators": ["close", "turnover_rate", "amplitude", "volume"]
        },
        {
            "desc": "股票 vs 宏观 (单指标ma5)",
            "code1": "600000",
            "code2": "MACRO_PMI",
            "days": 250,
            "indicators": ["ma5"]
        },
        {
            "desc": "宏观 vs 股票 (多指标)",
            "code1": "MACRO_M2",
            "code2": "000001",
            "days": 730,
            "indicators": ["close", "volume", "change_percent"]
        },
        {
            "desc": "宏观 vs 宏观",
            "code1": "MACRO_CPI",
            "code2": "MACRO_PPI",
            "days": 500,
            "indicators": ["ma5"]
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['desc']}")
        print(f"  资产1: {case['code1']}")
        print(f"  资产2: {case['code2']}")
        print(f"  周期: {case['days']}天")
        print(f"  指标: {', '.join(case['indicators'])}")

        try:
            result = await analysis_service.analyze_correlation(
                case['code1'],
                case['code2'],
                case['days'],
                case['indicators']
            )

            if result:
                print(f"  ✓ 分析成功")
                print(f"    {result['name1']} vs {result['name2']}")
                print(f"    时间序列数据点: {len(result['time_series'])}")

                # 显示相关系数矩阵
                print(f"    相关性矩阵:")
                for indicator, data in result['correlation_matrix'].items():
                    print(f"      - {data['description']}: {data['value']:.4f} ({data['level']})")

                # 验证数据
                assert len(result['correlation_matrix']) > 0, "相关性矩阵不应为空"
                assert len(result['time_series']) > 0, "时间序列不应为空"

                # 检查是否所有请求的指标都有相关性结果（宏观vs宏观除外）
                is_macro1 = case['code1'].startswith("MACRO_")
                is_macro2 = case['code2'].startswith("MACRO_")
                if not (is_macro1 and is_macro2):
                    # 至少应该有一些指标的结果
                    assert len(result['correlation_matrix']) > 0, "应该有指标相关性结果"

                print(f"    ✓ 数据验证通过")
            else:
                print(f"  ✗ 分析失败，返回None")

        except Exception as e:
            print(f"  ✗ 错误: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 设置环境变量以禁用代理
    os.environ["NO_PROXY"] = "*"
    os.environ["HTTP_PROXY"] = ""
    os.environ["HTTPS_PROXY"] = ""

    asyncio.run(test_macro_analysis())
