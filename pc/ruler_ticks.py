#!/usr/bin/env python3
"""
ruler_ticks.py - do khach quan hai thu tren anh khao sat quang hoc, bo sung
cho sharpness.py:

1. Chu ky vach cm cua thuoc dung (px/cm) bang ho so cuong do theo hang trong
   mot dai cot, detrend, tu tuong quan; roi tim cuc tieu (vach toi) va khop
   tuyen tinh y = a + b*k. Cho mm/pixel va truong nhin ma khong can doc toa
   do bang tay; dong thoi sinh chuoi --ruler cho sharpness.py tu hai dau
   cua duong khop.
2. Be rong mep (edge width): tren mot canh thang dung cua vat (vat toi tren
   nen tuong sang), lay ho so ngang tung hang, do be rong vung chuyen
   10 %-90 % giua hai muc on dinh hai ben, lay trung vi qua cac hang. Tinh
   bang px va quy ra mm o mat vat. Khac lap_var, so nay KHONG loi cho vat o
   xa, nen dung de so do net vat ly giua cac khoang cach.

Cach dung, chay tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/ruler_ticks.py --selftest
  .venv/Scripts/python.exe pc/ruler_ticks.py capture_qh_200mm --band 318,338,4,182 --lag 25,70 --edge 255,200,380
  .venv/Scripts/python.exe pc/ruler_ticks.py capture_qh_200mm --band ... --edge ... --json docs/logs/ten.json

--band X0,X1,Y0,Y1 : dai cot chua vach thuoc, tren nen tuong (khong de len vat).
--lag LO,HI        : khoang chu ky px cho phep (tranh bat boi 2x khi tin hieu yeu).
--edge X,Y0,Y1     : canh thang dung o gan cot X, do trong cac hang Y0..Y1;
                     ho so lay tu X-20 toi X+20.
Moi anh img_*.jpg cua phien deu duoc do; ket qua in ra va ghi JSON neu co --json.

Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = REPO_ROOT / "data" / "raw"
LF = chr(10)


def detrended_profile(gray, x0, x1, y0, y1, win=61):
    band = gray[y0:y1, x0:x1].mean(axis=1)
    pad = np.pad(band, (win // 2, win // 2), mode="edge")
    trend = np.convolve(pad, np.ones(win) / win, mode="valid")
    return band - trend


def autocorr_period(sig, lo, hi):
    """Chu ky (px) tu dinh tu tuong quan trong [lo, hi), noi suy parabol."""
    s = sig - sig.mean()
    ac = np.correlate(s, s, mode="full")[len(s) - 1:]
    if ac[0] <= 0:
        return None, 0.0
    ac = ac / ac[0]
    hi = min(hi, len(ac) - 1)
    if hi <= lo:
        return None, 0.0
    lag = lo + int(np.argmax(ac[lo:hi]))
    frac = 0.0
    if 1 <= lag < len(ac) - 1:
        y0, y1, y2 = ac[lag - 1], ac[lag], ac[lag + 1]
        denom = y0 - 2 * y1 + y2
        if denom != 0:
            frac = 0.5 * (y0 - y2) / denom
    return lag + frac, float(ac[lag])


def find_minima(sig, period, y_offset):
    thr = -0.5 * sig.std()
    idx = [i for i in range(1, len(sig) - 1) if sig[i] < sig[i - 1] and sig[i] <= sig[i + 1] and sig[i] < thr]
    keep = []
    for i in idx:
        if keep and i - keep[-1] < 0.6 * period:
            if sig[i] < sig[keep[-1]]:
                keep[-1] = i
        else:
            keep.append(i)
    return [i + y_offset for i in keep]


def fit_grid(ys, period):
    """Gan chi so k cho tung vach theo chu ky uoc, khop y = a + b*k."""
    ys = np.asarray(ys, dtype=float)
    k = np.round((ys - ys[0]) / period).astype(int)
    A = np.vstack([np.ones_like(k), k]).T
    (a, b), _, _, _ = np.linalg.lstsq(A, ys, rcond=None)
    resid = ys - (a + b * k)
    return float(a), float(b), k, resid


def edge_width_rows(gray, x, y0, y1, half=20):
    """Be rong 10-90 % cua mep thang dung gan cot x, tung hang; tra mang px."""
    widths = []
    for y in range(y0, y1):
        prof = gray[y, max(0, x - half):x + half]
        if prof.size < 10:
            continue
        lo_lvl = np.median(prof[:5])
        hi_lvl = np.median(prof[-5:])
        if abs(hi_lvl - lo_lvl) < 20:
            continue  # khong co mep ro trong hang nay
        a, b = sorted((lo_lvl, hi_lvl))
        t10, t90 = a + 0.1 * (b - a), a + 0.9 * (b - a)
        # vi tri cat nguong bang noi suy tuyen tinh, di tu trai sang
        def cross(level):
            for i in range(len(prof) - 1):
                p0, p1 = prof[i], prof[i + 1]
                if (p0 - level) * (p1 - level) <= 0 and p0 != p1:
                    return i + (level - p0) / (p1 - p0)
            return None
        c10, c90 = cross(t10), cross(t90)
        if c10 is None or c90 is None:
            continue
        widths.append(abs(c90 - c10))
    return np.asarray(widths)


def analyze_image(gray, band, lag, edge):
    out = {}
    if band:
        x0, x1, y0, y1 = band
        prof = detrended_profile(gray, x0, x1, y0, y1)
        per, strength = autocorr_period(prof, lag[0], lag[1])
        out["period_px"] = None if per is None else round(per, 2)
        out["ac_strength"] = round(strength, 3)
        out["_profile"] = prof
    if edge:
        x, ey0, ey1 = edge
        w = edge_width_rows(gray, x, ey0, ey1)
        out["edge_rows_used"] = int(w.size)
        out["edge_width_px_median"] = None if w.size == 0 else round(float(np.median(w)), 2)
    return out


def analyze_session(session_dir, band, lag, edge):
    """Do moi anh img_NNNN.jpg cua phien. Raise ValueError khi phien rong, anh khac
    kich thuoc nhau, hoac vung do nam ngoai anh (R09)."""
    rows = []
    profs = []
    width = height = None
    files = [p for p in sorted(session_dir.glob("img_*.jpg")) if p.stem[4:].isdigit()]
    if not files:
        raise ValueError("%s: khong co anh img_NNNN.jpg de do" % session_dir.name)
    for p in files:
        with Image.open(p) as im:
            g = np.asarray(im.convert("L"), dtype=float)
            w, h = im.size
        if width is None:
            width, height = w, h
            validate_regions(band, lag, edge, width, height)
        elif (w, h) != (width, height):
            raise ValueError("%s: anh %s %dx%d khac anh dau %dx%d" % (session_dir.name, p.name, w, h, width, height))
        r = analyze_image(g, band, lag, edge)
        prof = r.pop("_profile", None)
        if prof is not None:
            profs.append(prof)
        r["file"] = p.name
        rows.append(r)
    summary = {"session_id": session_dir.name, "n_images": len(rows), "width": width, "height": height,
               "band": band, "lag": lag, "edge": edge, "images": rows}
    if band and profs:
        mean_prof = np.mean(profs, axis=0)
        per, strength = autocorr_period(mean_prof, lag[0], lag[1])
        summary["period_mean_profile_px"] = None if per is None else round(per, 2)
        summary["ac_strength_mean_profile"] = round(strength, 3)
        if per:
            ys = find_minima(mean_prof, per, band[2])
            summary["tick_y"] = ys
            if len(ys) >= 2:
                a, b, k, resid = fit_grid(ys, per)
                xc = (band[0] + band[1]) / 2.0
                y_first, y_last = a, a + b * k[-1]
                summary["fit_px_per_cm"] = round(b, 3)
                summary["fit_resid_max_px"] = round(float(np.abs(resid).max()), 2)
                summary["n_ticks"] = len(ys)
                summary["mm_per_px"] = round(10.0 / b, 4)
                summary["fov_w_mm"] = round(width * 10.0 / b, 1)
                summary["fov_h_mm"] = round(height * 10.0 / b, 1)
                summary["ruler_arg"] = "%s=%.1f,%.1f,%.1f,%.1f,%d" % (session_dir.name, xc, y_first, xc, y_last, int(k[-1]) * 10)
    if edge:
        ws = [r["edge_width_px_median"] for r in rows if r.get("edge_width_px_median") is not None]
        if ws:
            summary["edge_width_px_median"] = round(float(np.median(ws)), 2)
            if summary.get("mm_per_px"):
                summary["edge_width_mm"] = round(summary["edge_width_px_median"] * summary["mm_per_px"], 3)
    return summary


def fmt(summary):
    s = summary
    lines = ["Phien %s: %d anh %sx%s" % (s["session_id"], s["n_images"], s["width"], s["height"])]
    if s.get("band"):
        pers = [r.get("period_px") for r in s["images"]]
        lines.append("  chu ky tung anh (px)  : %s" % ", ".join("%.2f" % p if p else "-" for p in pers))
        lines.append("  tu tuong quan         : %s" % ", ".join("%.2f" % r.get("ac_strength", 0) for r in s["images"]))
        if s.get("fit_px_per_cm"):
            lines.append("  vach cm tim thay      : %d tai y = %s" % (s["n_ticks"], s["tick_y"]))
            lines.append("  khop thang            : %.3f px/cm, sai lech toi da %.2f px" % (s["fit_px_per_cm"], s["fit_resid_max_px"]))
            lines.append("  mm/pixel              : %.4f  -> truong nhin %.1f x %.1f mm" % (s["mm_per_px"], s["fov_w_mm"], s["fov_h_mm"]))
            lines.append("  --ruler cho sharpness : %s" % s["ruler_arg"])
        else:
            lines.append("  KHONG khop duoc vach; chu ky ho so trung binh = %s" % s.get("period_mean_profile_px"))
    if s.get("edge"):
        ws = [r.get("edge_width_px_median") for r in s["images"]]
        lines.append("  be rong mep tung anh  : %s px" % ", ".join("%.2f" % w if w else "-" for w in ws))
        if s.get("edge_width_px_median") is not None:
            mm = s.get("edge_width_mm")
            lines.append("  be rong mep trung vi  : %.2f px%s" % (s["edge_width_px_median"], " = %.3f mm o mat vat" % mm if mm else ""))
    return LF.join(lines)


def parse_ints(text, n, name):
    parts = text.split(",")
    if len(parts) != n:
        raise ValueError("%s can %d so" % (name, n))
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        raise ValueError("%s: cac gia tri phai la so nguyen" % name)
    if min(vals) < 0:
        raise ValueError("%s: cac gia tri phai >= 0" % name)
    return vals


def validate_regions(band, lag, edge, width, height):
    """Kiem --band/--lag/--edge theo kich thuoc anh (R09). Raise ValueError neu sai.

    Nguoi dung nhap vung theo pixel doc tu anh, nen nhap lech khung, dao thu
    tu hay lag rong la tinh huong thuong gap; truoc day cho ra NaN, 0 hoac
    IndexError thay vi mot loi doc duoc.
    """
    if band:
        x0, x1, y0, y1 = band
        if not (0 <= x0 < x1 <= width):
            raise ValueError("--band: can 0 <= X0 < X1 <= %d (nhan %d,%d)" % (width, x0, x1))
        if not (0 <= y0 < y1 <= height):
            raise ValueError("--band: can 0 <= Y0 < Y1 <= %d (nhan %d,%d)" % (height, y0, y1))
        if y1 - y0 < 3:
            raise ValueError("--band: dai qua ngan (< 3 hang)")
    if lag is not None:
        lo, hi = lag
        if not (0 < lo < hi):
            raise ValueError("--lag: can 0 < LO < HI (nhan %d,%d)" % (lo, hi))
    if edge:
        x, ey0, ey1 = edge
        if not (0 <= x < width):
            raise ValueError("--edge: X phai trong [0, %d) (nhan %d)" % (width, x))
        if not (0 <= ey0 < ey1 <= height):
            raise ValueError("--edge: can 0 <= Y0 < Y1 <= %d (nhan %d,%d)" % (height, ey0, ey1))


def selftest():
    ok = True

    def check(cond, label):
        nonlocal ok
        print("  %-60s %s" % (label, "OK" if cond else "FAIL"))
        ok = ok and cond

    # 1. Thuoc tong hop: nen 220, vach toi rong 2 px moi 37.5 px, tu y=10
    g = np.full((300, 100), 220.0)
    true_period = 37.5
    ticks = [10 + i * true_period for i in range(7)]
    for t in ticks:
        g[int(round(t)):int(round(t)) + 2, 40:60] = 60.0
    prof = detrended_profile(g, 40, 60, 0, 300)
    per, st = autocorr_period(prof, 20, 60)
    check(per is not None and abs(per - true_period) < 0.6, "autocorr: chu ky %.2f gan 37.5" % (per or -1))
    check(st > 0.5, "autocorr: dinh ro (%.2f > 0.5)" % st)
    ys = find_minima(prof, per, 0)
    check(len(ys) == 7, "minima: tim thay 7 vach (%d)" % len(ys))
    a, b, k, resid = fit_grid(ys, per)
    check(abs(b - true_period) < 0.3 and np.abs(resid).max() < 1.5, "fit_grid: %.3f px/cm, resid %.2f" % (b, np.abs(resid).max()))

    # 2. Bat boi 2x khi lag qua rong -> nguoi dung phai thu hep --lag
    per2, _ = autocorr_period(prof, 60, 90)
    check(per2 is not None and abs(per2 - 2 * true_period) < 1.0, "autocorr: lag 60-90 bat boi 2x (%.1f) -> can --lag hep" % (per2 or -1))

    # 3. Mep tong hop: buoc 60->220 tai x=50, lam mo bang trung binh truot 5 px
    e = np.full((40, 100), 60.0)
    e[:, 50:] = 220.0
    kern = np.ones(5) / 5
    e_blur = np.vstack([np.convolve(row, kern, mode="same") for row in e])
    w_sharp = edge_width_rows(e, 50, 5, 35)
    w_blur = edge_width_rows(e_blur, 50, 5, 35)
    check(w_sharp.size > 0 and np.median(w_sharp) < 1.0, "edge: buoc sac cho be rong < 1 px (%.2f)" % np.median(w_sharp))
    check(w_blur.size > 0 and 3.0 < np.median(w_blur) < 5.0, "edge: mo 5 px cho be rong 3-5 px (%.2f)" % np.median(w_blur))
    check(edge_width_rows(np.full((10, 100), 128.0), 50, 0, 10).size == 0, "edge: khong co mep -> khong co hang")

    # 4. Phien gia tren dia
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sd = Path(td) / "capture_fake"
        sd.mkdir()
        img = np.full((240, 320), 220.0)
        for i in range(6):
            y = 8 + int(round(i * 30.0))
            img[y:y + 2, 150:170] = 60.0
        img[170:230, 100:200] = 90.0  # vat toi, nam DUOI dai cot thuoc nhu dieu kien dung
        for i in range(3):
            Image.fromarray(img.astype(np.uint8), mode="L").convert("RGB").save(sd / ("img_%04d.jpg" % (i + 1)), quality=95)
        s = analyze_session(sd, [150, 170, 0, 165], [20, 45], [100, 175, 225])
        check(s["n_images"] == 3, "analyze_session: 3 anh")
        check(s.get("fit_px_per_cm") and abs(s["fit_px_per_cm"] - 30.0) < 0.5, "analyze_session: 30 px/cm (%.2f)" % (s.get("fit_px_per_cm") or -1))
        check(abs(s["fov_w_mm"] - 320 / 3.0) < 2, "analyze_session: FOV 106.7 mm (%.1f)" % s["fov_w_mm"])
        check(s.get("edge_width_px_median") is not None and s["edge_width_px_median"] < 2.0, "analyze_session: mep JPEG sac < 2 px (%.2f)" % (s.get("edge_width_px_median") or -1))
        check(s["ruler_arg"].startswith("capture_fake=160.0,"), "analyze_session: ruler_arg co ID va x giua dai")

        # 5. R09: dau vao sai phai bao loi ro, khong NaN/IndexError
        def raises(fn, *a):
            try:
                fn(*a)
                return False
            except ValueError:
                return True
        check(raises(analyze_session, sd, None, [20, 45], [100, 0, 999]), "edge Y1=999 ngoai anh 240 -> ValueError (truoc: IndexError)")
        check(raises(analyze_session, sd, [20, 10, 0, 200], [20, 45], None), "band X0>X1 -> ValueError (truoc: NaN)")
        check(raises(analyze_session, sd, [150, 170, 0, 165], [45, 20], None), "lag LO>HI -> ValueError")
        check(raises(analyze_session, sd, [150, 170, 0, 165], [20, 45], [500, 0, 100]), "edge X ngoai be rong -> ValueError")
        check(raises(parse_ints, "1,-2,3,4", 4, "--band"), "parse_ints: so am bi tu choi")
        check(raises(parse_ints, "1,x,3,4", 4, "--band"), "parse_ints: chu bi tu choi")
        empty = Path(td) / "capture_empty"
        empty.mkdir()
        (empty / "img_0001_try1.jpg").write_bytes(b"x")
        check(raises(analyze_session, empty, [150, 170, 0, 165], [20, 45], None), "phien rong (chi co img_NNNN_tryK) -> ValueError, khong in 640x480 gia")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="?", help="thu muc phien hoac ten phien trong data/raw/")
    ap.add_argument("--band", help="X0,X1,Y0,Y1 dai cot vach thuoc tren nen tuong")
    ap.add_argument("--lag", default="15,70", help="LO,HI khoang chu ky px (mac dinh 15,70)")
    ap.add_argument("--edge", help="X,Y0,Y1 canh thang dung cua vat de do be rong mep")
    ap.add_argument("--json", help="ghi ket qua JSON vao tep nay (khong ghi de)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.session:
        ap.error("can ten phien (hoac --selftest)")
    if not args.band and not args.edge:
        ap.error("can --band va/hoac --edge")
    try:
        band = parse_ints(args.band, 4, "--band") if args.band else None
        lag = parse_ints(args.lag, 2, "--lag")
        edge = parse_ints(args.edge, 3, "--edge") if args.edge else None
    except ValueError as e:
        print("Loi tham so:", e)
        return 2
    p = Path(args.session)
    sd = p if p.is_dir() else RAW_ROOT / args.session
    if not sd.is_dir():
        print("khong thay thu muc phien:", sd)
        return 2
    try:
        s = analyze_session(sd.resolve(), band, lag, edge)
    except (ValueError, OSError) as e:
        print("Loi:", e)
        return 3
    print(fmt(s))
    if args.json:
        out = (REPO_ROOT / args.json).resolve()
        if out.exists():
            print("Tep JSON da ton tai, khong ghi de:", out)
            return 4
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s, indent=2, ensure_ascii=False) + LF, encoding="utf-8", newline=LF)
        print("Da ghi:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
