#!/usr/bin/env python3
"""Read /LOGS/mesh_seen.bin from the SD card: every node the Mesh app ever pushed out of its (memory limited) node table.

  python3 tools/read_seen.py /Volumes/MAYHEM/LOGS/mesh_seen.bin [--csv]

Record layout (64 bytes, little endian, appended in eviction order, at most 256 records):
  u32 node_id | u32 last_seen_unix (0 = clock not set) | i8 rssi | i8 snr in quarter dB | u8 hw_model | u8 role |
  u8 hops | u8 flags (bit 0: public key known) | char short_name[5] | char long_name[41] | 4 bytes reserved
"""
import struct, sys, time

def read(path):
    b = open(path, "rb").read()
    for i in range(len(b) // 64):
        r = b[i * 64:(i + 1) * 64]
        nid, ts, rssi, snr, hw, role, hops, flags = struct.unpack("<IIbbBBBB", r[:14])
        short = r[14:19].split(b"\0")[0].decode("utf-8", "replace")
        long_ = r[19:60].split(b"\0")[0].decode("utf-8", "replace")
        yield dict(id=nid, last_seen=ts, rssi=rssi, snr=snr / 4, hw=hw, role=role, hops=hops, pubkey=bool(flags & 1),
                   short=short, long=long_)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    csv = "--csv" in sys.argv
    if csv:
        print("id,name,short,last_seen,snr,rssi,hops,pubkey")
    for r in read(sys.argv[1]):
        when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["last_seen"])) if r["last_seen"] else "?"
        if csv:
            print(f'{r["id"]:08X},"{r["long"]}",{r["short"]},{when},{r["snr"]},{r["rssi"]},{r["hops"]},{int(r["pubkey"])}')
        else:
            print(f'{r["id"]:08X}  {when:16}  snr {r["snr"]:+5.1f}  {r["long"] or r["short"]}')
