# syntax=docker/dockerfile:1

# ---------- 构建阶段：只负责安装依赖并产出可移植的虚拟环境 ----------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt


# ---------- 运行阶段：最小体积 + 非 root 用户 ----------
FROM python:3.12-slim AS runtime

ARG APP_VERSION=0.0.0-dev
ARG VCS_REF=unknown

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_NAME=python-cicd-demo \
    APP_VERSION=${APP_VERSION} \
    APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

LABEL org.opencontainers.image.title="python-cicd-demo" \
      org.opencontainers.image.description="Python demo service for validating the GitHub Actions multi-arch CI/CD pipeline" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/nriet/python-cicd-demo"

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --home-dir /app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app.main:app"]
