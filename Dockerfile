# ─── Stage 1: Build frontend ─────────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --prefer-offline

COPY frontend/ ./
RUN npm run build


# ─── Stage 2: Production runtime ─────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install Python dependencies (production only)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/
COPY data/ ./data/
COPY scripts/ ./scripts/

# Copy built frontend assets
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Ensure data directory is writable for the DB
RUN mkdir -p /app/data && chown -R app:app /app

USER app

# Azure App Service expects the port from the PORT env var (default 8000)
ENV PORT=8000
EXPOSE ${PORT}

# Startup: auto-ingest on first boot if DB is missing, then serve the app.
CMD ["sh", "-c", "\
  if [ ! -f /app/data/o2c.db ]; then \
    echo '[startup] o2c.db not found — running ingestion...' && \
    cd /app && python -m backend.ingest && \
    echo '[startup] Ingestion complete.'; \
  else \
    echo '[startup] o2c.db exists — skipping ingestion.'; \
  fi && \
  uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 \
"]
