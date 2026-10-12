#!/usr/bin/env python3
"""Tester C3 - kiem doc lap pc/line_extract.py (handoff/2026-09-21_c3-line-extract).

Tester viet, khong dung bo sinh anh cua selftest Coder: vach nghieng (tam roi
vao moi pha phan so), cuong do tich phan Gauss tren dien tich pixel, nen co
van va nhieu doc lap o CA anh OFF lan ON, mot bien the nen JPEG.

Chay tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/test_line_extract.py
Thoat 0 khi khong co kich ban FAIL. Kich ban NOTE la ghi nhan, khong tinh FAIL.
Moi tep tam nam trong mot thu muc tam rieng (in ra dau chay); khong cham data/.
"""
import csv
import hashlib
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
LE = str(REPO / "pc" / "line_extract.py")
sys.path.insert(0, str(REPO / "pc"))
import line_extract as le  # noqa: E402

HEADER = ["row_y", "center_x_px", "valid", "reason", "width_px"]
# "edge" them tu Vong 5 theo R03 cua Reviewer (SCAN_SESSION.md muc 2 da cap nhat)
REASONS = {"ok", "no_signal", "weak", "saturated", "wide", "ambiguous", "edge"}
TMP = Path(tempfile.mkdtemp(prefix="tester_c3_"))
_erf = np.vectorize(math.erf)
SUMMARY = []


class Sc:
    def __init__(self, sid, title, note_only=False):
        self.sid, self.title, self.note_only = sid, title, note_only
        self.fails, self.notes = [], []
        print("\n---- %s %s" % (sid, title))

    def ok(self, cond, label, actual=""):
        print("  [%s] %s%s" % ("OK  " if cond else "FAIL", label, ("  | " + str(actual)) if actual != "" else ""))
        if not cond:
            self.fails.append(label)
        return cond

    def note(self, label, actual=""):
        print("  [NOTE] %s%s" % (label, ("  | " + str(actual)) if actual != "" else ""))
        self.notes.append(label)

    def done(self):
        st = "FAIL" if self.fails else ("NOTE" if self.note_only else "PASS")
        SUMMARY.append((self.sid, st, self.title))
        print("==== %s %s" % (self.sid, st))


# ------------------------------------------------------------------ du lieu tong hop (Tester)
def line_profile(xs, c, fwhm, amp):
    """Gauss tich phan tren dien tich pixel [x-0.5, x+0.5]; tam pixel i o toa do i."""
    s = max(fwhm / 2.3548, 0.3)
    k = s * math.sqrt(2.0)
    return amp * s * math.sqrt(math.pi / 2.0) * (_erf((xs + 0.5 - c) / k) - _erf((xs - 0.5 - c) / k))


def make_pair(w=640, h=480, lines=(), noise=2.0, seed=1, rows=None, sat_to=None):
    """lines: list (c_mid, slope, fwhm, amp); tam hang y = c_mid + slope*(y - h/2).
    rows: (ya, yb) chi co vach trong [ya, yb). Tra ve (off_img, on_img, truth_fn)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    scene = 45.0 + 25.0 * np.sin(xx / 37.0) + 15.0 * np.cos(yy / 23.0)
    off = np.stack([scene, scene * 0.9, scene * 0.8], axis=2) + rng.normal(0, noise, (h, w, 3))
    on = np.stack([scene, scene * 0.9, scene * 0.8], axis=2) + rng.normal(0, noise, (h, w, 3))
    ya, yb = rows if rows else (0, h)
    for (cm, slope, fwhm, amp) in lines:
        half = int(3 * fwhm + 6)
        for y in range(ya, yb):
            c = cm + slope * (y - h / 2.0)
            x_lo, x_hi = max(0, int(c) - half), min(w, int(c) + half + 1)
            xs = np.arange(x_lo, x_hi, dtype=float)
            p = line_profile(xs, c, fwhm, amp)
            on[y, x_lo:x_hi, 0] += p
            on[y, x_lo:x_hi, 1] += 0.25 * p
            if sat_to is not None:
                on[y, x_lo:x_hi, 0] = np.where(p > 0.5 * amp, sat_to, on[y, x_lo:x_hi, 0])
    off = np.clip(np.round(off), 0, 255).astype(np.uint8)
    on = np.clip(np.round(on), 0, 255).astype(np.uint8)
    cm0, sl0 = (lines[0][0], lines[0][1]) if lines else (None, None)
    truth = (lambda y: cm0 + sl0 * (y - h / 2.0)) if lines else None
    return Image.fromarray(off, "RGB"), Image.fromarray(on, "RGB"), truth


def save_pair(tag, off_img, on_img, q=92):
    d = TMP / tag
    d.mkdir(parents=True, exist_ok=True)
    po, pn = d / "img_0000_off.jpg", d / "img_0000_on.jpg"
    off_img.save(po, quality=q)
    on_img.save(pn, quality=q)
    return po, pn


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cli(*args):
    r = subprocess.run([PY, LE] + [str(a) for a in args], cwd=REPO, capture_output=True, text=True, errors="replace")
    return r.returncode, r.stdout, r.stderr


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        head = next(rd)
        return head, [row for row in rd]


def snapshot(d):
    return {str(p.relative_to(d)): sha(p) for p in sorted(Path(d).rglob("*")) if p.is_file()}


def errors_vs_truth(rows, truth):
    return [abs(float(r["center_x_px"]) - truth(int(r["row_y"]))) for r in rows if r["valid"] == "true"]


# ------------------------------------------------------------------ T1
def t1():
    s = Sc("T1", "vach sach nghieng (moi pha phan so), FWHM 4 px, JPEG q92, CLI dau-cuoi")
    off, on, truth = make_pair(lines=[(320.0, 0.037, 4.0, 150.0)], seed=11)
    po, pn = save_pair("t1", off, on)
    h_off, h_on = sha(po), sha(pn)
    out_csv, out_png = TMP / "t1" / "centers_0000.csv", TMP / "t1" / "annotated_0000.png"
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,60,540,420", "--csv", out_csv, "--annotate", out_png)
    s.ok(rc == 0, "rc 0", (rc, se.strip()[-200:]))
    s.ok(sha(po) == h_off and sha(pn) == h_on, "hash hai JPEG dau vao khong doi")
    head, rows = read_csv(out_csv)
    s.ok(head == HEADER, "header CSV dung 5 cot, dung thu tu", head)
    s.ok(len(rows) == 360 and [int(r[0]) for r in rows] == list(range(60, 420)), "moi hang ROI dung 1 dong, row_y 60..419 theo thu tu", len(rows))
    s.ok(all(len(r) == 5 for r in rows), "moi dong dung 5 truong")
    s.ok(all(r[2] in ("true", "false") and r[3] in REASONS for r in rows), "valid true/false, reason thuoc tap ma on dinh")
    val = [r for r in rows if r[2] == "true"]
    s.ok(all(r[3] == "ok" for r in val) and all(r[3] != "ok" for r in rows if r[2] == "false"), "valid=true <=> reason=ok")
    s.ok(all(math.isfinite(float(r[1])) and 100 <= float(r[1]) < 540 for r in val), "tam huu han, nam trong ROI [100,540)")
    s.ok(all(r[1] == "" for r in rows if r[2] == "false"), "hang invalid: center_x_px de trong")
    s.ok(all(r[4] == "" or r[4].isdigit() for r in rows), "width_px la so nguyen hoac trong")
    pct = 100.0 * len(val) / len(rows)
    errs = [abs(float(r[1]) - truth(int(r[0]))) for r in val]
    med = float(np.median(errs))
    s.ok(pct >= 90.0, ">= 90% hang ROI hop le", "%.1f%%" % pct)
    s.ok(med <= 0.1, "trung vi sai so tuyet doi <= 0.1 px", "%.4f px (p95 %.4f, max %.4f)" % (med, np.percentile(errs, 95), max(errs)))
    im = Image.open(out_png)
    s.ok(out_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and im.size == (640, 480), "PNG chu thich rieng, dung kich thuoc", (im.format, im.size))
    s.ok("100" in so and "540" in so and "min_diff" in so and "max_width" in so and "sat_thresh" in so, "stdout ghi ROI va nguong da dung")
    s.done()


# ------------------------------------------------------------------ T2
def matrix_row(fwhm, reps, noise=2.0, jpeg_q=None, amp=150.0, seed0=1000):
    x0, y0, x1, y1 = 150, 100, 450, 380
    n = y1 - y0
    cent = np.full((n, reps), np.nan)
    errs = []
    for k in range(reps):
        off, on, truth = make_pair(lines=[(300.0, 0.037, fwhm, amp)], noise=noise, seed=seed0 + k)
        if jpeg_q:
            po, pn = save_pair("t2j_%d" % k, off, on, q=jpeg_q)
            off, on = Image.open(po), Image.open(pn)
            off.load(); on.load()
        rows = le.extract_laser_centers(off, on, x0, y0, x1, y1, 20.0, 30, 250.0)
        assert len(rows) == n
        for i, r in enumerate(rows):
            if r["valid"] == "true":
                c = float(r["center_x_px"])
                cent[i, k] = c
                errs.append(abs(c - truth(int(r["row_y"]))))
    vm = ~np.isnan(cent)
    all_rows = np.where(vm.all(axis=1))[0]
    sig = [np.std(cent[i], ddof=1) for i in all_rows]
    return {
        "valid_pct": 100.0 * vm.mean(), "common": len(all_rows),
        "med_err": float(np.median(errs)) if errs else float("nan"),
        "p95_err": float(np.percentile(errs, 95)) if errs else float("nan"),
        "med_sig": float(np.median(sig)) if sig else float("nan"),
    }


def t2a():
    s = Sc("T2a", "ma tran FWHM 1/2/4/6 px x 30 lan, nhieu 2, vach nghieng, bo sinh anh cua Tester (khong nen)")
    print("  ROI [150,450)x[100,380) 280 hang; min_diff 20, max_width 30, sat_thresh 250; seed 1000..1029; bien do 150")
    print("  %6s | %4s | %10s | %9s | %12s | %12s | %13s" % ("FWHM", "lap", "hop le %", "hang chung", "sai so TV", "sai so p95", "sigma n-1 TV"))
    for fw in (1.0, 2.0, 4.0, 6.0):
        m = matrix_row(fw, 30)
        print("  %6.1f | %4d | %9.2f%% | %9d | %12.4f | %12.4f | %13.4f" % (fw, 30, m["valid_pct"], m["common"], m["med_err"], m["p95_err"], m["med_sig"]))
        s.ok(m["common"] >= 0, "FWHM %.0f: bang du, khong ngoai le" % fw)
    s.note("T2 khong co nguong dat/khong dat (ke hoach): chi bao so; so sanh voi bang selftest Coder o 03_TEST")
    s.done()


def t2a_jpeg():
    s = Sc("T2a-jpeg", "FWHM 4 px x 30 lan qua nen JPEG (Pillow q75, ca OFF lan ON)")
    m = matrix_row(4.0, 30, jpeg_q=75, seed0=2000)
    print("  hop le %.2f%%, hang chung %d, sai so TV %.4f px (p95 %.4f), sigma n-1 TV %.4f px" % (m["valid_pct"], m["common"], m["med_err"], m["p95_err"], m["med_sig"]))
    s.ok(m["valid_pct"] > 0, "chay het 30 lan qua JPEG, khong ngoai le")
    s.note("chi bao so; JPEG cua S3 (quality 10-20) khac Pillow q75")
    s.done()


def t2b():
    s = Sc("T2b", "tam sat mep ROI va sat mep anh: khong truy cap ngoai anh, tam trong ROI")
    cases = [("sat mep trai ROI", 150.3, (150, 100, 450, 380)), ("sat mep phai ROI", 448.7, (150, 100, 450, 380)),
             ("sat mep trai anh, ROI toan anh", 0.4, (0, 0, 640, 480)), ("sat mep phai anh, ROI toan anh", 639.6, (0, 0, 640, 480))]
    for name, c, (x0, y0, x1, y1) in cases:
        off, on, truth = make_pair(lines=[(c, 0.0, 3.0, 150.0)], seed=31)
        try:
            rows = le.extract_laser_centers(off, on, x0, y0, x1, y1, 20.0, 30, 250.0)
            exc = None
        except Exception as e:  # noqa: BLE001
            rows, exc = [], repr(e)
        s.ok(exc is None and len(rows) == y1 - y0, "%s: khong ngoai le, dung %d dong" % (name, y1 - y0), exc or len(rows))
        val = [r for r in rows if r["valid"] == "true"]
        s.ok(all(x0 <= float(r["center_x_px"]) < x1 for r in val), "%s: tam hop le nam trong ROI" % name)
        e = errors_vs_truth(rows, truth)
        s.note("%s: hop le %d/%d, sai so TV %s px (lech do cat vach o mep - chi bao)" % (name, len(val), len(rows), "%.3f" % np.median(e) if e else "-"))
    s.done()


def t2c():
    s = Sc("T2c", "ROI suy bien: 1 hang, 1 cot, 1x1, goc duoi-phai, toan anh")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=41)
    for name, roi in [("1 hang", (100, 200, 540, 201)), ("1 cot tai tam vach", (320, 0, 321, 480)), ("1x1", (5, 5, 6, 6)),
                      ("goc duoi-phai 1x1", (639, 479, 640, 480)), ("toan anh", (0, 0, 640, 480))]:
        try:
            rows = le.extract_laser_centers(off, on, *roi, 20.0, 30, 250.0)
            s.ok(len(rows) == roi[3] - roi[1], "%s: dung %d dong, khong ngoai le" % (name, roi[3] - roi[1]), len(rows))
        except Exception as e:  # noqa: BLE001
            s.ok(False, "%s: khong ngoai le" % name, repr(e))
    s.done()


# ------------------------------------------------------------------ T3 (CLI)
def t3():
    s = Sc("T3", "loi dau vao qua CLI: rc != 0, thong bao chi ro, khong tao/ghi de tep ket qua")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=51)
    po, pn = save_pair("t3", off, on)
    small = TMP / "t3" / "small.jpg"
    off.resize((320, 240)).save(small, quality=92)
    txt = TMP / "t3" / "not_image.jpg"; txt.write_text("khong phai jpeg", encoding="utf-8")
    empty = TMP / "t3" / "empty.jpg"; empty.write_bytes(b"")
    trunc = TMP / "t3" / "truncated.jpg"; trunc.write_bytes(pn.read_bytes()[: len(pn.read_bytes()) * 6 // 10])
    cases = [
        ("OFF/ON khac kich thuoc", ["--off", small, "--on", pn], "kich thuoc"),
        ("tep khong phai anh", ["--off", txt, "--on", pn], "anh"),
        ("tep rong 0 byte", ["--off", empty, "--on", pn], "anh"),
        ("JPEG cut cut 60%", ["--off", po, "--on", trunc], "anh"),
        ("tep khong ton tai", ["--off", TMP / "t3" / "khong_co.jpg", "--on", pn], "khong ton tai"),
        ("ROI x0 == x1 (rong)", ["--off", po, "--on", pn, "--roi", "100,50,100,400"], "x0"),
        ("ROI y0 == y1 (rong)", ["--off", po, "--on", pn, "--roi", "100,50,500,50"], "y0"),
        ("ROI vuot phai", ["--off", po, "--on", pn, "--roi", "100,50,641,400"], "x1"),
        ("ROI vuot duoi", ["--off", po, "--on", pn, "--roi", "100,50,500,481"], "y1"),
        # dang '--roi=...' vi argparse hieu '-1,...' la mot tuy chon neu tach rieng
        ("ROI am", ["--off", po, "--on", pn, "--roi=-1,50,500,400"], "am"),
        ("ROI 3 so", ["--off", po, "--on", pn, "--roi", "1,2,3"], "4 so"),
        ("ROI khong phai so nguyen", ["--off", po, "--on", pn, "--roi", "1.5,2,300,400"], "so nguyen"),
        ("min_diff am", ["--off", po, "--on", pn, "--min-diff", "-1"], "min_diff"),
        ("min_diff nan", ["--off", po, "--on", pn, "--min-diff", "nan"], "min_diff"),
        ("min_diff inf", ["--off", po, "--on", pn, "--min-diff", "inf"], "min_diff"),
        ("sat_thresh -1", ["--off", po, "--on", pn, "--sat-thresh", "-1"], "sat_thresh"),
        ("sat_thresh 256", ["--off", po, "--on", pn, "--sat-thresh", "256"], "sat_thresh"),
        ("sat_thresh nan", ["--off", po, "--on", pn, "--sat-thresh", "nan"], "sat_thresh"),
        # Vong 5 (R06): sat_thresh 0 va sat_thresh <= min_diff la to hop vo ly
        ("sat_thresh 0", ["--off", po, "--on", pn, "--sat-thresh", "0"], "sat_thresh"),
        ("sat_thresh = min_diff (30/30)", ["--off", po, "--on", pn, "--min-diff", "30", "--sat-thresh", "30"], "sat_thresh"),
        ("max_width 0", ["--off", po, "--on", pn, "--max-width", "0"], "max_width"),
        ("max_width am", ["--off", po, "--on", pn, "--max-width", "-3"], "max_width"),
        ("--csv trung anh ON", ["--off", po, "--on", pn, "--csv", pn], "trung"),
        ("--annotate trung anh OFF", ["--off", po, "--on", pn, "--annotate", po], "trung"),
    ]
    for i, (name, args, kw) in enumerate(cases):
        out = TMP / "t3" / ("out_%02d.csv" % i)  # moi ca mot tep rieng de mot ca lot khong lam lech ca sau
        before = snapshot(TMP / "t3")
        rc, so, se = cli(*(args + (["--csv", out] if "--csv" not in [str(a) for a in args] else [])))
        after = snapshot(TMP / "t3")
        msg = (se.strip().splitlines() or [""])[-1]
        s.ok(rc != 0 and kw.lower() in msg.lower(), "%s: rc != 0, thong bao co '%s'" % (name, kw), "rc %s | %s" % (rc, msg[:150]))
        s.ok(before == after, "%s: khong tao/ghi de tep nao" % name)
    # tep dau ra da ton tai, khong --force
    for flag, fname in (("--csv", "exist.csv"), ("--annotate", "exist.png")):
        p = TMP / "t3" / fname
        p.write_text("du lieu cu", encoding="utf-8")
        rc, so, se = cli("--off", po, "--on", pn, flag, p)
        s.ok(rc != 0 and p.read_text(encoding="utf-8") == "du lieu cu", "%s da ton tai, khong --force: rc != 0, tep cu nguyen" % flag, rc)
    s.done()


# ------------------------------------------------------------------ T4
def rows_for(off, on, roi, **kw):
    return le.extract_laser_centers(off, on, *roi, kw.get("min_diff", 20.0), kw.get("max_width", 30), kw.get("sat_thresh", 250.0))


def t4():
    s = Sc("T4", "tin hieu mo phong: dung reason, khong trung binh hai nhanh, hieu am ve 0")
    roi = (100, 50, 540, 430)
    # a. cung mot tep cho OFF va ON (CLI)
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=61)
    po, pn = save_pair("t4", off, on)
    c = TMP / "t4" / "same.csv"
    rc, so, se = cli("--off", pn, "--on", pn, "--roi", "100,50,540,430", "--csv", c)
    _, rr = read_csv(c)
    s.ok(rc == 0 and all(r[2] == "false" and r[3] == "no_signal" for r in rr), "OFF = ON (cung tep): moi hang no_signal", (rc, sorted({r[3] for r in rr})))
    # b. hai tep noi dung giong het
    p2 = TMP / "t4" / "copy_on.jpg"; p2.write_bytes(pn.read_bytes())
    c2 = TMP / "t4" / "same2.csv"
    rc, so, se = cli("--off", p2, "--on", pn, "--roi", "100,50,540,430", "--csv", c2)
    _, rr = read_csv(c2)
    s.ok(rc == 0 and all(r[3] == "no_signal" for r in rr), "OFF = ON (hai tep giong het): moi hang no_signal", sorted({r[3] for r in rr}))
    # c. vach yeu
    off, on, _ = make_pair(lines=[(320.0, 0.0, 4.0, 12.0)], noise=0.0, seed=62)
    r = rows_for(off, on, roi)
    s.ok(all(x["valid"] == "false" for x in r) and {x["reason"] for x in r} <= {"weak", "no_signal"} and any(x["reason"] == "weak" for x in r),
         "vach yeu (bien do 12 < min_diff 20): khong hang nao hop le, co 'weak'", sorted({x["reason"] for x in r}))
    # d. bao hoa
    off, on, _ = make_pair(lines=[(320.0, 0.0, 5.0, 200.0)], seed=63, sat_to=255)
    r = rows_for(off, on, roi)
    s.ok(all(x["reason"] == "saturated" and x["valid"] == "false" for x in r), "bao hoa (R_on = 255 o dinh): moi hang saturated", sorted({x["reason"] for x in r}))
    # e. qua rong
    off, on, _ = make_pair(lines=[(320.0, 0.0, 40.0, 150.0)], seed=64)
    r = rows_for(off, on, roi)
    s.ok(all(x["reason"] == "wide" and x["valid"] == "false" and x["width_px"] != "" and int(x["width_px"]) > 30 for x in r),
         "qua rong (FWHM 40 > max_width 30): moi hang wide, width_px > 30", sorted({x["reason"] for x in r}))
    # f. hai nhanh ngang suc suot ROI
    off, on, _ = make_pair(lines=[(250.0, 0.0, 3.0, 150.0), (330.0, 0.0, 3.0, 150.0)], seed=65)
    r = rows_for(off, on, roi)
    s.ok(all(x["reason"] == "ambiguous" and x["center_x_px"] == "" for x in r), "hai nhanh ngang suc: moi hang ambiguous, tam trong", sorted({x["reason"] for x in r}))
    s.ok(not any(x["valid"] == "true" and abs(float(x["center_x_px"]) - 290.0) < 5 for x in r), "khong co tam nao gan trung diem hai nhanh (x=290)")
    # g. hieu am
    for o, n_, exp in (((100, 50, 50), (40, 50, 50), 0), ((255, 0, 0), (0, 0, 0), 0), ((0, 0, 0), (255, 0, 0), 255)):
        d, _ = le.compute_red_difference(Image.new("RGB", (8, 4), o), Image.new("RGB", (8, 4), n_))
        s.ok(int(d.min()) == exp and int(d.max()) == exp, "R_off=%d R_on=%d -> hieu %d (khong cuon so)" % (o[0], n_[0], exp), (int(d.min()), int(d.max())))
    # h. nhanh phan xa xuat hien giua ROI, cach vach chinh 40 px, ngang suc: chon nhanh lien tuc
    off, on, truth = make_pair(lines=[(300.0, 0.02, 3.0, 150.0)], seed=66)
    off2, on2, _ = make_pair(lines=[(300.0, 0.02, 3.0, 150.0), (340.0, 0.02, 3.0, 150.0)], seed=66, rows=(240, 430))
    on_mix = np.asarray(on).copy(); on_mix[240:430] = np.asarray(on2)[240:430]
    r = rows_for(off, Image.fromarray(on_mix), roi)
    lower = [x for x in r if int(x["row_y"]) >= 240]
    val = [x for x in lower if x["valid"] == "true"]
    s.ok(len(val) >= 0.9 * len(lower) and all(abs(float(x["center_x_px"]) - truth(int(x["row_y"]))) < 0.5 for x in val),
         "nhanh phan xa tu hang 240: chon nhanh lien tuc voi hang truoc (>= 90% hop le, tam sat vach chinh)",
         "%d/%d hop le, reasons %s" % (len(val), len(lower), sorted({x["reason"] for x in lower})))
    # i. nhanh phu yeu (25%)
    off, on, truth = make_pair(lines=[(300.0, 0.0, 3.0, 150.0), (360.0, 0.0, 3.0, 37.0)], seed=67)
    r = rows_for(off, on, roi)
    val = [x for x in r if x["valid"] == "true"]
    s.ok(len(val) >= 0.9 * len(r) and all(abs(float(x["center_x_px"]) - 300.0) < 0.5 for x in val), "nhanh phu yeu 25%: chon nhanh chinh", "%d/%d" % (len(val), len(r)))
    s.done()


# ------------------------------------------------------------------ TX: kich ban them cua Tester
def tx1():
    s = Sc("TX1", "--csv va --annotate cung mot duong dan (hai tep ket qua de len nhau)")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=71)
    po, pn = save_pair("tx1", off, on)
    same = TMP / "tx1" / "ket_qua.out"
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--csv", same, "--annotate", same)
    head = same.read_bytes()[:16] if same.exists() else b""
    csv_intact = head.startswith(b"row_y,")
    s.ok(rc != 0 or csv_intact, "phai tu choi (rc != 0) hoac khong duoc de CSV bi PNG ghi de",
         "rc %s, tep dau ra bat dau bang %r" % (rc, head[:8]))
    s.done()


def tx2():
    s = Sc("TX2", "--force: ke hoach muc 4 buoc 3 'khong ghi de CSV/PNG da ton tai'")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=72)
    po, pn = save_pair("tx2", off, on)
    old_csv = TMP / "tx2" / "centers_0000.csv"; old_csv.write_text("ket qua lan truoc\n", encoding="utf-8")
    other_raw = TMP / "tx2" / "img_0001_on.jpg"; on.save(other_raw, quality=92)  # anh tho KHAC, khong phai dau vao
    h_raw = sha(other_raw)
    rc1, _, _ = cli("--off", po, "--on", pn, "--csv", old_csv, "--force")
    s.ok(old_csv.read_text(encoding="utf-8") == "ket qua lan truoc\n", "CSV da ton tai + --force: khong duoc ghi de", "rc %s, noi dung dau: %r" % (rc1, old_csv.read_text(encoding="utf-8")[:20]))
    rc2, _, _ = cli("--off", po, "--on", pn, "--annotate", other_raw, "--force")
    s.ok(sha(other_raw) == h_raw, "--annotate tro vao mot anh tho khac + --force: anh tho phai nguyen", "rc %s, anh tho %s" % (rc2, "NGUYEN" if sha(other_raw) == h_raw else "BI GHI DE thanh PNG"))
    # --force khong duoc vuot rao dau ra == dau vao, ke ca viet khac chu hoa/thuong va '..'
    for name, p in (("chu HOA", Path(str(pn).upper())), ("co '..'", pn.parent / ".." / pn.parent.name / pn.name)):
        h = sha(pn)
        rc, _, se = cli("--off", po, "--on", pn, "--csv", p, "--force")
        s.ok(rc != 0 and sha(pn) == h, "--csv = anh ON viet %s + --force: tu choi, anh ON nguyen" % name, "rc %s" % rc)
    s.done()


def tx3():
    s = Sc("TX3", "--min-diff 0 voi OFF = ON, ROI hep 20 px: khong duoc bia tam hop le")
    off, on, _ = make_pair(lines=[], seed=73)
    po, pn = save_pair("tx3", off, on)
    c = TMP / "tx3" / "c.csv"
    rc, so, se = cli("--off", pn, "--on", pn, "--roi", "300,50,320,430", "--min-diff", "0", "--csv", c)
    if rc == 0:
        _, rr = read_csv(c)
        nv = sum(1 for r in rr if r[2] == "true")
        s.ok(nv == 0, "khong co hang hop le khi khong co tin hieu", "rc 0, %d/%d hang valid=true, vi du tam %s" % (nv, len(rr), rr[0][1] if rr else "-"))
    else:
        s.ok(True, "min_diff 0 bi tu choi", se.strip()[-120:])
    s.done()


def tx4():
    s = Sc("TX4", "sat_thresh nan voi vach bao hoa (anh huong cua viec nhan nan)", note_only=True)
    off, on, _ = make_pair(lines=[(320.0, 0.0, 5.0, 200.0)], seed=74, sat_to=255)
    r = rows_for(off, on, (100, 50, 540, 430), sat_thresh=float("nan"))
    s.note("sat_thresh=nan qua ham: phan bo reason", sorted({(x["reason"]) for x in r}))
    r2 = rows_for(off, on, (100, 50, 540, 430), min_diff=float("nan"))
    s.note("min_diff=nan qua ham: phan bo reason", sorted({(x["reason"]) for x in r2}))
    s.done()


def tx5():
    s = Sc("TX5", "OFF anh xam (L), ON anh mau: ke hoach Vong 1 buoc 1 co 'kiem cung che do'", note_only=True)
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=75)
    d = TMP / "tx5"; d.mkdir(exist_ok=True)
    po = d / "off_L.jpg"; off.convert("L").save(po, quality=92)
    pn = d / "on_RGB.jpg"; on.save(pn, quality=92)
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--csv", d / "c.csv")
    s.note("OFF 'L' + ON 'RGB': rc %s (rc 0 = khong kiem che do anh; Vong 5 xem TX17)" % rc, (se.strip() or so.strip().splitlines()[-1])[-120:])
    s.done()


def tx6():
    s = Sc("TX6", "tham so/ROI co duoc ghi ra tep cung ket qua khong (SCAN_SESSION: params.json canh centers_*.csv)", note_only=True)
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=76)
    po, pn = save_pair("tx6", off, on)
    outd = TMP / "tx6" / "run"
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--min-diff", "17", "--csv", outd / "centers_0000.csv")
    files = sorted(p.name for p in outd.iterdir())
    txt = (outd / "centers_0000.csv").read_text(encoding="utf-8")
    s.note("tep tao ra: %s; CSV co chua '17'/ROI: %s; stdout co tham so: %s" % (files, "17" in txt.splitlines()[0], "min_diff=17" in so))
    s.done()


def tx7():
    s = Sc("TX7", "loi o buoc ghi PNG sau khi da ghi CSV: co de lai CSV do dang khong", note_only=True)
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=77)
    po, pn = save_pair("tx7", off, on)
    blocker = TMP / "tx7" / "la_tep"; blocker.write_text("x", encoding="utf-8")
    c = TMP / "tx7" / "c.csv"
    rc, so, se = cli("--off", po, "--on", pn, "--csv", c, "--annotate", blocker / "a.png")
    s.note("rc %s; CSV con lai sau loi: %s; thong bao: %s" % (rc, c.exists(), (se.strip().splitlines() or [""])[-1][:120]))
    s.done()


def tx8():
    s = Sc("TX8", "thoi gian chay CLI (ROI toan anh)", note_only=True)
    for (w, h) in ((640, 480), (800, 600), (1600, 1200)):
        off, on, _ = make_pair(w=w, h=h, lines=[(w / 2.0, 0.03, 4.0, 150.0)], seed=78)
        po, pn = save_pair("tx8_%d" % w, off, on)
        t = time.perf_counter(); rc, so, se = cli("--off", po, "--on", pn, "--csv", TMP / ("tx8_%d" % w) / "c.csv"); dt = time.perf_counter() - t
        s.note("%dx%d: rc %s, %.2f s / cap (ke ca khoi dong Python)" % (w, h, rc, dt))
    s.done()


def tx9():
    s = Sc("TX9", "hang mat vach nhung co mot dom sang le xa vach: co bi nhan la tam hop le khong", note_only=True)
    off, on, truth = make_pair(lines=[(300.0, 0.0, 3.0, 150.0)], seed=79)
    a = np.asarray(on).copy()
    a[200, 280:321, 0] = np.asarray(off)[200, 280:321, 0]  # xoa vach o hang 200
    a[200, 420:424, 0] = 230  # dom sang le cach 120 px
    r = rows_for(off, Image.fromarray(a), (100, 50, 540, 430))
    row = [x for x in r if x["row_y"] == "200"][0]
    s.note("hang 200: valid=%s reason=%s center=%s (vach that o 300)" % (row["valid"], row["reason"], row["center_x_px"]))
    s.done()


def tx10():
    s = Sc("TX10", "quy uoc toa do tam pixel: vach doi xung tam dung pixel 300", note_only=True)
    off, on, _ = make_pair(lines=[(300.0, 0.0, 4.0, 150.0)], noise=0.0, seed=80)
    r = rows_for(off, on, (100, 50, 540, 430))
    c = float(np.median([float(x["center_x_px"]) for x in r if x["valid"] == "true"]))
    s.note("tam do duoc %.4f -> quy uoc 'tam pixel i o toa do i' (khong phai i+0.5); tai lieu: xem TX19" % c)
    s.done()


def tx11():
    s = Sc("TX11", "JPEG co du lieu thua sau FFD9 (nhu anh S3 ngay 28/09)")
    off, on, truth = make_pair(lines=[(320.0, 0.03, 4.0, 150.0)], seed=81)
    po, pn = save_pair("tx11", off, on)
    pn.write_bytes(pn.read_bytes() + os.urandom(1678) + b"\xff\xd9")
    c = TMP / "tx11" / "c.csv"
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--csv", c)
    ok = rc == 0
    if ok:
        _, rr = read_csv(c)
        v = [r for r in rr if r[2] == "true"]
        ok = len(v) >= 0.9 * len(rr)
    s.ok(ok, "doc duoc, >= 90% hang hop le", rc)
    s.done()


# ------------------------------------------------------------------ Vong 2 (sau khi Coder sua L01-L04)
def tx12():
    s = Sc("TX12", "Vong 2 - L02 qua duong dan bi danh (junction, nhu data/raw): --csv va --annotate cung mot tep")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=82)
    po, pn = save_pair("tx12", off, on)
    target = TMP / "tx12" / "that"
    target.mkdir()
    link = TMP / "tx12" / "bi_danh"
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not link.is_dir():
        s.note("khong tao duoc junction, bo qua", (r.stdout + r.stderr).strip()[:120])
        s.done()
        return
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--csv", target / "kq.out", "--annotate", link / "kq.out")
    head = (target / "kq.out").read_bytes()[:8] if (target / "kq.out").exists() else b""
    s.ok(rc != 0 or head.startswith(b"row_y,"), "CSV va PNG tro cung tep qua junction: tu choi hoac CSV con nguyen",
         "rc %s, tep bat dau %r, %s" % (rc, head, (se.strip().splitlines() or [""])[-1][:100]))
    # dau ra = dau vao qua junction: phai tu choi, anh nguyen
    pn2 = target / "on.jpg"
    pn2.write_bytes(pn.read_bytes())
    h = sha(pn2)
    rc, so, se = cli("--off", po, "--on", pn2, "--csv", link / "on.jpg")
    s.ok(rc != 0 and sha(pn2) == h, "--csv = anh ON qua junction: tu choi, anh ON nguyen", "rc %s" % rc)
    s.done()


def tx13():
    s = Sc("TX13", "Vong 2 - bien nguong moi va --force da bo")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=83)
    po, pn = save_pair("tx13", off, on)
    for i, (args, want_ok, name) in enumerate([
            # Vong 5: ky vong DOI theo R06 cua Reviewer - min_diff 255 voi sat_thresh mac dinh 250
            # (sat_thresh <= min_diff) la to hop vo ly, phai bi tu choi (Vong 2-4 ky vong nhan)
            (["--min-diff", "255"], False, "min_diff 255 + sat_thresh 250 (R06) bi tu choi"),
            (["--min-diff", "255", "--sat-thresh", "255"], False, "min_diff 255 + sat_thresh 255 (R06) bi tu choi"),
            (["--min-diff", "100", "--sat-thresh", "101"], True, "min_diff 100 + sat_thresh 101 duoc nhan"),
            (["--min-diff", "255.5"], False, "min_diff 255.5 bi tu choi"),
            (["--min-diff", "0"], False, "min_diff 0 bi tu choi"),
            (["--min-diff", "0.001"], True, "min_diff 0.001 duoc nhan"),
            (["--sat-thresh", "255"], True, "sat_thresh 255 duoc nhan"),
            (["--max-width", "1"], True, "max_width 1 duoc nhan")]):
        c = TMP / "tx13" / ("ca%02d" % i) / "c.csv"  # Vong 7: moi ca mot thu muc (D036 mot thu muc = mot cau hinh)
        rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--csv", c, *args)
        s.ok((rc == 0) == want_ok and c.exists() == want_ok, name, "rc %s, csv %s" % (rc, c.exists()))
    # --force khong con: rc != 0, khong ghi de
    old = TMP / "tx13" / "cu.csv"
    old.write_text("cu\n", encoding="utf-8")
    rc, so, se = cli("--off", po, "--on", pn, "--csv", old, "--force")
    s.ok(rc != 0 and old.read_text(encoding="utf-8") == "cu\n", "--force: rc != 0, tep cu nguyen", "rc %s | %s" % (rc, (se.strip().splitlines() or [""])[-1][:100]))
    rc, so, se = cli("--help")
    s.ok("--force" not in so, "--help khong con --force")
    readme = (REPO / "pc" / "README.md").read_text(encoding="utf-8")
    s.ok("--force" not in readme, "pc/README.md khong con nhac --force")
    # dau ra = dau vao viet chu HOA / co '..' (khong --force)
    for name, p in (("chu HOA", Path(str(pn).upper())), ("co '..'", pn.parent / ".." / pn.parent.name / pn.name)):
        h = sha(pn)
        rc, _, se = cli("--off", po, "--on", pn, "--csv", p)
        s.ok(rc != 0 and sha(pn) == h, "--csv = anh ON viet %s: tu choi, anh nguyen" % name, "rc %s" % rc)
    s.done()


def tx14():
    s = Sc("TX14", "Vong 2 - ma con sot va sat_thresh 0", note_only=True)
    import inspect
    s.note("chu ky process_pair: %s" % list(inspect.signature(le.process_pair).parameters),
           "'force' con trong chu ky" if "force" in inspect.signature(le.process_pair).parameters else "khong con 'force'")
    src = inspect.getsource(le.process_pair)
    s.note("'force' duoc dung trong than ham: %s" % (src.count("force") > 1))
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=84)
    r = rows_for(off, on, (100, 50, 540, 430), sat_thresh=0.0)
    s.note("sat_thresh 0 goi thang ham (khong qua kiem tham so CLI); phan bo reason", sorted({x["reason"] for x in r}))
    s.done()


# ------------------------------------------------------------------ Vong 5 (sau khi Coder xu ly R02-R07 cua Reviewer)
def pair_from_rows(w, h, spec, noise=2.0, seed=90):
    """spec: {row: [(center, fwhm, amp), ...]}; OFF/ON cung nen, nhieu doc lap."""
    rng = np.random.default_rng(seed)
    base = np.full((h, w), 40.0)
    off = base + rng.normal(0, noise, (h, w))
    on = base + rng.normal(0, noise, (h, w))
    xs = np.arange(w, dtype=float)
    for y, items in spec.items():
        for (c, fw, amp) in items:
            on[y] += line_profile(xs, c, fw, amp)
    f = lambda a: Image.fromarray(np.clip(np.round(a), 0, 255).astype(np.uint8), "L").convert("RGB")
    return f(off), f(on)


def tx15():
    s = Sc("TX15", "Vong 5 - R02 lien tuc giua cac hang (dom le, buoc nhay that, dom o hang dau)")
    # a. vach 20 hang -> 3 hang chi con dom xa 120 px -> 20 hang ca vach lan dom ngang suc
    spec = {}
    for y in range(0, 20):
        spec[y] = [(100.0, 3.0, 150.0)]
    for y in range(20, 23):
        spec[y] = [(220.0, 3.0, 150.0)]
    for y in range(23, 43):
        spec[y] = [(100.0, 3.0, 150.0), (220.0, 3.0, 150.0)]
    off, on = pair_from_rows(320, 43, spec)
    r = le.extract_laser_centers(off, on, 0, 0, 320, 43, 20.0, 30, 250.0)
    spot = [x for x in r if 20 <= int(x["row_y"]) < 23]
    after = [x for x in r if int(x["row_y"]) >= 23]
    s.ok(all(x["valid"] == "false" for x in spot), "hang chi con dom xa: khong hop le", sorted({x["reason"] for x in spot}))
    s.ok(all(x["valid"] == "true" and abs(float(x["center_x_px"]) - 100.0) < 0.5 for x in after),
         "hang sau (vach + dom ngang suc): bam dung vach x=100, khong bi dom keo sang x=220",
         sorted({(x["reason"], x["center_x_px"][:5]) for x in after})[:3])
    # b. buoc nhay that 60 px (mep vat) tai hang 240
    spec = {y: [(300.0 if y < 240 else 360.0, 3.0, 150.0)] for y in range(0, 480)}
    off, on = pair_from_rows(640, 480, spec, seed=91)
    r = le.extract_laser_centers(off, on, 100, 0, 540, 480, 20.0, 30, 250.0)
    lost = [int(x["row_y"]) for x in r if int(x["row_y"]) >= 240 and x["valid"] == "false"]
    s.note("vach that nhay 60 px tai hang 240: %d hang bi loai sau buoc nhay (hang %s..%s), reason %s" % (
        len(lost), lost[0] if lost else "-", lost[-1] if lost else "-", sorted({x["reason"] for x in r if int(x["row_y"]) in lost})))
    # c. dom le o hang dau ROI roi vach that
    spec = {0: [(450.0, 3.0, 150.0)]}
    spec.update({y: [(300.0, 3.0, 150.0)] for y in range(1, 100)})
    off, on = pair_from_rows(640, 100, spec, seed=92)
    r = le.extract_laser_centers(off, on, 100, 0, 540, 100, 20.0, 30, 250.0)
    lost = [int(x["row_y"]) for x in r if 1 <= int(x["row_y"]) and x["valid"] == "false"]
    s.note("dom le o hang 0 lam moc: %d hang vach that bi loai (hang %s..%s); hang 0 %s" % (
        len(lost), lost[0] if lost else "-", lost[-1] if lost else "-", r[0]["reason"]))
    s.done()


def tx16():
    s = Sc("TX16", "Vong 5 - R03 vach bi cat o bien ROI: reason 'edge'; vach sat nhung khong cham bien van hop le")
    off, on, truth = make_pair(lines=[(150.3, 0.0, 3.0, 150.0)], seed=93)
    r = rows_for(off, on, (150, 100, 450, 380))
    s.ok(all(x["reason"] == "edge" and x["valid"] == "false" and x["center_x_px"] == "" for x in r),
         "tam 150,3, ROI bat dau 150: moi hang edge", sorted({x["reason"] for x in r}))
    off, on, truth = make_pair(lines=[(449.0, 0.0, 3.0, 150.0)], seed=94)
    r = rows_for(off, on, (150, 100, 450, 380))
    s.ok(all(x["reason"] == "edge" for x in r), "tam 449,0, ROI ket thuc 450: moi hang edge", sorted({x["reason"] for x in r}))
    off, on, truth = make_pair(lines=[(157.0, 0.0, 3.0, 150.0)], seed=95)
    r = rows_for(off, on, (150, 100, 450, 380))
    val = [x for x in r if x["valid"] == "true"]
    e = errors_vs_truth(r, truth)
    s.ok(len(val) >= 0.9 * len(r) and np.median(e) < 0.1, "tam 157 (cach bien 7 px, FWHM 3): >= 90% hop le, sai so TV < 0,1 px",
         "%d/%d, TV %.4f" % (len(val), len(r), np.median(e) if e else float("nan")))
    s.done()


def tx17():
    s = Sc("TX17", "Vong 5 - R04 che do anh")
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=96)
    d = TMP / "tx17"; d.mkdir(exist_ok=True)
    po = d / "off_L.jpg"; off.convert("L").save(po, quality=92)
    pn = d / "on_RGB.jpg"; on.save(pn, quality=92)
    rc, so, se = cli("--off", po, "--on", pn, "--csv", d / "c1.csv")
    msg = (se.strip().splitlines() or [""])[-1]
    s.ok(rc != 0 and "che do" in msg.lower() and not (d / "c1.csv").exists(), "OFF L + ON RGB: rc != 0, bao 'che do', khong tao CSV", "rc %s | %s" % (rc, msg[:120]))
    pl = d / "on_L.jpg"; on.convert("L").save(pl, quality=92)
    rc, so, se = cli("--off", po, "--on", pl, "--roi", "100,50,540,430", "--csv", d / "c2.csv")
    s.ok(rc == 0, "OFF L + ON L: duoc nhan", rc)
    pp = d / "on_RGB.png"; on.save(pp)
    po2 = d / "off_RGB.jpg"; off.save(po2, quality=92)
    rc, so, se = cli("--off", po2, "--on", pp, "--csv", d / "c3.csv")
    s.note("OFF JPEG RGB + ON PNG RGB: rc %s | %s" % (rc, (se.strip().splitlines() or [""])[-1][:100]))
    s.done()


def tx18():
    s = Sc("TX18", "Vong 5 - R05 params.json: noi dung, nhieu lan chay cung thu muc, tep san co, don dep khi loi")
    import json
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=97)
    po, pn = save_pair("tx18", off, on)
    run = TMP / "tx18" / "run"
    rc, so, se = cli("--off", po, "--on", pn, "--roi", "100,50,540,430", "--min-diff", "17", "--max-width", "25", "--sat-thresh", "240",
                     "--csv", run / "centers_0000.csv")
    pj = run / "params.json"
    d1 = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}
    s.ok(rc == 0 and d1.get("roi") == [100, 50, 540, 430] and d1.get("min_diff") == 17.0 and d1.get("max_width") == 25
         and d1.get("sat_thresh") == 240.0 and d1.get("img_width") == 640 and d1.get("img_height") == 480,
         "lan 1: params.json co ROI, nguong, kich thuoc anh dung tham so CLI", d1)
    s.note("params.json co tro toi CSV/PNG/anh dau vao nao khong: %s" % sorted(k for k in d1 if k not in ("roi", "min_diff", "max_width", "sat_thresh", "img_width", "img_height", "total_rows", "ok_count", "valid_pct")))
    h1 = sha(pj) if pj.exists() else None
    rc2, so, se = cli("--off", po, "--on", pn, "--roi", "200,60,500,300", "--min-diff", "30", "--csv", run / "centers_0001.csv")
    kept = pj.exists() and sha(pj) == h1
    s.ok(kept or rc2 != 0, "lan 2 cung thu muc, ROI/nguong KHAC: khong duoc am tham ghi de params.json cua lan 1",
         "rc %s, params.json %s" % (rc2, "giu nguyen" if kept else "BI GHI DE -> centers_0000.csv mat tham so that"))
    other = TMP / "tx18" / "co_san"; other.mkdir()
    (other / "params.json").write_text('{"scan_id": "scan_cu", "commit": "abc"}', encoding="utf-8")
    rc3, so, se = cli("--off", po, "--on", pn, "--csv", other / "centers_0000.csv")
    s.ok((other / "params.json").read_text(encoding="utf-8") == '{"scan_id": "scan_cu", "commit": "abc"}',
         "params.json co san (cua cong cu khac) khong bi ghi de", "rc %s" % rc3)
    ann = TMP / "tx18" / "chi_png"
    rc4, so, se = cli("--off", po, "--on", pn, "--annotate", ann / "a.png")
    s.ok(rc4 == 0 and (ann / "params.json").exists(), "chi --annotate: params.json canh PNG", rc4)
    bad = TMP / "tx18" / "loi"; bad.mkdir(); (bad / "params.json").mkdir()  # params.json la thu muc -> ghi loi SAU khi da tao CSV/PNG
    rc5, so, se = cli("--off", po, "--on", pn, "--csv", bad / "c.csv", "--annotate", bad / "a.png")
    left = sorted(p.name for p in bad.iterdir() if p.name != "params.json")
    s.ok(rc5 != 0 and not left, "ghi params.json loi: rc != 0 va khong con CSV/PNG do dang (README: 'moi tep ... duoc don dep')",
         "rc %s, con lai %s" % (rc5, left))
    s.done()


def tx19():
    s = Sc("TX19", "Vong 5 - R07 va tai lieu: quy uoc tam pixel, ma edge, params.json, che do anh")
    ss = (REPO / "docs" / "design" / "SCAN_SESSION.md").read_text(encoding="utf-8")
    rd = (REPO / "pc" / "README.md").read_text(encoding="utf-8")
    s.ok("`i.0`" in ss and "0.5" in ss, "SCAN_SESSION.md ghi quy uoc tam pixel i o toa do i.0")
    s.ok("ambiguous|edge" in ss and "params.json" in ss, "SCAN_SESSION.md co ma edge va params.json")
    s.ok("edge" in rd and "params.json" in rd and "mode" in rd, "pc/README.md co edge, params.json, che do anh")
    s.done()


# ------------------------------------------------------------------ Vong 6 (sau khi Coder sua L06-L08)
def tx20():
    s = Sc("TX20", "Vong 6 - R05/L07: moi CSV phai gan duoc voi tham so THAT cua lan chay tao ra no")
    import json
    off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=98)
    po, pn = save_pair("tx20", off, on)
    run = TMP / "tx20" / "run"
    A = ["--roi", "100,50,540,430", "--min-diff", "20"]
    rc1, _, _ = cli("--off", po, "--on", pn, *A, "--csv", run / "centers_0000.csv")
    rc2, _, _ = cli("--off", po, "--on", pn, *A, "--csv", run / "centers_0001.csv")
    pj = run / "params.json"
    d = json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}
    s.ok(rc1 == 0 and rc2 == 0 and d.get("roi") == [100, 50, 540, 430] and d.get("min_diff") == 20.0,
         "hai buoc CUNG tham so vao cung thu muc: chay duoc, params.json dung tham so chung", (rc1, rc2, d.get("roi")))
    # buoc 3 tham so KHAC vao cung thu muc
    rc3, so3, se3 = cli("--off", po, "--on", pn, "--roi", "200,60,500,300", "--min-diff", "35", "--csv", run / "centers_0002.csv")
    found = [p.name for p in run.iterdir() if p.suffix == ".json"
             and "200" in p.read_text(encoding="utf-8") and "35" in p.read_text(encoding="utf-8")]
    # Vong 7 (01_PLAN muc 5): chon (a) - chi con mot ket qua dung: tu choi params_mismatch
    s.ok(rc3 != 0 and "params_mismatch" in se3 and not (run / "centers_0002.csv").exists(),
         "buoc 3 tham so KHAC: tu choi params_mismatch, khong tao centers_0002.csv",
         "rc %s; tep json co ROI/nguong lan 3: %s; params.json van la ROI %s min_diff %s -> centers_0002.csv mang tham so SAI"
         % (rc3, found, d.get("roi"), d.get("min_diff")) if rc3 == 0 and not found else "rc %s, %s" % (rc3, found))
    # params.json co san cua cong cu khac
    other = TMP / "tx20" / "co_san"; other.mkdir()
    (other / "params.json").write_text('{"scan_id": "scan_cu"}', encoding="utf-8")
    rc4, _, se4 = cli("--off", po, "--on", pn, "--csv", other / "centers_0000.csv")
    s.ok(rc4 != 0 and "params_invalid" in se4 and not (other / "centers_0000.csv").exists()
         and (other / "params.json").read_text(encoding="utf-8") == '{"scan_id": "scan_cu"}',
         "thu muc co params.json cua cong cu khac: tu choi params_invalid, tep khong doi, khong tao CSV",
         "rc %s, tep: %s" % (rc4, sorted(p.name for p in other.iterdir())))
    # params.json trung duong dan dau ra khac (kiem moi cua Coder Vong 6)
    rc5, _, se5 = cli("--off", po, "--on", pn, "--csv", TMP / "tx20" / "o" / "params.json")
    s.ok(rc5 != 0 and not (TMP / "tx20" / "o" / "params.json").exists(), "--csv <thu muc>/params.json: tu choi, khong tao tep",
         "rc %s | %s" % (rc5, (se5.strip().splitlines() or [""])[-1][:100]))
    s.done()


# ------------------------------------------------------------------ Vong 7: hop dong V7-T1..T6 (01_PLAN.md Vong 7 muc 5, D036)
import json as _json  # noqa: E402

BASE = ["--roi", "100,50,540,430", "--min-diff", "20", "--max-width", "30", "--sat-thresh", "250"]
CFG6 = {"roi": [100, 50, 540, 430], "min_diff": 20.0, "max_width": 30, "sat_thresh": 250.0, "img_width": 640, "img_height": 480}
REPS = 3


class Patch:
    """Thay tam mot thuoc tinh (tiem loi / dem loi goi) roi tra lai."""
    def __init__(self, obj, name, new):
        self.obj, self.name, self.new = obj, name, new

    def __enter__(self):
        self.old = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.new)
        return self

    def __exit__(self, *a):
        setattr(self.obj, self.name, self.old)


class WriteSpy:
    """Dem loi goi ba ham ghi cua line_extract trong mot lan goi process_pair."""
    def __init__(self):
        self.calls = {"write_centers_csv": 0, "create_annotated_image": 0, "write_params_json": 0}
        self._ps = []

    def __enter__(self):
        for n in self.calls:
            orig = getattr(le, n)

            def wrap(*a, _n=n, _o=orig, **k):
                self.calls[_n] += 1
                return _o(*a, **k)
            p = Patch(le, n, wrap)
            p.__enter__()
            self._ps.append(p)
        return self

    def __exit__(self, *a):
        for p in reversed(self._ps):
            p.__exit__()


def pair_files(tag, seed, w=640, h=480, cx=320.0):
    off, on, _ = make_pair(w=w, h=h, lines=[(cx, 0.02, 3.0, 150.0)], seed=seed)
    return save_pair(tag, off, on)


def v7_t1():
    s = Sc("V7-T1", "3 cap anh khac nhau, cung cau hinh, 3 CSV cung thu muc: mot params.json, giu nguyen byte, chi 6 truong")
    for k in range(REPS):
        run = TMP / ("v7t1_%d" % k) / "run"
        pj = run / "params.json"
        hashes, rcs, valids = [], [], []
        for step in range(3):
            po, pn = pair_files("v7t1_%d_in%d" % (k, step), seed=1100 + 10 * k + step, cx=250.0 + 60 * step)
            rc, so, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / ("centers_%04d.csv" % step))
            rcs.append(rc)
            hashes.append(sha(pj) if pj.exists() else None)
            valids.append(sum(1 for r in read_csv(run / ("centers_%04d.csv" % step))[1] if r[2] == "true") if rc == 0 else None)
        d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else {}
        s.ok(rcs == [0, 0, 0], "lap %d: 3 lan rc 0" % k, rcs)
        s.ok(len(set(hashes)) == 1 and hashes[0], "lap %d: hash params.json sau lan 1 giu nguyen o lan 2-3" % k, [h[:8] if h else h for h in hashes])
        s.ok(sorted(p.name for p in run.iterdir()) == ["centers_0000.csv", "centers_0001.csv", "centers_0002.csv", "params.json"],
             "lap %d: mot params.json + 3 CSV" % k)
        s.ok(d == CFG6, "lap %d: params.json dung 6 truong cau hinh, khong co thong ke rieng cap dau" % k, d)
        s.note("lap %d: so hang valid 3 buoc %s (khac nhau van cung cau hinh)" % (k, valids))
    s.done()


def v7_t2():
    s = Sc("V7-T2", "bien tuong duong: thu tu khoa/khoang trang, 20 va 20.0, ROI mac dinh = toan anh, metadata C3 cu co thong ke")
    variants = [
        ("thu tu khoa + khoang trang khac, ngung la so nguyen",
         '{ "img_height":480,"img_width":640,\n  "sat_thresh":250 , "max_width":30, "min_diff":20, "roi":[100,50,540,430] }', BASE),
        ("metadata C3 cu co 3 khoa thong ke", _json.dumps(dict(CFG6, total_rows=999, ok_count=777, valid_pct=12.5)), BASE),
    ]
    for k in range(REPS):
        po, pn = pair_files("v7t2_%d_in" % k, seed=1200 + k)
        for i, (name, txt, args) in enumerate(variants):
            run = TMP / ("v7t2_%d_%d" % (k, i)); run.mkdir(parents=True)
            (run / "params.json").write_text(txt, encoding="utf-8")
            h = sha(run / "params.json")
            rc, so, se = cli("--off", po, "--on", pn, *args, "--csv", run / "centers_0000.csv")
            s.ok(rc == 0 and sha(run / "params.json") == h, "lap %d: %s: nhan, params.json khong bi viet lai" % (k, name), rc)
            if "thong ke" in name and rc == 0:
                nv = sum(1 for r in read_csv(run / "centers_0000.csv")[1] if r[2] == "true")
                s.ok(("%d/" % nv) in so and "777/" not in so, "lap %d: stdout la so lieu cap hien tai (%d), khong phai ok_count cu 777" % (k, nv),
                     [l for l in so.splitlines() if "hop le (ok)" in l][:1])
        run = TMP / ("v7t2_%d_roi" % k)
        rc1, _, _ = cli("--off", po, "--on", pn, "--csv", run / "centers_0000.csv")
        h = sha(run / "params.json") if (run / "params.json").exists() else None
        rc2, _, se2 = cli("--off", po, "--on", pn, "--roi", "0,0,640,480", "--csv", run / "centers_0001.csv")
        s.ok(rc1 == 0 and rc2 == 0 and h and sha(run / "params.json") == h, "lap %d: bo --roi roi --roi 0,0,640,480: cung cau hinh" % k, (rc1, rc2))
    s.done()


V7_FIELDS = [
    ("roi", {"args": ["--roi", "100,50,540,431"]}),
    ("min_diff", {"args": ["--min-diff", "21"]}),
    ("max_width", {"args": ["--max-width", "31"]}),
    ("sat_thresh", {"args": ["--sat-thresh", "249"]}),
    ("img_width", {"size": (641, 480)}),
    ("img_height", {"size": (640, 481)}),
]


def _args_with(over):
    a = list(BASE)
    for i in range(0, len(over), 2):
        j = a.index(over[i]); a[j + 1] = over[i + 1]
    return a


def v7_t3():
    s = Sc("V7-T3", "lech tung truong trong 6 truong: params_mismatch neu ten truong, CHUA goi ham ghi, tep cu giu hash; thu muc moi thi chay duoc")
    for k in range(REPS):
        po, pn = pair_files("v7t3_%d_in" % k, seed=1300 + k)
        run = TMP / ("v7t3_%d" % k) / "run"
        rc0, _, _ = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0000.csv")
        h_pj, h_c0 = sha(run / "params.json"), sha(run / "centers_0000.csv")
        for field, spec in V7_FIELDS:
            if "size" in spec:
                qo, qn = pair_files("v7t3_%d_%s" % (k, field), seed=1350 + k, w=spec["size"][0], h=spec["size"][1])
                args = list(BASE)
            else:
                qo, qn = po, pn
                args = _args_with(spec["args"])
            out = run / ("centers_%s.csv" % field)
            rc, so, se = cli("--off", qo, "--on", qn, *args, "--csv", out, "--annotate", run / ("ann_%s.png" % field))
            msg = (se.strip().splitlines() or [""])[-1]
            s.ok(rc != 0 and "params_mismatch" in msg and ("'%s'" % field) in msg, "lap %d: lech %s: rc != 0, params_mismatch neu '%s'" % (k, field, field),
                 "rc %s | %s" % (rc, msg[:140]))
            s.ok(not out.exists() and not (run / ("ann_%s.png" % field)).exists() and sha(run / "params.json") == h_pj
                 and sha(run / "centers_0000.csv") == h_c0, "lap %d: lech %s: khong tep moi, params.json va buoc 0 giu hash" % (k, field))
            if k == 0:  # theo doi loi goi ham ghi (chung minh chan TRUOC ghi)
                with WriteSpy() as spy:
                    try:
                        le.process_pair(qo, qn, roi_str=args[1], min_diff=float(args[3]), max_width=int(args[5]),
                                        sat_thresh=float(args[7]), csv_path=run / ("spy_%s.csv" % field))
                        exc = None
                    except Exception as e:  # noqa: BLE001
                        exc = str(e)
                s.ok(exc and "params_mismatch" in exc and sum(spy.calls.values()) == 0,
                     "lech %s (goi ham): 0 loi goi write_centers_csv/create_annotated_image/write_params_json" % field, spy.calls)
            newdir = TMP / ("v7t3_%d_moi_%s" % (k, field))
            rcn, _, _ = cli("--off", qo, "--on", qn, *args, "--csv", newdir / "centers_0000.csv")
            s.ok(rcn == 0, "lap %d: cau hinh lech %s chay thanh cong o thu muc moi" % (k, field), rcn)
    s.done()


V7_INVALID = [
    ("tep cua cong cu khac", '{"scan_id": "scan_cu", "commit": "abc"}'),
    ("thieu truong max_width", _json.dumps({k: v for k, v in CFG6.items() if k != "max_width"})),
    ("roi la chuoi", _json.dumps(dict(CFG6, roi="100,50,540,430"))),
    ("min_diff la chuoi so", _json.dumps(dict(CFG6, min_diff="20"))),
    ("bool thay so (max_width true)", _json.dumps(dict(CFG6, max_width=True))),
    ("bool thay so (min_diff true)", _json.dumps(dict(CFG6, min_diff=True))),
    ("min_diff null", _json.dumps(dict(CFG6, min_diff=None))),
    ("JSON hong", '{"roi": [100, 50, 540, 430], "min_diff": '),
    ("JSON list", "[1, 2, 3]"),
    ("JSON null", "null"),
    ("NaN", _json.dumps(dict(CFG6, sat_thresh=float("nan")))),
    ("Infinity", _json.dumps(dict(CFG6, min_diff=float("inf")))),
    ("nguong vo ly sat <= min", _json.dumps(dict(CFG6, sat_thresh=20.0))),
    ("ROI vuot anh", _json.dumps(dict(CFG6, roi=[100, 50, 700, 430]))),
    ("ROI rong", _json.dumps(dict(CFG6, roi=[100, 50, 100, 430]))),
    ("khoa la them vao", _json.dumps(dict(CFG6, note="x"))),
]


def v7_t4():
    s = Sc("V7-T4", "metadata khong hop le: params_invalid co nguyen nhan, khong ghi CSV/PNG, du lieu san co nguyen")
    for k in range(REPS):
        po, pn = pair_files("v7t4_%d_in" % k, seed=1400 + k)
        h_in = (sha(po), sha(pn))
        for i, (name, txt) in enumerate(V7_INVALID + [("params.json la thu muc", None)]):
            run = TMP / ("v7t4_%d_%02d" % (k, i)); run.mkdir(parents=True)
            if txt is None:
                (run / "params.json").mkdir()
                before = None
            else:
                (run / "params.json").write_text(txt, encoding="utf-8")
                before = sha(run / "params.json")
            rc, so, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / "c.csv", "--annotate", run / "a.png")
            msg = (se.strip().splitlines() or [""])[-1]
            left = sorted(p.name for p in run.iterdir() if p.name != "params.json")
            same = (run / "params.json").is_dir() if txt is None else sha(run / "params.json") == before
            s.ok(rc != 0 and "params_invalid" in msg and not left and same,
                 "lap %d: %s: rc != 0, params_invalid, khong CSV/PNG, params.json nguyen" % (k, name), "rc %s | %s" % (rc, msg[:120]))
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh dau vao giu hash" % k)
    # theo doi ham ghi cho mot ca (tep cong cu khac)
    run = TMP / "v7t4_spy"; run.mkdir()
    (run / "params.json").write_text('{"scan_id": "x"}', encoding="utf-8")
    po, pn = pair_files("v7t4_spy_in", seed=1450)
    with WriteSpy() as spy:
        try:
            le.process_pair(po, pn, csv_path=run / "c.csv", annotate_path=run / "a.png")
        except Exception:  # noqa: BLE001
            pass
    s.ok(sum(spy.calls.values()) == 0, "params_invalid (goi ham): 0 loi goi ham ghi", spy.calls)
    s.done()


def v7_t5():
    s = Sc("V7-T5", "tiem loi luu tru: loi doc metadata, ghi mot phan CSV/PNG/params.json, tranh chap tao params.json")
    for k in range(REPS):
        po, pn = pair_files("v7t5_%d_in" % k, seed=1500 + k)
        kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
        # thu muc da co buoc 0 (params tai su dung)
        run = TMP / ("v7t5_%d" % k) / "run"
        le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
        h_pj, h_c0 = sha(run / "params.json"), sha(run / "centers_0000.csv")
        # a. loi doc metadata
        orig_rt = Path.read_text

        def bad_read(self, *a, **k2):
            if self.name == "params.json":
                raise PermissionError("tiem loi: khong co quyen doc")
            return orig_rt(self, *a, **k2)
        with Patch(Path, "read_text", bad_read), WriteSpy() as spy:
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0001.csv", **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = str(e)
        s.ok(exc and "params_invalid" in exc and sum(spy.calls.values()) == 0 and not (run / "centers_0001.csv").exists(),
             "lap %d: loi doc params.json: params_invalid, 0 loi goi ghi" % k, (exc or "")[:80])

        # Vong 8: tiem loi BEN TRONG ham ghi that (writerow / Image.save hong giua chung) thay cho
        # stub thay nguyen ham ghi o Vong 7 - stub khong mo phong duoc co che so huu cua ma that.
        # Ky vong giu nguyen: khong con tep do dang. Doi tuong patch: csv.DictWriter, PIL Image.save.
        csv_mod = le.csv
        RealDW = csv_mod.DictWriter

        class FailingDW(RealDW):
            def writerow(self, row):
                self._n = getattr(self, "_n", 0) + 1
                if self._n > 5:
                    raise OSError("tiem loi: dia day giua chung CSV (sau 5 dong)")
                return super().writerow(row)

        def failing_save(self, fp, *a, **k2):
            fp.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
            raise OSError("tiem loi: dia day giua chung PNG")

        class _PatchCSV(Patch):
            def __init__(self):
                super().__init__(csv_mod, "DictWriter", FailingDW)

        class _PatchPNG(Patch):
            def __init__(self):
                super().__init__(Image.Image, "save", failing_save)
        partial_csv = partial_png = None  # noqa: F841 (giu ten cho de doi chieu log cu)
        # b. CSV ghi mot phan, params tai su dung
        with _PatchCSV():
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0002.csv", **kw)
            except Exception:  # noqa: BLE001
                pass
        s.ok(not (run / "centers_0002.csv").exists(), "lap %d: CSV ghi mot phan (params tai su dung): khong con CSV do dang" % k,
             sorted(p.name for p in run.iterdir()))
        s.ok(sha(run / "params.json") == h_pj and sha(run / "centers_0000.csv") == h_c0, "lap %d: params.json tai su dung va buoc 0 giu hash" % k)
        # c. PNG ghi mot phan (cung CSV cua lan goi), params tai su dung
        with _PatchPNG():
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0003.csv", annotate_path=run / "ann_0003.png", **kw)
            except Exception:  # noqa: BLE001
                pass
        s.ok(not (run / "ann_0003.png").exists() and not (run / "centers_0003.csv").exists(),
             "lap %d: PNG ghi mot phan: khong con PNG va CSV cua lan goi" % k, sorted(p.name for p in run.iterdir()))
        s.ok(sha(run / "params.json") == h_pj and sha(run / "centers_0000.csv") == h_c0, "lap %d: (sau loi PNG) params/buoc 0 giu hash" % k)
        # d. CSV ghi mot phan trong thu muc MOI (params.json do lan goi tao)
        new = TMP / ("v7t5_%d" % k) / "moi"
        with _PatchCSV():
            try:
                le.process_pair(po, pn, csv_path=new / "centers_0000.csv", **kw)
            except Exception:  # noqa: BLE001
                pass
        # Vong 10 (01_PLAN Vong 10 muc 5, D037): ky vong 'thu muc rong' thay bang: khong con CSV do dang,
        # params.json con du 6 truong dung cau hinh, khong tep danh dau moi
        left = sorted(p.name for p in new.iterdir()) if new.exists() else []
        pjd = _json.loads((new / "params.json").read_text(encoding="utf-8")) if (new / "params.json").is_file() else None
        s.ok(left == ["params.json"] and pjd == CFG6,
             "lap %d: thu muc moi, CSV ghi mot phan: khong con CSV do dang; params.json con, dung 6 truong; khong tep danh dau" % k,
             "%s; params.json %s" % (left, "dung cau hinh" if pjd == CFG6 else pjd))
        # e. params.json ghi mot phan (thu muc moi)
        new2 = TMP / ("v7t5_%d" % k) / "moi2"
        orig_dump = le.json.dump
        PART = '{"roi": ['

        def partial_dump(obj, f, *a, **k2):
            f.write(PART)
            f.flush()
            raise OSError("tiem loi: dia day giua chung params.json")
        with Patch(le.json, "dump", partial_dump):
            try:
                le.process_pair(po, pn, csv_path=new2 / "centers_0000.csv", **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = repr(e)
        # Vong 10: ky vong 'xoa params ghi do' thay bang: bao loi, khong CSV/PNG; tep ghi do giu nguyen;
        # luot sau bi params_invalid; thu muc moi voi dau vao hop le chay duoc
        left = sorted(p.name for p in new2.iterdir()) if new2.exists() else []
        txt = (new2 / "params.json").read_text(encoding="utf-8") if (new2 / "params.json").is_file() else None
        s.ok(exc is not None and left == ["params.json"] and txt == PART,
             "lap %d: params.json ghi mot phan: luot dau bao loi, khong CSV/PNG, tep ghi do giu nguyen" % k,
             "exc %s; %s; noi dung %r" % ((exc or "")[:50], left, txt))
        rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", new2 / "centers_0001.csv")
        txt2 = (new2 / "params.json").read_text(encoding="utf-8") if (new2 / "params.json").is_file() else None
        s.ok(rc != 0 and "params_invalid" in se and txt2 == PART and not (new2 / "centers_0001.csv").exists(),
             "lap %d: luot sau vao thu muc co params ghi do: params_invalid, tep giu nguyen, khong CSV" % k, rc)
        rc, _, _ = cli("--off", po, "--on", pn, *BASE, "--csv", TMP / ("v7t5_%d" % k) / "moi2b" / "centers_0000.csv")
        s.ok(rc == 0, "lap %d: thu muc moi voi dau vao hop le: chay duoc" % k, rc)
        # f. tranh chap: tien trinh khac tao params.json giua luc kiem va luc ghi -> che do KHONG ghi de (01_PLAN Vong 7 muc 2.3)
        new3 = TMP / ("v7t5_%d" % k) / "tranh_chap"
        foreign = '{"scan_id": "tien_trinh_khac"}'
        orig_chk = le.check_or_match_params

        def racing_check(path, cfg):
            r = orig_chk(path, cfg)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(foreign, encoding="utf-8")
            return r
        with Patch(le, "check_or_match_params", racing_check):
            try:
                le.process_pair(po, pn, csv_path=new3 / "centers_0000.csv", **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = repr(e)
        txt = (new3 / "params.json").read_text(encoding="utf-8") if (new3 / "params.json").is_file() else None
        s.ok(txt == foreign and not (new3 / "centers_0000.csv").exists(),
             "lap %d: params.json xuat hien giua kiem va ghi: khong bi ghi de (tao kieu khong ghi de), khong tao CSV" % k,
             "params.json %s; exc %s" % ("GIU NGUYEN" if txt == foreign else "BI GHI DE" if txt else "mat", (exc or "")[:60]))
    s.done()


def v7_t6():
    s = Sc("V7-T6", "duong dan: PNG-only, CSV+PNG khac thu muc, cung thu muc qua junction, dau ra ten params.json, chi stdout")
    for k in range(REPS):
        po, pn = pair_files("v7t6_%d_in" % k, seed=1600 + k)
        d = TMP / ("v7t6_%d" % k)
        # PNG-only: tao, tai dung, lech
        pdir = d / "png"
        rc1, _, _ = cli("--off", po, "--on", pn, *BASE, "--annotate", pdir / "a0.png")
        h = sha(pdir / "params.json") if (pdir / "params.json").exists() else None
        rc2, _, _ = cli("--off", po, "--on", pn, *BASE, "--annotate", pdir / "a1.png")
        rc3, _, se3 = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "25"]), "--annotate", pdir / "a2.png")
        s.ok(rc1 == 0 and rc2 == 0 and h and sha(pdir / "params.json") == h and rc3 != 0 and "params_mismatch" in se3 and not (pdir / "a2.png").exists(),
             "lap %d: PNG-only tao/tai dung/so khop params.json" % k, (rc1, rc2, rc3))
        # CSV + PNG khac thu muc
        a, b = d / "a", d / "b"
        rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", a / "c.csv", "--annotate", b / "p.png")
        s.ok(rc != 0 and not (a.exists() and any(a.iterdir())) and not (b.exists() and any(b.iterdir())),
             "lap %d: CSV + PNG khac thu muc: tu choi, khong tao tep" % k, "rc %s" % rc)
        # cung thu muc qua junction
        tgt = d / "that"; tgt.mkdir(parents=True)
        lnk = d / "bi_danh"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(lnk), str(tgt)], capture_output=True, text=True, errors="replace")
        if r.returncode == 0:
            rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", tgt / "c.csv", "--annotate", lnk / "p.png")
            s.ok(rc == 0 and sorted(p.name for p in tgt.iterdir()) == ["c.csv", "p.png", "params.json"],
                 "lap %d: CSV that + PNG qua junction cung thu muc: nhan, mot params.json" % k, (rc, sorted(p.name for p in tgt.iterdir())))
            rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", tgt / "c2.csv", "--annotate", lnk / "params.json")
            s.ok(rc != 0 and sha(tgt / "params.json") == sha(tgt / "params.json"), "lap %d: --annotate <junction>/params.json: tu choi" % k, rc)
        else:
            s.note("khong tao duoc junction", r.stderr[:80])
        # dau ra ten params.json
        q = d / "q"
        rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", q / "params.json")
        s.ok(rc != 0 and not (q / "params.json").exists(), "lap %d: --csv <thu muc>/params.json: tu choi" % k, rc)
        # tep dau ra co san
        e = d / "e"; e.mkdir()
        (e / "c.csv").write_text("cu", encoding="utf-8")
        rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", e / "c.csv")
        s.ok(rc != 0 and (e / "c.csv").read_text(encoding="utf-8") == "cu" and not (e / "params.json").exists(),
             "lap %d: CSV da ton tai: tu choi, khong tao params.json" % k, rc)
        # chi stdout
        before = snapshot(po.parent)
        rc, so, se = cli("--off", po, "--on", pn, *BASE)
        s.ok(rc == 0 and snapshot(po.parent) == before and not (REPO / "params.json").exists(), "lap %d: chi stdout: khong tao params.json" % k, rc)
    s.done()


def v7_order():
    s = Sc("V7-T3b", "01_PLAN Vong 7 muc 2.3: tao params.json SAU khi moi kiem dau vao dat (anh khac kich thuoc / khac che do)")
    for k in range(REPS):
        d = TMP / ("v7ord_%d" % k); d.mkdir()
        off, on, _ = make_pair(lines=[(320.0, 0.0, 3.0, 150.0)], seed=1700 + k)
        po = d / "off.jpg"; off.save(po, quality=92)
        pn_small = d / "on_small.jpg"; on.resize((320, 240)).save(pn_small, quality=92)
        pn_L = d / "on_L.jpg"; on.convert("L").save(pn_L, quality=92)
        for name, pn in (("khac kich thuoc", pn_small), ("khac che do", pn_L)):
            out = d / name.replace(" ", "_") / "c.csv"
            with WriteSpy() as spy:
                try:
                    le.process_pair(po, pn, csv_path=out); exc = None
                except Exception as e:  # noqa: BLE001
                    exc = str(e)
            s.ok(exc is not None and spy.calls["write_params_json"] == 0 and not out.parent.exists() or
                 (exc is not None and spy.calls["write_params_json"] == 0 and not any(out.parent.iterdir())),
                 "lap %d: %s: bi tu choi, KHONG goi write_params_json truoc khi kiem dau vao xong" % (k, name),
                 "loi goi %s | %s" % (spy.calls, (exc or "")[:60]))
    s.done()


def v7_owner():
    s = Sc("V7-T5b", "01_PLAN Vong 7 muc 2.7: khi loi CHI don tep do chinh lan goi tao; tep cua tien trinh khac xuat hien trong luc chay phai con nguyen")
    foreign = "tep cua tien trinh khac"
    for k in range(REPS):
        po, pn = pair_files("v7own_%d_in" % k, seed=1800 + k)
        kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
        # a. CSV cua tien trinh khac xuat hien, roi lan goi nay loi (params_mismatch) truoc khi ghi CSV
        run = TMP / ("v7own_%d" % k) / "a"
        le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
        out = run / "centers_0001.csv"
        orig_chk = le.check_or_match_params

        def chk_then_foreign(path, cfg, _out=out):
            _out.write_text(foreign, encoding="utf-8")  # tien trinh khac vua ghi buoc 0001
            raise ValueError("params_mismatch: tiem loi (mo phong lech cau hinh)")
        with Patch(le, "check_or_match_params", chk_then_foreign):
            try:
                le.process_pair(po, pn, csv_path=out, **kw)
            except Exception:  # noqa: BLE001
                pass
        txt = out.read_text(encoding="utf-8") if out.exists() else None
        s.ok(txt == foreign, "lap %d: loi truoc khi ghi CSV: CSV cua tien trinh khac (cung ten) con nguyen" % k,
             "con nguyen" if txt == foreign else "BI XOA" if txt is None else "BI GHI DE")
        # b. PNG cua tien trinh khac xuat hien truoc buoc ghi PNG -> chot 'exists' nem loi -> khoi except
        run = TMP / ("v7own_%d" % k) / "b"
        csvp, pngp = run / "centers_0000.csv", run / "ann_0000.png"
        orig_w = le.write_centers_csv

        def csv_then_foreign_png(path, rows, _png=pngp):
            orig_w(path, rows)
            _png.write_text(foreign, encoding="utf-8")  # tien trinh khac vua ghi PNG cung ten
        with Patch(le, "write_centers_csv", csv_then_foreign_png):
            try:
                le.process_pair(po, pn, csv_path=csvp, annotate_path=pngp, **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = type(e).__name__
        txt = pngp.read_text(encoding="utf-8") if pngp.exists() else None
        s.ok(exc is not None and txt == foreign, "lap %d: PNG cung ten do tien trinh khac tao: lan goi bao loi, PNG cua ho con nguyen" % k,
             "exc %s; PNG %s" % (exc, "con nguyen" if txt == foreign else "BI XOA" if txt is None else "BI GHI DE"))
        s.ok(not csvp.exists(), "lap %d: CSV do chinh lan goi tao duoc don" % k)
        # c. (ghi nhan) CSV cung ten xuat hien giua luc kiem dau ham va luc ghi CSV: bi ghi de?
        run = TMP / ("v7own_%d" % k) / "c"
        csvc = run / "centers_0000.csv"
        orig_ex = le.extract_laser_centers

        def extract_then_foreign(*a, _c=csvc, **k2):
            r = orig_ex(*a, **k2)
            _c.parent.mkdir(parents=True, exist_ok=True)
            _c.write_text(foreign, encoding="utf-8")
            return r
        with Patch(le, "extract_laser_centers", extract_then_foreign):
            try:
                le.process_pair(po, pn, csv_path=csvc, **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = type(e).__name__
        txt = csvc.read_text(encoding="utf-8") if csvc.exists() else None
        s.note("lap %d: CSV cung ten xuat hien truoc buoc ghi CSV: exc %s, tep %s" % (
            k, exc, "con nguyen" if txt == foreign else "BI XOA" if txt is None else "BI GHI DE (mode w)"))
    s.done()


FOREIGN_CSV = "row_y,center_x_px,valid,reason,width_px\n# ket qua cua mot tien trinh line_extract khac\n"
FOREIGN_PNG = b"\x89PNG\r\n\x1a\n" + b"PNG cua tien trinh khac"


def v8_r08():
    s = Sc("V8-R08", "R08: tep cung ten cua tien trinh khac xuat hien SAU khi ham ghi da tu don tep do, TRUOC khoi don ngoai -> phai con nguyen")
    orig_unlink = Path.unlink
    for k in range(REPS):
        po, pn = pair_files("v8r08_%d_in" % k, seed=1900 + k)
        kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
        # a. CSV: loi giua chung trong writerow -> ham ghi xoa tep do -> tien trinh khac tao CSV cung ten
        run = TMP / ("v8r08_%d" % k) / "a"
        le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
        tgt = run / "centers_0001.csv"
        RealDW = le.csv.DictWriter

        class FailDW(RealDW):
            def writerow(self, row):
                self._n = getattr(self, "_n", 0) + 1
                if self._n > 3:
                    raise OSError("tiem loi: dia day")
                return super().writerow(row)

        def unlink_then_foreign(self, *a, _t=tgt, _data=FOREIGN_CSV, **k2):
            orig_unlink(self, *a, **k2)
            if os.path.normcase(str(self)) == os.path.normcase(str(_t)):
                _t.write_text(_data, encoding="utf-8")
        with Patch(le.csv, "DictWriter", FailDW), Patch(Path, "unlink", unlink_then_foreign):
            try:
                le.process_pair(po, pn, csv_path=tgt, **kw)
            except Exception:  # noqa: BLE001
                pass
        txt = tgt.read_text(encoding="utf-8") if tgt.exists() else None
        s.ok(txt == FOREIGN_CSV, "lap %d: CSV: tep cua tien trinh khac (xuat hien sau khi tep do bi xoa) con nguyen" % k,
             "con nguyen" if txt == FOREIGN_CSV else "BI XOA" if txt is None else "BI THAY")
        # b. PNG: loi giua chung trong Image.save -> ham ghi xoa PNG do -> tien trinh khac tao PNG cung ten
        run = TMP / ("v8r08_%d" % k) / "b"
        le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
        png = run / "ann_0001.png"

        def failing_save(self, fp, *a, **k2):
            fp.write(b"\x89PNG\r\n\x1a\n\x00")
            raise OSError("tiem loi: dia day PNG")

        def unlink_then_foreign_png(self, *a, _t=png, **k2):
            orig_unlink(self, *a, **k2)
            if os.path.normcase(str(self)) == os.path.normcase(str(_t)):
                _t.write_bytes(FOREIGN_PNG)
        with Patch(Image.Image, "save", failing_save), Patch(Path, "unlink", unlink_then_foreign_png):
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0001.csv", annotate_path=png, **kw)
            except Exception:  # noqa: BLE001
                pass
        data = png.read_bytes() if png.exists() else None
        s.ok(data == FOREIGN_PNG, "lap %d: PNG: tep cua tien trinh khac con nguyen" % k,
             "con nguyen" if data == FOREIGN_PNG else "BI XOA" if data is None else "BI THAY")
        s.ok(not (run / "centers_0001.csv").exists(), "lap %d: CSV do chinh lan goi tao (truoc buoc PNG) duoc don" % k)
        # c. params.json - Vong 10 (01_PLAN Vong 10 muc 5): hook 'tao tep ngoai lai sau params.unlink' khong con
        # diem kich hoat vi ma khong con xoa metadata. Thay bang hai ca:
        # c1. loi giua chung trong json.dump (thu muc moi): duong loi KHONG goi xoa params.json (dem moi loi xoa)
        run = TMP / ("v8r08_%d" % k) / "c"
        pj = run / "params.json"
        deleted = []

        def partial_dump(obj, f, *a, **k2):
            f.write('{"roi": [')
            raise OSError("tiem loi: dia day params")

        def spy_unlink(self, *a, **k2):
            deleted.append(str(self))
            return orig_unlink(self, *a, **k2)

        def spy_os_rm(p, *a, _o=os.remove, **k2):
            deleted.append(str(p))
            return _o(p, *a, **k2)
        with Patch(le.json, "dump", partial_dump), Patch(Path, "unlink", spy_unlink), \
                Patch(os, "remove", spy_os_rm), Patch(os, "unlink", spy_os_rm):
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = type(e).__name__
        pj_del = [x for x in deleted if Path(x).name == "params.json"]
        txt = pj.read_text(encoding="utf-8") if pj.exists() else None
        s.ok(exc is not None and not pj_del and txt == '{"roi": [' and not (run / "centers_0000.csv").exists(),
             "lap %d: params.json ghi do: duong loi khong goi xoa metadata, tep giu nguyen, khong tao CSV" % k,
             "exc %s; loi goi xoa params.json %d; tep %s" % (exc, len(pj_del), "giu nguyen" if txt == '{"roi": [' else txt))
        # c2. tep ngoai lai chiem ten params.json ngay truoc luc mo 'x' -> tep do con nguyen
        import builtins
        real_open = builtins.open
        run = TMP / ("v8r08_%d" % k) / "c2"
        pj = run / "params.json"
        foreign_pj = '{"scan_id": "tien_trinh_khac"}'
        fired = []

        def open_foreign_first(file, mode="r", *a, _t=pj, **k2):
            if os.path.normcase(str(file)) == os.path.normcase(str(_t)) and "x" in mode and not fired:
                fired.append(1)
                with real_open(_t, "w", encoding="utf-8") as f:
                    f.write(foreign_pj)
            return real_open(file, mode, *a, **k2)
        le.open = open_foreign_first  # write_params_json dung ten 'open' cua module
        try:
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = type(e).__name__
        finally:
            del le.open
        txt = pj.read_text(encoding="utf-8") if pj.exists() else None
        s.ok(fired and exc is not None and txt == foreign_pj and not (run / "centers_0000.csv").exists(),
             "lap %d: params.json ngoai lai xuat hien truoc mo 'x': con nguyen, lan goi bao loi, khong tao CSV" % k,
             "hook %s; exc %s; tep %s" % ("chay" if fired else "KHONG chay", exc,
                                          "con nguyen" if txt == foreign_pj else "BI XOA" if txt is None else "BI THAY"))
    s.done()


def v8_heur():
    s = Sc("V8-R08b", "01_PLAN Vong 7 muc 2.7 voi ham ghi THAT: open(x) bi tu choi (PermissionError - tep dang bi khoa/cho xoa) khi da co CSV cung ten cua mot line_extract khac -> tep do phai con nguyen")
    import builtins
    real_open = builtins.open
    for k in range(REPS):
        po, pn = pair_files("v8heur_%d_in" % k, seed=1950 + k)
        kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
        run = TMP / ("v8heur_%d" % k)
        tgt = run / "centers_0000.csv"

        def open_denied(file, mode="r", *a, _t=tgt, **k2):
            if os.path.normcase(str(file)) == os.path.normcase(str(_t)) and "x" in mode:
                with real_open(_t, "w", encoding="utf-8") as f:  # tien trinh khac vua ghi xong tep cung ten
                    f.write(FOREIGN_CSV)
                raise PermissionError(13, "tiem loi: Windows tu choi mo (tep dang bi khoa/cho xoa)", str(file))
            return real_open(file, mode, *a, **k2)
        le.open = open_denied  # ham ghi that write_centers_csv dung ten 'open' cua module
        try:
            try:
                le.process_pair(po, pn, csv_path=tgt, **kw); exc = None
            except Exception as e:  # noqa: BLE001
                exc = type(e).__name__
        finally:
            del le.open
        txt = tgt.read_text(encoding="utf-8") if tgt.exists() else None
        s.ok(txt == FOREIGN_CSV, "lap %d: CSV (header row_y) cua tien trinh khac con nguyen" % k,
             "exc %s; tep %s" % (exc, "con nguyen" if txt == FOREIGN_CSV else "BI XOA" if txt is None else "BI THAY"))
    s.done()


def v9_r09():
    s = Sc("V9-R09", "R09: rollback cua luot A khong duoc xoa params.json ma luot B da dung; ket qua cua B phai gan duoc voi tham so that; luot C cau hinh khac bi chan")
    import threading
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    for k in range(REPS):
        po, pn = pair_files("v9r09_%d_in" % k, seed=2000 + k)
        for variant, b_args in (("a", ["--csv", "centers_0001.csv"]), ("b", ["--annotate", "ann_0001.png"])):
            run = TMP / ("v9r09_%d_%s" % (k, variant)) / "run"
            a_csv = run / "centers_0000.csv"
            b_out = run / b_args[1]
            orig_w = le.write_centers_csv
            state = {}

            def a_writer(path, rows, _a=a_csv, _run=run, _b=b_args):
                if os.path.normcase(str(path)) == os.path.normcase(str(_a)):
                    # luot B (tien trinh rieng) hoan tat khi A da tao params.json, truoc khi A ghi CSV
                    r = subprocess.run([PY, LE, "--off", str(po), "--on", str(pn), *BASE, _b[0], str(_run / _b[1])],
                                       cwd=REPO, capture_output=True, text=True, errors="replace")
                    state["b_rc"] = r.returncode
                    state["pj_after_b"] = sha(_run / "params.json") if (_run / "params.json").exists() else None
                    raise OSError("tiem loi: luot A hong khi ghi CSV")
                return orig_w(path, rows)
            with Patch(le, "write_centers_csv", a_writer):
                try:
                    le.process_pair(po, pn, csv_path=a_csv, **kw)
                except Exception:  # noqa: BLE001
                    pass
            pj = run / "params.json"
            d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
            s.ok(state.get("b_rc") == 0 and b_out.exists(), "lap %d (%s): luot B (%s) hoan tat" % (k, variant, b_args[0]), state.get("b_rc"))
            s.ok(d == CFG6 and sha(pj) == state.get("pj_after_b"),
                 "lap %d (%s): sau khi A loi, params.json B da dung con nguyen (hash nhu luc B xong)" % (k, variant),
                 "params.json %s" % ("con, dung cau hinh B" if d == CFG6 else "MAT" if d is None else d))
            rc, _, se = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0002.csv")
            d2 = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
            s.ok(rc != 0 and not (run / "centers_0002.csv").exists() and d2 in (CFG6, None) and (d2 is None or sha(pj) == state.get("pj_after_b")),
                 "lap %d (%s): luot C min_diff 30 bi tu choi, khong tao metadata moi cho ket qua cua B" % (k, variant),
                 "rc %s | params.json sau C: %s" % (rc, d2 if d2 != CFG6 else "cau hinh B"))
        # c. B dang chay do: B da doc/khop params.json, A loi va rollback, roi B moi ghi CSV
        run = TMP / ("v9r09_%d_c" % k) / "run"
        a_csv, b_csv = run / "centers_0000.csv", run / "centers_0001.csv"
        ev_b_checked, ev_a_done = threading.Event(), threading.Event()
        orig_chk, orig_w = le.check_or_match_params, le.write_centers_csv
        res = {}

        def chk(path, cfg):
            r = orig_chk(path, cfg)
            if threading.current_thread().name == "luot_B":
                ev_b_checked.set()
                ev_a_done.wait(20)
            return r

        def b_thread():
            try:
                le.process_pair(po, pn, csv_path=b_csv, **kw)
                res["b"] = "ok"
            except Exception as e:  # noqa: BLE001
                res["b"] = repr(e)[:80]

        def a_writer2(path, rows, _a=a_csv):
            if os.path.normcase(str(path)) == os.path.normcase(str(_a)):
                t = threading.Thread(target=b_thread, name="luot_B")
                res["t"] = t
                t.start()
                ev_b_checked.wait(20)
                raise OSError("tiem loi: luot A hong khi ghi CSV")
            return orig_w(path, rows)
        with Patch(le, "check_or_match_params", chk), Patch(le, "write_centers_csv", a_writer2):
            try:
                le.process_pair(po, pn, csv_path=a_csv, **kw)
            except Exception:  # noqa: BLE001
                pass
            ev_a_done.set()
            res["t"].join(30)
        pj = run / "params.json"
        d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
        ok = (b_csv.exists() and d == CFG6) or (not b_csv.exists() and res.get("b") != "ok")
        s.ok(ok, "lap %d (c): B dang chay khi A rollback: CSV cua B phai con metadata dung, hoac B that bai khong de ket qua" % k,
             "B %s; centers_0001.csv %s; params.json %s" % (res.get("b"), "CO" if b_csv.exists() else "khong",
                                                             "con" if d == CFG6 else "MAT" if d is None else d))
    s.done()


def v9_gap():
    # Vong 10 (01_PLAN Vong 10 muc 5): diem dieu phoi chuyen tu Path.unlink (khong con) sang: B dung o
    # (d) ngay sau khi khop metadata / (e) ngay truoc ghi CSV; A loi trong khoang do; C cau hinh khac chay;
    # roi B chay tiep. Khang dinh B thuc su den diem chan va A thuc su loi - hook khong chay la FAIL.
    s = Sc("V9-L16b", "L16: B dung ngay sau khop metadata (d) / ngay truoc ghi CSV (e), A loi trong khoang do, C khac cau hinh; B phai giu dung metadata")
    import threading
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    for k in range(REPS):
        po, pn = pair_files("v9gap_%d_in" % k, seed=2100 + k)
        h_in = (sha(po), sha(pn))
        for variant in ("d", "e"):
            run = TMP / ("v9gap_%d_%s" % (k, variant)) / "run"
            a_csv, b_csv = run / "centers_0000.csv", run / "centers_0001.csv"
            ev_b, ev_go = threading.Event(), threading.Event()
            orig_chk, orig_w = le.check_or_match_params, le.write_centers_csv
            res = {}

            def b_thread():
                try:
                    le.process_pair(po, pn, csv_path=b_csv, **kw)
                    res["b"] = "ok"
                except Exception as e:  # noqa: BLE001
                    res["b"] = repr(e)[:80]

            def chk(path, cfg, _v=variant):
                r = orig_chk(path, cfg)
                if _v == "d" and threading.current_thread().name == "luot_B":
                    ev_b.set()
                    ev_go.wait(30)
                return r

            def writer(path, rows, _a=a_csv, _v=variant, _run=run):
                if os.path.normcase(str(path)) == os.path.normcase(str(_a)):
                    res["pj_a"] = sha(_run / "params.json")
                    t = threading.Thread(target=b_thread, name="luot_B")
                    res["t"] = t
                    t.start()
                    res["b_reached"] = ev_b.wait(30)
                    raise OSError("tiem loi: luot A hong khi ghi CSV")
                if _v == "e" and threading.current_thread().name == "luot_B":
                    ev_b.set()
                    ev_go.wait(30)
                return orig_w(path, rows)
            with Patch(le, "check_or_match_params", chk), Patch(le, "write_centers_csv", writer):
                try:
                    le.process_pair(po, pn, csv_path=a_csv, **kw)
                    res["a"] = "ok"
                except Exception as e:  # noqa: BLE001
                    res["a"] = type(e).__name__
                # A da loi, B van dang dung: C (tien trinh rieng) min_diff 30
                rc_c, _, se_c = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0002.csv")
                ev_go.set()
                if "t" in res:
                    res["t"].join(30)
            pj = run / "params.json"
            d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
            fired = res.get("b_reached") is True and res.get("a") not in (None, "ok")
            s.ok(fired, "lap %d (%s): thu tu da kich hoat: B den diem chan, A loi trong luc B dung" % (k, variant),
                 "B den diem chan %s; A %s" % (res.get("b_reached"), res.get("a")))
            s.ok(fired and res.get("b") == "ok" and b_csv.exists() and d == CFG6 and sha(pj) == res.get("pj_a")
                 and not a_csv.exists(),
                 "lap %d (%s): B thanh cong, CSV cua B co metadata dung (hash nhu luc A tao), khong con CSV cua A" % (k, variant),
                 "B %s; centers_0001.csv %s; params.json %s" % (res.get("b"), "CO" if b_csv.exists() else "khong",
                                                                 "cau hinh B, giu hash" if d == CFG6 and sha(pj) == res.get("pj_a")
                                                                 else "MAT" if d is None else d))
            s.ok(rc_c != 0 and "params_mismatch" in se_c and not (run / "centers_0002.csv").exists(),
                 "lap %d (%s): C min_diff 30 bi chan params_mismatch, khong dau ra" % (k, variant), rc_c)
            s.ok((sha(po), sha(pn)) == h_in, "lap %d (%s): anh tho giu hash" % (k, variant))
    s.done()


def v9_note():
    # Vong 10 (01_PLAN Vong 10 muc 5): bo ky vong sinh marker; kiem khong sinh .active_* moi, marker cu
    # dung trong fixture khong bi xoa va khong tac dong hop dong metadata. Ghi nhan PNG giu nguyen la NOTE.
    s = Sc("V9-N", "Vong 10 - khong sinh .active_*; marker cu khong bi xoa, khong anh huong metadata; ghi nhan 'moi .csv/.png = ket qua'")
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    po, pn = pair_files("v9n_in", seed=2200)
    run = TMP / "v9n_stale" / "run"
    run.mkdir(parents=True)
    mk = run / ".active_99999_1_1"
    mk.write_bytes(b"marker cu")

    def bad(path, rows):
        raise OSError("tiem loi: luot A hong khi ghi CSV")
    with Patch(le, "write_centers_csv", bad):
        try:
            le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
        except Exception:  # noqa: BLE001
            pass
    left = sorted(p.name for p in run.iterdir())
    pj = run / "params.json"
    h = sha(pj) if pj.exists() else None
    s.ok(left == [".active_99999_1_1", "params.json"] and mk.read_bytes() == b"marker cu"
         and _json.loads(pj.read_text(encoding="utf-8")) == CFG6,
         "marker cu + A tao params.json roi loi: marker giu nguyen, params.json giu (D037), khong marker moi", left)
    rc1, _, _ = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0000.csv")
    rc2, _, se2 = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0001.csv")
    left = sorted(p.name for p in run.iterdir())
    s.ok(rc1 == 0 and h and sha(pj) == h and rc2 != 0 and "params_mismatch" in se2
         and left == [".active_99999_1_1", "centers_0000.csv", "params.json"] and mk.read_bytes() == b"marker cu",
         "thu lai cung cau hinh chay duoc (tai dung byte), khac cau hinh params_mismatch; marker cu khong doi", left)
    r3 = TMP / "v9n_ok"
    rc, _, _ = cli("--off", po, "--on", pn, *BASE, "--csv", r3 / "c.csv", "--annotate", r3 / "a.png")
    left = sorted(p.name for p in r3.iterdir())
    s.ok(rc == 0 and left == ["a.png", "c.csv", "params.json"], "chay binh thuong CSV+PNG: khong sinh .active_*", left)
    d = TMP / "v9n_png"
    d.mkdir(parents=True)
    Image.open(po).save(d / "off.png")
    Image.open(pn).save(d / "on.png")
    rc, _, se = cli("--off", d / "off.png", "--on", d / "on.png", *BASE, "--csv", d / "centers_0000.csv")
    s.note("(ghi nhan, 01_PLAN Vong 10 muc 7) anh vao dang PNG trong thu muc dau ra moi: rc %s, %s" % (
        rc, "params_invalid" if "params_invalid" in se else se.strip()[-80:]))
    s.done()


class _FailDW:
    """csv.DictWriter hong giua chung (sau n dong) - loi BEN TRONG ham ghi that."""
    def __init__(self, n=5):
        self.n = n

    def __enter__(self):
        Real = le.csv.DictWriter
        n = self.n

        class F(Real):
            def writerow(self, row):
                self._k = getattr(self, "_k", 0) + 1
                if self._k > n:
                    raise OSError("tiem loi: dia day giua chung CSV")
                return super().writerow(row)
        self.p = Patch(le.csv, "DictWriter", F)
        self.p.__enter__()
        return self

    def __exit__(self, *a):
        self.p.__exit__()


def _fail_png_save(self, fp, *a, **k2):
    fp.write(b"\x89PNG\r\n\x1a\n\x00\x00")
    raise OSError("tiem loi: dia day giua chung PNG")


def _ls(d):
    return sorted(p.name for p in Path(d).iterdir()) if Path(d).exists() else []


def v10_t1():
    s = Sc("V10-T1", "A tao metadata du roi loi CSV hoac PNG, chua co B: metadata giu hash; dau ra cua A duoc don; cung cau hinh thu lai chay duoc, khac cau hinh params_mismatch")
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    for k in range(REPS):
        po, pn = pair_files("v10t1_%d_in" % k, seed=2300 + k)
        h_in = (sha(po), sha(pn))
        for kind in ("csv", "png"):
            run = TMP / ("v10t1_%d_%s" % (k, kind)) / "run"
            c0, a0 = run / "centers_0000.csv", run / "ann_0000.png"
            try:
                if kind == "csv":
                    with _FailDW():
                        le.process_pair(po, pn, csv_path=c0, **kw)
                else:
                    with Patch(Image.Image, "save", _fail_png_save):
                        le.process_pair(po, pn, csv_path=c0, annotate_path=a0, **kw)
                exc = None
            except Exception as e:  # noqa: BLE001
                exc = type(e).__name__
            pj = run / "params.json"
            d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
            h = sha(pj) if pj.exists() else None
            s.ok(exc is not None and _ls(run) == ["params.json"] and d == CFG6,
                 "lap %d (%s): A bao loi; CSV/PNG cua A duoc don; params.json con, dung 6 truong" % (k, kind),
                 "exc %s; %s" % (exc, _ls(run)))
            args = ["--csv", c0] + (["--annotate", a0] if kind == "png" else [])
            rc, _, se = cli("--off", po, "--on", pn, *BASE, *args)
            s.ok(rc == 0 and h and sha(pj) == h and c0.exists() and (kind == "csv" or a0.exists()),
                 "lap %d (%s): cung cau hinh, cung ten dau ra thu lai: chay duoc, params.json giu nguyen byte" % (k, kind), rc)
            snap = snapshot(run)
            rc, _, se = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0001.csv",
                            "--annotate", run / "ann_0001.png")
            s.ok(rc != 0 and "params_mismatch" in se and snapshot(run) == snap,
                 "lap %d (%s): khac cau hinh: params_mismatch, khong dau ra moi, thu muc giu nguyen" % (k, kind), rc)
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh tho giu hash" % k)
    s.done()


def v10_t2():
    s = Sc("V10-T2", "R09/L15: B da hoan tat CSV hoac PNG-only (tien trinh rieng) roi A loi: giu hash metadata va ket qua B; C khac cau hinh bi chan TRUOC ghi")
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    for k in range(REPS):
        po, pn = pair_files("v10t2_%d_in" % k, seed=2400 + k)
        h_in = (sha(po), sha(pn))
        for kind, b_args in (("csv", ["--csv", "centers_0001.csv"]), ("png", ["--annotate", "ann_0001.png"])):
            run = TMP / ("v10t2_%d_%s" % (k, kind)) / "run"
            a_csv, b_out = run / "centers_0000.csv", run / b_args[1]
            orig_w = le.write_centers_csv
            st = {}

            def a_writer(path, rows, _a=a_csv, _run=run, _b=b_args, _st=st):
                if os.path.normcase(str(path)) == os.path.normcase(str(_a)):
                    r = subprocess.run([PY, LE, "--off", str(po), "--on", str(pn), *BASE, _b[0], str(_run / _b[1])],
                                       cwd=REPO, capture_output=True, text=True, errors="replace")
                    _st["b_rc"] = r.returncode
                    _st["snap_b"] = snapshot(_run)
                    raise OSError("tiem loi: luot A hong khi ghi CSV")
                return orig_w(path, rows)
            with Patch(le, "write_centers_csv", a_writer):
                try:
                    le.process_pair(po, pn, csv_path=a_csv, **kw)
                    st["a"] = "ok"
                except Exception as e:  # noqa: BLE001
                    st["a"] = type(e).__name__
            snap_b = st.get("snap_b") or {}
            s.ok(st.get("b_rc") == 0 and st.get("a") != "ok" and b_out.name in snap_b and "params.json" in snap_b,
                 "lap %d (%s): B (tien trinh rieng) hoan tat truoc khi A loi" % (k, kind), "B rc %s; A %s" % (st.get("b_rc"), st.get("a")))
            s.ok(snapshot(run) == snap_b and not a_csv.exists(),
                 "lap %d (%s): sau khi A loi: params.json va ket qua cua B giu nguyen hash; khong con CSV cua A" % (k, kind), _ls(run))
            with WriteSpy() as spy:
                try:
                    le.process_pair(po, pn, csv_path=run / "centers_0002.csv", annotate_path=run / "ann_0002.png",
                                    **dict(kw, min_diff=30.0))
                    exc = None
                except Exception as e:  # noqa: BLE001
                    exc = str(e)
            s.ok(exc and "params_mismatch" in exc and sum(spy.calls.values()) == 0 and snapshot(run) == snap_b,
                 "lap %d (%s): C min_diff 30 (API): params_mismatch, 0 loi goi ham ghi, thu muc giu nguyen" % (k, kind),
                 "%s; goi ghi %s" % ((exc or "")[:50], dict(spy.calls)))
            rc, _, se = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0003.csv")
            s.ok(rc != 0 and "params_mismatch" in se and snapshot(run) == snap_b,
                 "lap %d (%s): C min_diff 30 (CLI): params_mismatch, thu muc giu nguyen" % (k, kind), rc)
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh tho giu hash" % k)
    s.done()


_B_WRAP = r'''
import sys, time, pathlib
sys.path.insert(0, sys.argv[1])
import line_extract as le
mode, reached, go = sys.argv[2], pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
def pause():
    reached.write_text(repr(time.time()))
    t0 = time.time()
    while not go.exists():
        if time.time() - t0 > 60:
            raise SystemExit("B: het han cho tin hieu chay tiep")
        time.sleep(0.02)
name = {"match": "check_or_match_params", "csv": "write_centers_csv", "png": "create_annotated_image"}[mode]
orig = getattr(le, name)
def hook(*a, **k):
    if mode == "match":
        r = orig(*a, **k); pause(); return r
    pause(); return orig(*a, **k)
setattr(le, name, hook)
sys.argv = ["line_extract.py"] + sys.argv[5:]
le.main()
'''


def v10_t3():
    s = Sc("V10-T3", "L16 qua TIEN TRINH RIENG: B dung ngay sau so khop / ngay truoc ghi CSV / ngay truoc ghi PNG; A loi trong khoang do; C khac cau hinh; B chay tiep")
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    wrap = TMP / "b_wrap.py"
    wrap.write_text(_B_WRAP, encoding="utf-8")
    for k in range(REPS):
        po, pn = pair_files("v10t3_%d_in" % k, seed=2500 + k)
        h_in = (sha(po), sha(pn))
        for mode, b_args in (("match", ["--csv", "centers_0001.csv"]), ("csv", ["--csv", "centers_0001.csv"]),
                             ("png", ["--annotate", "ann_0001.png"])):
            run = TMP / ("v10t3_%d_%s" % (k, mode)) / "run"
            sig = TMP / ("v10t3_%d_%s" % (k, mode)) / "sig"
            sig.mkdir(parents=True)
            reached, go = sig / "reached", sig / "go"
            a_csv, b_out = run / "centers_0000.csv", run / b_args[1]
            orig_w = le.write_centers_csv
            st = {}

            def a_writer(path, rows, _a=a_csv, _run=run, _b=b_args, _m=mode, _r=reached, _g=go, _st=st):
                if os.path.normcase(str(path)) == os.path.normcase(str(_a)):
                    _st["pj_a"] = sha(_run / "params.json")
                    _st["p"] = subprocess.Popen([PY, str(wrap), str(REPO / "pc"), _m, str(_r), str(_g), "--off", str(po),
                                                 "--on", str(pn), *BASE, _b[0], str(_run / _b[1])],
                                                cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
                    t0 = time.time()
                    while not _r.exists() and time.time() - t0 < 60 and _st["p"].poll() is None:
                        time.sleep(0.02)
                    _st["b_reached"] = _r.exists()
                    _st["t_fail"] = time.time()
                    raise OSError("tiem loi: luot A hong khi ghi CSV")
                return orig_w(path, rows)
            with Patch(le, "write_centers_csv", a_writer):
                try:
                    le.process_pair(po, pn, csv_path=a_csv, **kw)
                    st["a"] = "ok"
                except Exception as e:  # noqa: BLE001
                    st["a"] = type(e).__name__
            rc_c, _, se_c = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0002.csv")
            go.write_text("go", encoding="utf-8")
            b_rc, b_err = None, ""
            if "p" in st:
                try:
                    _, b_err = st["p"].communicate(timeout=90)
                    b_rc = st["p"].returncode
                except subprocess.TimeoutExpired:
                    st["p"].kill()
                    b_rc = "het han"
            t_reach = float(reached.read_text()) if reached.exists() else None
            fired = bool(st.get("b_reached") and st.get("a") not in (None, "ok") and t_reach is not None
                         and t_reach < st["t_fail"])
            s.ok(fired, "lap %d (%s): thu tu da kich hoat: B (tien trinh rieng) den diem chan truoc khi A loi" % (k, mode),
                 "B den %s; A %s" % (st.get("b_reached"), st.get("a")))
            pj = run / "params.json"
            d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
            s.ok(fired and b_rc == 0 and b_out.exists() and d == CFG6 and sha(pj) == st.get("pj_a") and not a_csv.exists(),
                 "lap %d (%s): B thanh cong voi dung metadata (hash nhu luc A tao), khong con CSV cua A" % (k, mode),
                 "B rc %s %s; %s; params.json %s" % (b_rc, (b_err or "").strip()[-60:], _ls(run),
                                                      "cau hinh B" if d == CFG6 else "MAT" if d is None else d))
            s.ok(rc_c != 0 and "params_mismatch" in se_c and not (run / "centers_0002.csv").exists(),
                 "lap %d (%s): C min_diff 30 bi chan truoc ghi" % (k, mode), rc_c)
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh tho giu hash" % k)
    s.done()


def v10_t4():
    s = Sc("V10-T4", "loi luu tru params.json: truoc mo / ghi mot phan / sau khi JSON du / luc dong; da tao thi khong xoa; khong dau ra; lan sau chan tep hong, tai dung tep du")
    import builtins
    real_open = builtins.open
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)

    class CloseFail:
        def __init__(self, f):
            self.f = f

        def __enter__(self):
            return self.f.__enter__()

        def __exit__(self, *a):
            self.f.__exit__(*a)
            raise OSError("tiem loi: loi luc dong params.json")
    for k in range(REPS):
        po, pn = pair_files("v10t4_%d_in" % k, seed=2600 + k)
        h_in = (sha(po), sha(pn))
        for case in ("truoc_mo", "mot_phan", "du_roi_loi", "luc_dong"):
            run = TMP / ("v10t4_%d_%s" % (k, case)) / "run"
            pj = run / "params.json"

            def op(file, mode="r", *a, _c=case, _t=pj, **k2):
                if os.path.normcase(str(file)) == os.path.normcase(str(_t)) and "x" in mode:
                    if _c == "truoc_mo":
                        raise PermissionError(13, "tiem loi: tu choi mo params.json", str(file))
                    if _c == "luc_dong":
                        return CloseFail(real_open(file, mode, *a, **k2))
                return real_open(file, mode, *a, **k2)
            real_dump = le.json.dump

            def dump(obj, f, *a, _c=case, _rd=real_dump, **k2):
                if _c == "mot_phan":
                    f.write('{"roi": [100, 50,')
                    f.flush()
                    raise OSError("tiem loi: dia day giua chung params.json")
                _rd(obj, f, *a, **k2)
                if _c == "du_roi_loi":
                    f.flush()
                    raise OSError("tiem loi: loi bao ve sau khi JSON da du")
            le.open = op
            try:
                with Patch(le.json, "dump", dump):
                    try:
                        le.process_pair(po, pn, csv_path=run / "centers_0000.csv", annotate_path=run / "ann_0000.png", **kw)
                        exc = None
                    except Exception as e:  # noqa: BLE001
                        exc = type(e).__name__
            finally:
                del le.open
            left = _ls(run)
            if case == "truoc_mo":
                s.ok(exc is not None and left == [], "lap %d (%s): bao loi, khong tao tep nao" % (k, case), "exc %s; %s" % (exc, left))
                continue
            txt = pj.read_text(encoding="utf-8") if pj.exists() else None
            s.ok(exc is not None and left == ["params.json"],
                 "lap %d (%s): bao loi; params.json da tao KHONG bi xoa; khong CSV/PNG" % (k, case), "exc %s; %s" % (exc, left))
            h = sha(pj) if pj.exists() else None
            rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0001.csv")
            if case == "mot_phan":
                s.ok(rc != 0 and "params_invalid" in se and sha(pj) == h and _ls(run) == ["params.json"],
                     "lap %d (%s): lan sau bi params_invalid, tep hong giu nguyen, khong CSV" % (k, case), "rc %s; noi dung %r" % (rc, txt))
            else:
                d = _json.loads(txt) if txt else None
                s.ok(d == CFG6 and rc == 0 and sha(pj) == h and (run / "centers_0001.csv").exists(),
                     "lap %d (%s): JSON da du -> lan sau cung cau hinh tai dung nguyen byte, chay duoc" % (k, case), rc)
                rc2, _, se2 = cli("--off", po, "--on", pn, *_args_with(["--min-diff", "30"]), "--csv", run / "centers_0002.csv")
                s.ok(rc2 != 0 and "params_mismatch" in se2 and sha(pj) == h and not (run / "centers_0002.csv").exists(),
                     "lap %d (%s): khac cau hinh -> params_mismatch, tep giu nguyen" % (k, case), rc2)
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh tho giu hash" % k)
    s.done()


def v10_t5():
    s = Sc("V10-T5", "tranh chap/dau vao: hai luot cung tao, doc khi params dang ghi do, tep ngoai lai chiem ten, thu muc co CSV/PNG thieu params")
    import threading
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    for k in range(REPS):
        po, pn = pair_files("v10t5_%d_in" % k, seed=2700 + k)
        h_in = (sha(po), sha(pn))
        # a. hai luot cung vuot buoc kiem (chua co params) roi cung mo 'x': cung cau hinh / khac cau hinh
        for case, md2 in (("cung", 20.0), ("khac", 30.0)):
            run = TMP / ("v10t5_%d_a_%s" % (k, case)) / "run"
            bar = threading.Barrier(2, timeout=30)
            orig_chk = le.check_or_match_params
            res = {}

            def chk(path, cfg, _bar=bar, _res=res):
                r = orig_chk(path, cfg)
                nm = threading.current_thread().name
                if nm in ("luot_1", "luot_2"):
                    try:
                        _bar.wait()
                        _res["bar_" + nm] = True
                    except threading.BrokenBarrierError:
                        pass
                return r
            cfgs = {"luot_1": dict(kw), "luot_2": dict(kw, min_diff=md2)}

            def worker(_run=run, _res=res, _cfgs=cfgs):
                nm = threading.current_thread().name
                try:
                    le.process_pair(po, pn, csv_path=_run / ("%s.csv" % nm), **_cfgs[nm])
                    _res[nm] = "ok"
                except Exception as e:  # noqa: BLE001
                    _res[nm] = type(e).__name__
            with Patch(le, "check_or_match_params", chk):
                ts = [threading.Thread(target=worker, name=n) for n in ("luot_1", "luot_2")]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(60)
            pj = run / "params.json"
            d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
            both = res.get("bar_luot_1") and res.get("bar_luot_2")
            winners = [n for n in ("luot_1", "luot_2") if res.get(n) == "ok"]
            good = bool(both and winners and d is not None and all(
                d["min_diff"] == cfgs[n]["min_diff"] and (run / ("%s.csv" % n)).exists() for n in winners) and all(
                not (run / ("%s.csv" % n)).exists() for n in ("luot_1", "luot_2") if res.get(n) != "ok"))
            s.ok(good, "lap %d (a-%s): hai luot cung tao: luot thua bao loi khong dau ra, khong xoa/doi params cua luot thang; moi CSV mang dung cau hinh" % (k, case),
                 "ca hai qua buoc kiem %s; %s; params min_diff %s; %s" % (bool(both), {n: res.get(n) for n in ("luot_1", "luot_2")},
                                                                         d and d["min_diff"], _ls(run)))
        # b. luot B doc params.json khi A dang ghi do
        run = TMP / ("v10t5_%d_b" % k) / "run"
        ev_bdone = threading.Event()
        real_dump = le.json.dump
        res = {}

        def b_run(_run=run, _res=res, _ev=ev_bdone):
            try:
                le.process_pair(po, pn, csv_path=_run / "centers_0001.csv", **kw)
                _res["b"] = "ok"
            except Exception as e:  # noqa: BLE001
                _res["b"] = str(e)
            _ev.set()

        def slow_dump(obj, f, *a, _res=res, _ev=ev_bdone, _rd=real_dump, **k2):
            if threading.current_thread() is threading.main_thread():
                txt = _json.dumps(obj, *a, **k2)
                f.write(txt[:len(txt) // 2])
                f.flush()
                t = threading.Thread(target=b_run, name="luot_B")
                t.start()
                _res["b_done"] = _ev.wait(30)
                f.write(txt[len(txt) // 2:])
                t.join(30)
                return None
            return _rd(obj, f, *a, **k2)
        with Patch(le.json, "dump", slow_dump):
            try:
                le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
                res["a"] = "ok"
            except Exception as e:  # noqa: BLE001
                res["a"] = repr(e)[:60]
        pj = run / "params.json"
        d = _json.loads(pj.read_text(encoding="utf-8")) if pj.exists() else None
        s.ok(bool(res.get("b_done") and res.get("a") == "ok" and d == CFG6 and (run / "centers_0000.csv").exists()
                  and ((res.get("b") == "ok" and (run / "centers_0001.csv").exists())
                       or ("params_invalid" in str(res.get("b")) and not (run / "centers_0001.csv").exists()))),
             "lap %d (b): B doc luc params dang ghi do: B loi ro rang (params_invalid) khong dau ra; A hoan tat, params dung" % k,
             "A %s; B %s; %s" % (res.get("a"), str(res.get("b"))[:70], _ls(run)))
        # c. tep ngoai lai chiem ten: params.json cua cong cu khac; CSV dau ra cung ten trong thu muc da co params
        run = TMP / ("v10t5_%d_c" % k) / "run"
        run.mkdir(parents=True)
        (run / "params.json").write_text('{"scan_id": "khac"}', encoding="utf-8")
        snap = snapshot(run)
        rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0000.csv")
        s.ok(rc != 0 and "params_invalid" in se and snapshot(run) == snap,
             "lap %d (c1): params.json cua cong cu khac: params_invalid, tep giu nguyen, khong dau ra" % k, rc)
        run = TMP / ("v10t5_%d_c2" % k) / "run"
        cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0000.csv")
        (run / "centers_0001.csv").write_text(FOREIGN_CSV, encoding="utf-8")
        snap = snapshot(run)
        rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0001.csv")
        s.ok(rc != 0 and len(snap) == 3 and snapshot(run) == snap,
             "lap %d (c2): CSV ngoai lai chiem ten dau ra: tu choi, CSV do va params giu nguyen" % k, rc)
        # d. thu muc co CSV / PNG ma thieu params.json
        for nm, data in (("centers_0000.csv", FOREIGN_CSV.encode()), ("ann_0000.png", FOREIGN_PNG)):
            run = TMP / ("v10t5_%d_d_%s" % (k, nm[:3])) / "run"
            run.mkdir(parents=True)
            (run / nm).write_bytes(data)
            snap = snapshot(run)
            rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0009.csv")
            s.ok(rc != 0 and "params_invalid" in se and snapshot(run) == snap,
                 "lap %d (d): thu muc co %s thieu params.json: params_invalid, khong tao params/CSV" % (k, nm), rc)
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh tho giu hash" % k)
    s.done()


V10_REF = "db4782bf973f57a907a16970a1d565e50e8d136b"  # ma Tester Vong 9 lan 2 da kiem (truoc khi sua vong doi metadata)


def v10_t6():
    s = Sc("V10-T6", "hoi quy thuat toan: CSV/PNG/params.json cua B10 trung tung byte voi ma %s tren cung dau vao" % V10_REF[:7])
    old = TMP / "le_ref" / "line_extract.py"
    old.parent.mkdir(parents=True)
    r = subprocess.run(["git", "show", V10_REF + ":pc/line_extract.py"], cwd=REPO, capture_output=True)
    if r.returncode != 0:
        s.ok(False, "lay ma tham chieu bang git show", r.stderr[-120:])
        s.done()
        return
    old.write_bytes(r.stdout)
    cases = [
        ("sach", dict(lines=[(320.0, 0.05, 4.0, 150.0)]), BASE),
        ("bao_hoa", dict(lines=[(300.0, 0.02, 5.0, 220.0)], sat_to=255), BASE),
        ("hai_vach", dict(lines=[(250.0, 0.0, 3.0, 120.0), (330.0, 0.0, 3.0, 120.0)]), BASE),
        ("yeu_nhieu", dict(lines=[(310.0, -0.03, 4.0, 18.0)], noise=6.0), BASE),
        ("mac_dinh_roi", dict(lines=[(200.0, 0.1, 3.0, 150.0)]), []),
    ]
    for i, (nm, mk, args) in enumerate(cases):
        off, on, _ = make_pair(seed=2800 + i, **mk)
        po, pn = save_pair("v10t6_%s" % nm, off, on)
        outs = {}
        for tag, exe in (("ref", str(old)), ("b10", LE)):
            d = TMP / ("v10t6_%s_%s" % (nm, tag))
            rr = subprocess.run([PY, exe, "--off", str(po), "--on", str(pn), *args, "--csv", str(d / "c.csv"),
                                 "--annotate", str(d / "a.png")], cwd=REPO, capture_output=True, text=True, errors="replace")
            outs[tag] = (rr.returncode, {f: sha(d / f) for f in ("c.csv", "a.png", "params.json") if (d / f).exists()})
        s.ok(outs["ref"][0] == 0 and outs["ref"] == outs["b10"] and len(outs["b10"][1]) == 3,
             "%s: rc va sha CSV/PNG/params.json trung nhau" % nm,
             "ref rc %s, b10 rc %s, %d tep" % (outs["ref"][0], outs["b10"][0], len(outs["b10"][1])))
    s.done()


def v10_r10():
    # R10 (04_REVIEW Vong 5): khong xac minh duoc thu muc da co ket qua hay chua -> params_invalid, dung truoc
    # moi ghi; tep cu giu nguyen, khong dau ra moi. Tiem OSError o tung diem + ACL THAT cam liet ke thu muc.
    s = Sc("V10-R10", "R10: loi liet ke thu muc / kiem tep / kiem metadata -> params_invalid truoc moi ghi; tep cu giu nguyen; kem ACL that cam liet ke (CLI)")
    kw = dict(roi_str="100,50,540,430", min_diff=20.0, max_width=30, sat_thresh=250.0)
    real_iterdir, real_is_file, real_exists, real_is_dir = Path.iterdir, Path.is_file, Path.exists, Path.is_dir

    def same(a, b):
        return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))
    for k in range(REPS):
        po, pn = pair_files("v10r10_%d_in" % k, seed=2900 + k)
        h_in = (sha(po), sha(pn))

        def c_iter(run):
            def f(self, _r=run):
                if same(self, _r):
                    raise PermissionError(13, "tiem loi: tu choi liet ke thu muc", str(self))
                return real_iterdir(self)
            return [(Path, "iterdir", f)]

        def c_iter_mid(run):
            def f(self, _r=run):
                if same(self, _r):
                    def g():
                        yield self / "ghi_chu.txt"
                        raise OSError(5, "tiem loi: loi I/O giua luc liet ke", str(self))
                    return g()
                return real_iterdir(self)
            return [(Path, "iterdir", f)]

        def c_isfile(run):
            def f(self, _r=run):
                if same(self.parent, _r) and self.suffix.lower() == ".csv":
                    raise PermissionError(13, "tiem loi: tu choi doc thuoc tinh tep", str(self))
                return real_is_file(self)
            return [(Path, "is_file", f)]

        def c_pj_exists(run):
            def f(self, _r=run):
                if same(self, _r / "params.json"):
                    raise PermissionError(13, "tiem loi: tu choi kiem params.json", str(self))
                return real_exists(self)
            return [(Path, "exists", f)]

        def c_parent(run):
            def f(self, _r=run):
                if same(self, _r):
                    raise PermissionError(13, "tiem loi: tu choi kiem thu muc cha", str(self))
                return real_exists(self)
            return [(Path, "exists", f)]

        def c_pj_isdir(run):
            def f(self, _r=run):
                if same(self, _r / "params.json"):
                    raise PermissionError(13, "tiem loi: tu choi kiem params.json la thu muc", str(self))
                return real_is_dir(self)
            return [(Path, "is_dir", f)]
        # (ten, ham tiem, dung san: "cu" = co CSV cu thieu params | "rong" = thu muc rong | "pj" = da co params hop le)
        cases = [("iterdir_co_csv_cu", c_iter, "cu"), ("iterdir_thu_muc_rong", c_iter, "rong"),
                 ("iterdir_loi_giua_chung", c_iter_mid, "cu"), ("is_file_csv_cu", c_isfile, "cu"),
                 ("exists_params", c_pj_exists, "pj"), ("exists_thu_muc_cha", c_parent, "cu"),
                 ("is_dir_params", c_pj_isdir, "pj")]
        for name, mk, setup in cases:
            run = TMP / ("v10r10_%d_%s" % (k, name)) / "run"
            run.mkdir(parents=True)
            if setup == "cu":
                (run / "centers_0000.csv").write_text(FOREIGN_CSV, encoding="utf-8")
            elif setup == "pj":
                le.process_pair(po, pn, csv_path=run / "centers_0000.csv", **kw)
            snap = snapshot(run)
            patches = [Patch(o, n, f) for (o, n, f) in mk(run)]
            with WriteSpy() as spy:
                for p in patches:
                    p.__enter__()
                try:
                    try:
                        le.process_pair(po, pn, csv_path=run / "centers_0001.csv", annotate_path=run / "ann_0001.png", **kw)
                        exc = None
                    except Exception as e:  # noqa: BLE001
                        exc = str(e)
                finally:
                    for p in reversed(patches):
                        p.__exit__()
            s.ok(exc is not None and "params_invalid" in exc and sum(spy.calls.values()) == 0 and snapshot(run) == snap,
                 "lap %d (%s): params_invalid, 0 loi goi ghi, thu muc giu nguyen (khong params/CSV/PNG moi)" % (k, name),
                 "%s; goi ghi %s; %s" % ((exc or "KHONG LOI")[:70], sum(spy.calls.values()), _ls(run)))
        # ACL that: cam liet ke (RD) nhung van cho tao tep - dung dieu kien Reviewer chua thu; chay CLI tien trinh rieng
        run = TMP / ("v10r10_%d_acl" % k) / "run"
        run.mkdir(parents=True)
        (run / "centers_0000.csv").write_text(FOREIGN_CSV, encoding="utf-8")
        snap = snapshot(run)
        user = os.environ.get("USERNAME", "")
        r = subprocess.run(["icacls", str(run), "/deny", user + ":(RD)"], capture_output=True, text=True, errors="replace")
        try:
            try:
                os.listdir(run)
                acl = False
            except PermissionError:
                acl = True
            s.ok(r.returncode == 0 and acl, "lap %d (acl): dung duoc ACL that (liet ke thu muc bi tu choi)" % k,
                 "icacls rc %s" % r.returncode)
            rc, _, se = cli("--off", po, "--on", pn, *BASE, "--csv", run / "centers_0001.csv", "--annotate", run / "ann_0001.png")
        finally:
            r2 = subprocess.run(["icacls", str(run), "/remove:d", user], capture_output=True, text=True, errors="replace")
        s.ok(acl and rc != 0 and "params_invalid" in se and r2.returncode == 0 and snapshot(run) == snap,
             "lap %d (acl): CLI rc != 0, params_invalid; sau khi go ACL thu muc chi con CSV cu, giu hash" % k,
             "rc %s; %s; con lai %s" % (rc, se.strip()[-70:], _ls(run)))
        s.ok((sha(po), sha(pn)) == h_in, "lap %d: anh tho giu hash" % k)
    s.done()


def main():
    print("Tester C3 - pc/line_extract.py; thu muc tam:", TMP)
    t0 = time.time()
    for f in (t1, t2a, t2a_jpeg, t2b, t2c, t3, t4, tx1, tx2, tx3, tx4, tx5, tx6, tx7, tx8, tx9, tx10, tx11, tx12, tx13, tx14,
              tx15, tx16, tx17, tx18, tx19, tx20, v7_t1, v7_t2, v7_t3, v7_order, v7_t4, v7_t5, v7_owner, v7_t6,
              v8_r08, v8_heur, v9_r09, v9_gap, v9_note, v10_t1, v10_t2, v10_t3, v10_t4, v10_t5, v10_t6,
              v10_r10):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            SUMMARY.append((f.__name__.upper(), "FAIL", "ngoai le trong kich ban: %r" % e))
    print("\nMa        KQ    Kich ban")
    for sid, st, title in SUMMARY:
        print("%-9s %-5s %s" % (sid, st, title))
    nf = sum(1 for x in SUMMARY if x[1] == "FAIL")
    print("\nTONG: %d PASS, %d FAIL, %d NOTE, %d kich ban, %.0f s" % (
        sum(1 for x in SUMMARY if x[1] == "PASS"), nf, sum(1 for x in SUMMARY if x[1] == "NOTE"), len(SUMMARY), time.time() - t0))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
