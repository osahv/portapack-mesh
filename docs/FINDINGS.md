# Notes from getting Mesh to read a real private network

Collected while testing PR #3306 on a HackRF One R10 + PortaPack H2, EU 433 MHz, LongFast, against two stock nodes
(Heltec V3 and Wireless Paper) on a private mesh.

## "Received, but chat and node list stay empty"

Symptom in the Chat console: `* hash 62!=08 src 1D64 n1`. The packet arrived intact (the radio side is fine) but belongs to a
channel the app is not on. The channel hash is `xor(name bytes) ^ xor(key bytes)`:

- the app's primary slot uses the well-known default key (hash `0x08` for "LongFast");
- the nodes' primary channel was named "LongFast" **with its own 32-byte key** -> hash `0x62`.

Nothing in such a packet can be decoded without the key, including NodeInfo, so the node list stays empty as well.

## Why 256-bit keys needed a patch

The router and the crypto code handle 16 and 32 byte keys, but `derive_channel_key()` only produced 16 bytes, so a custom
channel could only be a 32-hex-digit AES-128 key. `patches/0001-*` makes it return 32 bytes for 64 hex digits and passes the
length on to the channel hash, router and channel-share code.

## Entering the channels

Channels live in `/SETTINGS/meshtastic.ini` on the SD card (`c1_name`, `c1_key`, `c1_en` ... up to `c10_*`). Typing 64 hex
digits on the PortaPack keyboard is painful; use `tools/mesh_channels_to_ini.py`, which reads the channels (names and keys)
directly from your node. The keys end up in plain text on the card: keep it private.

A node's TCP API serves one client at a time (Home Assistant's integration, for example, holds it): use `--port` with
a USB cable, or stop the other client first.

## Limits worth knowing

- **10 nodes** in the node list (`MAX_NODES`): memory on the M0 is the constraint. The oldest entry is evicted when the
  list is full. Names and public keys of nodes you have heard are kept on the card (`/LOGS/mesh_dms.txt`), and with
  `log=1` in the ini every received frame is written to `/LOGS/mesh_rx.csv`, so nothing is lost.
- First launch after boot can report "out of memory": reset and open Mesh first.
- 11 other apps' baseband images moved from flash to `/BASEBAND` on the card (APRS, AIS, weather, ...): copy the folder.
  Weather and the SubGHz decoder may not load because of memory.
- SF12 (LongSlow) is transmit-only.
- The status row has an `RX` lock (`radiomode=2` in the ini): nothing is ever sent. Use it when you only want to listen.
