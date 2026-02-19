"""
图像理解模块

提供景点图片识别、图像描述等功能。
支持与 LLM 结合进行图像理解。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class ImageType(Enum):
    """图像类型"""
    ATTRACTION = "attraction"       # 景点图片
    FOOD = "food"                   # 美食图片
    HOTEL = "hotel"                 # 酒店图片
    MAP = "map"                     # 地图截图
    SCENERY = "scenery"             # 风景图片
    UNKNOWN = "unknown"             # 未知


@dataclass
class ImageAnalysisResult:
    """图像分析结果"""
    image_type: ImageType
    description: str
    tags: List[str] = field(default_factory=list)
    location: Optional[str] = None
    confidence: float = 0.0
    suggestions: List[str] = field(default_factory=list)


class VisionProcessor:
    """图像处理器

    特性：
    - 图像类型识别
    - 景点识别
    - 图像描述生成
    - LLM 增强理解
    """

    # 常见景点特征
    ATTRACTION_KEYWORDS = {
        "故宫": ["红墙", "琉璃瓦", "金銮殿"],
        "长城": ["城墙", "砖石", "山峰"],
        "天坛": ["祈年殿", "圆顶", "蓝色"],
        "西湖": ["湖面", "断桥", "雷峰塔"],
        "黄山": ["奇石", "云海", "迎客松"],
    }

    def __init__(self, llm_client: Any = None):
        """
        初始化图像处理器

        Args:
            llm_client: 可选的 LLM 客户端，用于增强理解
        """
        self._llm_client = llm_client
        logger.info("VisionProcessor initialized")

    def set_llm_client(self, llm_client):
        """设置 LLM 客户端"""
        self._llm_client = llm_client

    async def analyze_image(
        self,
        image_data: str,
        image_type_hint: ImageType = None
    ) -> ImageAnalysisResult:
        """分析图像

        Args:
            image_data: 图像数据 (base64 或 URL)
            image_type_hint: 图像类型提示

        Returns:
            图像分析结果
        """
        # 如果有 LLM，使用 LLM 进行分析
        if self._llm_client:
            return await self._analyze_with_llm(image_data, image_type_hint)

        # 回退到规则分析
        return self._analyze_with_rules(image_data, image_type_hint)

    async def _analyze_with_llm(
        self,
        image_data: str,
        image_type_hint: ImageType
    ) -> ImageAnalysisResult:
        """使用 LLM 分析图像

        Args:
            image_data: 图像数据
            image_type_hint: 图像类型提示

        Returns:
            图像分析结果
        """
        try:
            hint = image_type_hint.value if image_type_hint else "未知"

            system_prompt = """你是一个专业的旅游图像分析专家。根据图像内容，识别景点类型和特征。

分析要点：
1. 判断图像类型（景点/美食/酒店/地图/风景）
2. 识别具体景点或地点
3. 提取关键特征标签
4. 提供旅游建议"""

            user_prompt = f"""图像类型提示: {hint}
图像数据: {image_data[:100]}...

请以 JSON 格式返回分析结果：
{{
    "image_type": "景点/美食/酒店/地图/风景/未知",
    "description": "图像描述",
    "tags": ["标签1", "标签2"],
    "location": "可能的位置（如果有）",
    "confidence": 0.0-1.0,
    "suggestions": ["建议1", "建议2"]
}}

只返回 JSON。"""

            result = self._llm_client.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], temperature=0.3)

            if result.get("success"):
                content = result.get("content", "")
                try:
                    data = json.loads(content)
                    return ImageAnalysisResult(
                        image_type=ImageType(data.get("image_type", "unknown")),
                        description=data.get("description", ""),
                        tags=data.get("tags", []),
                        location=data.get("location"),
                        confidence=data.get("confidence", 0.5),
                        suggestions=data.get("suggestions", [])
                    )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM vision response")

        except Exception as e:
            logger.warning(f"LLM vision analysis failed: {e}")

        return self._analyze_with_rules(image_data, image_type_hint)

    def _analyze_with_rules(
        self,
        image_data: str,
        image_type_hint: ImageType
    ) -> ImageAnalysisResult:
        """使用规则分析图像

        Args:
            image_data: 图像数据
            image_type_hint: 图像类型提示

        Returns:
            图像分析结果
        """
        # 基础分析
        image_type = image_type_hint or ImageType.UNKNOWN
        description = "这是一张旅游相关的图像"
        tags = []
        confidence = 0.5

        # 基于提示调整
        if image_type_hint == ImageType.ATTRACTION:
            description = "这可能是一个景点"
            tags = ["景点", "旅游"]
            confidence = 0.6
        elif image_type_hint == ImageType.FOOD:
            description = "这可能是一张美食图片"
            tags = ["美食", "餐厅"]
            confidence = 0.6
        elif image_type_hint == ImageType.SCENERY:
            description = "这是一张风景图片"
            tags = ["风景", "自然"]
            confidence = 0.6

        return ImageAnalysisResult(
            image_type=image_type,
            description=description,
            tags=tags,
            confidence=confidence,
            suggestions=["了解更多景点信息"]
        )

    def recognize_attraction(self, image_data: str) -> Optional[str]:
        """识别景点

        Args:
            image_data: 图像数据

        Returns:
            景点名称或 None
        """
        # 简化实现：基于关键词匹配
        for attraction, keywords in self.ATTRACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in image_data:
                    return attraction

        return None

    def get_travel_info(self, result: ImageAnalysisResult) -> Dict[str, Any]:
        """根据图像分析结果获取旅游信息

        Args:
            result: 图像分析结果

        Returns:
            旅游相关信息
        """
        info = {
            "type": result.image_type.value,
            "description": result.description,
            "tags": result.tags,
            "suggestions": result.suggestions
        }

        if result.location:
            info["location"] = result.location

        return info


# 全局单例
vision_processor = VisionProcessor()


class ImageComparison:
    """图像比较器

    特性：
    - 相似度计算
    - 差异检测
    - 批量比较
    """

    def __init__(self):
        logger.info("ImageComparison initialized")

    def compare(
        self,
        image1: str,
        image2: str
    ) -> Dict[str, Any]:
        """比较两张图像

        Args:
            image1: 图像1
            image2: 图像2

        Returns:
            比较结果
        """
        # 简化实现
        similarity = 0.5 if image1 != image2 else 1.0

        return {
            "similarity": similarity,
            "is_similar": similarity > 0.8,
            "differences": []
        }

    def find_duplicates(
        self,
        images: List[str],
        threshold: float = 0.8
    ) -> List[List[int]]:
        """查找重复图像

        Args:
            images: 图像列表
            threshold: 阈值

        Returns:
            重复组
        """
        duplicates = []
        for i in range(len(images)):
            for j in range(i + 1, len(images)):
                result = self.compare(images[i], images[j])
                if result["similarity"] > threshold:
                    duplicates.append([i, j])
        return duplicates


class ImageSearchEngine:
    """图像搜索引擎

    特性：
    - 基于内容的搜索
    - 相似图像检索
    - 索引管理
    """

    def __init__(self):
        self._index: Dict[str, Any] = {}
        logger.info("ImageSearchEngine initialized")

    def index_image(
        self,
        image_id: str,
        features: Dict[str, Any]
    ):
        """索引图像

        Args:
            image_id: 图像ID
            features: 特征
        """
        self._index[image_id] = features
        logger.info(f"Indexed image: {image_id}")

    def search_similar(
        self,
        query_features: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索相似图像

        Args:
            query_features: 查询特征
            top_k: 返回数量

        Returns:
            相似图像列表
        """
        results = []
        for image_id, features in self._index.items():
            score = self._compute_similarity(query_features, features)
            results.append({
                "image_id": image_id,
                "score": score
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _compute_similarity(
        self,
        features1: Dict[str, Any],
        features2: Dict[str, Any]
    ) -> float:
        """计算相似度"""
        # 简化实现
        return 0.5


class SceneRecognizer:
    """场景识别器

    特性：
    - 场景分类
    - 场景理解
    - 上下文推断
    """

    SCENES = {
        "beach": ["沙滩", "海洋", "阳光"],
        "mountain": ["山", "森林", "云"],
        "city": ["建筑", "街道", "人群"],
        "desert": ["沙漠", "仙人掌", "骆驼"]
    }

    def __init__(self, llm_client: Any = None):
        self._llm_client = llm_client
        logger.info("SceneRecognizer initialized")

    def recognize_scene(
        self,
        image_data: str
    ) -> Dict[str, Any]:
        """识别场景

        Args:
            image_data: 图像数据

        Returns:
            场景信息
        """
        # 简化实现
        scene_type = "unknown"
        confidence = 0.5

        for scene, keywords in self.SCENES.items():
            for keyword in keywords:
                if keyword in image_data:
                    scene_type = scene
                    confidence = 0.7
                    break

        return {
            "scene_type": scene_type,
            "confidence": confidence,
            "description": f"这是一个{scene_type}场景"
        }
