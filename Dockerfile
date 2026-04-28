# ─────────────────────────────────────────────────────────────
# Django web image.
#
# Heavy because the /classify/ endpoint runs BirdNET (TensorFlow) in
# the same process. ~2 GB final image is expected. If we ever split
# the classifier into a worker we can shrink this down to ~200 MB.
# ─────────────────────────────────────────────────────────────

# ── Stage 1: builder ─────────────────────────────────────────
# Compiles wheels for any C-extension packages (psycopg, Pillow, etc.)
# in a fat image, then we copy only the installed packages forward.
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for Pillow / psycopg / scientific stack.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libsndfile1 \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENV=production \
    PORT=8000

# Runtime-only system libs (libpq for psycopg, libsndfile/ffmpeg for librosa).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libsndfile1 \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user — the app and its files are owned by `app`, never root.
RUN useradd --create-home --uid 1000 app

# Copy installed Python packages from builder.
COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=app:app . /app

# Make entrypoint executable (Windows checkouts lose the +x bit).
RUN chmod +x /app/entrypoint.sh

# Drop privileges before running anything.
USER app

# Static files are collected at container start (entrypoint), not build,
# so SECRET_KEY env var is available. Skip if you prefer build-time:
#   RUN SECRET_KEY=dummy DJANGO_ENV=production python manage.py collectstatic --noinput

EXPOSE 8000

# Healthcheck hits the Django liveness probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/birds/api/healthz/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
