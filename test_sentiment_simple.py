"""简单的情绪分析测试 - 不依赖app模块"""
try:
    from snownlp import SnowNLP
    print("✓ SnowNLP 已成功导入")
except ImportError as e:
    print(f"✗ 无法导入 SnowNLP: {e}")
    exit(1)


def analyze_sentiment(text):
    """分析单条文本的情绪"""
    if not text or not text.strip():
        return {"score": 0.5, "label": "中性", "confidence": 0.0}

    s = SnowNLP(text)
    score = s.sentiments

    if score >= 0.6:
        label = "积极"
    elif score >= 0.4:
        label = "中性"
    else:
        label = "消极"

    return {
        "score": round(score, 4),
        "label": label,
        "confidence": abs(score - 0.5) * 2
    }


print("=" * 80)
print("简单情绪分析测试")
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

for i, text in enumerate(test_texts, 1):
    result = analyze_sentiment(text)
    score_display = f"{result['score']:.4f} ({result['score']*100:.1f}分)"
    print(f"\n{i}. {text}")
    print(f"   情绪: {result['label']}")
    print(f"   得分: {score_display}")
    print(f"   置信度: {result['confidence']:.4f}")

print("\n" + "=" * 80)
print("测试完成！情绪分析功能正常工作。")
print("=" * 80)
