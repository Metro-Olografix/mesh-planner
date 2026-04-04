# Metro Olografix — Mesh Planner

Collaborative Meshtastic node deployment planner for the Metro Olografix association (Abruzzo, Italy).

## Features

| Feature | Description |
|---|---|
| **Node management** | Add, edit, delete nodes with full RF parameters |
| **Hardware presets** | Library of 28 Meshtastic devices (LilyGo, Heltec, RAKwireless, Seeed, Elecrow…) with pre-filled TX power, frequency, and sensitivity |
| **Deployment status** | Mark nodes as **Planned** (orange) or **Deployed** (green) |
| **Coverage analysis** | Per-node SPLAT! RF propagation maps rendered as GeoTIFF overlays on the map |
| **Path planner** | Find the best A→B relay route using deployed nodes; maximises worst-hop SNR (bottleneck Dijkstra) |
| **Real-time sync** | Server-Sent Events broadcast node changes instantly to all connected members |
| **Zitadel auth** | OAuth2 PKCE login via your Zitadel instance; read is public, writes require authentication |
| **Activity feed** | Live log of who added or changed what |

## Architecture

```
┌─────────────────────────────────────────┐
│  Browser  (Vue 3 · Pinia · Leaflet)     │
│   ├── NodePanel  (CRUD + coverage)      │
│   ├── PathPlanner  (A→B routing)        │
│   └── ActivityFeed  (SSE stream)        │
└────────────────┬────────────────────────┘
                 │ REST + SSE
┌────────────────▼────────────────────────┐
│  FastAPI backend                        │
│   ├── /api/nodes      CRUD              │
│   ├── /api/hardware   presets           │
│   ├── /api/coverage   SPLAT! engine     │
│   ├── /api/path/find  pathfinder        │
│   └── /api/events     SSE broadcast     │
└────────┬───────────────┬────────────────┘
         │               │
   PostgreSQL        SPLAT! binary
   (node data,       (ITM propagation
    GeoTIFF cache)    model + SRTM tiles)
```

## Prerequisites

- Docker & Docker Compose v2
- A Zitadel instance with an application configured for PKCE

SPLAT! is compiled automatically from source ([jmcmellen/splat](https://github.com/jmcmellen/splat)) during the Docker build — no manual binary installation needed.

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd mx-site-planner
cp .env.example .env
# Edit .env with your secrets
```

### 2. Build the frontend

```bash
cd frontend
cp ../.env.example .env           # copy Vite env vars
pnpm install
pnpm build
cp -r dist/* ../backend/app/ui/
```

Or use Docker:
```bash
docker compose --profile build run frontend-builder
```

### 4. Start services

```bash
docker compose up -d
```

The app is now available at `http://localhost:8000`.

## Zitadel Configuration

In your Zitadel console, create a **User Agent (PKCE)** application with:

- **Redirect URI**: `https://your-domain.com/callback`
- **Post-Logout URI**: `https://your-domain.com`
- **Scopes**: `openid profile email`

Then, in the application's **Token settings**, set:

- **Access Token Type → JWT** (required — the default "Bearer" opaque token cannot be validated locally)

Set the resulting **Client ID** and your **Zitadel domain** in `.env`.

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Requires a running PostgreSQL. Set DATABASE_URL in .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev          # proxies /api to http://localhost:8000
```

## RF Model

Coverage uses **SPLAT! with the standard ITM (Irregular Terrain / Longley-Rice) model** (`-olditm` flag), fed by 3-arcsecond (~90 m) SRTM elevation tiles automatically downloaded from AWS Open Data and cached locally.

ITWOM is explicitly disabled — it produced unrealistic results for typical Meshtastic link distances.

When SPLAT! coverage data is not available for a hop, the path planner falls back to the **Friis free-space path loss** equation.

All nodes default to **Meshtastic EU_868 MEDIUM_FAST** parameters:

| Parameter | Value |
|---|---|
| Frequency | 869.525 MHz |
| Spread Factor | 9 |
| Bandwidth | 250 kHz |
| Receiver noise figure | 6.0 dB (SX1262 typical) |
| LoRa noise floor | ≈ −121 dBm |

The noise floor is computed as: `−174 dBm + 10·log₁₀(BW_Hz) + NF_dB`.

Available LoRa presets (per-node override):

| Preset | SF | BW (kHz) | Noise floor (dBm) |
|---|---|---|---|
| SHORT_FAST | 7 | 500 | −114 |
| SHORT_SLOW | 8 | 250 | −120 |
| MEDIUM_FAST *(default)* | 9 | 250 | −121 |
| MEDIUM_SLOW | 10 | 250 | −121 |
| LONG_FAST | 11 | 250 | −121 |
| LONG_SLOW | 12 | 125 | −124 |
| VERY_LONG_SLOW | 12 | 125 | −124 |

Radio climate is configurable (equatorial, continental/maritime subtropical, desert, **continental temperate** *(default)*, maritime temperate land/sea).

## Path Planning Algorithm

The path planner builds a graph over deployed nodes and finds the **maximum bottleneck SNR path** (the route whose weakest link is as strong as possible) using a modified Dijkstra algorithm:

1. **Edge condition** — hop is included only if Friis RX power > receiver RX sensitivity; SPLAT! coverage data vetoes the edge when available
2. **Edge weight** — SNR in dB = `friis_rx_dbm − noise_floor_dbm`
3. **Optimisation** — maximise `min(SNR)` across all hops (max-min bottleneck Dijkstra using a max-heap)
4. **Result** — ordered list of node hops + bottleneck SNR for the full path

Source and destination are modelled as virtual nodes with generic handheld-device parameters.

## Hardware Presets

All presets are seeded at `EU_868` (869.525 MHz). Default antenna gain is 2.0 dBi unless noted. Custom antenna gain can be set per-node to override the hardware default.

**LilyGo**

| Model | TX (dBm) | RX Sens. (dBm) | Notes |
|---|---|---|---|
| T-Beam v1.1 | 20 | −137 | SX1276, classic workhorse |
| T-Beam S3 Supreme | 22 | −130 | SX1262, improved RF |
| T3 S3 v1.3 | 22 | −130 | SX1262, solar relay |
| T-Echo | 13.4 | −130 | nRF52840, e-ink, low power |
| T-Deck | 22 | −130 | SX1262, keyboard device |
| T-Deck Plus | 22 | −130 | SX1262, keyboard + GPS |
| T-Deck Pro | 22 | −130 | SX1262, e-ink touch |
| T-LoRa Pager | 22 | −130 | LR1121, tri-band |

**Heltec**

| Model | TX (dBm) | RX Sens. (dBm) | Notes |
|---|---|---|---|
| HT-CT62 | 21 | −130 | ESP32-C3 + SX1262 |
| WiFi LoRa 32 v3 | 21 | −120 | ESP32-S3, OLED |
| WiFi LoRa 32 v4 | 28 | −120 | ESP32-S3, solar-ready |
| Wireless Tracker v1.1 | 21 | −120 | SX1262, GPS |
| Wireless Tracker v2.1 | 28 | −120 | SX1262, boosted TX |
| Mesh Node T114 | 22 | −130 | nRF52840, solar |
| Wireless Paper v1.1 | 21 | −130 | ESP32-S3, e-ink |
| MeshPocket | 22 | −130 | nRF52840, integrated power bank |
| MeshTower | 22 | −130 | nRF52840, IP65, solar, 3 dBi |

**RAKwireless**

| Model | TX (dBm) | RX Sens. (dBm) | Notes |
|---|---|---|---|
| RAK4631 (WisBlock) | 20 | −137 | nRF52840, modular |
| WisMesh Pocket V2 | 20 | −137 | nRF52840, GPS |
| WisMesh Repeater | 20 | −137 | nRF52840, IP67, 3 dBi |
| WisMesh 1W Booster | 30 | −137 | 1 W output, ham licence required, 3 dBi |

**Seeed Studio**

| Model | TX (dBm) | RX Sens. (dBm) | Notes |
|---|---|---|---|
| SenseCAP T1000-E | 20 | −130 | nRF52840, LR1110 |
| Wio Tracker L1 Pro | 20 | −130 | nRF52840, SX1262 |
| SenseCAP Solar P1 Pro | 20 | −130 | Solar, 3 dBi |

**Elecrow ThinkNode**

| Model | TX (dBm) | RX Sens. (dBm) | Notes |
|---|---|---|---|
| ThinkNode M1 | 20 | −130 | nRF52840, e-paper |
| ThinkNode M2 | 20 | −130 | ESP32-S3, OLED |

**Fixed / High-Power**

| Model | TX (dBm) | RX Sens. (dBm) | Notes |
|---|---|---|---|
| Station G1 | 30 | −130 | 1 W, backbone node, 3 dBi |
| Nano G1 Explorer | 20 | −130 | B&Q Consulting, compact |

## License

Internal use — Metro Olografix association.
