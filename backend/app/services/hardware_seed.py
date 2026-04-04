"""
Seed the hardware_profiles table with known Meshtastic-compatible devices.
Frequency is the Meshtastic EU_868 MEDIUM_FAST primary channel frequency.
TX power and RX sensitivity reflect hardware datasheets; sensitivity values
are for the default EU_868 MEDIUM_FAST preset (SF9, BW250 kHz) unless noted.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hardware_profile import HardwareProfile

EU_868_FREQ = 869.525  # MHz — Meshtastic EU_868 slot 0

HARDWARE_PROFILES = [
    # ── LilyGo ────────────────────────────────────────────────────────────────
    {
        "id": "t-beam-v1",
        "name": "T-Beam v1.1",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -137.0,   # SX1276, best-in-class sensitivity
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32 + SX1276, GPS, classic Meshtastic workhorse",
    },
    {
        "id": "t-beam-s3",
        "name": "T-Beam Supreme",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,   # SX1262
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, GPS, BME280, IMU, RTC, microSD",
    },
    {
        "id": "t3-s3",
        "name": "T3 S3 v1.3",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,   # SX1262
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, solar charging, low-cost relay node",
    },
    {
        "id": "t-echo",
        "name": "T-Echo",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 13.4,           # nRF52840 limited TX
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,   # SX1262
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, E-Ink display, GPS, NFC, multi-day battery",
    },
    {
        "id": "t-deck",
        "name": "T-Deck",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, QWERTY keyboard, 2.8\" touch LCD",
    },
    {
        "id": "t-deck-plus",
        "name": "T-Deck Plus",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, QWERTY keyboard, GPS, 2000 mAh — standalone Meshtastic phone",
    },
    {
        "id": "t-deck-pro",
        "name": "T-Deck Pro",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, E-Ink touch, GPS, optional 4G, audio jack",
    },
    {
        "id": "t-lora-pager",
        "name": "T-LoRa Pager",
        "manufacturer": "LilyGo",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,   # LR1121 tri-band, similar to SX1262
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + LR1121 tri-band, GPS, Qi wireless charging, pager form factor",
    },

    # ── Heltec ────────────────────────────────────────────────────────────────
    {
        "id": "ht-ct62",
        "name": "HT-CT62",
        "manufacturer": "Heltec",
        "tx_power_dbm": 21.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-C3 + SX1262, stamp-sized module, cheapest Meshtastic node",
    },
    {
        "id": "heltec-v3",
        "name": "Heltec LoRa 32 v3",
        "manufacturer": "Heltec",
        "tx_power_dbm": 21.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -120.0,   # slightly lower sensitivity than SX1262 spec due to layout
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, OLED, most popular beginner board",
    },
    {
        "id": "heltec-v4",
        "name": "Heltec LoRa 32 v4",
        "manufacturer": "Heltec",
        "tx_power_dbm": 28.0,           # doubled TX vs v3
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -120.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, 28 dBm TX, solar interface, USB native",
    },
    {
        "id": "heltec-tracker-v1",
        "name": "Heltec Wireless Tracker v1.1",
        "manufacturer": "Heltec",
        "tx_power_dbm": 21.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -120.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262 + GPS (UC6580 dual-freq), color TFT",
    },
    {
        "id": "heltec-tracker-v2",
        "name": "Heltec Wireless Tracker v2.1",
        "manufacturer": "Heltec",
        "tx_power_dbm": 28.0,           # boosted TX
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -120.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262 + GPS (UC6580 dual-freq), 28 dBm TX, solar",
    },
    {
        "id": "mesh-node-t114",
        "name": "Mesh Node T114",
        "manufacturer": "Heltec",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, 11 µA deep sleep, best choice for solar relay nodes",
    },
    {
        "id": "heltec-paper",
        "name": "Wireless Paper v1.1",
        "manufacturer": "Heltec",
        "tx_power_dbm": 21.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, 2.13\" E-Ink display (180-day image retention)",
    },
    {
        "id": "heltec-meshpocket",
        "name": "MeshPocket",
        "manufacturer": "Heltec",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, Qi2 power bank (5000-10000 mAh) + Meshtastic node",
    },
    {
        "id": "heltec-meshtower",
        "name": "MeshTower",
        "manufacturer": "Heltec",
        "tx_power_dbm": 22.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 3.0,
        "description": "nRF52840 + SX1262, IP65 solar repeater, 3× 2800 mAh, plug-and-play",
    },

    # ── RAKwireless ───────────────────────────────────────────────────────────
    {
        "id": "rak4631",
        "name": "RAK4631 (WisBlock)",
        "manufacturer": "RAKwireless",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -137.0,   # highest sensitivity in class
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, modular WisBlock system, best RX sensitivity",
    },
    {
        "id": "wismesh-pocket-v2",
        "name": "WisMesh Pocket V2",
        "manufacturer": "RAKwireless",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -137.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, GPS, 1.3\" OLED, 3200 mAh, SMA connector",
    },
    {
        "id": "wismesh-repeater",
        "name": "WisMesh Repeater",
        "manufacturer": "RAKwireless",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -137.0,
        "default_antenna_gain_dbi": 3.0,
        "description": "nRF52840 + SX1262, IP67, solar, 5200 mAh, professional backbone node",
    },
    {
        "id": "wismesh-1w",
        "name": "WisMesh 1W Booster",
        "manufacturer": "RAKwireless",
        "tx_power_dbm": 30.0,           # 1 W, ham license required outside USA
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -137.0,
        "default_antenna_gain_dbi": 3.0,
        "description": "nRF52840 + SX1262 + PA, 30 dBm TX — requires ham license outside USA",
    },

    # ── Seeed Studio ──────────────────────────────────────────────────────────
    {
        "id": "sensecap-t1000e",
        "name": "SenseCAP T1000-E",
        "manufacturer": "Seeed Studio",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,   # LR1110 (note: no SX1276 legacy rx)
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + LR1110, 6.5 mm credit-card form, IP65 — best-selling tracker",
    },
    {
        "id": "wio-tracker-l1-pro",
        "name": "Wio Tracker L1 Pro",
        "manufacturer": "Seeed Studio",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, GPS, 1.3\" OLED, 2000 mAh, joystick — best value handheld",
    },
    {
        "id": "sensecap-solar-p1-pro",
        "name": "SenseCAP Solar Node P1 Pro",
        "manufacturer": "Seeed Studio",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 3.0,
        "description": "nRF52840 + SX1262, GPS, 13400 mAh (4× 18650), 5W solar panel included",
    },

    # ── Elecrow ThinkNode ─────────────────────────────────────────────────────
    {
        "id": "thinknode-m1",
        "name": "ThinkNode M1",
        "manufacturer": "Elecrow",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "nRF52840 + SX1262, GPS, 1.54\" E-Paper, 1200 mAh, rotary encoder",
    },
    {
        "id": "thinknode-m2",
        "name": "ThinkNode M2",
        "manufacturer": "Elecrow",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "ESP32-S3 + SX1262, 1.3\" OLED, 1000 mAh — budget handheld",
    },

    # ── High-power fixed stations ─────────────────────────────────────────────
    {
        "id": "station-g1",
        "name": "Station G1",
        "manufacturer": "Meshtastic",
        "tx_power_dbm": 30.0,           # 1 W
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 3.0,
        "description": "1 W high-power fixed station, ideal for backbone nodes",
    },

    # ── Generic / custom ──────────────────────────────────────────────────────
    {
        "id": "nano-g1",
        "name": "Nano G1 Explorer",
        "manufacturer": "B&Q Consulting",
        "tx_power_dbm": 20.0,
        "frequency_mhz": EU_868_FREQ,
        "rx_sensitivity_dbm": -130.0,
        "default_antenna_gain_dbi": 2.0,
        "description": "Compact nRF52840 + SX1262 device",
    },
]


async def seed_hardware(db: AsyncSession) -> None:
    for data in HARDWARE_PROFILES:
        existing = await db.get(HardwareProfile, data["id"])
        if not existing:
            db.add(HardwareProfile(**data))
    await db.commit()
