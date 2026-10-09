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

## Smaller node table entries

`NodeEntry` was 216 bytes (compiler padding around doubles and floats, ten separate `bool`s). Now 152 bytes: sensor values are
`Fixed<int16_t, N>` (a float kept as a scaled integer, converts both ways, so call sites did not change), latitude and longitude
are `Coord` (the 1e-7 degree integer they travel as on the wire), flags are bit fields, members are ordered widest first.
Fourteen entries take 2128 bytes, less than the ten (2160) did. The cost is code: this change grew the firmware by about 1 kB
because the M0 has no FPU and every conversion is a library call.

## The "All" list (`/LOGS/mesh_seen.bin`)

When the table is full and a new node arrives, the oldest entry is not simply dropped: a 64 byte record is parked in the NodeDB and
written to the card by the timer (once a second), so no file access happens in the packet path. Memory nodes are written on exit.
The file is fixed 64 byte records (layout in `tools/read_seen.py`), at most 256; a node already in the file is updated in place, a full
file overwrites the record heard longest ago. The **All** screen (`MeshtasticSeenView`) shows memory first, newest first, then the card,
newest first, skipping ids that are in memory. The card is opened with `chHeapAlloc` (not `new`, which panics when the heap is short),
one 64 byte record on the stack, so it is safe in a repaint.

## Flash budget

Free flash after the build: 4.7 kB (AES-256 patch only), 3.6 kB (+ node table), 0.6 kB (+ All list), 0.45 kB (+ navigation fix).
A bigger change needs something else to go: the PR already moves eleven other apps' baseband images to the SD card.

## Nodes tab: the button row

The node list is focusable and has the same rectangle as the button row below it, so the focus manager (which only looks for a
widget whose top is below the focused widget's bottom) never found the buttons with the D-pad. `Down` on the list now jumps to the buttons,
`Up` on a button returns to the list.
