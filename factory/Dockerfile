# Two interpreters in one image: the physics engine (3.10) and the agent harness (3.11).
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg git && rm -rf /var/lib/apt/lists/*
COPY factory/requirements.txt /tmp/req.txt
COPY factory/requirements-engine.txt /tmp/req-engine.txt
RUN python -m venv /opt/factory && /opt/factory/bin/pip install --no-cache-dir -r /tmp/req.txt
# Engine venv: uv fetches a standalone CPython 3.10 so the image does not depend on distro packages.
RUN pip install --no-cache-dir uv && uv venv --python 3.10 /opt/engine && \
    VIRTUAL_ENV=/opt/engine uv pip install --no-cache -r /tmp/req-engine.txt
WORKDIR /app/factory
EXPOSE 8000
