#!/bin/bash
set -e
echo "🚀 Starting Lantern + Lumen system..."

# =========================
# 1. Setup Ollama
# =========================
export OLLAMA_MODELS=/workspace/ollama_models
echo "🧠 Starting Ollama..."
ollama serve &
sleep 5

echo "📦 Pulling models..."
ollama pull gemma2:9b  || true
ollama pull llama3.1:8b || true
# =========================
# 2. Start Lantern (8000)
# =========================
echo "🔵 Starting Lantern..."
cd /workspace/lantern-lumen/Lantern_V2
uvicorn app:app --host 0.0.0.0 --port 8000 &
sleep 20
# =========================
# 3. Start Lumen (8002)
# =========================
echo "🟣 Starting Lumen eval system..."
cd /workspace/lantern-lumen/eval_system
uvicorn api.main:app --host 0.0.0.0 --port 8002 &

# =========================
# 4. Keep container alive
# =========================
echo "✅ All services started."
wait
