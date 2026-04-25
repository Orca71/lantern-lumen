FROM runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04

WORKDIR /workspace

RUN apt-get update && apt-get install -y curl zstd openssh-server && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    mkdir /var/run/sshd && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication no" >> /etc/ssh/sshd_config

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /workspace/start_all.sh

EXPOSE 22 8000 8002 11434

CMD mkdir -p /root/.ssh && \
    echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys && \
    chmod 700 /root/.ssh && \
    chmod 600 /root/.ssh/authorized_keys && \
    service ssh start && \
    /workspace/start_all.sh
