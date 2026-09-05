# Builds the UpajMitra FastAPI backend as a container so it can be deployed
# on Render, Railway, Fly.io, or anywhere else that runs a Dockerfile.
#
# Build context is the backend/ folder (see render.yaml at the repo root).
FROM python:3.11-slim

WORKDIR /app

# libgomp1 -> CatBoost needs OpenMP at runtime.
# The rest -> opencv-python-headless still wants a couple of shared libs
# on a bare slim image even in "headless" mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render (and most PaaS hosts) inject a $PORT env var and expect the app to
# bind to it -- falls back to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
