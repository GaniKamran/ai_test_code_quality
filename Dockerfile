# syntax=docker/dockerfile:1
# =============================================================================
# Dockerfile  —  non-root, multi-stage, minimal attack surface
#
# Build:   docker build -t train_station .
# Run:     docker run --rm train_station
# =============================================================================

# ── Stage 1: install deps as root into /install ───────────────────── #
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: lean runtime image ───────────────────────────────────── #
FROM python:3.12-slim AS runner

# Create a dedicated non-root user + group (no home dir, no shell)
RUN groupadd --system appgroup \
 && useradd  --system \
             --gid appgroup \
             --no-create-home \
             --shell /usr/sbin/nologin \
             appuser

WORKDIR /app

# Pull in only the installed packages (no build tools)
COPY --from=builder /install /usr/local

# Copy source with correct ownership — never chown after COPY
COPY --chown=appuser:appgroup . .

# Ensure the DB file can be written by appuser at runtime
RUN mkdir -p /app/data \
 && chown appuser:appgroup /app/data

# Drop privileges
USER appuser

# Never run as root, read-only filesystem friendly
ENV PYTHONPATH=".:train_station_app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL="sqlite:////app/data/train_station.db"

# setup_db → uvicorn (bg) → pytest → exit
CMD ["bash", "bash.sh"]
