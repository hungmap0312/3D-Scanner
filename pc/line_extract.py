#!/usr/bin/env python3
"""
line_extract.py - Trich tam vach laser tu cap anh JPEG OFF/ON bang phuong phap
trong tam cuong do phan so pixel tren tung hang trong vung quan tam (ROI).

Phuc vu buoc Q6 cua de tai May quet 3D (C3).
Co so: docs/SPEC.md muc 14.1, 16.1 va docs/design/SCAN_SESSION.md muc 2.

Thuat toan:
1. Doc hai anh JPEG OFF va ON, kiem tra cung kich thuoc va che do anh.
2. Chuyen kenh do sang kieu co dau (int16), tru ON - OFF, chan am ve 0.
3. Tren tung hang trong ROI [x0, x1) x [y0, y1) (nua mo, pixel goc 0):
   - Tim cac cum pixel lien tuc co hieu kenh do >= min_diff.
   - Neu khong co cum:
     + diff toan bo <= 0: reason = "no_signal"
     + co pixel > 0 nhung khong dat min_diff: reason = "weak"
   - Neu co cum:
     + Tinh be rong width = end - start + 1.
     + Kiem tra bao hoa (pixel ON dat >= sat_thresh hoac diff >= sat_thresh).
     + Kiem tra qua rong (width > max_width).
     + Neu co nhieu cum canh tranh ngang suc tren cung mot hang:
       danh dau reason = "ambiguous", khong lay trung binh hai nhanh.
     + Cum hop le duy nhat: tinh trong tam cuong do (intensity centroid):
       center_x_px = sum(x * I(x)) / sum(I(x)), reason = "ok", valid = "true".
4. Xuat tep CSV: row_y,center_x_px,valid,reason,width_px theo dung quy uoc Q4.
5. Xuat anh PNG chu thich rieng (ve ROI, tam hop le, danh dau loi) tren ban sao.
   Bao toan tuyet doi anh goc, khong ghi de neu tep dau ra da ton tai.

Cach dung tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/line_extract.py --selftest
  .venv/Scripts/python.exe pc/line_extract.py --off <anh_off.jpg> --on <anh_on.jpg> [tuy_chon]
"""

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class ClusterCandidate:
    start_col: int
    end_col: int
    width: int
    total_intensity: float
    peak_intensity: float
    max_on: int
    centroid: float
    saturated: bool
    wide: bool
    touch_edge: bool = False



def compute_file_sha256(path: Path) -> str:
    """Tinh ma hash SHA-256 cua tep de kiem tra tinh toan ven."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def parse_roi(roi_str: Optional[str], img_width: int, img_height: int) -> Tuple[int, int, int, int]:
    """
    Phan tich va kiem tra tinh hop le cua chuoi ROI x0,y0,x1,y1.
    ROI la khoang nua mo [x0, x1) x [y0, y1) theo toa do pixel goc 0.
    """
    if roi_str is None or not roi_str.strip():
        return 0, 0, img_width, img_height

    parts = [p.strip() for p in roi_str.split(",")]
    if len(parts) != 4:
        raise ValueError(
            f"ROI phai gom dung 4 so nguyen cach nhau boi dau phay (x0,y0,x1,y1), nhan duoc: '{roi_str}'"
        )

    try:
        x0, y0, x1, y1 = [int(p) for p in parts]
    except ValueError as e:
        raise ValueError(f"Toa do ROI phai la so nguyen: {e}")

    if x0 < 0 or y0 < 0:
        raise ValueError(f"Toa do bat dau ROI khong duoc am: x0={x0}, y0={y0}")
    if x0 >= x1:
        raise ValueError(f"Toa do x0 phai nho hon x1: x0={x0} >= x1={x1}")
    if y0 >= y1:
        raise ValueError(f"Toa do y0 phai nho hon y1: y0={y0} >= y1={y1}")
    if x1 > img_width:
        raise ValueError(f"Toa do x1 vuot qua be rong anh: x1={x1} > img_width={img_width}")
    if y1 > img_height:
        raise ValueError(f"Toa do y1 vuot qua be cao anh: y1={y1} > img_height={img_height}")

    return x0, y0, x1, y1


def compute_red_difference(
    off_img: Image.Image, on_img: Image.Image
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Kiem tra kich thuoc, che do va dinh dang anh; chuyen kenh do sang int16; tinh ON - OFF va chan am ve 0.
    Tra ve tuple (diff, R_on).
    """
    if off_img.size != on_img.size:
        raise ValueError(
            f"Kich thuoc anh OFF ({off_img.size[0]}x{off_img.size[1]}) "
            f"khac anh ON ({on_img.size[0]}x{on_img.size[1]})"
        )
    if off_img.mode != on_img.mode:
        raise ValueError(
            f"Che do anh OFF ({off_img.mode}) khac anh ON ({on_img.mode})"
        )
    if (
        getattr(off_img, "format", None)
        and getattr(on_img, "format", None)
        and off_img.format != on_img.format
    ):
        raise ValueError(
            f"Dinh dang anh OFF ({off_img.format}) khac anh ON ({on_img.format})"
        )

    rgb_off = np.asarray(off_img.convert("RGB"))
    rgb_on = np.asarray(on_img.convert("RGB"))

    r_off = rgb_off[:, :, 0].astype(np.int16)
    r_on = rgb_on[:, :, 0].astype(np.int16)

    # Chuyen kieu co dau int16 roi tru, chan am ve 0
    diff = np.clip(r_on - r_off, 0, None)
    return diff, r_on


def find_row_clusters(
    row_diff: np.ndarray,
    row_on: np.ndarray,
    x0: int,
    min_diff: float,
    max_width: int,
    sat_thresh: float,
) -> List[ClusterCandidate]:
    """
    Tim cac cum pixel lien tuc tren mot hang co hieu do >= min_diff.
    Xac dinh ro cum co cham bien ROI/anh hay khong de phong ngua sai so do cat vach.
    """
    active = row_diff >= min_diff
    candidates: List[ClusterCandidate] = []

    if not np.any(active):
        return candidates

    n = len(row_diff)
    in_run = False
    run_start = 0

    for i in range(n):
        if active[i]:
            if not in_run:
                in_run = True
                run_start = i
        else:
            if in_run:
                in_run = False
                run_end = i - 1
                width = run_end - run_start + 1
                intensities = row_diff[run_start:run_end + 1]
                x_coords = np.arange(x0 + run_start, x0 + run_end + 1)
                total_int = float(np.sum(intensities))
                peak_int = float(np.max(intensities))
                if total_int <= 0 or peak_int <= 0:
                    continue
                max_on_val = int(np.max(row_on[run_start:run_end + 1]))
                centroid = float(np.sum(x_coords * intensities) / total_int)
                saturated = (max_on_val >= sat_thresh) or (peak_int >= sat_thresh)
                wide = width > max_width
                touch_edge = (run_start == 0) or (run_end == n - 1)

                candidates.append(
                    ClusterCandidate(
                        start_col=run_start,
                        end_col=run_end,
                        width=width,
                        total_intensity=total_int,
                        peak_intensity=peak_int,
                        max_on=max_on_val,
                        centroid=centroid,
                        saturated=saturated,
                        wide=wide,
                        touch_edge=touch_edge,
                    )
                )

    if in_run:
        run_end = n - 1
        width = run_end - run_start + 1
        intensities = row_diff[run_start:run_end + 1]
        x_coords = np.arange(x0 + run_start, x0 + run_end + 1)
        total_int = float(np.sum(intensities))
        peak_int = float(np.max(intensities))
        if total_int > 0 and peak_int > 0:
            max_on_val = int(np.max(row_on[run_start:run_end + 1]))
            centroid = float(np.sum(x_coords * intensities) / total_int)
            saturated = (max_on_val >= sat_thresh) or (peak_int >= sat_thresh)
            wide = width > max_width
            touch_edge = (run_start == 0) or (run_end == n - 1)

            candidates.append(
                ClusterCandidate(
                    start_col=run_start,
                    end_col=run_end,
                    width=width,
                    total_intensity=total_int,
                    peak_intensity=peak_int,
                    max_on=max_on_val,
                    centroid=centroid,
                    saturated=saturated,
                    wide=wide,
                    touch_edge=touch_edge,
                )
            )

    return candidates



def analyze_single_row(
    row_diff: np.ndarray,
    row_on: np.ndarray,
    row_y: int,
    x0: int,
    min_diff: float,
    max_width: int,
    sat_thresh: float,
    prev_valid_center: Optional[float],
    prev_valid_y: Optional[int] = None,
) -> Tuple[Dict[str, str], Optional[float]]:
    """
    Phan tich mot hang trong ROI:
    Tra ve (row_dict, new_valid_center).
    row_dict gom 5 cot: row_y, center_x_px, valid, reason, width_px.
    """
    clusters = find_row_clusters(row_diff, row_on, x0, min_diff, max_width, sat_thresh)

    if len(clusters) == 0:
        max_val = np.max(row_diff) if len(row_diff) > 0 else 0
        if max_val <= 0:
            return {
                "row_y": str(row_y),
                "center_x_px": "",
                "valid": "false",
                "reason": "no_signal",
                "width_px": "",
            }, None
        else:
            return {
                "row_y": str(row_y),
                "center_x_px": "",
                "valid": "false",
                "reason": "weak",
                "width_px": "",
            }, None

    chosen_cluster: Optional[ClusterCandidate] = None

    if len(clusters) == 1:
        c = clusters[0]
        # Xet tinh lien tuc voi hang hop le truoc do (R02)
        if prev_valid_center is not None and prev_valid_y is not None:
            dy = row_y - prev_valid_y
            allowed_jump = 25.0 + 2.0 * max(0, dy - 1)
            if abs(c.centroid - prev_valid_center) > allowed_jump:
                # Dom co lap cach qua xa vach chinh: khong cho tu thiet lap nhanh hop le
                return {
                    "row_y": str(row_y),
                    "center_x_px": "",
                    "valid": "false",
                    "reason": "ambiguous",
                    "width_px": str(c.width),
                }, None
        chosen_cluster = c
    else:
        # Nhieu cum tren cung mot hang: xet do tuong dong cuong do va tinh lien tuc
        clusters.sort(key=lambda c: c.total_intensity, reverse=True)
        c0, c1 = clusters[0], clusters[1]

        # Neu cum thu hai co cuong do tuong duong (>= 40% cum lon nhat)
        is_comparable = (c1.total_intensity >= 0.4 * c0.total_intensity) or (
            c1.peak_intensity >= 0.5 * c0.peak_intensity
        )

        if is_comparable:
            # Thu xet tinh lien tuc voi hang truoc
            if prev_valid_center is not None:
                d0 = abs(c0.centroid - prev_valid_center)
                d1 = abs(c1.centroid - prev_valid_center)
                continuity_thresh = 5.0
                if d0 <= continuity_thresh and d1 > 2.0 * continuity_thresh:
                    chosen_cluster = c0
                elif d1 <= continuity_thresh and d0 > 2.0 * continuity_thresh:
                    chosen_cluster = c1
                else:
                    chosen_cluster = None
            else:
                chosen_cluster = None

            if chosen_cluster is None:
                # Khong the phan biet ro rang hai nhanh: gan ambiguous, khong lay trung binh
                return {
                    "row_y": str(row_y),
                    "center_x_px": "",
                    "valid": "false",
                    "reason": "ambiguous",
                    "width_px": str(c0.width),
                }, None
        else:
            # Cum phu nho hon han (nhieu co lap), kiem tra tinh lien tuc
            if prev_valid_center is not None and prev_valid_y is not None:
                dy = row_y - prev_valid_y
                allowed_jump = 25.0 + 2.0 * max(0, dy - 1)
                d0 = abs(c0.centroid - prev_valid_center)
                d1 = abs(c1.centroid - prev_valid_center)
                if d1 <= 5.0 and d0 > allowed_jump:
                    chosen_cluster = c1
                elif d0 > allowed_jump:
                    return {
                        "row_y": str(row_y),
                        "center_x_px": "",
                        "valid": "false",
                        "reason": "ambiguous",
                        "width_px": str(c0.width),
                    }, None
                else:
                    chosen_cluster = c0
            else:
                chosen_cluster = c0

    # Kiem tra cac tieu chi loai tru tren cum da chon
    if chosen_cluster.saturated:
        return {
            "row_y": str(row_y),
            "center_x_px": "",
            "valid": "false",
            "reason": "saturated",
            "width_px": str(chosen_cluster.width),
        }, None

    if chosen_cluster.wide:
        return {
            "row_y": str(row_y),
            "center_x_px": "",
            "valid": "false",
            "reason": "wide",
            "width_px": str(chosen_cluster.width),
        }, None

    if chosen_cluster.touch_edge:
        return {
            "row_y": str(row_y),
            "center_x_px": "",
            "valid": "false",
            "reason": "edge",
            "width_px": str(chosen_cluster.width),
        }, None

    # Cum hop le
    return {
        "row_y": str(row_y),
        "center_x_px": f"{chosen_cluster.centroid:.4f}",
        "valid": "true",
        "reason": "ok",
        "width_px": str(chosen_cluster.width),
    }, chosen_cluster.centroid


def extract_laser_centers(
    off_img: Image.Image,
    on_img: Image.Image,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    min_diff: float = 20.0,
    max_width: int = 30,
    sat_thresh: float = 250.0,
) -> List[Dict[str, str]]:
    """
    Trich tam vach tren toan bo ROI tung hang mot.
    Tra ve danh sach cac dict row, moi hang trong ROI dung 1 phan tu.
    """
    diff, r_on = compute_red_difference(off_img, on_img)

    results: List[Dict[str, str]] = []
    prev_center: Optional[float] = None
    prev_y: Optional[int] = None

    for row_y in range(y0, y1):
        if prev_y is not None and (row_y - prev_y) > 20:
            prev_center = None
            prev_y = None

        row_diff = diff[row_y, x0:x1]
        row_on = r_on[row_y, x0:x1]

        row_dict, new_center = analyze_single_row(
            row_diff=row_diff,
            row_on=row_on,
            row_y=row_y,
            x0=x0,
            min_diff=min_diff,
            max_width=max_width,
            sat_thresh=sat_thresh,
            prev_valid_center=prev_center,
            prev_valid_y=prev_y,
        )
        results.append(row_dict)
        if new_center is not None:
            prev_center = new_center
            prev_y = row_y

    return results



def write_centers_csv(csv_path: Path, rows: List[Dict[str, str]]) -> None:
    """Ghi danh sach ket qua vao tep CSV dung 5 cot (che do khong ghi de 'x')."""
    fieldnames = ["row_y", "center_x_px", "valid", "reason", "width_px"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with open(csv_path, "x", newline="", encoding="utf-8") as f:
            created = True
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    except Exception:
        if created and csv_path.is_file():
            try:
                csv_path.unlink()
            except OSError:
                pass
        raise


def create_annotated_image(
    on_img: Image.Image,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    rows: List[Dict[str, str]],
    output_png: Path,
) -> None:
    """
    Tao anh chu thich tren ban sao cua anh ON va luu ra tep PNG rieng (che do khong ghi de 'xb').
    Ve khung ROI va cac diem tam / danh dau loi.
    """
    annotated = on_img.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)

    # Ve khung ROI mau xanh duong nhat
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(0, 160, 255), width=2)

    for r in rows:
        row_y = int(r["row_y"])
        reason = r["reason"]
        valid = r["valid"].lower() == "true"

        if valid and r["center_x_px"]:
            cx = float(r["center_x_px"])
            # Ve diem tam mau xanh la
            draw.ellipse([cx - 1, row_y - 1, cx + 1, row_y + 1], fill=(0, 255, 0))
        elif reason == "saturated":
            # Danh dau bao hoa mau tim / magenta o mep trai ROI
            draw.point((x0 + 2, row_y), fill=(255, 0, 255))
        elif reason == "wide":
            # Danh dau qua rong mau cam
            draw.point((x0 + 4, row_y), fill=(255, 140, 0))
        elif reason == "ambiguous":
            # Danh dau hai nhanh mau do
            draw.point((x0 + 6, row_y), fill=(255, 0, 0))

    output_png.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with open(output_png, "xb") as f:
            created = True
            annotated.save(f, format="PNG")
    except Exception:
        if created and output_png.is_file():
            try:
                output_png.unlink()
            except OSError:
                pass
        raise


def check_or_match_params(
    params_path: Path,
    target_cfg: Dict[str, object],
) -> Tuple[bool, Optional[Dict[str, object]]]:
    """
    Kiem tra tinh hop le va so khop 6 truong cau hinh voi params.json trong thu muc dau ra.
    Tra ve (reused, existing_data). Neu params_path chua ton tai, tra ve (False, None).
    Nem ValueError voi tien to 'params_invalid:' neu tep hong, sai kieu, sai mien hoac chua khoa la.
    Nem ValueError voi tien to 'params_mismatch:' neu khac bat ky truong nao trong 6 truong cau hinh.
    """
    try:
        metadata_exists = params_path.exists()
    except OSError as e:
        raise ValueError(
            f"params_invalid: khong the kiem tra metadata {params_path}: {e}"
        ) from e

    if not metadata_exists:
        parent_dir = params_path.parent
        try:
            parent_exists = parent_dir.exists()
            parent_is_dir = parent_dir.is_dir() if parent_exists else False
        except OSError as e:
            raise ValueError(
                f"params_invalid: khong the kiem tra thu muc cha {parent_dir}: {e}"
            ) from e

        if parent_exists and parent_is_dir:
            has_existing_result = False
            try:
                for item in parent_dir.iterdir():
                    try:
                        is_f = item.is_file()
                    except OSError as e:
                        raise ValueError(
                            f"params_invalid: khong the kiem tra tep {item} trong thu muc {parent_dir}: {e}"
                        ) from e
                    if is_f and item.suffix.lower() in (".csv", ".png"):
                        has_existing_result = True
                        break
            except OSError as e:
                raise ValueError(
                    f"params_invalid: khong the liet ke thu muc {parent_dir}: {e}"
                ) from e
            if has_existing_result:
                raise ValueError(
                    f"params_invalid: thu muc da chua ket qua (CSV hoac PNG) nhung thieu metadata {params_path}. "
                    "Khong the xac dinh hoac tao cau hinh moi vao thu muc nay."
                )
        return False, None

    try:
        is_dir = params_path.is_dir()
    except OSError as e:
        raise ValueError(
            f"params_invalid: khong the kiem tra duong dan metadata {params_path}: {e}"
        ) from e

    if is_dir:
        raise ValueError(
            f"params_invalid: duong dan metadata la thu muc, khong phai tep: {params_path}"
        )

    try:
        content = params_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except UnicodeDecodeError as e:
        raise ValueError(
            f"params_invalid: khong the giai ma UTF-8 tep metadata {params_path}: {e}"
        )
    except json.JSONDecodeError as e:
        raise ValueError(
            f"params_invalid: tep metadata khong dung dinh dang JSON {params_path}: {e}"
        )
    except OSError as e:
        raise ValueError(
            f"params_invalid: khong the doc tep metadata {params_path}: {e}"
        )

    if not isinstance(data, dict):
        raise ValueError(
            f"params_invalid: metadata khong phai la JSON object tai {params_path}"
        )

    config_keys = ("roi", "min_diff", "max_width", "sat_thresh", "img_width", "img_height")
    legacy_stat_keys = ("total_rows", "ok_count", "valid_pct")
    allowed_keys = set(config_keys) | set(legacy_stat_keys)

    extra_keys = set(data.keys()) - allowed_keys
    if extra_keys:
        raise ValueError(
            f"params_invalid: metadata chua khoa khong duoc ho tro {sorted(extra_keys)} tai {params_path}"
        )

    missing_keys = [k for k in config_keys if k not in data]
    if missing_keys:
        raise ValueError(
            f"params_invalid: metadata thieu truong bat buoc {missing_keys} tai {params_path}"
        )

    # Kiem tra kieu va mien gia tri cua 6 truong cau hinh (loai tru bool vi bool la subclass cua int)
    img_w = data["img_width"]
    if type(img_w) is not int or img_w <= 0:
        raise ValueError(
            f"params_invalid: truong img_width phai la so nguyen duong tai {params_path}"
        )

    img_h = data["img_height"]
    if type(img_h) is not int or img_h <= 0:
        raise ValueError(
            f"params_invalid: truong img_height phai la so nguyen duong tai {params_path}"
        )

    max_w = data["max_width"]
    if type(max_w) is not int or max_w <= 0:
        raise ValueError(
            f"params_invalid: truong max_width phai la so nguyen duong tai {params_path}"
        )

    roi_val = data["roi"]
    if not (
        isinstance(roi_val, list)
        and len(roi_val) == 4
        and all(type(v) is int for v in roi_val)
    ):
        raise ValueError(
            f"params_invalid: truong roi phai la danh sach 4 so nguyen tai {params_path}"
        )
    rx0, ry0, rx1, ry1 = roi_val
    if (
        rx0 < 0
        or ry0 < 0
        or rx0 >= rx1
        or ry0 >= ry1
        or rx1 > img_w
        or ry1 > img_h
    ):
        raise ValueError(
            f"params_invalid: toa do roi khong hop le hoac vuot qua kich thuoc anh tai {params_path}: roi={roi_val}, size=({img_w}x{img_h})"
        )

    min_d = data["min_diff"]
    if (
        type(min_d) not in (int, float)
        or not math.isfinite(min_d)
        or min_d <= 0
        or min_d > 255
    ):
        raise ValueError(
            f"params_invalid: truong min_diff phai la so huu han trong khoang (0, 255] tai {params_path}"
        )

    sat_t = data["sat_thresh"]
    if (
        type(sat_t) not in (int, float)
        or not math.isfinite(sat_t)
        or sat_t <= 0
        or sat_t > 255
    ):
        raise ValueError(
            f"params_invalid: truong sat_thresh phai la so huu han trong khoang (0, 255] tai {params_path}"
        )

    if float(sat_t) <= float(min_d):
        raise ValueError(
            f"params_invalid: truong sat_thresh ({sat_t}) phai lon hon min_diff ({min_d}) tai {params_path}"
        )

    # So khop gia tri 6 truong voi target_cfg (khong dung sai)
    if roi_val != target_cfg["roi"]:
        raise ValueError(
            f"params_mismatch: tham so khong khop voi metadata da co tai {params_path} o truong 'roi': metadata={roi_val} != hien_tai={target_cfg['roi']}. Vui long dung thu muc chay moi."
        )
    if img_w != target_cfg["img_width"]:
        raise ValueError(
            f"params_mismatch: tham so khong khop voi metadata da co tai {params_path} o truong 'img_width': metadata={img_w} != hien_tai={target_cfg['img_width']}. Vui long dung thu muc chay moi."
        )
    if img_h != target_cfg["img_height"]:
        raise ValueError(
            f"params_mismatch: tham so khong khop voi metadata da co tai {params_path} o truong 'img_height': metadata={img_h} != hien_tai={target_cfg['img_height']}. Vui long dung thu muc chay moi."
        )
    if max_w != target_cfg["max_width"]:
        raise ValueError(
            f"params_mismatch: tham so khong khop voi metadata da co tai {params_path} o truong 'max_width': metadata={max_w} != hien_tai={target_cfg['max_width']}. Vui long dung thu muc chay moi."
        )
    if float(min_d) != float(target_cfg["min_diff"]):
        raise ValueError(
            f"params_mismatch: tham so khong khop voi metadata da co tai {params_path} o truong 'min_diff': metadata={min_d} != hien_tai={target_cfg['min_diff']}. Vui long dung thu muc chay moi."
        )
    if float(sat_t) != float(target_cfg["sat_thresh"]):
        raise ValueError(
            f"params_mismatch: tham so khong khop voi metadata da co tai {params_path} o truong 'sat_thresh': metadata={sat_t} != hien_tai={target_cfg['sat_thresh']}. Vui long dung thu muc chay moi."
        )

    return True, data


def write_params_json(
    params_path: Path,
    roi: Tuple[int, int, int, int],
    min_diff: float,
    max_width: int,
    sat_thresh: float,
    img_width: int,
    img_height: int,
    stats: Optional[Dict[str, object]] = None,
) -> None:
    """Ghi metadata chua 6 tham so cau hinh dung chung theo SCAN_SESSION (che do khong ghi de 'x')."""
    params_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "roi": list(roi),
        "min_diff": float(min_diff),
        "max_width": int(max_width),
        "sat_thresh": float(sat_thresh),
        "img_width": int(img_width),
        "img_height": int(img_height),
    }
    with open(params_path, "x", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def process_pair(
    off_path: Path,
    on_path: Path,
    roi_str: Optional[str] = None,
    min_diff: float = 20.0,
    max_width: int = 30,
    sat_thresh: float = 250.0,
    csv_path: Optional[Path] = None,
    annotate_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, str]], Dict[str, object]]:
    """
    Xu ly cap anh OFF va ON voi day du kiem tra hop le dau vao va dau ra.
    """
    if not off_path.is_file():
        raise FileNotFoundError(f"Tep anh OFF khong ton tai: {off_path}")
    if not on_path.is_file():
        raise FileNotFoundError(f"Tep anh ON khong ton tai: {on_path}")

    # Kiem tra xung dot duong dan dau ra (dung realpath de phan giai dung junction/symlink)
    resolved_off = os.path.normcase(os.path.realpath(str(off_path)))
    resolved_on = os.path.normcase(os.path.realpath(str(on_path)))

    resolved_csv = (
        os.path.normcase(os.path.realpath(str(csv_path)))
        if csv_path is not None
        else None
    )
    resolved_ann = (
        os.path.normcase(os.path.realpath(str(annotate_path)))
        if annotate_path is not None
        else None
    )

    if resolved_csv is not None:
        if resolved_csv in (resolved_off, resolved_on):
            raise ValueError(f"Duong dan CSV trung voi tep anh dau vao: {csv_path}")
        if csv_path.exists():
            raise FileExistsError(
                f"Tep CSV dau ra da ton tai (khong ghi de): {csv_path}"
            )

    if resolved_ann is not None:
        if resolved_ann in (resolved_off, resolved_on):
            raise ValueError(f"Duong dan anh chu thich trung voi tep anh dau vao: {annotate_path}")
        if annotate_path.exists():
            raise FileExistsError(
                f"Tep PNG chu thich da ton tai (khong ghi de): {annotate_path}"
            )

    if resolved_csv is not None and resolved_ann is not None:
        if resolved_csv == resolved_ann:
            raise ValueError(
                f"Duong dan CSV va anh chu thich khong duoc trung nhau: {csv_path}"
            )
        dir_csv = os.path.normcase(os.path.realpath(str(csv_path.parent)))
        dir_ann = os.path.normcase(os.path.realpath(str(annotate_path.parent)))
        if dir_csv != dir_ann:
            raise ValueError(
                f"Thu muc dau ra CSV ({csv_path.parent}) va anh chu thich ({annotate_path.parent}) phai trung nhau"
            )

    if type(min_diff) is bool or not math.isfinite(min_diff) or min_diff <= 0 or min_diff > 255:
        raise ValueError(f"Nguong min_diff phai la so thuc huu han > 0 va <= 255: {min_diff}")
    if type(max_width) is bool or not math.isfinite(max_width) or max_width <= 0:
        raise ValueError(f"Nguong max_width phai > 0: {max_width}")
    if type(sat_thresh) is bool or not math.isfinite(sat_thresh) or sat_thresh <= 0 or sat_thresh > 255:
        raise ValueError(f"Nguong sat_thresh phai trong khoang (0, 255]: {sat_thresh}")
    if sat_thresh <= min_diff:
        raise ValueError(
            f"Nguong sat_thresh ({sat_thresh}) phai lon hon min_diff ({min_diff})"
        )

    params_path: Optional[Path] = None
    if csv_path is not None:
        params_path = csv_path.parent / "params.json"
    elif annotate_path is not None:
        params_path = annotate_path.parent / "params.json"

    if params_path is not None:
        resolved_params = os.path.normcase(os.path.realpath(str(params_path)))
        if resolved_params in (resolved_off, resolved_on):
            raise ValueError(f"Duong dan metadata params.json trung voi tep anh dau vao: {params_path}")
        if resolved_csv is not None and resolved_params == resolved_csv:
            raise ValueError(f"Duong dan metadata params.json trung voi CSV: {params_path}")
        if resolved_ann is not None and resolved_params == resolved_ann:
            raise ValueError(f"Duong dan metadata params.json trung voi anh chu thich: {params_path}")

    csv_created_by_us = False
    ann_created_by_us = False

    try:
        with Image.open(off_path) as im_off, Image.open(on_path) as im_on:
            im_off.load()
            im_on.load()

            # Kiem tra tinh hop le dau vao cua cap anh truoc moi kiem metadata/dau ra (L12)
            if im_off.size != im_on.size:
                raise ValueError(
                    f"Kich thuoc anh OFF ({im_off.size[0]}x{im_off.size[1]}) "
                    f"khac anh ON ({im_on.size[0]}x{im_on.size[1]})"
                )
            if im_off.mode != im_on.mode:
                raise ValueError(
                    f"Che do anh OFF ({im_off.mode}) khac anh ON ({im_on.mode})"
                )
            if (
                getattr(im_off, "format", None)
                and getattr(im_on, "format", None)
                and im_off.format != im_on.format
            ):
                raise ValueError(
                    f"Dinh dang anh OFF ({im_off.format}) khac anh ON ({im_on.format})"
                )

            w, h = im_off.size
            x0, y0, x1, y1 = parse_roi(roi_str, w, h)

            # Doc, kiem tra hop le va so khop tham so truoc moi lan ghi CSV/PNG
            params_reused = False
            if params_path is not None:
                target_cfg = {
                    "roi": [x0, y0, x1, y1],
                    "min_diff": float(min_diff),
                    "max_width": int(max_width),
                    "sat_thresh": float(sat_thresh),
                    "img_width": int(w),
                    "img_height": int(h),
                }

                params_reused, _ = check_or_match_params(params_path, target_cfg)
                if not params_reused:
                    write_params_json(
                        params_path=params_path,
                        roi=(x0, y0, x1, y1),
                        min_diff=min_diff,
                        max_width=max_width,
                        sat_thresh=sat_thresh,
                        img_width=w,
                        img_height=h,
                    )

            rows = extract_laser_centers(
                off_img=im_off,
                on_img=im_on,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                min_diff=min_diff,
                max_width=max_width,
                sat_thresh=sat_thresh,
            )

            if csv_path is not None:
                if params_path is not None and not params_path.exists():
                    raise ValueError(
                        f"params_invalid: metadata {params_path} khong ton tai hoac da bi xoa truoc khi ghi CSV"
                    )
                if csv_path.exists():
                    raise FileExistsError(
                        f"Tep CSV dau ra da ton tai (khong ghi de): {csv_path}"
                    )
                write_centers_csv(csv_path, rows)
                csv_created_by_us = True

            if annotate_path is not None:
                if params_path is not None and not params_path.exists():
                    raise ValueError(
                        f"params_invalid: metadata {params_path} khong ton tai hoac da bi xoa truoc khi ghi PNG"
                    )
                if annotate_path.exists():
                    raise FileExistsError(
                        f"Tep PNG chu thich da ton tai hoac bi trung voi tep dau ra khac: {annotate_path}"
                    )
                create_annotated_image(im_on, x0, y0, x1, y1, rows, annotate_path)
                ann_created_by_us = True

    except Exception as e:
        if csv_created_by_us and csv_path is not None and csv_path.exists():
            try:
                csv_path.unlink()
            except OSError:
                pass
        if ann_created_by_us and annotate_path is not None and annotate_path.exists():
            try:
                annotate_path.unlink()
            except OSError:
                pass
        if isinstance(e, (FileNotFoundError, FileExistsError, ValueError)):
            raise
        raise ValueError(f"Loi doc hoac xu ly anh: {e}")

    # Tong hop thong ke
    total_rows = len(rows)
    ok_count = sum(1 for r in rows if r["reason"] == "ok")
    no_signal_count = sum(1 for r in rows if r["reason"] == "no_signal")
    weak_count = sum(1 for r in rows if r["reason"] == "weak")
    sat_count = sum(1 for r in rows if r["reason"] == "saturated")
    wide_count = sum(1 for r in rows if r["reason"] == "wide")
    amb_count = sum(1 for r in rows if r["reason"] == "ambiguous")
    edge_count = sum(1 for r in rows if r["reason"] == "edge")

    stats = {
        "img_width": w,
        "img_height": h,
        "roi": (x0, y0, x1, y1),
        "total_rows": total_rows,
        "ok_count": ok_count,
        "valid_pct": (ok_count / total_rows * 100.0) if total_rows > 0 else 0.0,
        "no_signal_count": no_signal_count,
        "weak_count": weak_count,
        "saturated_count": sat_count,
        "wide_count": wide_count,
        "ambiguous_count": amb_count,
        "edge_count": edge_count,
    }


    return rows, stats


# ==============================================================================
# PHAN KIEM THU TU DONG (SELFTEST)
# ==============================================================================


def generate_synthetic_images(
    width: int,
    height: int,
    line_width: float,
    center_x: float,
    amplitude: float = 180.0,
    noise_sigma: float = 2.0,
    rng: Optional[np.random.Generator] = None,
    second_line_x: Optional[float] = None,
    second_line_amp: Optional[float] = None,
    saturation: bool = False,
    flat_diff: Optional[float] = None,
    off_greater_than_on: bool = False,
) -> Tuple[Image.Image, Image.Image]:
    """
    Sinh cap anh tong hop OFF va ON voi vach laser biet truoc tam va cac hien tuong.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    # Nen toi co gradient nhe va nhieu
    bg = 20.0 + rng.normal(0, noise_sigma, size=(height, width))
    bg = np.clip(bg, 0, 255)

    on_arr = bg.copy()
    x_coords = np.arange(width)

    if flat_diff is not None:
        on_arr = np.clip(on_arr + flat_diff, 0, 255)
    elif off_greater_than_on:
        # ON nho hon OFF o mot so pixel
        on_arr = np.clip(on_arr - 15.0, 0, 255)
    else:
        sigma = max(0.4, line_width / 2.355)
        laser_profile = amplitude * np.exp(-0.5 * ((x_coords - center_x) / sigma) ** 2)

        if second_line_x is not None:
            amp2 = second_line_amp if second_line_amp is not None else amplitude
            laser_profile += amp2 * np.exp(-0.5 * ((x_coords - second_line_x) / sigma) ** 2)

        on_arr += laser_profile[np.newaxis, :]
        if noise_sigma > 0:
            on_arr += rng.normal(0, noise_sigma, size=(height, width))

        if saturation:
            # Ep vung dinh len 255
            mask = laser_profile > 0.8 * amplitude
            on_arr[:, mask] = 255.0

        on_arr = np.clip(on_arr, 0, 255)

    off_img = Image.fromarray(np.round(bg).astype(np.uint8), mode="L").convert("RGB")
    on_img = Image.fromarray(np.round(on_arr).astype(np.uint8), mode="L").convert("RGB")
    return off_img, on_img


def run_selftest() -> None:
    """
    Chay toan bo bo selftest theo tieu chi cua handoff C3:
    T1: Vach sach, tam phan so biet truoc, bao toan hash JPEG.
    T2: Ma tran rong 1/2/4/6 px x >=30 lan lap, do sigma mau n-1; tam sat mep ROI; ROI 1 hang.
    T3: Kiem tra tu choi cac loi dau vao (sai kich thuoc, file khong hop le, ROI sai, file da co...).
    T4: Mo phong tin hieu: OFF=ON, yeu, bao hoa, qua rong, hai nhanh ngang suc, ON<OFF.
    """
    print("=== SELFTEST: pc/line_extract.py ===")
    seed = 20260928
    rng = np.random.default_rng(seed)

    with tempfile.TemporaryDirectory(prefix="selftest_line_extract_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # ----------------------------------------------------------------------
        # T1: Kiem tra co ban, tam phan so biet truoc va bao toan hash anh goc
        # ----------------------------------------------------------------------
        print("\n--- [T1] Kiem tra vach sach, tam phan so va bao toan hash anh goc ---")
        img_w, img_h = 640, 480
        true_center = 320.35
        off_img, on_img = generate_synthetic_images(
            width=img_w,
            height=img_h,
            line_width=2.0,
            center_x=true_center,
            amplitude=190.0,
            noise_sigma=1.0,
            rng=rng,
        )

        off_path = tmpdir / "t1_off.jpg"
        on_path = tmpdir / "t1_on.jpg"
        csv_path = tmpdir / "t1_centers.csv"
        ann_path = tmpdir / "t1_annotated.png"

        off_img.save(off_path, quality=95)
        on_img.save(on_path, quality=95)

        hash_off_before = compute_file_sha256(off_path)
        hash_on_before = compute_file_sha256(on_path)

        roi_t1 = "100,80,540,400"  # 320 hang
        rows, stats = process_pair(
            off_path=off_path,
            on_path=on_path,
            roi_str=roi_t1,
            min_diff=20.0,
            max_width=30,
            sat_thresh=250.0,
            csv_path=csv_path,
            annotate_path=ann_path,
        )

        hash_off_after = compute_file_sha256(off_path)
        hash_on_after = compute_file_sha256(on_path)

        assert hash_off_before == hash_off_after, "Hash anh OFF bi thay doi sau khi chay!"
        assert hash_on_before == hash_on_after, "Hash anh ON bi thay doi sau khi chay!"
        print("  [x] Tinh toan ven hash anh goc: OFF va ON giu nguyen 100%.")

        assert csv_path.is_file(), "Tep CSV khong duoc tao!"
        assert ann_path.is_file(), "Tep anh chu thich khong duoc tao!"
        params_file = tmpdir / "params.json"
        assert params_file.is_file(), "Tep params.json metadata khong duoc tao canh CSV!"
        with open(params_file, "r", encoding="utf-8") as f:
            p_data = json.load(f)
            assert p_data["roi"] == [100, 80, 540, 400], "ROI trong params.json sai!"
            assert p_data["min_diff"] == 20.0, "min_diff trong params.json sai!"
        print("  [x] Tep CSV, PNG chu thich va metadata params.json duoc tao thanh cong tai duong dan rieng.")

        # Kiem tra ty le hop le va sai so tam
        valid_rows = [r for r in rows if r["valid"] == "true"]
        valid_rate = len(valid_rows) / len(rows) * 100.0
        assert valid_rate >= 90.0, f"Ty le hop le ({valid_rate:.1f}%) < 90%"

        errors = [abs(float(r["center_x_px"]) - true_center) for r in valid_rows]
        med_error = float(np.median(errors))
        assert (
            med_error <= 0.1
        ), f"Trung vi sai so tuyet doi ({med_error:.4f} px) vuot nguong 0.1 px!"
        print(
            f"  [x] Ty le hop le: {valid_rate:.1f}% (yeu cau >= 90%), "
            f"trung vi sai so: {med_error:.4f} px (yeu cau <= 0.1 px)."
        )

        # Kiem tra cau truc CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected_header = ["row_y,center_x_px,valid,reason,width_px"]
            assert (
                header == ["row_y", "center_x_px", "valid", "reason", "width_px"]
            ), f"Header CSV sai: {header}"
            csv_rows = list(reader)
            assert len(csv_rows) == len(rows) == 320, f"So hang CSV ({len(csv_rows)}) != 320"
            for row in csv_rows:
                assert len(row) == 5, f"Dong CSV khong du 5 cot: {row}"
                y, cx, val, rsn, w = row
                if val == "true":
                    assert 100 <= float(cx) < 540, f"Tam {cx} nam ngoai ROI [100, 540)"
        print("  [x] Khop quy uoc 5 cot CSV, so dong khop dung so hang ROI.")

        # ----------------------------------------------------------------------
        # T2: Ma tran be rong 1, 2, 4, 6 px x 30 lan lap; tam sat mep; ROI 1 hang
        # ----------------------------------------------------------------------
        print("\n--- [T2] Ma tran be rong 1/2/4/6 px (N=30 lan) va kiem tra bien ---")
        widths = [1.0, 2.0, 4.0, 6.0]
        n_reps = 30
        roi_x0, roi_x1 = 150, 450
        roi_y0, roi_y1 = 100, 380
        num_rows = roi_y1 - roi_y0  # 280 hang
        sim_center = 300.25
        noise_level = 2.0

        print(f"  Cac thong so: N={n_reps}, Seed={seed}, ROI=[{roi_x0},{roi_x1}) x [{roi_y0},{roi_y1})")
        print(f"  Nguong: min_diff=20.0, max_width=30, sat_thresh=250.0, Noise sigma={noise_level}")
        print("  " + "-" * 95)
        print(
            f"  {'Be rong (px)':>12} | {'So lap':>6} | {'So hang chung':>13} | "
            f"{'Hop le (%)':>10} | {'Sai so trung vi (px)':>20} | {'Sigma mau trung vi (px)':>23}"
        )
        print("  " + "-" * 95)

        for w in widths:
            all_centers = np.full((num_rows, n_reps), np.nan)
            all_errors = []

            for rep in range(n_reps):
                off_syn, on_syn = generate_synthetic_images(
                    width=img_w,
                    height=img_h,
                    line_width=w,
                    center_x=sim_center,
                    amplitude=180.0,
                    noise_sigma=noise_level,
                    rng=rng,
                )
                rows_syn = extract_laser_centers(
                    off_img=off_syn,
                    on_img=on_syn,
                    x0=roi_x0,
                    y0=roi_y0,
                    x1=roi_x1,
                    y1=roi_y1,
                    min_diff=20.0,
                    max_width=30,
                    sat_thresh=250.0,
                )
                for idx_r, r in enumerate(rows_syn):
                    if r["valid"] == "true":
                        c_val = float(r["center_x_px"])
                        all_centers[idx_r, rep] = c_val
                        all_errors.append(abs(c_val - sim_center))

            valid_matrix = ~np.isnan(all_centers)
            total_valid_rate = np.mean(valid_matrix) * 100.0
            row_valid_counts = np.sum(valid_matrix, axis=1)
            # Hang hop le chung: cac hang co it nhat 2 lan do de tinh sigma mau n-1
            common_row_indices = np.where(row_valid_counts >= 2)[0]
            sigmas = []
            for r_idx in common_row_indices:
                vals = all_centers[r_idx, valid_matrix[r_idx, :]]
                s = np.std(vals, ddof=1)  # do lech chuan mau (n-1)
                sigmas.append(s)

            med_s = float(np.median(sigmas)) if len(sigmas) > 0 else float("nan")
            med_err = float(np.median(all_errors)) if len(all_errors) > 0 else float("nan")

            print(
                f"  {w:12.1f} | {n_reps:6d} | {len(common_row_indices):13d} | "
                f"{total_valid_rate:9.1f}% | {med_err:20.4f} | {med_s:23.4f}"
            )

        print("  " + "-" * 95)
        print("  [x] Ma tran 4 cau hinh hoan tat voi day du so hang chung va sigma mau n-1.")

        # Kiem tra tam sat mep ROI
        print("  Kiem tra tam sat mep ROI:")
        off_edge, on_edge = generate_synthetic_images(
            width=img_w,
            height=img_h,
            line_width=2.0,
            center_x=roi_x0 + 1.2,  # sat mep trai
            amplitude=180.0,
            noise_sigma=0.5,
            rng=rng,
        )
        edge_rows = extract_laser_centers(
            off_edge, on_edge, x0=roi_x0, y0=roi_y0, x1=roi_x1, y1=roi_y1
        )
        assert len(edge_rows) == num_rows, "So hang khong dung khi tam sat mep"
        assert all(r["reason"] == "edge" and r["valid"] == "false" for r in edge_rows), "Cum cham bien phai gan reason=edge va valid=false"
        print("  [x] Tam sat mep ROI: phat hien dung cum cham bien (reason='edge', valid='false'), khong vuot bien mang.")

        # Kiem tra ROI dung 1 hang
        off_1r, on_1r = generate_synthetic_images(
            width=img_w,
            height=img_h,
            line_width=2.0,
            center_x=sim_center,
            amplitude=180.0,
            noise_sigma=0.5,
            rng=rng,
        )
        single_row_res = extract_laser_centers(
            off_1r, on_1r, x0=roi_x0, y0=200, x1=roi_x1, y1=201
        )
        assert len(single_row_res) == 1, "ROI 1 hang phai tra ve dung 1 dong"
        assert single_row_res[0]["valid"] == "true", "ROI 1 hang phai hop le"
        print("  [x] ROI 1 hang ([y0, y0+1)): tra ve dung 1 dong, hoat dong on dinh.")

        # ----------------------------------------------------------------------
        # T3: Kiem tra tu choi cac loi dau vao (rc != 0, khong tao PASS do dang)
        # ----------------------------------------------------------------------
        print("\n--- [T3] Kiem tra tu choi loi dau vao ---")

        # 1. Anh khac kich thuoc
        im_small = Image.new("RGB", (320, 240), color="black")
        im_large = Image.new("RGB", (640, 480), color="black")
        p_small = tmpdir / "small.jpg"
        p_large = tmpdir / "large.jpg"
        im_small.save(p_small)
        im_large.save(p_large)
        try:
            process_pair(p_small, p_large)
            assert False, "Phai bao loi khi hai anh khac kich thuoc!"
        except ValueError as e:
            print(f"  [x] Bat dung loi khac kich thuoc: {e}")

        # 2. Tep khong phai anh
        p_corrupt = tmpdir / "corrupt.jpg"
        p_corrupt.write_text("day khong phai anh jpeg", encoding="utf-8")
        try:
            process_pair(p_corrupt, p_large)
            assert False, "Phai bao loi khi tep khong phai anh!"
        except ValueError as e:
            print(f"  [x] Bat dung loi tep khong phai anh: {e}")

        # 3. ROI rong hoac vuot bien
        try:
            process_pair(p_large, p_large, roi_str="200,100,150,300")
            assert False, "Phai bao loi khi x0 >= x1!"
        except ValueError as e:
            print(f"  [x] Bat dung loi ROI x0 >= x1: {e}")

        try:
            process_pair(p_large, p_large, roi_str="0,0,700,480")
            assert False, "Phai bao loi khi x1 > img_width!"
        except ValueError as e:
            print(f"  [x] Bat dung loi ROI vuot anh: {e}")

        # 1b. Anh khac che do (L va RGB)
        im_gray = Image.new("L", (640, 480), color=0)
        p_gray = tmpdir / "gray.jpg"
        im_gray.save(p_gray)
        try:
            process_pair(p_gray, p_large)
            assert False, "Phai bao loi khi hai anh khac che do mau!"
        except ValueError as e:
            print(f"  [x] Bat dung loi khac che do anh: {e}")

        # 4. Nguong vo ly (am, 0, nan, inf, vuot mien, sat_thresh <= min_diff)
        for bad_md in (-5.0, 0.0, float("nan"), float("inf")):
            try:
                process_pair(p_large, p_large, min_diff=bad_md)
                assert False, f"Phai bao loi khi min_diff={bad_md}!"
            except ValueError as e:
                print(f"  [x] Bat dung loi min_diff={bad_md}: {e}")

        for bad_sat in (-1.0, 0.0, 256.0, float("nan")):
            try:
                process_pair(p_large, p_large, sat_thresh=bad_sat)
                assert False, f"Phai bao loi khi sat_thresh={bad_sat}!"
            except ValueError as e:
                print(f"  [x] Bat dung loi sat_thresh={bad_sat}: {e}")

        try:
            process_pair(p_large, p_large, min_diff=20.0, sat_thresh=15.0)
            assert False, "Phai bao loi khi sat_thresh <= min_diff!"
        except ValueError as e:
            print(f"  [x] Bat dung loi sat_thresh <= min_diff: {e}")

        # 5. Duong dan dau ra trung dau vao
        try:
            process_pair(p_large, p_large, csv_path=p_large)
            assert False, "Phai bao loi khi duong dan CSV trung anh dau vao!"
        except ValueError as e:
            print(f"  [x] Bat dung loi dau ra trung dau vao: {e}")

        # 6. Duong dan CSV va PNG chu thich trung nhau
        p_same_out = tmpdir / "same_output.dat"
        try:
            process_pair(p_large, p_large, csv_path=p_same_out, annotate_path=p_same_out)
            assert False, "Phai bao loi khi CSV va PNG chu thich trung duong dan!"
        except ValueError as e:
            print(f"  [x] Bat dung loi CSV va PNG chu thich trung nhau: {e}")

        # 7. Tep dau ra da ton tai
        p_existing = tmpdir / "already_exists.csv"
        p_existing.write_text("test", encoding="utf-8")
        try:
            process_pair(p_large, p_large, csv_path=p_existing)
            assert False, "Phai tu choi ghi de khi tep da ton tai!"
        except FileExistsError as e:
            print(f"  [x] Tu choi ghi de tep da ton tai: {e}")

        # 8. Kiem tra L09: khoa tham so theo thu muc (cung cau hinh thanh cong, lech cau hinh tu choi)
        p_run = tmpdir / "run_l09"
        p_run.mkdir()
        c0 = p_run / "centers_0000.csv"
        c1 = p_run / "centers_0001.csv"
        c2 = p_run / "centers_0002.csv"
        pj = p_run / "params.json"

        # Buoc 0: tao params.json moi
        process_pair(p_large, p_large, roi_str="100,50,540,430", min_diff=20.0, csv_path=c0)
        assert c0.exists() and pj.exists(), "Buoc 0 phai tao CSV va params.json"
        h0_params = compute_file_sha256(pj)
        h0_img = compute_file_sha256(p_large)
        print("  [x] L09 buoc 0: tao CSV va params.json dung 6 truong cau hinh.")

        # Buoc 1: cung cau hinh -> thanh cong, params.json giu nguyen byte
        process_pair(p_large, p_large, roi_str="100,50,540,430", min_diff=20.0, csv_path=c1)
        assert c1.exists(), "Buoc 1 phai tao centers_0001.csv"
        assert compute_file_sha256(pj) == h0_params, "params.json phai giu nguyen byte khi cung cau hinh"
        assert compute_file_sha256(p_large) == h0_img, "Anh goc phai giu nguyen"
        print("  [x] L09 buoc 1: cung cau hinh tai su dung nguyen byte params.json.")

        # Buoc 2: lech cau hinh -> tu choi params_mismatch, khong tao centers_0002.csv, params.json giu nguyen
        try:
            process_pair(p_large, p_large, roi_str="200,60,500,300", min_diff=35.0, csv_path=c2)
            assert False, "Phai tu choi khi tham so khac vao cung thu muc!"
        except ValueError as e:
            assert "params_mismatch" in str(e), f"Loi phai chua 'params_mismatch': {e}"
            assert not c2.exists(), "centers_0002.csv khong duoc tao khi params_mismatch"
            assert compute_file_sha256(pj) == h0_params, "params.json khong duoc bi thay doi khi params_mismatch"
            print(f"  [x] L09 buoc 2: bat dung params_mismatch khi doi tham so: {e}")

        # 9. Kiem tra params_invalid (tep cua cong cu khac, JSON hong, la thu muc)
        p_other = tmpdir / "run_other"
        p_other.mkdir()
        (p_other / "params.json").write_text('{"scan_id": "scan_cu"}', encoding="utf-8")
        try:
            process_pair(p_large, p_large, csv_path=p_other / "c.csv")
            assert False, "Phai tu choi metadata cua cong cu khac!"
        except ValueError as e:
            assert "params_invalid" in str(e), f"Loi phai chua 'params_invalid': {e}"
            assert not (p_other / "c.csv").exists(), "Khong duoc tao CSV khi params_invalid"
            print(f"  [x] Bat dung params_invalid voi cong cu khac: {e}")

        # 10. Kiem tra bao toan metadata khi loi o buoc sau (khong xoa params.json tai su dung)
        # Tao file c1_err bi loi FileExistsError o anh chu thich da co
        p_ann_exist = p_run / "exist.png"
        p_ann_exist.write_text("dummy", encoding="utf-8")
        c_fail = p_run / "c_fail.csv"
        try:
            process_pair(
                p_large,
                p_large,
                roi_str="100,50,540,430",
                min_diff=20.0,
                csv_path=c_fail,
                annotate_path=p_ann_exist,
            )
            assert False, "Phai bao loi FileExistsError do anh chu thich da co!"
        except FileExistsError:
            assert not c_fail.exists(), "CSV do dang phai duoc don dep"
            assert compute_file_sha256(pj) == h0_params, "params.json tai su dung KHONG duoc bi xoa khi loi"
            assert p_ann_exist.read_text(encoding="utf-8") == "dummy", "PNG da co cua tien trinh khac KHONG duoc bi xoa khi loi"
            print("  [x] Bao toan metadata tai su dung va don dep dung tep do dang khi loi.")

        # 11. Kiem tra L13: CSV cua tien trinh khac khong bi xoa khi loi truoc ghi
        c_foreign = p_run / "foreign.csv"
        c_foreign.write_text("tien_trinh_khac", encoding="utf-8")
        try:
            process_pair(
                p_small,
                p_large,
                csv_path=c_foreign,
            )
            assert False, "Phai bao loi kich thuoc!"
        except (ValueError, FileExistsError):
            assert c_foreign.read_text(encoding="utf-8") == "tien_trinh_khac", "CSV cua tien trinh khac KHONG duoc bi xoa"
            print("  [x] L13: tep cua tien trinh khac duoc bao toan nguyen ven khi co loi.")

        # 12. Kiem tra V10 (D037): Vong doi metadata bat bien khi luot tao gap loi va khi metadata ghi do
        p_v10 = tmpdir / "run_v10"
        p_v10.mkdir()
        c_v10_fail = p_v10 / "centers_0000.csv"
        pj_v10 = p_v10 / "params.json"

        # A: tao metadata moi nhung bi loi o buoc ghi CSV sau do
        orig_writerow = csv.DictWriter.writerow
        def failing_writerow(self, row):
            raise OSError("Disk full simulation")
        csv.DictWriter.writerow = failing_writerow
        try:
            process_pair(
                p_large,
                p_large,
                roi_str="100,50,540,430",
                min_diff=20.0,
                csv_path=c_v10_fail,
            )
            assert False, "Phai bao loi khi ghi CSV!"
        except (OSError, ValueError):
            assert not c_v10_fail.exists(), "CSV do dang cua A phai duoc don dep"
            assert pj_v10.exists(), "params.json moi tao KHONG duoc bi xoa khi A loi"
            h_v10 = compute_file_sha256(pj_v10)
            print("  [x] V10: metadata hoan chinh giu nguyen tren dia sau khi luot tao gap loi.")
        finally:
            csv.DictWriter.writerow = orig_writerow

        # B: luot sau cung cau hinh vao thu muc tren -> thanh cong, tai su dung nguyen byte
        c_v10_ok = p_v10 / "centers_0001.csv"
        process_pair(
            p_large,
            p_large,
            roi_str="100,50,540,430",
            min_diff=20.0,
            csv_path=c_v10_ok,
        )
        assert c_v10_ok.exists(), "Luot B cung cau hinh phai tao CSV thanh cong"
        assert compute_file_sha256(pj_v10) == h_v10, "params.json phai giu nguyen byte khi B tai su dung"
        print("  [x] V10: luot sau cung cau hinh tai su dung nguyen byte metadata da ton tai.")

        # C: luot sau khac cau hinh vao thu muc tren -> tu choi params_mismatch
        c_v10_diff = p_v10 / "centers_0002.csv"
        try:
            process_pair(
                p_large,
                p_large,
                roi_str="100,50,540,430",
                min_diff=35.0,
                csv_path=c_v10_diff,
            )
            assert False, "Phai tu choi params_mismatch khi khac cau hinh!"
        except ValueError as e:
            assert "params_mismatch" in str(e), f"Loi phai la params_mismatch: {e}"
            assert not c_v10_diff.exists(), "Khong duoc tao CSV khi params_mismatch"
            print("  [x] V10: luot sau khac cau hinh bi tu choi voi params_mismatch.")

        # D: Thu muc co metadata ghi do -> bi tu choi params_invalid, tep ghi do giu nguyen tren dia
        p_v10_partial = tmpdir / "run_v10_partial"
        p_v10_partial.mkdir()
        pj_partial = p_v10_partial / "params.json"
        partial_content = '{"roi": [100, 50, 540, 430], "min_diff":'
        pj_partial.write_text(partial_content, encoding="utf-8")
        try:
            process_pair(
                p_large,
                p_large,
                csv_path=p_v10_partial / "c.csv",
            )
            assert False, "Phai bao loi params_invalid khi metadata ghi do!"
        except ValueError as e:
            assert "params_invalid" in str(e), f"Loi phai chua 'params_invalid': {e}"
            assert pj_partial.read_text(encoding="utf-8") == partial_content, "Tep ghi do phai giu nguyen, khong duoc xoa hay sua"
            print("  [x] V10: metadata ghi do bi tu choi dung (params_invalid) va giu nguyen tren dia.")

        # E: Loi giua chung khi ghi params.json -> khong tao CSV, khong tu xoa tep ghi do
        p_v10_err = tmpdir / "run_v10_err"
        p_v10_err.mkdir()
        pj_err = p_v10_err / "params.json"
        orig_dump = json.dump
        def failing_dump(obj, fp, **kwargs):
            fp.write('{"roi": [100, 50, 540, 430], "min_diff":')
            fp.flush()
            raise OSError("I/O error during json.dump simulation")
        json.dump = failing_dump
        try:
            process_pair(
                p_large,
                p_large,
                csv_path=p_v10_err / "c.csv",
            )
            assert False, "Phai bao loi khi json.dump fail!"
        except (OSError, ValueError):
            assert pj_err.exists(), "params.json ghi do KHONG duoc bi xoa"
            assert not (p_v10_err / "c.csv").exists(), "Khong duoc tao CSV khi ghi metadata fail"
            print("  [x] V10: loi giua chung khi ghi metadata giu nguyen tep do va khong tao CSV.")
        finally:
            json.dump = orig_dump

        # 13. Kiem tra R10: Loi liet ke thu muc hoac kiem tra tep cu nem OSError phai bi tu choi params_invalid
        p_r10 = tmpdir / "run_r10"
        p_r10.mkdir()
        c_r10_old = p_r10 / "centers_0000.csv"
        c_r10_old.write_text("old_csv_data", encoding="utf-8")
        c_r10_new = p_r10 / "centers_0001.csv"
        pj_r10 = p_r10 / "params.json"

        # A: iterdir() nem PermissionError/OSError
        orig_iterdir = Path.iterdir
        def failing_iterdir(self):
            if self.resolve() == p_r10.resolve():
                raise PermissionError("Access denied during iterdir")
            return orig_iterdir(self)
        Path.iterdir = failing_iterdir
        try:
            process_pair(
                p_large,
                p_large,
                csv_path=c_r10_new,
            )
            assert False, "Phai bao loi params_invalid khi iterdir nem OSError!"
        except ValueError as e:
            assert "params_invalid" in str(e), f"Loi phai chua 'params_invalid': {e}"
            assert not pj_r10.exists(), "params.json khong duoc tao khi gap loi iterdir"
            assert not c_r10_new.exists(), "CSV moi khong duoc tao khi gap loi iterdir"
            assert c_r10_old.read_text(encoding="utf-8") == "old_csv_data", "CSV cu phai duoc bao toan nguyen ven"
            print("  [x] R10: iterdir nem OSError bi chan bang params_invalid va khong ghi de.")
        finally:
            Path.iterdir = orig_iterdir

        # B: is_file() nem PermissionError/OSError tren tep trong thu muc
        orig_is_file = Path.is_file
        def failing_is_file(self):
            if self.name == "centers_0000.csv" and self.parent.resolve() == p_r10.resolve():
                raise PermissionError("Access denied during is_file")
            return orig_is_file(self)
        Path.is_file = failing_is_file
        try:
            process_pair(
                p_large,
                p_large,
                csv_path=c_r10_new,
            )
            assert False, "Phai bao loi params_invalid khi is_file nem OSError!"
        except ValueError as e:
            assert "params_invalid" in str(e), f"Loi phai chua 'params_invalid': {e}"
            assert not pj_r10.exists(), "params.json khong duoc tao khi gap loi is_file"
            assert not c_r10_new.exists(), "CSV moi khong duoc tao khi gap loi is_file"
            assert c_r10_old.read_text(encoding="utf-8") == "old_csv_data", "CSV cu phai duoc bao toan nguyen ven"
            print("  [x] R10: is_file nem OSError bi chan bang params_invalid va khong ghi de.")
        finally:
            Path.is_file = orig_is_file


        # ----------------------------------------------------------------------
        # T4: Kiem tra tin hieu mo phong (no_signal, weak, saturated, wide, ambiguous, ON<OFF)
        # ----------------------------------------------------------------------
        print("\n--- [T4] Kiem tra cac trang thai tin hieu mo phong ---")

        # 1. OFF = ON -> no_signal
        off_same = Image.new("RGB", (200, 50), color=(30, 30, 30))
        on_same = Image.new("RGB", (200, 50), color=(30, 30, 30))
        res_same = extract_laser_centers(off_same, on_same, 10, 10, 190, 40, min_diff=20.0)
        assert all(
            r["reason"] == "no_signal" and r["valid"] == "false" for r in res_same
        ), "OFF=ON phai cho no_signal"
        print("  [x] OFF = ON: 100% hang cho reason='no_signal', valid='false'.")

        # 2. Vach yeu (diff < min_diff) -> weak
        off_wk = Image.new("RGB", (200, 50), color=(30, 30, 30))
        on_wk = Image.new("RGB", (200, 50), color=(40, 30, 30))  # diff = 10 < 20
        res_wk = extract_laser_centers(off_wk, on_wk, 10, 10, 190, 40, min_diff=20.0)
        assert all(
            r["reason"] == "weak" and r["valid"] == "false" for r in res_wk
        ), "Diff < min_diff phai cho weak"
        print("  [x] Vach yeu (diff < min_diff): 100% hang cho reason='weak', valid='false'.")

        # 3. Bao hoa (ON >= 250) -> saturated
        off_sat, on_sat = generate_synthetic_images(
            width=200, height=50, line_width=4.0, center_x=100.0, saturation=True, rng=rng
        )
        res_sat = extract_laser_centers(
            off_sat, on_sat, 10, 10, 190, 40, min_diff=20.0, sat_thresh=250.0
        )
        assert any(
            r["reason"] == "saturated" and r["valid"] == "false" for r in res_sat
        ), "Vung bao hoa phai duoc danh dau saturated"
        print("  [x] Bao hoa (pixel ON >= sat_thresh): phat hien dung reason='saturated'.")

        # 4. Qua rong (width > max_width) -> wide
        off_wd, on_wd = generate_synthetic_images(
            width=200, height=50, line_width=15.0, center_x=100.0, rng=rng
        )
        res_wd = extract_laser_centers(
            off_wd, on_wd, 10, 10, 190, 40, min_diff=20.0, max_width=10
        )
        assert any(
            r["reason"] == "wide" and r["valid"] == "false" for r in res_wd
        ), "Cum co be rong > max_width phai danh dau wide"
        print("  [x] Qua rong (width > max_width): phat hien dung reason='wide'.")

        # 5. Hai nhanh ngang suc -> ambiguous (khong lay trung binh)
        off_amb, on_amb = generate_synthetic_images(
            width=200,
            height=50,
            line_width=2.0,
            center_x=70.0,
            second_line_x=130.0,
            second_line_amp=180.0,
            rng=rng,
        )
        res_amb = extract_laser_centers(off_amb, on_amb, 10, 10, 190, 40, min_diff=20.0)
        amb_rows = [r for r in res_amb if r["reason"] == "ambiguous"]
        assert len(amb_rows) > 0, "Hai nhanh ngang suc phai duoc danh dau ambiguous"
        for r in amb_rows:
            assert r["valid"] == "false", "Hang ambiguous khong duoc valid"
            assert r["center_x_px"] == "", "Hang ambiguous khong duoc phep chua toan bo hoac trung binh hai tam"
        print("  [x] Hai nhanh ngang suc: gan dung reason='ambiguous', KHONG lay trung binh hai tam.")

        # 6. Pixel ON < OFF -> chan am ve 0, khong bi cuon so
        off_rev = Image.new("RGB", (200, 50), color=(100, 50, 50))
        on_rev = Image.new("RGB", (200, 50), color=(40, 50, 50))
        diff_rev, _ = compute_red_difference(off_rev, on_rev)
        assert np.all(diff_rev == 0), f"Hieu am phai duoc chan ve 0, nhan duoc max={np.max(diff_rev)}"
        print("  [x] Pixel ON < OFF: tinh kieu co dau va chan am ve 0 tuyet doi (khong tran so).")

        # 7. Dom sang don le o xa vach chinh (R02/TX9)
        off_spot = Image.new("RGB", (200, 3), color=(20, 20, 20))
        on_arr = np.full((3, 200, 3), 20, dtype=np.uint8)
        on_arr[0, 28:33, 0] = 200  # vach x=30
        on_arr[1, 128:133, 0] = 200  # dom le x=130
        on_arr[2, 28:33, 0] = 200  # vach x=30
        on_arr[2, 128:133, 0] = 200  # dom le x=130
        on_spot = Image.fromarray(on_arr, mode="RGB")
        res_spot = extract_laser_centers(off_spot, on_spot, 0, 0, 200, 3, min_diff=20.0)
        assert res_spot[0]["valid"] == "true" and abs(float(res_spot[0]["center_x_px"]) - 30.0) < 1.0
        assert res_spot[1]["valid"] == "false" and res_spot[1]["reason"] == "ambiguous", "Dom le o xa phai bi tu choi"
        assert res_spot[2]["valid"] == "true" and abs(float(res_spot[2]["center_x_px"]) - 30.0) < 1.0, "Hang 2 phai bam dung vach chinh x=30"
        print("  [x] Dom sang le xa vach: tu choi dung (ambiguous), khong keo lech tam sang nhanh sai.")

    print("\n" + "=" * 50)
    print("KET QUA SELFTEST: PASS (tat ca cac tieu chi T1-T4 deu dat)")
    print("=" * 50)


# ==============================================================================
# CLI CHINH
# ==============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trich tam vach laser tu cap anh JPEG OFF/ON (pc/line_extract.py)"
    )
    parser.add_argument("--off", type=str, help="Duong dan tep anh JPEG khi laser tat (OFF)")
    parser.add_argument("--on", type=str, help="Duong dan tep anh JPEG khi laser bat (ON)")
    parser.add_argument(
        "--roi",
        type=str,
        default=None,
        help="Vung quan tam nua mo [x0, x1) x [y0, y1) theo toan anh goc 0 (vi du: 100,50,540,430)",
    )
    parser.add_argument(
        "--min-diff",
        type=float,
        default=20.0,
        help="Nguong hieu kenh do toi thieu de nhan dien pixel laser (mac dinh: 20.0)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=30,
        help="Be rong cum laser toi da tinh bang pixel (mac dinh: 30)",
    )
    parser.add_argument(
        "--sat-thresh",
        type=float,
        default=250.0,
        help="Nguong gia tri bao hoa tren kenh do (mac dinh: 250.0)",
    )
    parser.add_argument("--csv", type=str, default=None, help="Duong dan tep CSV luu ket qua")
    parser.add_argument(
        "--annotate",
        type=str,
        default=None,
        help="Duong dan tep anh PNG chu thich ve tam va ROI",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Chay bo kiem tra tu dong toan dien (T1-T4) va thoat",
    )

    args = parser.parse_args()

    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except Exception as e:
            print(f"SELFTEST THAT BAI: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            sys.exit(1)

    if not args.off or not args.on:
        parser.print_help()
        print("\nLoi: Bat buoc phai truyen ca --off va --on (hoac chay --selftest).", file=sys.stderr)
        sys.exit(1)

    off_p = Path(args.off)
    on_p = Path(args.on)
    csv_p = Path(args.csv) if args.csv else None
    ann_p = Path(args.annotate) if args.annotate else None

    try:
        rows, stats = process_pair(
            off_path=off_p,
            on_path=on_p,
            roi_str=args.roi,
            min_diff=args.min_diff,
            max_width=args.max_width,
            sat_thresh=args.sat_thresh,
            csv_path=csv_p,
            annotate_path=ann_p,
        )

        x0, y0, x1, y1 = stats["roi"]
        print("--- Tham so va ket qua xu ly (pc/line_extract.py) ---")
        print(f"Anh OFF: {off_p}")
        print(f"Anh ON:  {on_p}")
        print(f"Kich thuoc anh: {stats['img_width']}x{stats['img_height']}")
        print(f"ROI: [{x0}, {x1}) x [{y0}, {y1}) (Tong so hang ROI: {stats['total_rows']})")
        print(
            f"Nguong: min_diff={args.min_diff}, max_width={args.max_width}, sat_thresh={args.sat_thresh}"
        )
        if csv_p:
            print(f"Xuat CSV: {csv_p}")
        if ann_p:
            print(f"Xuat PNG chu thich: {ann_p}")
        print(
            f"So hang hop le (ok): {stats['ok_count']}/{stats['total_rows']} ({stats['valid_pct']:.1f}%)"
        )
        print(f"So hang khong tin hieu (no_signal): {stats['no_signal_count']}")
        print(f"So hang tin hieu yeu (weak):        {stats['weak_count']}")
        print(f"So hang bao hoa (saturated):         {stats['saturated_count']}")
        print(f"So hang qua rong (wide):             {stats['wide_count']}")
        print(f"So hang hai nhanh (ambiguous):       {stats['ambiguous_count']}")
        print(f"So hang cham bien (edge):            {stats['edge_count']}")

    except Exception as e:
        print(f"Loi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
