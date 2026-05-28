# 国内免费 LLM 接入方案

## 候选模型（国内可用，有免费额度）

| 模型 | 提供方 | 免费额度 | API 风格 | 备注 |
|------|--------|----------|----------|------|
| DeepSeek-V3 | DeepSeek | 每日免费 | OpenAI 兼容 | 推荐首选，中文最强 |
| Qwen-Max | 阿里云百炼 | 有免费 token | OpenAI 兼容 | 备选 |
| GLM-4 | 智谱 AI | 有免费额度 | OpenAI 兼容 | 备选 |
| Doubao | 字节跳动 | 有免费额度 | OpenAI 兼容 | 备选 |

## 推荐方案：DeepSeek-V3
- 注册：https://platform.deepseek.com
- API Key 申请后即可使用
- 兼容 OpenAI SDK，只需换 base_url 和 key

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_deepseek_key",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": prompt}]
)
```

## 接入位置
后端 `analysis` 模块：`backend/analysis/llm_client.py`
规则引擎计算出结构化指标后调用

## 成本估算
- 每次分析 prompt 约 1000~1500 tokens
- DeepSeek 免费额度完全够 MVP 阶段使用
- 后续按量计费也极便宜（约 ¥0.001/次）
