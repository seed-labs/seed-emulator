#!/bin/bash
echo "🧠 初始化AI模型..."

# 拉取Ollama模型
docker exec seed_ollama_llm ollama pull qwen2:7b
docker exec seed_ollama_llm ollama pull chatglm3:6b

# 下载预训练模型
echo "📥 下载预训练模型..."
echo "模型将存储在 ./ai_models/ 目录"

echo "✅ AI模型初始化完成！"
