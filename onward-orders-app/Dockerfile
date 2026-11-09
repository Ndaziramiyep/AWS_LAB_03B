# ---- Stage 1: build wheels (has pip cache and build tools, thrown away afterwards)
FROM python:3.12-slim AS build
# Build directory
WORKDIR /build
# Dependency list first, so this layer is cached between code changes
COPY app/requirements.txt .
# Pre-build all dependencies as wheels
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- Stage 2: small runtime image
FROM python:3.12-slim
# Version (git SHA) passed in by GitHub Actions
ARG APP_VERSION=dev
# Expose version to the app; unbuffered logs go straight to CloudWatch
ENV APP_VERSION=$APP_VERSION PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# App directory
WORKDIR /srv
# Bring in the pre-built wheels only
COPY --from=build /wheels /wheels
# Install offline from wheels, then delete them
RUN pip install --no-cache-dir --no-index /wheels/* && rm -rf /wheels
# Application code
COPY app/ .
# Unprivileged user (never run as root)
RUN useradd --system --uid 10001 --no-create-home appuser
# Switch to it
USER appuser
# Container port used by the ALB target groups
EXPOSE 8080
# 2 workers x 4 threads fits 0.25 vCPU / 512 MiB; worker tmp in memory; logs to stdout
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "--threads", "4", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "main:app"]
