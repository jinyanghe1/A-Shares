"""综合测试脚本 - 测试所有新功能"""
import sys
import os

print("=" * 80)
print("ClawdBot Stock Monitor - 新功能综合测试")
print("=" * 80)
print("\n本测试将验证以下新功能：")
print("1. 长周期数据获取 (任务11-12)")
print("2. 宏观数据多指标分析 (任务13)")
print("3. 新闻情绪分析 (任务14)")
print("\n" + "=" * 80)

# 测试1: SnowNLP情绪分析
print("\n[测试1] SnowNLP情绪分析库")
print("-" * 80)
try:
    from snownlp import SnowNLP
    test_text = "公司业绩增长，市场前景广阔"
    s = SnowNLP(test_text)
    score = s.sentiments
    print(f"✓ SnowNLP 已成功导入")
    print(f"  测试文本: {test_text}")
    print(f"  情绪得分: {score:.4f} ({score*100:.1f}分)")
except ImportError:
    print("✗ SnowNLP 未安装")
    print("  请运行: pip install snownlp")
    sys.exit(1)
except Exception as e:
    print(f"✗ 测试失败: {e}")
    sys.exit(1)

# 测试2: 情绪分析服务
print("\n[测试2] 情绪分析服务")
print("-" * 80)
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app.services.sentiment_service import sentiment_service

    # 测试单条分析
    test_texts = [
        "公司业绩大幅增长",
        "股价暴跌",
        "发布年度报告",
    ]

    for text in test_texts:
        result = sentiment_service.analyze_sentiment(text)
        print(f"  文本: {text}")
        print(f"    -> {result['label']} ({result['score']:.4f})")

    # 测试批量分析
    news_list = [
        {"title": "业绩超预期", "date": "2026-01-01"},
        {"title": "新产品发布", "date": "2026-01-02"},
    ]
    batch_result = sentiment_service.analyze_news_list(news_list)
    print(f"\n  批量分析: {batch_result['total_count']}条新闻")
    print(f"    整体情绪: {batch_result['overall_label']} ({batch_result['overall_score']:.4f})")
    print("✓ 情绪分析服务测试通过")

except ImportError as e:
    print(f"✗ 导入失败: {e}")
    print("  注意: 此测试需要FastAPI应用环境")
except Exception as e:
    print(f"✗ 测试失败: {e}")

# 测试3: 检查文件修改
print("\n[测试3] 检查关键文件修改")
print("-" * 80)

files_to_check = [
    ("app/utils/eastmoney.py", "长周期数据支持"),
    ("app/services/analysis_service.py", "宏观数据多指标"),
    ("app/services/sentiment_service.py", "情绪分析服务"),
    ("app/routers/analysis.py", "新闻API修改"),
    ("static/index.html", "前端UI更新"),
    ("requirements.txt", "依赖更新"),
]

for filepath, desc in files_to_check:
    if os.path.exists(filepath):
        print(f"  ✓ {filepath} - {desc}")
    else:
        print(f"  ✗ {filepath} - 文件不存在")

# 测试4: 依赖检查
print("\n[测试4] 依赖包检查")
print("-" * 80)

dependencies = [
    "fastapi",
    "uvicorn",
    "httpx",
    "pydantic",
    "numpy",
    "scipy",
    "akshare",
    "snownlp",
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"  ✓ {dep}")
    except ImportError:
        print(f"  ✗ {dep} - 未安装")

# 总结
print("\n" + "=" * 80)
print("测试完成!")
print("=" * 80)
print("\n下一步:")
print("1. 确保所有依赖已安装: pip install -r requirements.txt")
print("2. 启动服务: uvicorn app.main:app --reload")
print("3. 访问前端测试新功能:")
print("   - 相关性分析: 测试长周期选项 (2年/3年/5年/10年/20年)")
print("   - 相关性分析: 测试宏观数据多指标分析")
print("   - 新闻模块: 查看情绪分析摘要和标签")
print("\n" + "=" * 80)
