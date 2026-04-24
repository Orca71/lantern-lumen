FROM runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04

WORKDIR /workspace

# Install system deps + Ollama
RUN apt-get update && apt-get install -y curl zstd && \
    curl -fsSL https://ollama.com/install.sh | sh

# Copy requirements
COPY requirements.txt .

# Install Python deps
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy your code
COPY . .

# Expose ports
EXPOSE 8000
EXPOSE 8002
EXPOSE 11434

CMD ["/bin/bash"]
