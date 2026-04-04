# ── Stage 1: build frontend ───────────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app

RUN npm install -g pnpm

COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY frontend/ .

ARG VITE_ZITADEL_AUTHORITY
ARG VITE_ZITADEL_CLIENT_ID
ENV VITE_ZITADEL_AUTHORITY=$VITE_ZITADEL_AUTHORITY
ENV VITE_ZITADEL_CLIENT_ID=$VITE_ZITADEL_CLIENT_ID

RUN pnpm build

# ── Stage 2: build SPLAT! ─────────────────────────────────────────────────────
FROM python:3.12-slim AS splat-builder

RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    libbz2-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 https://github.com/jmcmellen/splat /build/splat
WORKDIR /build/splat
# configure prompts: (8) MAXPAGES 64 for standard, (4) MAXPAGES 16 for HD
# It calls ./build all then ./install all (as root), placing binaries in /usr/local/bin
RUN chmod +x build configure install utils/build utils/install && \
    sed -i.bak 's/-march=\$cpu/-march=native/g' build && \
    printf "8\n4\n" | ./configure

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libbz2-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SPLAT! binaries (installed to /usr/local/bin by configure → ./install all)
# srtm2sdf-hd is a symlink to srtm2sdf — recreate it here
COPY --from=splat-builder /usr/local/bin/splat /app/splat
COPY --from=splat-builder /usr/local/bin/splat-hd /app/splat-hd
COPY --from=splat-builder /usr/local/bin/srtm2sdf /app/srtm2sdf
RUN ln -s /app/srtm2sdf /app/srtm2sdf-hd

# Frontend static assets
COPY --from=frontend-builder /app/dist/ app/ui/

# Application code
COPY backend/app/ app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
