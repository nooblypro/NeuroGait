#!/usr/bin/env python3
"""Dataset download and management utility for the Figshare Parkinson's turning-task dataset.

DOI: 10.6084/m9.figshare.14984667
"""

import argparse
import os
from pathlib import Path
import struct
import urllib.request
import zipfile
import zlib

PDFEINFO_URL = "https://ndownloader.figshare.com/files/31544582"
IMU_ZIP_URL = "https://ndownloader.figshare.com/files/33413717"
VIDEOS_ZIP_URL = "https://ndownloader.figshare.com/files/31324702"


def download_file(url: str, dest_path: Path) -> None:
    if dest_path.exists() and dest_path.stat().st_size > 0:
        print(f"{dest_path} already exists, skipping download.")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} to {dest_path}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    print(f"Saved {dest_path} ({dest_path.stat().st_size / 1024:.1f} KB)")


def extract_single_video(target_name: str, out_path: Path) -> None:
    if out_path.exists() and out_path.stat().st_size > 1000000:
        print(f"{out_path} already exists, skipping extraction.")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    req0 = urllib.request.Request(VIDEOS_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req0) as resp0:
        final_url = resp0.geturl()

    # Read Central Directory (Zip64)
    cd_offset = 5011293199
    cd_size = 4853
    cd_req = urllib.request.Request(
        final_url,
        headers={"User-Agent": "Mozilla/5.0", "Range": f"bytes={cd_offset}-{cd_offset+cd_size-1}"}
    )
    with urllib.request.urlopen(cd_req) as resp:
        cd_data = resp.read()

    pos = 0
    target_info = None
    while pos < len(cd_data):
        if cd_data[pos:pos+4] != b"\x50\x4b\x01\x02":
            break
        comp_sz = int.from_bytes(cd_data[pos+20:pos+24], "little")
        uncomp_sz = int.from_bytes(cd_data[pos+24:pos+28], "little")
        fn_len = int.from_bytes(cd_data[pos+28:pos+30], "little")
        ex_len = int.from_bytes(cd_data[pos+30:pos+32], "little")
        cm_len = int.from_bytes(cd_data[pos+32:pos+34], "little")
        loc_off = int.from_bytes(cd_data[pos+42:pos+46], "little")
        fn = cd_data[pos+46:pos+46+fn_len].decode("utf-8", errors="ignore")

        extra = cd_data[pos+46+fn_len:pos+46+fn_len+ex_len]
        epos = 0
        while epos < len(extra):
            tag = int.from_bytes(extra[epos:epos+2], "little")
            sz = int.from_bytes(extra[epos+2:epos+4], "little")
            if tag == 0x0001:
                idx = epos + 4
                if uncomp_sz == 0xFFFFFFFF:
                    uncomp_sz = struct.unpack("<Q", extra[idx:idx+8])[0]
                    idx += 8
                if comp_sz == 0xFFFFFFFF:
                    comp_sz = struct.unpack("<Q", extra[idx:idx+8])[0]
                    idx += 8
                if loc_off == 0xFFFFFFFF:
                    loc_off = struct.unpack("<Q", extra[idx:idx+8])[0]
                    idx += 8
            epos += 4 + sz
        if fn == target_name:
            target_info = (comp_sz, uncomp_sz, loc_off)
            break
        pos += 46 + fn_len + ex_len + cm_len

    if not target_info:
        raise ValueError(f"Video {target_name} not found in remote archive")

    comp_sz, uncomp_sz, loc_off = target_info
    lh_req = urllib.request.Request(
        final_url,
        headers={"User-Agent": "Mozilla/5.0", "Range": f"bytes={loc_off}-{loc_off+100}"}
    )
    with urllib.request.urlopen(lh_req) as resp:
        lhdr = resp.read()
    l_fn_len = int.from_bytes(lhdr[26:28], "little")
    l_ex_len = int.from_bytes(lhdr[28:30], "little")
    d_start = loc_off + 30 + l_fn_len + l_ex_len
    d_end = d_start + comp_sz - 1

    print(f"Streaming {target_name} ({comp_sz/(1024*1024):.1f} MB compressed)...")
    f_req = urllib.request.Request(
        final_url,
        headers={"User-Agent": "Mozilla/5.0", "Range": f"bytes={d_start}-{d_end}"}
    )
    with urllib.request.urlopen(f_req) as resp:
        cdata = resp.read()

    decomp = zlib.decompressobj(-zlib.MAX_WBITS)
    raw = decomp.decompress(cdata)
    with open(out_path, "wb") as f:
        f.write(raw)
    print(f"Successfully saved {out_path} ({len(raw)/(1024*1024):.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Download NeuroGait Figshare dataset files.")
    parser.add_argument("--dest", type=str, default="data/raw", help="Target raw data directory")
    parser.add_argument("--videos", nargs="*", default=["PDFE01_1", "PDFE03_1", "PDFE09_1"], help="Video identifiers to download")
    args = parser.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Download PDFEinfo.csv
    download_file(PDFEINFO_URL, dest / "PDFEinfo.csv")

    # 2. Download IMU.zip if not already extracted
    imu_dir = dest / "imu"
    if not imu_dir.exists() or len(list(imu_dir.glob("*.txt"))) == 0:
        imu_zip = dest / "IMU.zip"
        download_file(IMU_ZIP_URL, imu_zip)
        print("Extracting IMU files...")
        with zipfile.ZipFile(imu_zip) as zf:
            for member in zf.namelist():
                if member.startswith("IMU/"):
                    filename = Path(member).name
                    if filename:
                        imu_dir.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(imu_dir / filename, "wb") as dst:
                            dst.write(src.read())
        print("Extracted IMU files successfully.")

    # 3. Extract requested videos
    videos_dir = dest / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    for v_id in args.videos:
        fn = f"Videos/{v_id}.mp4" if not v_id.startswith("Videos/") else v_id
        out_f = videos_dir / f"{Path(fn).stem}.mp4"
        extract_single_video(fn, out_f)


if __name__ == "__main__":
    main()
