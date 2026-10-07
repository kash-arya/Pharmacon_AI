#!/usr/bin/env python3
"""
Automated Lightweight Cohort Packager for Pharmacon.
Scans raw writer calibration folders, crops lines locally, and packages
them into a tiny ZIP file (under 2 MB for 3 writers, ~15 MB for 30 writers)
for instant upload to Google Colab.
"""

import os, sys, glob, cv2, zipfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from pharmacon_ai.crop import process_photo

SEARCH_BASE = os.path.expanduser("~/Documents/From S23 by GS-KDE Connect")
PDF_PATH    = os.path.join(REPO_ROOT, "Pharmacon_Writer_Calibration_Protocol.pdf")
ZIP_OUTPUT  = os.path.join(REPO_ROOT, "colab_packages", "pharmacon_cohort_crops.zip")

def map_writer_sheets(writer_dir):
    files = sorted(os.listdir(writer_dir))
    mapping = {}
    for f in files:
        if not f.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        fl = f.lower()
        full = os.path.join(writer_dir, f)
        if "ts1" in fl or "trains1" in fl or ("train" in fl and "1" in fl): mapping[2] = full
        elif "ts2" in fl or "trains2" in fl or ("train" in fl and "2" in fl): mapping[3] = full
        elif "ts3" in fl or "trains3" in fl or ("train" in fl and "3" in fl): mapping[4] = full
        elif "ts4" in fl or "trains4" in fl or ("train" in fl and "4" in fl): mapping[5] = full
        elif "vs" in fl or "valid" in fl: mapping[6] = full
        elif "hs1" in fl or "heldouts1" in fl or ("held" in fl and "1" in fl): mapping[7] = full
        elif "hs2" in fl or "heldouts2" in fl or ("held" in fl and "2" in fl): mapping[8] = full
    return mapping

def main():
    print("=" * 70)
    print("PHARMACON — AUTOMATED LIGHTWEIGHT COHORT PACKAGER")
    print("=" * 70)

    # 1. Prioritize local dataset/ if present, otherwise check phone KDE folder
    local_dataset = os.path.join(REPO_ROOT, "dataset")
    import re
    def _wid_num(path):
        m = re.search(r"[wW](\d+)", os.path.basename(path))
        return int(m.group(1)) if m else 999

    if os.path.isdir(local_dataset) and any(os.path.isdir(os.path.join(local_dataset, d)) for d in os.listdir(local_dataset)):
        candidate_dirs = sorted([
            os.path.join(local_dataset, d) for d in os.listdir(local_dataset)
            if os.path.isdir(os.path.join(local_dataset, d))
        ], key=_wid_num)
        print(f"Detected {len(candidate_dirs)} writer folders in workspace: {local_dataset}")
    else:
        candidate_dirs = sorted([
            d for d in glob.glob(os.path.join(SEARCH_BASE, "*CS*"))
            if os.path.isdir(d)
        ], key=_wid_num)
        print(f"Detected {len(candidate_dirs)} writer source folders in: {SEARCH_BASE}")
    
    os.makedirs(os.path.dirname(ZIP_OUTPUT), exist_ok=True)
    if os.path.exists(ZIP_OUTPUT):
        os.remove(ZIP_OUTPUT)

    total_lines = 0
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Package core code
        for root, dirs, files in os.walk(os.path.join(REPO_ROOT, "pharmacon_ai")):
            for file in files:
                if not file.endswith(".pyc") and "__pycache__" not in root:
                    full = os.path.join(root, file)
                    rel = os.path.relpath(full, REPO_ROOT)
                    zf.write(full, arcname=rel)

        # 2. Package protocol PDF
        zf.write(PDF_PATH, arcname=os.path.basename(PDF_PATH))

        # 3. Crop and pack each writer
        import re
        for idx, w_dir in enumerate(candidate_dirs, 1):
            folder_name = os.path.basename(w_dir)
            match = re.search(r"[wW](\d+)", folder_name)
            w_id = f"W{int(match.group(1)):02d}" if match else f"W{idx:02d}"
            mapping = map_writer_sheets(w_dir)
            print(f"[{w_id}] Processing '{folder_name}' ({len(mapping)} sheets)...")
            
            w_lines = 0
            for page_idx, p_path in sorted(mapping.items()):
                try:
                    lines = process_photo(p_path, PDF_PATH, page_idx, writer_id=w_id)
                    for lid, data in lines.items():
                        _, buf = cv2.imencode(".jpg", data["image"], [int(cv2.IMWRITE_JPEG_QUALITY), 88])
                        zf.writestr(f"crops/{w_id}/{lid}.jpg", buf.tobytes())
                        w_lines += 1
                except Exception as e:
                    print(f"    Error cropping page {page_idx} ({os.path.basename(p_path)}): {e}")
            total_lines += w_lines
            print(f"    Cropped {w_lines} lines cleanly.")

    size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print("\n" + "=" * 70)
    print(f"SUCCESS! Output package created:")
    print(f"  Path      : {ZIP_OUTPUT}")
    print(f"  Writers   : {len(candidate_dirs)}")
    print(f"  Lines     : {total_lines}")
    print(f"  File Size : {size_mb:.2f} MB  (Uploads to Colab in ~2-3 seconds!)")
    print("=" * 70)

if __name__ == "__main__":
    main()
