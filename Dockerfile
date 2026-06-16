FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QUESTCUT_MAX_UPLOAD_MB=25

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py ./
COPY scripts ./scripts
COPY src ./src
COPY models/MODEL_SOURCES.md ./models/MODEL_SOURCES.md
# Model binaries are ignored by Git. Mount or copy them to /app/models before inference:
#   models/rembg/birefnet-general.onnx
#   models/rembg/birefnet-portrait.onnx
#   models/modnet/modnet.onnx

EXPOSE 7860
CMD ["python", "scripts/run_web.py", "--host", "0.0.0.0", "--port", "7860"]
