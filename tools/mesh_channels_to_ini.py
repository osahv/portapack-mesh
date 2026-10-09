#!/usr/bin/env python3
"""Copy the channels (name + key) of a Meshtastic node into the PortaPack Mesh app's settings file.

The keys are read straight from the node over TCP or serial; no key is printed or kept anywhere except in the .ini you
point it at (plain text on the SD card - keep the card private).

  pip install meshtastic
  python3 tools/mesh_channels_to_ini.py --host 192.168.1.50 --ini /Volumes/MAYHEM/SETTINGS/meshtastic.ini
  python3 tools/mesh_channels_to_ini.py --port /dev/cu.usbserial-0001 --ini ... --dry-run     # show what would be written

The app has 10 custom channel slots (c1..c10). Existing lines of the .ini are kept; only c<N>_name / c<N>_key / c<N>_en
are replaced. 64 hex digits (AES-256) need the firmware from this repository (patched); stock PR #3306 handles 32 only.
"""
import argparse, os, sys

DEFAULT_KEY = bytes([0xd4, 0xf1, 0xbb, 0x3a, 0x20, 0x29, 0x07, 0x59, 0xf0, 0xbc, 0xff, 0xab, 0xcf, 0x4e, 0x69, 0x01])
PRESET_NAMES = {0: "LongFast", 1: "LongSlow", 2: "VeryLongSlow", 3: "MediumSlow", 4: "MediumFast", 5: "ShortSlow",
                6: "ShortFast", 7: "LongModerate", 8: "ShortTurbo"}


def expand_psk(psk: bytes) -> bytes:
    """One byte = shorthand for the well-known key (1) or a variant of it (2..10); otherwise the raw key."""
    if len(psk) == 1:
        key = bytearray(DEFAULT_KEY)
        key[-1] = (key[-1] + psk[0] - 1) & 0xFF
        return bytes(key)
    return psk


def channels_from_node(node):
    """List of (name, key bytes) for the node's enabled channels, at most 10."""
    preset = PRESET_NAMES.get(node.localConfig.lora.modem_preset, "LongFast")
    chans = []
    for c in node.channels:
        if c.role == 0:  # DISABLED
            continue
        name = c.settings.name or (preset if c.index == 0 else "")
        psk = bytes(c.settings.psk)
        if not name or not psk:
            print(f"skip channel {c.index}: no name or no key")
            continue
        chans.append((name, expand_psk(psk)))
    return chans[:10]


def merge_ini(path, chans):
    """Replace c<N>_name/_key/_en in the settings file, keep every other line. Returns the new text."""
    new = {}
    for n, (name, key) in enumerate(chans, 1):
        new[f"c{n}_name"], new[f"c{n}_key"], new[f"c{n}_en"] = name, key.hex(), "1"
    old = open(path).read().split("\n") if os.path.exists(path) else []
    out, seen = [], set()
    for line in old:
        k = line.split("=", 1)[0]
        if k in new:
            out.append(f"{k}={new[k]}")
            seen.add(k)
        else:
            out.append(line)
    while out and out[-1] == "":
        out.pop()
    out += [f"{k}={v}" for k, v in new.items() if k not in seen]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--host", help="node address for TCP (Wi-Fi)")
    g.add_argument("--port", help="serial port of the node")
    ap.add_argument("--ini", help="path of the Mesh app settings file (SETTINGS/meshtastic.ini on the SD card)")
    ap.add_argument("--dry-run", action="store_true", help="only list channels (names and key lengths)")
    a = ap.parse_args()
    if not a.dry_run and not a.ini:
        ap.error("--ini is required unless --dry-run")

    if a.host:
        from meshtastic.tcp_interface import TCPInterface
        iface = TCPInterface(a.host)
    else:
        from meshtastic.serial_interface import SerialInterface
        iface = SerialInterface(a.port)
    chans = channels_from_node(iface.localNode)
    for n, (name, key) in enumerate(chans, 1):
        print(f"c{n}: {name!r}, {len(key)}-byte key" + ("  (needs the AES-256 build)" if len(key) == 32 else ""))
    if a.dry_run:
        os._exit(0)
    text = merge_ini(a.ini, chans)
    with open(a.ini, "w") as f:
        f.write(text)
    print(f"written to {a.ini}")
    os._exit(0)  # the meshtastic library can hang on close


if __name__ == "__main__":
    main()
