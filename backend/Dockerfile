# ── Stage 1: build SPLAT! ─────────────────────────────────────────────────────
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
RUN chmod +x build configure install utils/build utils/install && \
    sed -i.bak 's/-march=\$cpu/-march=native/g' build && \
    printf "8\n4\n" | ./configure

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libbz2-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SPLAT! binaries
COPY --from=splat-builder /usr/local/bin/splat /app/splat
COPY --from=splat-builder /usr/local/bin/splat-hd /app/splat-hd
COPY --from=splat-builder /usr/local/bin/srtm2sdf /app/srtm2sdf
RUN ln -s /app/srtm2sdf /app/srtm2sdf-hd

COPY backend/app/ app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
