#!/usr/bin/env python3
"""
sharpness.py - do do net va uoc luong truong nhin cho cac phien anh cua
capture_session.py. Phuc vu chi tieu MT "Quang hoc" tuan 1: chon khoang
cach nhin ro vat 50-100 mm trong ba muc 200, 250, 350 mm.

Moi anh (chuyen sang thang xam) tinh tren mot ROI:
  - lap_var     : phuong sai cua Laplacian 4 lan can. Anh net cho gia tri
                  cao, anh mo cho gia tri thap. Phu thuoc noi dung anh va do
                  tuong phan, nen CHI so sanh tuong doi giua cac phien chup
                  cung vat, cung anh sang.
  - grad_energy : trung binh Gx^2 + Gy^2 voi nhan Sobel 3x3. Cung y nghia,
                  dung de doi chieu cheo voi lap_var.
  - mean, std   : do sang trung binh va do lech chuan trong ROI (thang xam),
                  de thay phoi sang co doi giua cac phien khong (AEC dang
                  tu chinh).
  - sat_frac    : ti le diem anh >= 250 (bao hoa); dark_frac: ti le <= 5.

  Vong 5 (L06, xu ly ho so camera am luc - xem camera_profile.py va
  01_PLAN.md Phu luc ky thuat Vong 5): them bo so mau RGB tren cung ROI,
  doc lap voi bon so tren (thang xam):
  - mean_r/g/b        : do sang trung binh tung kenh mau trong ROI.
  - channel_spread_pct: 100 x (max(R,G,B) - min(R,G,B)) / trung binh ba
                        kenh - lech mau cang lon thi so cang cao; anh xam
                        that (R=G=B) cho 0.
  - dark_frac_rgb, sat_frac_rgb: ti le diem anh co IT NHAT MOT kenh mau
                        <= 5 (toi) hoac >= 250 (bao hoa) - khac dark_frac/
                        sat_frac o tren (tinh tren thang xam da tron kenh).

Truong nhin: nguoi dung doc toa do hai diem tren thuoc trong anh goc (vi du
mo bang Paint, toa do hien o goc duoi trai) va khoang cach thuc giua chung
theo mm. Script tinh mm/pixel va be rong, be cao truong nhin o mat vat.
Gia dinh pixel vuong va thuoc nam trong mat phang vuong goc voi truc quang;
sai lech do dat nghieng khong duoc hieu chinh o day.

Cach dung, chay tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/sharpness.py --selftest
  .venv/Scripts/python.exe pc/sharpness.py capture_20260916_154847
  .venv/Scripts/python.exe pc/sharpness.py capture_A capture_B --roi center
  .venv/Scripts/python.exe pc/sharpness.py capture_A --ruler 120,300,520,300,100
  .venv/Scripts/python.exe pc/sharpness.py capture_A capture_B --roi capture_A=100,200,440,120 --roi capture_B=180,220,280,80 --ruler capture_A=120,300,520,300,100 --ruler capture_B=... --out docs/logs --annotate

Ten phien khong co duong dan duoc tim trong data/raw/. Ket qua in ra man
hinh; voi --out ghi them thu muc rieng khong ghi de: per_image.csv,
summary.json, summary.txt va (neu --annotate) mot anh dai dien moi phien co
ve ROI va hai diem thuoc.

Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import csv
import math
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from capture_session import git_info, now_iso

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = REPO_ROOT / "data" / "raw"
LF = chr(10)

CSV_FIELDS = [
    "session_id", "idx", "file", "width", "height", "roi",
    "lap_var", "grad_energy", "mean", "std", "sat_frac", "dark_frac",
    "mean_r", "mean_g", "mean_b", "channel_spread_pct", "dark_frac_rgb", "sat_frac_rgb",
]


# ----------------------------------------------------------------------
# Phep do tren mot mang xam float64.
# ----------------------------------------------------------------------

def metrics_on_gray(g):
    """g: mang 2 chieu float64, it nhat 3x3. Tra dict cac so do."""
    if g.ndim != 2 or g.shape[0] < 3 or g.shape[1] < 3:
        raise ValueError("ROI phai it nhat 3x3, dang la %s" % (g.shape,))
    c = g[1:-1, 1:-1]
    lap = 4.0 * c - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    gx = (g[:-2, :-2] + 2.0 * g[1:-1, :-2] + g[2:, :-2]) - (g[:-2, 2:] + 2.0 * g[1:-1, 2:] + g[2:, 2:])
    gy = (g[:-2, :-2] + 2.0 * g[:-2, 1:-1] + g[:-2, 2:]) - (g[2:, :-2] + 2.0 * g[2:, 1:-1] + g[2:, 2:])
    return {
        "lap_var": float(lap.var()),
        "grad_energy": float(np.mean(gx * gx + gy * gy)),
        "mean": float(g.mean()),
        "std": float(g.std()),
        "sat_frac": float(np.mean(g >= 250.0)),
        "dark_frac": float(np.mean(g <= 5.0)),
    }


def image_to_gray(im):
    """PIL Image -> mang float64 thang xam (ITU-R 601-2 cua Pillow)."""
    return np.asarray(im.convert("L"), dtype=np.float64)


def image_to_rgb(im):
    """PIL Image -> mang float64 HxWx3 (kenh R,G,B)."""
    return np.asarray(im.convert("RGB"), dtype=np.float64)


def metrics_rgb_on_roi(rgb):
    """rgb: mang HxWx3 float64. Tra dict mean_r/g/b, channel_spread_pct,
    dark_frac_rgb, sat_frac_rgb (Vong 5, L06 - xem docstring dau tep)."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("ROI RGB phai co dang HxWx3, dang la %s" % (rgb.shape,))
    mr = float(rgb[..., 0].mean())
    mg = float(rgb[..., 1].mean())
    mb = float(rgb[..., 2].mean())
    mean_rgb = (mr + mg + mb) / 3.0
    spread = 0.0 if mean_rgb == 0 else 100.0 * (max(mr, mg, mb) - min(mr, mg, mb)) / mean_rgb
    return {
        "mean_r": mr, "mean_g": mg, "mean_b": mb,
        "channel_spread_pct": spread,
        "dark_frac_rgb": float(np.mean(np.any(rgb <= 5.0, axis=2))),
        "sat_frac_rgb": float(np.mean(np.any(rgb >= 250.0, axis=2))),
    }


def parse_roi(text):
    """'[ID=]X,Y,W,H' hoac '[ID=]center' -> (ID hoac None, roi).
    roi la tuple int, hoac chuoi 'center', hoac None khi text la None.
    Co ID= thi ROI chi ap cho phien ten do (moi khoang cach vat to nho
    khac nhau nen ROI khac nhau); khong ID thi ap cho moi phien."""
    if text is None:
        return None, None
    key = None
    t = text.strip()
    if "=" in t:
        key, t = t.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--roi: ID truoc dau = dang rong")
    t = t.strip().lower()
    if t == "center":
        return key, "center"
    parts = t.split(",")
    if len(parts) != 4:
        raise ValueError("--roi can 4 so X,Y,W,H hoac chu 'center'")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError:
        raise ValueError("--roi phai la so nguyen")
    if w < 3 or h < 3 or x < 0 or y < 0:
        raise ValueError("--roi: X,Y >= 0 va W,H >= 3")
    return key, (x, y, w, h)


def resolve_roi(roi, width, height):
    """Doi ROI thanh (x,y,w,h) cu the cho kich thuoc anh, kiem tra bien."""
    if roi is None:
        return (0, 0, width, height)
    if roi == "center":
        return (width // 4, height // 4, width // 2, height // 2)
    x, y, w, h = roi
    if x + w > width or y + h > height:
        raise ValueError("--roi %s vuot khung %dx%d" % (roi, width, height))
    return roi


def crop_roi(g, roi):
    x, y, w, h = roi
    return g[y:y + h, x:x + w]


def parse_ruler(text):
    """'[ID=]x1,y1,x2,y2,mm' -> (id hoac None, dict)."""
    key = None
    body = text.strip()
    if "=" in body:
        key, body = body.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--ruler: ID truoc dau = dang rong")
    parts = body.split(",")
    if len(parts) != 5:
        raise ValueError("--ruler can 5 so x1,y1,x2,y2,mm (co the co ID= dang truoc)")
    try:
        x1, y1, x2, y2 = (float(p) for p in parts[:4])
        mm = float(parts[4])
    except ValueError:
        raise ValueError("--ruler: cac gia tri phai la so")
    # R09: nan/inf qua duoc float() nhung cho ra mm/px = nan hoac 0
    if not all(math.isfinite(v) for v in (x1, y1, x2, y2, mm)):
        raise ValueError("--ruler: cac gia tri phai la so huu han (khong nan/inf)")
    if min(x1, y1, x2, y2) < 0:
        raise ValueError("--ruler: toa do phai >= 0")
    if mm <= 0:
        raise ValueError("--ruler: mm phai > 0")
    px = float(np.hypot(x2 - x1, y2 - y1))
    if px < 1.0:
        raise ValueError("--ruler: hai diem trung nhau, khong tinh duoc")
    return key, {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "mm": mm, "px": px, "mm_per_px": mm / px}


def check_ruler_in_image(ruler, width, height):
    """Hai dau thuoc phai nam trong khung anh; nguoi dung nhap theo pixel nen lech la thuong gap."""
    for k in ("x1", "x2"):
        if ruler[k] > width:
            raise ValueError("--ruler: %s=%.1f vuot be rong anh %d" % (k, ruler[k], width))
    for k in ("y1", "y2"):
        if ruler[k] > height:
            raise ValueError("--ruler: %s=%.1f vuot chieu cao anh %d" % (k, ruler[k], height))


def fov_mm(mm_per_px, width, height):
    return width * mm_per_px, height * mm_per_px


# ----------------------------------------------------------------------
# Doc mot phien capture_session.py.
# ----------------------------------------------------------------------

def resolve_session_dir(text):
    p = Path(text)
    if p.is_dir():
        return p.resolve()
    q = RAW_ROOT / text
    if q.is_dir():
        return q.resolve()
    raise FileNotFoundError("khong thay thu muc phien: %s (da thu ca %s)" % (text, q))


def load_session(session_dir):
    """Tra (meta dict, danh sach (idx, path)) chi gom anh decode_ok theo frames.csv."""
    meta = {"session_id": session_dir.name, "dir": str(session_dir)}
    sj = session_dir / "session.json"
    if sj.is_file():
        try:
            j = json.loads(sj.read_text(encoding="utf-8"))
            meta["framesize"] = (j.get("requested") or {}).get("framesize")
            meta["note"] = j.get("note")
            meta["capture_commit"] = (j.get("source") or {}).get("commit")
            meta["started_at"] = j.get("started_at")
            meta["verdict"] = (j.get("result") or {}).get("verdict")
        except (ValueError, OSError) as e:
            meta["session_json_error"] = str(e)
    else:
        meta["session_json_error"] = "khong co session.json"

    bad = set()
    fc = session_dir / "frames.csv"
    if fc.is_file():
        with fc.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if str(row.get("decode_ok", "True")).strip().lower() != "true":
                    try:
                        bad.add(int(row["idx"]))
                    except (KeyError, ValueError):
                        pass

    images = []
    for p in sorted(session_dir.glob("img_*.jpg")):
        # chi anh duoc chon img_NNNN.jpg; bo qua payload lan thu img_NNNN_tryK.jpg (capture 20/09)
        tail = p.stem[4:]
        if not tail.isdigit():
            continue
        idx = int(tail)
        if idx in bad:
            continue
        images.append((idx, p))
    meta["skipped_decode_fail"] = len(bad)
    return meta, images


def analyze_session(session_dir, roi, ruler=None):
    """Do tung anh cua phien. Tra (summary dict, rows list)."""
    meta, images = load_session(session_dir)
    if not images:
        raise ValueError("%s: khong co anh hop le (img_NNNN.jpg co decode_ok) de do" % meta["session_id"])
    rows = []
    roi_used = None
    width = height = None
    for idx, p in images:
        with Image.open(p) as im:
            im.load()
            w, h = im.size
            g = image_to_gray(im)
            rgb = image_to_rgb(im)
        if width is None:
            width, height = w, h
            roi_used = resolve_roi(roi, w, h)
            if ruler:
                check_ruler_in_image(ruler, w, h)
        elif (w, h) != (width, height):
            raise ValueError("%s: anh %s co kich thuoc %dx%d khac anh dau %dx%d" % (meta["session_id"], p.name, w, h, width, height))
        m = metrics_on_gray(crop_roi(g, roi_used))
        m.update(metrics_rgb_on_roi(crop_roi(rgb, roi_used)))
        row = {
            "session_id": meta["session_id"], "idx": idx, "file": p.name,
            "width": w, "height": h, "roi": "%d,%d,%d,%d" % roi_used,
        }
        row.update(m)
        rows.append(row)

    summary = dict(meta)
    summary["n_images"] = len(rows)
    summary["width"] = width
    summary["height"] = height
    summary["roi"] = list(roi_used) if roi_used else None
    if rows:
        lv = np.array([r["lap_var"] for r in rows])
        ge = np.array([r["grad_energy"] for r in rows])
        summary["lap_var_median"] = float(np.median(lv))
        summary["lap_var_min"] = float(lv.min())
        summary["lap_var_max"] = float(lv.max())
        summary["grad_energy_median"] = float(np.median(ge))
        summary["mean_median"] = float(np.median([r["mean"] for r in rows]))
        summary["std_median"] = float(np.median([r["std"] for r in rows]))
        summary["sat_frac_max"] = float(max(r["sat_frac"] for r in rows))
        summary["dark_frac_max"] = float(max(r["dark_frac"] for r in rows))
        # Vong 5 (L06): RGB - trung vi cho mau/spread, max cho ti le clipping
        # (cung nguyen tac voi sat_frac_max/dark_frac_max o tren: mot anh
        # clipping da la dau hieu can bao, khong trung binh loang no di).
        summary["mean_r_median"] = float(np.median([r["mean_r"] for r in rows]))
        summary["mean_g_median"] = float(np.median([r["mean_g"] for r in rows]))
        summary["mean_b_median"] = float(np.median([r["mean_b"] for r in rows]))
        summary["channel_spread_pct_median"] = float(np.median([r["channel_spread_pct"] for r in rows]))
        summary["dark_frac_rgb_max"] = float(max(r["dark_frac_rgb"] for r in rows))
        summary["sat_frac_rgb_max"] = float(max(r["sat_frac_rgb"] for r in rows))
        # anh dai dien: lap_var gan trung vi nhat
        k = int(np.argmin(np.abs(lv - summary["lap_var_median"])))
        summary["representative"] = rows[k]["file"]
    summary["ruler"] = ruler
    if ruler and width:
        fw, fh = fov_mm(ruler["mm_per_px"], width, height)
        summary["mm_per_px"] = ruler["mm_per_px"]
        summary["fov_w_mm"] = fw
        summary["fov_h_mm"] = fh
    return summary, rows


# ----------------------------------------------------------------------
# Trinh bay va ghi ho so.
# ----------------------------------------------------------------------

def fmt_table(summaries):
    hdr = "%-28s %4s %-9s %12s %12s %12s %7s %6s %7s %10s %9s" % (
        "phien", "n", "kich_thuoc", "lap_var_med", "lap_var_min", "lap_var_max",
        "grad_med", "mean", "sat_max", "mm/px", "fov_w_mm")
    lines = [hdr, "-" * len(hdr)]
    for s in summaries:
        if s.get("n_images", 0) == 0:
            lines.append("%-28s %4d  (khong co anh hop le)" % (s["session_id"], 0))
            continue
        mmpx = "%.4f" % s["mm_per_px"] if s.get("mm_per_px") else "-"
        fov = "%.1f" % s["fov_w_mm"] if s.get("fov_w_mm") else "-"
        lines.append("%-28s %4d %-9s %12.1f %12.1f %12.1f %7.0f %6.1f %7.3f %10s %9s" % (
            s["session_id"], s["n_images"], "%dx%d" % (s["width"], s["height"]),
            s["lap_var_median"], s["lap_var_min"], s["lap_var_max"],
            s["grad_energy_median"], s["mean_median"], s["sat_frac_max"], mmpx, fov))
    return LF.join(lines)


def fmt_details(summaries):
    lines = []
    for s in summaries:
        lines.append("Phien %s" % s["session_id"])
        lines.append("  thu muc      : %s" % s["dir"])
        lines.append("  note         : %s" % (s.get("note") or "-"))
        lines.append("  framesize    : %s, anh %sx%s, ROI x,y,w,h = %s" % (
            s.get("framesize") or "?", s.get("width"), s.get("height"),
            ",".join(str(v) for v in s["roi"]) if s.get("roi") else "-"))
        lines.append("  anh hop le   : %d (bo %d anh decode_ok=False theo frames.csv)" % (s.get("n_images", 0), s.get("skipped_decode_fail", 0)))
        if s.get("session_json_error"):
            lines.append("  session.json : %s" % s["session_json_error"])
        if s.get("n_images"):
            lines.append("  lap_var      : trung vi %.1f, min %.1f, max %.1f" % (s["lap_var_median"], s["lap_var_min"], s["lap_var_max"]))
            lines.append("  grad_energy  : trung vi %.0f" % s["grad_energy_median"])
            lines.append("  do sang ROI  : mean %.1f, std %.1f; bao hoa toi da %.3f, toi toi da %.3f" % (
                s["mean_median"], s["std_median"], s["sat_frac_max"], s["dark_frac_max"]))
            lines.append("  mau RGB ROI  : mean R=%.1f G=%.1f B=%.1f; spread kenh mau %.1f%%; bao hoa/toi bat ky kenh (max) %.3f%% / %.3f%%" % (
                s["mean_r_median"], s["mean_g_median"], s["mean_b_median"], s["channel_spread_pct_median"],
                s["sat_frac_rgb_max"] * 100.0, s["dark_frac_rgb_max"] * 100.0))
            lines.append("  anh dai dien : %s" % s["representative"])
        r = s.get("ruler")
        if r:
            lines.append("  thuoc        : (%.0f,%.0f)-(%.0f,%.0f) = %.1f px = %.1f mm -> %.4f mm/px" % (
                r["x1"], r["y1"], r["x2"], r["y2"], r["px"], r["mm"], r["mm_per_px"]))
            lines.append("  truong nhin  : %.1f x %.1f mm o mat thuoc (gia dinh pixel vuong)" % (s["fov_w_mm"], s["fov_h_mm"]))
        else:
            lines.append("  thuoc        : khong nhap, chua tinh mm/px")
        lines.append("")
    return LF.join(lines)


def annotate(session_dir, summary, out_path):
    """Ve ROI va hai diem thuoc len anh dai dien, ghi JPEG. Khong sua anh goc."""
    src = session_dir / summary["representative"]
    with Image.open(src) as im:
        im.load()
        canvas = im.convert("RGB")
    d = ImageDraw.Draw(canvas)
    x, y, w, h = summary["roi"]
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=(0, 255, 0), width=2)
    d.text((x + 4, y + 4), "ROI %d,%d,%d,%d" % (x, y, w, h), fill=(0, 255, 0))
    r = summary.get("ruler")
    if r:
        d.line([(r["x1"], r["y1"]), (r["x2"], r["y2"])], fill=(255, 0, 0), width=2)
        for px, py in ((r["x1"], r["y1"]), (r["x2"], r["y2"])):
            d.ellipse([px - 4, py - 4, px + 4, py + 4], outline=(255, 0, 0), width=2)
        d.text((min(r["x1"], r["x2"]), max(r["y1"], r["y2"]) + 6),
               "%.0f mm = %.1f px -> %.4f mm/px; FOV %.0f x %.0f mm" % (
                   r["mm"], r["px"], r["mm_per_px"], summary["fov_w_mm"], summary["fov_h_mm"]),
               fill=(255, 0, 0))
    d.text((4, canvas.size[1] - 14), "%s %s lap_var=%.0f" % (summary["session_id"], summary["representative"], summary["lap_var_median"]), fill=(255, 255, 0))
    canvas.save(out_path, format="JPEG", quality=92)
    return out_path


def write_report(out_dir, report, summaries, rows, session_dirs, do_annotate):
    out_dir.mkdir(parents=True, exist_ok=False)
    with (out_dir / "per_image.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in CSV_FIELDS})
    if do_annotate:
        report["annotated"] = []
        for s, sd in zip(summaries, session_dirs):
            if s.get("representative"):
                p = annotate(sd, s, out_dir / ("annotated_%s.jpg" % s["session_id"]))
                report["annotated"].append(p.name)
    report["sessions"] = summaries
    # newline=LF: Path.write_text mac dinh doi LF thanh CRLF tren Windows,
    # trai voi .gitattributes (eol=lf). fmt_details ket thuc bang dong trong
    # nen rstrip de tep khong thua dong trang cuoi (git diff --check bao).
    (out_dir / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + LF, encoding="utf-8", newline=LF)
    text = fmt_table(summaries) + LF + LF + fmt_details(summaries)
    (out_dir / "summary.txt").write_text(text.rstrip() + LF, encoding="utf-8", newline=LF)
    return text


# ----------------------------------------------------------------------
# Selftest, khong can bo va khong can anh that.
# ----------------------------------------------------------------------

def _synthetic_texture(seed=0, size=(320, 240)):
    rng = np.random.RandomState(seed)
    arr = rng.randint(0, 256, size=(size[1], size[0]), dtype=np.uint8)
    return Image.fromarray(arr, mode="L")


def _stripes(size=(320, 240), period=8):
    xs = np.arange(size[0])
    row = ((xs // period) % 2) * 255
    arr = np.tile(row.astype(np.uint8), (size[1], 1))
    return Image.fromarray(arr, mode="L")


def selftest():
    import tempfile
    ok = True

    def check(cond, label):
        nonlocal ok
        print("  %-60s %s" % (label, "OK" if cond else "FAIL"))
        ok = ok and cond

    # 0. R09: dau vao khong the cho so do hop le phai bi tu choi som
    def raises(fn, *a):
        try:
            fn(*a)
            return False
        except ValueError:
            return True
    check(raises(parse_ruler, "0,0,100,0,nan"), "parse_ruler: mm = nan bi tu choi")
    check(raises(parse_ruler, "0,0,inf,0,10"), "parse_ruler: x2 = inf bi tu choi")
    check(raises(parse_ruler, "-5,0,100,0,10"), "parse_ruler: toa do am bi tu choi")
    check(parse_ruler("0,0,100,0,10")[1]["mm_per_px"] == 0.1, "parse_ruler: 100 px = 10 mm -> 0.1 mm/px")
    check(raises(check_ruler_in_image, {"x1": 0, "y1": 0, "x2": 999, "y2": 0}, 320, 240), "check_ruler_in_image: x2 vuot khung bi tu choi")
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "capture_empty"
        empty.mkdir()
        check(raises(analyze_session, empty, None, None), "analyze_session: phien rong -> ValueError, khong tra summary thieu truong")
        (empty / "img_0001_try1.jpg").write_bytes(b"x")
        check(load_session(empty)[1] == [], "load_session: bo qua img_NNNN_tryK.jpg cua lan thu")

    # 1. Anh phang: khong co canh -> hai so do bang 0
    flat = metrics_on_gray(np.full((50, 60), 128.0))
    check(flat["lap_var"] == 0.0 and flat["grad_energy"] == 0.0, "metrics: anh phang cho lap_var = grad_energy = 0")
    check(flat["mean"] == 128.0 and flat["std"] == 0.0, "metrics: anh phang mean 128, std 0")

    # 2. Bao hoa va toi
    check(metrics_on_gray(np.full((10, 10), 255.0))["sat_frac"] == 1.0, "metrics: anh trang sat_frac = 1")
    check(metrics_on_gray(np.zeros((10, 10)))["dark_frac"] == 1.0, "metrics: anh den dark_frac = 1")

    # 2b. RGB (Vong 5, L06): anh xam that -> spread 0; anh am luc -> spread lon;
    # anh den/trang -> phat hien clipping ca ba kenh.
    gray_rgb = np.full((10, 10, 3), 128.0)
    m_gray_rgb = metrics_rgb_on_roi(gray_rgb)
    check(m_gray_rgb["channel_spread_pct"] == 0.0, "metrics_rgb: anh xam that (R=G=B) -> channel_spread_pct = 0")
    check(m_gray_rgb["dark_frac_rgb"] == 0.0 and m_gray_rgb["sat_frac_rgb"] == 0.0, "metrics_rgb: anh xam giua thang -> khong toi, khong bao hoa")

    green_tint = np.zeros((10, 10, 3))
    green_tint[..., 0] = 50.0
    green_tint[..., 1] = 150.0
    green_tint[..., 2] = 50.0
    m_green = metrics_rgb_on_roi(green_tint)
    check(m_green["channel_spread_pct"] > 50.0, "metrics_rgb: anh am luc (G cao hon R/B) -> channel_spread_pct lon (%.1f%%)" % m_green["channel_spread_pct"])
    check(abs(m_green["mean_g"] - 150.0) < 1e-9 and abs(m_green["mean_r"] - 50.0) < 1e-9, "metrics_rgb: mean_r/mean_g doc dung tung kenh")

    black_rgb = np.zeros((10, 10, 3))
    check(metrics_rgb_on_roi(black_rgb)["dark_frac_rgb"] == 1.0, "metrics_rgb: anh den -> dark_frac_rgb = 1")
    white_rgb = np.full((10, 10, 3), 255.0)
    check(metrics_rgb_on_roi(white_rgb)["sat_frac_rgb"] == 1.0, "metrics_rgb: anh trang -> sat_frac_rgb = 1")
    one_channel_sat = np.zeros((10, 10, 3))
    one_channel_sat[..., 1] = 255.0  # chi kenh G bao hoa, R/B binh thuong
    check(metrics_rgb_on_roi(one_channel_sat)["sat_frac_rgb"] == 1.0, "metrics_rgb: chi mot kenh bao hoa (G) van tinh la diem bao hoa")
    check(raises(metrics_rgb_on_roi, np.zeros((10, 10))), "metrics_rgb: mang 2 chieu (khong phai RGB) -> ValueError")

    # 3. Mo dan -> lap_var va grad_energy giam don dieu (nhieu ngau nhien)
    tex = _synthetic_texture()
    seq = [metrics_on_gray(image_to_gray(tex.filter(ImageFilter.GaussianBlur(r))) if r else image_to_gray(tex)) for r in (0, 1, 2, 4)]
    lv = [m["lap_var"] for m in seq]
    ge = [m["grad_energy"] for m in seq]
    check(all(lv[i] > lv[i + 1] for i in range(3)), "blur: lap_var giam don dieu qua radius 0,1,2,4 (%.0f > %.0f > %.0f > %.0f)" % tuple(lv))
    check(all(ge[i] > ge[i + 1] for i in range(3)), "blur: grad_energy giam don dieu qua radius 0,1,2,4")

    # 4. Cung ket luan voi anh soc (gan hoa tiet thuoc mm)
    st = _stripes()
    m_sharp = metrics_on_gray(image_to_gray(st))
    m_blur = metrics_on_gray(image_to_gray(st.filter(ImageFilter.GaussianBlur(2))))
    check(m_sharp["lap_var"] > 2 * m_blur["lap_var"], "stripes: anh net lap_var > 2x anh mo (%.0f vs %.0f)" % (m_sharp["lap_var"], m_blur["lap_var"]))

    # 5. JPEG round-trip van giu thu tu net/mo
    import io as _io
    def jpeg_gray(im, q=90):
        b = _io.BytesIO()
        im.convert("RGB").save(b, format="JPEG", quality=q)
        b.seek(0)
        with Image.open(b) as j:
            return image_to_gray(j)
    check(metrics_on_gray(jpeg_gray(tex))["lap_var"] > metrics_on_gray(jpeg_gray(tex.filter(ImageFilter.GaussianBlur(2))))["lap_var"],
          "jpeg: sau nen JPEG anh net van > anh mo")

    # 6. ROI
    check(parse_roi("10,20,30,40") == (None, (10, 20, 30, 40)), "parse_roi: '10,20,30,40' -> khong ID")
    check(parse_roi("capture_x=10,20,30,40") == ("capture_x", (10, 20, 30, 40)), "parse_roi: 'capture_x=10,20,30,40' -> co ID")
    check(parse_roi("CENTER") == (None, "center") and resolve_roi("center", 640, 480) == (160, 120, 320, 240), "parse_roi: center -> 160,120,320,240 tren VGA")
    check(parse_roi("capture_x=center") == ("capture_x", "center"), "parse_roi: 'capture_x=center'")
    check(parse_roi(None) == (None, None) and resolve_roi(None, 800, 600) == (0, 0, 800, 600), "resolve_roi: None -> toan khung")
    for bad in ("1,2,3", "a,b,c,d", "0,0,2,2", "-1,0,10,10", "=1,2,3,4"):
        try:
            parse_roi(bad)
            check(False, "parse_roi: '%s' phai bao loi" % bad)
        except ValueError:
            check(True, "parse_roi: '%s' bao loi dung" % bad)
    try:
        resolve_roi((600, 0, 100, 100), 640, 480)
        check(False, "resolve_roi: vuot khung phai bao loi")
    except ValueError:
        check(True, "resolve_roi: vuot khung bao loi dung")
    g = np.arange(100.0 * 80).reshape(80, 100)
    check(crop_roi(g, (10, 5, 30, 20)).shape == (20, 30), "crop_roi: (10,5,30,20) -> mang 20x30")

    # 7. Thuoc
    key, r = parse_ruler("0,0,300,400,50")
    check(key is None and abs(r["px"] - 500.0) < 1e-9 and abs(r["mm_per_px"] - 0.1) < 1e-12, "parse_ruler: 3-4-5 -> 500 px, 0.1 mm/px")
    key, r = parse_ruler("capture_x=10,10,110,10,20")
    check(key == "capture_x" and abs(r["mm_per_px"] - 0.2) < 1e-12, "parse_ruler: co ID= -> key va 0.2 mm/px")
    for bad in ("1,2,3,4", "0,0,10,10,0", "5,5,5,5,10", "=1,2,3,4,5", "a,b,c,d,e"):
        try:
            parse_ruler(bad)
            check(False, "parse_ruler: '%s' phai bao loi" % bad)
        except ValueError:
            check(True, "parse_ruler: '%s' bao loi dung" % bad)
    fw, fh = fov_mm(0.25, 640, 480)
    check(fw == 160.0 and fh == 120.0, "fov_mm: 0.25 mm/px tren VGA -> 160 x 120 mm")

    # 8. Phien gia: 3 anh JPEG, frames.csv danh dau anh 2 decode_ok=False
    with tempfile.TemporaryDirectory() as td:
        sd = Path(td) / "capture_test"
        sd.mkdir()
        for i, im in ((1, tex), (2, tex), (3, tex.filter(ImageFilter.GaussianBlur(3)))):
            im.convert("RGB").save(sd / ("img_%04d.jpg" % i), format="JPEG", quality=90)
        (sd / "session.json").write_text(json.dumps({
            "session_id": "capture_test", "requested": {"framesize": "QVGA"}, "note": "selftest",
            "source": {"commit": "0" * 40}, "result": {"verdict": "PASS"}}), encoding="utf-8")
        (sd / "frames.csv").write_text("idx,decode_ok" + LF + "1,True" + LF + "2,False" + LF + "3,True" + LF, encoding="utf-8")
        s, rows = analyze_session(sd, "center", parse_ruler("0,0,320,0,64")[1])
        check(s["n_images"] == 2 and [r["idx"] for r in rows] == [1, 3], "analyze_session: bo anh decode_ok=False, con idx 1 va 3")
        check(s["framesize"] == "QVGA" and s["note"] == "selftest", "analyze_session: doc framesize va note tu session.json")
        check(rows[0]["lap_var"] > rows[1]["lap_var"], "analyze_session: anh net (idx 1) > anh mo (idx 3)")
        check(s["roi"] == [80, 60, 160, 120], "analyze_session: ROI center tren 320x240 = 80,60,160,120")
        check(abs(s["fov_w_mm"] - 64.0) < 1e-9 and abs(s["fov_h_mm"] - 48.0) < 1e-9, "analyze_session: thuoc 320 px = 64 mm -> FOV 64 x 48 mm")
        check(s["representative"] in ("img_0001.jpg", "img_0003.jpg"), "analyze_session: chon duoc anh dai dien")

        # 9. Ghi ho so, tu choi ghi de, anh chu thich
        out = Path(td) / "report"
        report = {"report_id": "selftest", "created_at": now_iso()}
        text = write_report(out, report, [s], rows, [sd], True)
        check((out / "per_image.csv").is_file() and (out / "summary.json").is_file() and (out / "summary.txt").is_file(), "write_report: ba tep ho so co mat")
        with (out / "per_image.csv").open(encoding="utf-8", newline="") as f:
            n = sum(1 for _ in csv.DictReader(f))
        check(n == 2, "write_report: per_image.csv co 2 dong")
        ann = out / "annotated_capture_test.jpg"
        with Image.open(ann) as a:
            check(a.size == (320, 240) and a.format == "JPEG", "annotate: JPEG 320x240 co ve ROI va thuoc")
        check("capture_test" in text and "mm/px" in text, "write_report: summary.txt co ten phien va cot mm/px")
        for name in ("summary.txt", "summary.json"):
            raw = (out / name).read_bytes()
            check(chr(13).encode() not in raw and raw.endswith(LF.encode()) and not raw.endswith((LF + LF).encode()),
                  "write_report: %s dung LF, ket thuc bang dung mot LF" % name)
        try:
            write_report(out, report, [s], rows, [sd], False)
            check(False, "write_report: ghi de phai bao loi")
        except FileExistsError:
            check(True, "write_report: thu muc da co -> FileExistsError, khong ghi de")

    # 10. git_info dung chung voi capture_session
    check(len(git_info().get("commit", "")) == 40, "git_info: doc duoc commit 40 ky tu")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sessions", nargs="*", help="thu muc phien hoac ten phien trong data/raw/")
    ap.add_argument("--roi", action="append", default=[], help="[ID=]X,Y,W,H theo pixel, hoac [ID=]center (giua khung, 1/2 moi chieu); co ID= thi chi ap cho phien do, lap lai cho tung phien; khong ID ap cho moi phien; mac dinh toan khung")
    ap.add_argument("--ruler", action="append", default=[], help="[ID=]x1,y1,x2,y2,mm: hai diem tren thuoc va khoang cach that; lap lai cho tung phien")
    ap.add_argument("--out", help="thu muc goc de ghi ho so, vi du docs/logs; tao thu muc con <report-id> khong ghi de")
    ap.add_argument("--report-id", help="ten thu muc ho so; mac dinh sharpness_YYYYMMDD_HHMMSS")
    ap.add_argument("--annotate", action="store_true", help="cung --out: ghi anh dai dien moi phien co ve ROI va thuoc")
    ap.add_argument("--selftest", action="store_true", help="chay kiem tra noi bo, khong can anh that")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.sessions:
        ap.error("can it nhat mot phien (hoac --selftest)")
    if args.annotate and not args.out:
        ap.error("--annotate can di cung --out")

    try:
        roi_default, rois = None, {}
        for text in args.roi:
            key, r = parse_roi(text)
            if key is None:
                if roi_default is not None:
                    ap.error("--roi khong co ID= chi duoc mot lan")
                roi_default = r
            else:
                rois[key] = r
        rulers = {}
        for text in args.ruler:
            key, r = parse_ruler(text)
            if key is None:
                if len(args.sessions) != 1:
                    ap.error("--ruler khong co ID= chi dung khi co dung mot phien; co %d phien" % len(args.sessions))
                key = Path(args.sessions[0]).name
            rulers[key] = r
        session_dirs = [resolve_session_dir(s) for s in args.sessions]
    except (ValueError, FileNotFoundError) as e:
        print("Loi tham so:", e)
        return 2

    known = {d.name for d in session_dirs}
    for label, keyed in (("--ruler", rulers), ("--roi", rois)):
        for key in keyed:
            if key not in known:
                print("Loi tham so: %s cho '%s' nhung khong co phien nao ten do (co: %s)" % (label, key, ", ".join(sorted(known))))
                return 2

    summaries, rows = [], []
    for sd in session_dirs:
        try:
            s, r = analyze_session(sd, rois.get(sd.name, roi_default), rulers.get(sd.name))
        except (ValueError, OSError) as e:
            print("Loi khi do phien %s: %s" % (sd.name, e))
            return 3
        summaries.append(s)
        rows.extend(r)

    print(fmt_table(summaries))
    print()
    print(fmt_details(summaries))

    if args.out:
        report_id = args.report_id or datetime.now().strftime("sharpness_%Y%m%d_%H%M%S")
        out_dir = (REPO_ROOT / args.out / report_id).resolve()
        if out_dir.exists():
            print("Thu muc ho so da ton tai, khong ghi de:", out_dir)
            return 4
        report = {
            "report_id": report_id,
            "created_at": now_iso(),
            "script": "pc/sharpness.py",
            "source": git_info(),
            "args": {"roi": args.roi, "ruler": args.ruler, "sessions": args.sessions},
        }
        write_report(out_dir, report, summaries, rows, session_dirs, args.annotate)
        print("Da ghi ho so:", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
