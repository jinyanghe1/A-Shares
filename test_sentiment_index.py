"""测试舆情指数模块功能"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("舆情指数模块测试")
print("=" * 80)


def test_sentiment_service():
    """测试情绪分析服务"""
    print("\n[测试1] 情绪分析服务")
    print("-" * 80)

    try:
        from app.services.sentiment_service import sentiment_service

        # 测试get_sentiment_level
        print("\n1.1 测试舆情等级判定:")
        test_scores = [0.1, 0.3, 0.45, 0.55, 0.65, 0.75, 0.9]
        for score in test_scores:
            level = sentiment_service.get_sentiment_level(score)
            print(f"  得分 {score:.2f} -> {level['icon']} {level['level']} (指数: {level['index']})")

        # 测试calculate_sentiment_index
        print("\n1.2 测试舆情指数计算:")
        mock_news = [
            {"title": "公司业绩大幅增长，市场前景广阔", "date": "2026-01-15", "url": "http://example.com/1"},
            {"title": "新产品发布会成功举办，市场反响热烈", "date": "2026-01-14", "url": "http://example.com/2"},
            {"title": "股价回调，分析师建议观望", "date": "2026-01-13", "url": "http://example.com/3"},
            {"title": "公司发布年度报告", "date": "2026-01-12", "url": "http://example.com/4"},
            {"title": "面临行业竞争压力", "date": "2026-01-11", "url": "http://example.com/5"},
            {"title": "技术创新获得国家专利", "date": "2026-01-10", "url": "http://example.com/6"},
            {"title": "高管团队稳定", "date": "2026-01-09", "url": "http://example.com/7"},
            {"title": "股东大会顺利召开", "date": "2026-01-08", "url": "http://example.com/8"},
            {"title": "营收持续增长，创历史新高", "date": "2026-01-07", "url": "http://example.com/9"},
            {"title": "获得重大订单，业绩有望提升", "date": "2026-01-06", "url": "http://example.com/10"},
        ]

        result = sentiment_service.calculate_sentiment_index(mock_news)

        print(f"  舆情指数: {result['index']}")
        print(f"  舆情等级: {result['level_info']['icon']} {result['level_info']['level']}")
        print(f"  加权得分: {result['weighted_score']:.4f}")
        print(f"  简单得分: {result['simple_score']:.4f}")
        print(f"  新闻总数: {result['total_news']}")

        print(f"\n  情绪分布:")
        for key, value in result['distribution'].items():
            print(f"    {value['label']}: {value['count']} ({value['ratio']*100:.1f}%)")

        print(f"\n  趋势分析: {result['trend']['description']}")
        print(f"    变化幅度: {result['trend']['change']:.2f}%")

        if result['keywords']:
            print(f"\n  热门关键词:")
            for kw in result['keywords'][:5]:
                print(f"    - {kw['word']} ({kw['count']})")

        print("\n  ✓ 舆情指数计算测试通过")

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_eastmoney_market_news():
    """测试市场新闻获取"""
    print("\n[测试2] 市场新闻获取 (需要网络)")
    print("-" * 80)

    try:
        import asyncio

        async def fetch_news():
            # 设置环境变量以禁用代理
            os.environ["NO_PROXY"] = "*"
            os.environ["HTTP_PROXY"] = ""
            os.environ["HTTPS_PROXY"] = ""

            from app.utils.eastmoney import eastmoney_api

            print("\n2.1 测试获取市场新闻:")
            news = await eastmoney_api.get_market_news("all", page_size=10)
            if news:
                print(f"  ✓ 成功获取 {len(news)} 条市场新闻")
                for i, n in enumerate(news[:3], 1):
                    print(f"    {i}. {n['title'][:40]}...")
            else:
                print("  ⚠ 未获取到市场新闻（可能是API限制）")

            print("\n2.2 测试获取个股新闻:")
            stock_news = await eastmoney_api.get_stock_news("000001", page_size=10)
            if stock_news:
                print(f"  ✓ 成功获取 {len(stock_news)} 条个股新闻")
                for i, n in enumerate(stock_news[:3], 1):
                    print(f"    {i}. {n['title'][:40]}...")
            else:
                print("  ⚠ 未获取到个股新闻")

        asyncio.run(fetch_news())
        print("\n  ✓ 新闻获取测试完成")

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_file_changes():
    """检查文件修改"""
    print("\n[测试3] 检查文件修改")
    print("-" * 80)

    files = [
        ("app/services/sentiment_service.py", "舆情指数计算"),
        ("app/utils/eastmoney.py", "市场新闻获取"),
        ("app/routers/analysis.py", "舆情API端点"),
        ("static/index.html", "前端舆情模块"),
    ]

    for filepath, desc in files:
        if os.path.exists(filepath):
            # 检查文件内容
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if filepath == "app/services/sentiment_service.py":
                if "calculate_sentiment_index" in content:
                    print(f"  ✓ {filepath} - {desc} (已包含舆情指数计算)")
                else:
                    print(f"  ⚠ {filepath} - 缺少舆情指数计算方法")

            elif filepath == "app/utils/eastmoney.py":
                if "get_market_news" in content:
                    print(f"  ✓ {filepath} - {desc} (已包含市场新闻获取)")
                else:
                    print(f"  ⚠ {filepath} - 缺少市场新闻获取方法")

            elif filepath == "app/routers/analysis.py":
                if "sentiment/index" in content:
                    print(f"  ✓ {filepath} - {desc} (已包含舆情API端点)")
                else:
                    print(f"  ⚠ {filepath} - 缺少舆情API端点")

            elif filepath == "static/index.html":
                if "loadMarketSentiment" in content and "舆情指数" in content:
                    print(f"  ✓ {filepath} - {desc} (已包含舆情模块)")
                else:
                    print(f"  ⚠ {filepath} - 缺少舆情模块")
        else:
            print(f"  ✗ {filepath} - 文件不存在")


if __name__ == "__main__":
    print("\n开始测试舆情指数模块\n")

    # 测试1: 情绪分析服务
    test_sentiment_service()

    # 测试2: 市场新闻获取
    test_eastmoney_market_news()

    # 测试3: 文件检查
    test_file_changes()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    print("\n功能说明:")
    print("1. 市场舆情指数 - 分析100条市场新闻，计算整体舆情")
    print("2. 个股舆情分析 - 分析特定股票的相关新闻舆情")
    print("3. 舆情对比 - 对比多只股票的舆情指数")
    print("\n使用方法:")
    print("1. 启动服务: uvicorn app.main:app --reload")
    print("2. 访问舆情指数选项卡进行测试")
