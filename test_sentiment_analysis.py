"""测试情绪分析功能"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.sentiment_service import sentiment_service


def test_single_sentiment():
    """测试单条文本情绪分析"""
    print("=" * 80)
    print("测试单条文本情绪分析")
    print("=" * 80)

    test_texts = [
        "公司业绩大幅增长，市场前景广阔",
        "股价暴跌，投资者损失惨重",
        "公司发布年度财报",
        "新产品上市，市场反应热烈",
        "面临监管调查，风险加大",
        "稳步推进业务发展战略",
        "创新技术获得重大突破",
        "营收下滑，利润大幅缩水",
    ]

    for text in test_texts:
        result = sentiment_service.analyze_sentiment(text)
        score_display = f"{result['score']:.4f} ({result['score']*100:.1f}分)"
        print(f"\n文本: {text}")
        print(f"  情绪: {result['label']}")
        print(f"  得分: {score_display}")
        print(f"  置信度: {result['confidence']:.4f}")


def test_news_list_sentiment():
    """测试新闻列表情绪分析"""
    print("\n" + "=" * 80)
    print("测试新闻列表情绪分析")
    print("=" * 80)

    # 模拟新闻列表
    news_list = [
        {"title": "公司Q4业绩超预期，营收增长30%", "date": "2026-01-15", "url": "http://example.com/1"},
        {"title": "新产品发布会成功举办，市场反响热烈", "date": "2026-01-14", "url": "http://example.com/2"},
        {"title": "股价回调，分析师建议观望", "date": "2026-01-13", "url": "http://example.com/3"},
        {"title": "公司发布年度报告", "date": "2026-01-12", "url": "http://example.com/4"},
        {"title": "面临行业竞争压力，市场份额下降", "date": "2026-01-11", "url": "http://example.com/5"},
        {"title": "技术创新获得国家专利", "date": "2026-01-10", "url": "http://example.com/6"},
        {"title": "高管团队稳定，战略清晰", "date": "2026-01-09", "url": "http://example.com/7"},
        {"title": "股东大会顺利召开", "date": "2026-01-08", "url": "http://example.com/8"},
    ]

    result = sentiment_service.analyze_news_list(news_list)

    print(f"\n整体情绪分析:")
    print(f"  整体评分: {result['overall_score']:.4f} ({result['overall_score']*100:.1f}分)")
    print(f"  整体标签: {result['overall_label']}")
    print(f"  总新闻数: {result['total_count']}")
    print(f"  积极: {result['positive_count']} ({result['positive_ratio']*100:.1f}%)")
    print(f"  中性: {result['neutral_count']} ({result['neutral_ratio']*100:.1f}%)")
    print(f"  消极: {result['negative_count']} ({result['negative_ratio']*100:.1f}%)")

    print(f"\n各条新闻情绪:")
    for item in result['news_sentiments']:
        s = item['sentiment']
        print(f"  [{s['label']}] {item['title'][:40]}...")
        print(f"      得分: {s['score']:.4f}, 置信度: {s['confidence']:.4f}")


def test_empty_input():
    """测试空输入"""
    print("\n" + "=" * 80)
    print("测试边界情况")
    print("=" * 80)

    # 空字符串
    result1 = sentiment_service.analyze_sentiment("")
    print(f"\n空字符串:")
    print(f"  情绪: {result1['label']}")
    print(f"  得分: {result1['score']}")

    # 空列表
    result2 = sentiment_service.analyze_news_list([])
    print(f"\n空新闻列表:")
    print(f"  整体情绪: {result2['overall_label']}")
    print(f"  总数: {result2['total_count']}")


if __name__ == "__main__":
    print("开始测试情绪分析功能\n")

    # 测试1: 单条文本
    test_single_sentiment()

    # 测试2: 新闻列表
    test_news_list_sentiment()

    # 测试3: 边界情况
    test_empty_input()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    print("\n注意: 需要先安装 snownlp 库: pip install snownlp")
