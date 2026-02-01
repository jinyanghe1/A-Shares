"""新闻情绪分析服务 - 舆情指数模块"""
from typing import List, Dict, Any
from datetime import datetime
from snownlp import SnowNLP


class SentimentService:
    """情绪分析服务 - 舆情指数模块"""

    # 舆情指数等级定义
    SENTIMENT_LEVELS = [
        {"min": 0, "max": 20, "level": "极度悲观", "color": "#cf1322", "icon": "📉"},
        {"min": 20, "max": 40, "level": "偏悲观", "color": "#f5222d", "icon": "😟"},
        {"min": 40, "max": 50, "level": "谨慎", "color": "#fa8c16", "icon": "🤔"},
        {"min": 50, "max": 60, "level": "中性", "color": "#faad14", "icon": "😐"},
        {"min": 60, "max": 70, "level": "偏乐观", "color": "#52c41a", "icon": "🙂"},
        {"min": 70, "max": 85, "level": "乐观", "color": "#389e0d", "icon": "😊"},
        {"min": 85, "max": 100, "level": "极度乐观", "color": "#237804", "icon": "🚀"},
    ]

    @staticmethod
    def get_sentiment_level(score: float) -> Dict[str, Any]:
        """根据舆情指数获取等级信息"""
        index = score * 100  # 转换为0-100的指数
        for level in SentimentService.SENTIMENT_LEVELS:
            if level["min"] <= index < level["max"]:
                return {
                    "index": round(index, 1),
                    "level": level["level"],
                    "color": level["color"],
                    "icon": level["icon"]
                }
        # 默认返回最后一个等级
        last = SentimentService.SENTIMENT_LEVELS[-1]
        return {
            "index": round(index, 1),
            "level": last["level"],
            "color": last["color"],
            "icon": last["icon"]
        }

    @staticmethod
    def analyze_sentiment(text: str) -> Dict[str, Any]:
        """
        分析单条文本的情绪
        返回：情绪分数 (0-1)，越接近1越积极
        """
        if not text or not text.strip():
            return {
                "score": 0.5,
                "label": "中性",
                "confidence": 0.0
            }

        try:
            s = SnowNLP(text)
            score = s.sentiments  # 0-1之间的值

            # 分类
            if score >= 0.6:
                label = "积极"
            elif score >= 0.4:
                label = "中性"
            else:
                label = "消极"

            return {
                "score": round(score, 4),
                "label": label,
                "confidence": abs(score - 0.5) * 2  # 转换为置信度 0-1
            }
        except Exception as e:
            print(f"情绪分析失败: {e}")
            return {
                "score": 0.5,
                "label": "中性",
                "confidence": 0.0
            }

    @staticmethod
    def analyze_news_list(news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析新闻列表的整体情绪
        news_list: 新闻列表，每条新闻包含title字段
        返回：情绪统计和每条新闻的情绪分析
        """
        if not news_list:
            return {
                "overall_score": 0.5,
                "overall_label": "中性",
                "positive_count": 0,
                "neutral_count": 0,
                "negative_count": 0,
                "total_count": 0,
                "news_sentiments": []
            }

        positive_count = 0
        neutral_count = 0
        negative_count = 0
        total_score = 0.0
        news_sentiments = []

        for news in news_list:
            title = news.get("title", "")
            sentiment = SentimentService.analyze_sentiment(title)

            # 统计
            if sentiment["label"] == "积极":
                positive_count += 1
            elif sentiment["label"] == "消极":
                negative_count += 1
            else:
                neutral_count += 1

            total_score += sentiment["score"]

            # 添加到结果
            news_sentiments.append({
                "title": title,
                "sentiment": sentiment,
                "date": news.get("date", ""),
                "url": news.get("url", "")
            })

        total_count = len(news_list)
        avg_score = total_score / total_count if total_count > 0 else 0.5

        # 整体情绪标签
        if avg_score >= 0.6:
            overall_label = "积极"
        elif avg_score >= 0.4:
            overall_label = "中性"
        else:
            overall_label = "消极"

        return {
            "overall_score": round(avg_score, 4),
            "overall_label": overall_label,
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "total_count": total_count,
            "positive_ratio": round(positive_count / total_count, 4) if total_count > 0 else 0,
            "negative_ratio": round(negative_count / total_count, 4) if total_count > 0 else 0,
            "neutral_ratio": round(neutral_count / total_count, 4) if total_count > 0 else 0,
            "news_sentiments": news_sentiments
        }

    def calculate_sentiment_index(self, news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算舆情指数
        基于100条新闻计算综合舆情指数，返回详细的舆情分析报告
        """
        if not news_list:
            return {
                "success": False,
                "message": "无新闻数据",
                "index": 50.0,
                "level_info": self.get_sentiment_level(0.5)
            }

        # 分析所有新闻
        analysis_result = self.analyze_news_list(news_list)

        # 计算加权舆情指数
        # 权重：最近的新闻权重更高
        weighted_score = 0.0
        total_weight = 0.0

        for i, news_sentiment in enumerate(analysis_result["news_sentiments"]):
            # 时间衰减权重：最新的新闻权重为1，越旧权重越小
            weight = 1.0 / (1 + i * 0.02)  # 衰减因子
            weighted_score += news_sentiment["sentiment"]["score"] * weight
            total_weight += weight

        weighted_avg = weighted_score / total_weight if total_weight > 0 else 0.5

        # 获取舆情等级信息
        level_info = self.get_sentiment_level(weighted_avg)

        # 情绪分布分析
        distribution = {
            "positive": {
                "count": analysis_result["positive_count"],
                "ratio": analysis_result["positive_ratio"],
                "label": "积极"
            },
            "neutral": {
                "count": analysis_result["neutral_count"],
                "ratio": analysis_result["neutral_ratio"],
                "label": "中性"
            },
            "negative": {
                "count": analysis_result["negative_count"],
                "ratio": analysis_result["negative_ratio"],
                "label": "消极"
            }
        }

        # 关键词提取（简单实现：统计高频词）
        keywords = self._extract_keywords(news_list)

        # 情绪趋势分析（将新闻按时间分组，计算趋势）
        trend = self._analyze_trend(analysis_result["news_sentiments"])

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "index": level_info["index"],
            "weighted_score": round(weighted_avg, 4),
            "simple_score": analysis_result["overall_score"],
            "level_info": level_info,
            "distribution": distribution,
            "total_news": analysis_result["total_count"],
            "keywords": keywords,
            "trend": trend,
            "top_positive": self._get_top_news(analysis_result["news_sentiments"], "积极", 5),
            "top_negative": self._get_top_news(analysis_result["news_sentiments"], "消极", 5),
            "news_sentiments": analysis_result["news_sentiments"][:20]  # 只返回前20条详情
        }

    def _extract_keywords(self, news_list: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """提取关键词"""
        from collections import Counter

        # 简单的关键词提取：统计词频
        word_freq = Counter()

        # 停用词列表（简化版）
        stopwords = {"的", "了", "是", "在", "有", "和", "与", "为", "对", "等",
                     "将", "被", "到", "也", "从", "但", "更", "或", "该", "这",
                     "个", "上", "下", "中", "大", "小", "新", "多", "已", "可"}

        for news in news_list:
            title = news.get("title", "")
            try:
                s = SnowNLP(title)
                words = s.words
                for word in words:
                    if len(word) >= 2 and word not in stopwords:
                        word_freq[word] += 1
            except Exception:
                continue

        # 返回前N个高频词
        return [{"word": word, "count": count} for word, count in word_freq.most_common(top_n)]

    def _analyze_trend(self, news_sentiments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析情绪趋势"""
        if len(news_sentiments) < 10:
            return {"direction": "neutral", "change": 0.0, "description": "数据不足"}

        # 将新闻分为前半部分和后半部分
        mid = len(news_sentiments) // 2
        recent_half = news_sentiments[:mid]
        earlier_half = news_sentiments[mid:]

        recent_avg = sum(n["sentiment"]["score"] for n in recent_half) / len(recent_half)
        earlier_avg = sum(n["sentiment"]["score"] for n in earlier_half) / len(earlier_half)

        change = recent_avg - earlier_avg

        if change > 0.05:
            direction = "improving"
            description = "舆情正在好转"
        elif change < -0.05:
            direction = "declining"
            description = "舆情正在恶化"
        else:
            direction = "stable"
            description = "舆情保持稳定"

        return {
            "direction": direction,
            "change": round(change * 100, 2),  # 转换为百分比变化
            "recent_score": round(recent_avg, 4),
            "earlier_score": round(earlier_avg, 4),
            "description": description
        }

    def _get_top_news(
        self,
        news_sentiments: List[Dict[str, Any]],
        label: str,
        n: int
    ) -> List[Dict[str, Any]]:
        """获取指定情绪类型的头条新闻"""
        filtered = [n for n in news_sentiments if n["sentiment"]["label"] == label]
        # 按情绪得分排序
        if label == "积极":
            sorted_news = sorted(filtered, key=lambda x: x["sentiment"]["score"], reverse=True)
        else:
            sorted_news = sorted(filtered, key=lambda x: x["sentiment"]["score"])

        return sorted_news[:n]


# 全局实例
sentiment_service = SentimentService()
