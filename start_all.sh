#!/bin/bash

set -e

echo "🚀 Starting Lantern + Lumen system..."

# =========================
# 1. Setup Ollama
# =========================
export OLLAMA_MODELS=/workspace/ollama_models

echo "🧠 Starting Ollama..."
ollama serve &

# wait for ollama to boot
sleep 5

echo "📦 Pulling model (gemma)..."
ollama pull gemma:2b || true

# =========================
# 2. Activate env
# =========================
source /workspace/lantern_env/bin/activate

# =========================
# 3. Start Lantern (8000)
# =========================
echo "🔵 Starting Lantern..."
cd /workspace/Lantern_V2
uvicorn app:app --host 0.0.0.0 --port 8000 &

# =========================
# 4. Start Lumen (8002)
# =========================
echo "🟣 Starting Lumen eval system..."
cd /workspace/eval_system
uvicorn api.main:app --host 0.0.0.0 --port 8002 &

# =========================
# 5. Keep container alive
# =========================
echo "✅ All services started."

wait
