# SolarTree AI v0.8 — React/Vite frontend + FastAPI backend (one Render service)
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app ./backend/app
COPY backend/model_media ./backend/model_media
COPY --from=frontend-build /build/frontend/dist ./frontend_dist
WORKDIR /app/backend
EXPOSE 10000
# The provider injects PORT. One worker is appropriate for a modest deployment.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
