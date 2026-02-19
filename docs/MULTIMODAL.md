# 多模态支持设计文档 (v3.1.0)

## 概述

v3.1.0 引入了多模态支持，包括视觉理解、地图可视化和语音处理能力。

## 模块架构

```
Multimodal
├── vision/
│   ├── VisionProcessor      # 图像理解
│   ├── ImageComparison      # 图像比较
│   ├── ImageSearchEngine   # 图像搜索
│   └── SceneRecognizer     # 场景识别
├── visualization/
│   ├── MapVisualizer       # 地图可视化
│   ├── RouteOptimizer      # 路线优化
│   ├── MapRenderer         # 地图渲染
│   └── HeatmapGenerator    # 热力图生成
└── speech/
    ├── SpeechRecognizer    # 语音识别
    ├── SpeechSynthesizer   # 语音合成
    ├── VoiceInteractionHandler  # 语音交互
    ├── VoiceActivityDetector    # 语音活动检测
    └── AudioFeatureExtractor   # 音频特征提取
```

## 核心特性

### 1. 视觉理解 (Vision)

| 类 | 功能 | LLM 支持 |
|-----|------|---------|
| VisionProcessor | 图像类型识别、景点识别 | ✓ |
| ImageComparison | 图像相似度比较 | - |
| ImageSearchEngine | 基于内容的图像搜索 | - |
| SceneRecognizer | 场景分类与理解 | ✓ |

### 2. 地图可视化 (Visualization)

| 类 | 功能 | LLM 支持 |
|-----|------|---------|
| MapVisualizer | 路线绘制、标记点管理 | - |
| RouteOptimizer | 贪心/遗传算法/LLM优化 | ✓ |
| MapRenderer | HTML/PNG 渲染 | ✓ |
| HeatmapGenerator | 热力图生成与分析 | ✓ |

### 3. 语音处理 (Speech)

| 类 | 功能 | LLM 支持 |
|-----|------|---------|
| SpeechRecognizer | 语音转文字 | ✓ |
| SpeechSynthesizer | 文字转语音 | - |
| VoiceInteractionHandler | 语音交互管理 | ✓ |
| VoiceActivityDetector | VAD 检测 | - |
| AudioFeatureExtractor | MFCC/频谱特征 | - |

## 使用示例

### 图像分析

```python
from vision import VisionProcessor, ImageType

processor = VisionProcessor(llm_client=llm_client)
result = await processor.analyze_image(image_data, ImageType.ATTRACTION)
```

### 路线规划

```python
from visualization import MapVisualizer, RouteOptimizer

visualizer = MapVisualizer()
route = visualizer.create_route("route_1", "北京游", "北京")
visualizer.add_marker(route, "故宫", 39.916, 116.397)

# LLM 增强优化
optimizer = RouteOptimizer(llm_client=llm_client)
optimized = optimizer.optimize(route, method="llm")
```

### 语音交互

```python
from speech import SpeechRecognizer, SpeechSynthesizer

recognizer = SpeechRecognizer(llm_client=llm_client)
text = await recognizer.recognize(audio_data, "zh-CN")

synthesizer = SpeechSynthesizer()
audio = synthesizer.synthesize("您好！")
```

## 版本信息

- **版本**: v3.1.0
- **发布日期**: 2024
- **依赖**: LLM Client (可选，用于增强功能)
