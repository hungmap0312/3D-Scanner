#!/usr/bin/env python3
"""
capture_session.py - thu anh thu tu ESP32-S3 CameraWebServer qua /capture.

Phuc vu chi tieu B "Thu anh thu" cua tuan 1 trong roadmap: 100/100 tep
nhan duoc giai ma dung va dung kich thuoc, khong reset trong 20 phut, ghi
so lan phai chup lai.

Quy uoc theo data/README.md:
  - Moi lan chay la MOT PHIEN co ID rieng, thu muc rieng, khong ghi de.
    Ca thu muc anh lan thu muc --meta-copy deu bi tu choi neu da ton tai.
  - JPEG giu NGUYEN GOC dung nhu nhan tu bo: ghi thang bytes, khong chuyen ma.
  - Metadata ghi: commit nguon (sketch va script cung repo), trang thai
    working tree, cau hinh camera doc tu /status truoc va sau phien, thoi
    gian tung anh, ket qua kiem tra giai ma va kich thuoc, so lan chup lai,
    moi loi. Truong chua co o tuan 1 (calibration_id, goc, laser) ghi ro
    "chua ap dung", khong dien gia tri gia.
  - Moi LAN THU (attempt) deu duoc ghi: attempts.jsonl mot dong moi lan,
    payload cua lan thu KHONG dat luu rieng img_NNNN_tryK.jpg (neu la JPEG)
    hoac .bin (neu la body loi HTTP). Anh cuoi cung duoc chon la img_NNNN.jpg.

Phat hien reset: header X-Timestamp cua /capture la gettimeofday tren bo,
khong co NTP nen no la thoi gian tu luc khoi dong. Neu gia tri nay LUI lai
giua hai anh thi bo da khoi dong lai. Ngoai ra dem loi ket noi.
Anh THIEU hoac SAI X-Timestamp la loi cua anh do: khong co du lieu thi
khong ket luan duoc "khong reset", phien FAIL.

Phat hien anh cu: so sha256 voi anh truoc, va so X-Timestamp voi anh truoc.
Hai bo dem nay chi de theo doi o tuan 1; tieu chi "anh moi" cho cap OFF/ON
se dinh nghia rieng o tuan 2 (C5), khong dung hash giong nhau lam bang
chung duy nhat.

Doi chieu /status dau-cuoi: chi khi CA HAI lan doc deu la JSON object co
truong bat buoc thi moi noi "khong doi" hay "doi o cac truong ...". Khong
doc duoc mot dau thi ghi "KHONG DOI CHIEU DUOC" va phien FAIL, khong ngam
hieu la khong doi.

Cach dung, chay tu goc repo:
  .venv/Scripts/python.exe pc/capture_session.py --selftest
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize VGA
  .venv/Scripts/python.exe pc/capture_session.py --host 192.168.31.9 --framesize SVGA --count 100 --interval 12

Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Chi so framesize cua core esp32 3.3.11, doc tu
# tools/esp32s3-libs/3.3.11/include/espressif__esp32-camera/driver/include/sensor.h
# LUU Y: khac bang cu trong nhieu tai lieu (o do VGA=8, SVGA=9).
FRAMESIZES = {
    "QVGA": (6, 320, 240),
    "VGA": (10, 640, 480),
    "SVGA": (11, 800, 600),
    "XGA": (12, 1024, 768),
    "HD": (13, 1280, 720),
    "SXGA": (14, 1280, 1024),
    "UXGA": (15, 1600, 1200),
}
INDEX_TO_NAME = {v[0]: k for k, v in FRAMESIZES.items()}
INDEX_TO_WH = {v[0]: (v[1], v[2]) for v in FRAMESIZES.values()}

# Truong bat buoc trong JSON /status cua CameraWebServer de coi la doc duoc.
STATUS_REQUIRED = ("framesize",)

REPO_ROOT = Path(__file__).resolve().parent.parent
LF = chr(10)


# ----------------------------------------------------------------------
# Phan khong can bo: kiem tra anh, hash, parse timestamp, phan loai
# phan hoi, doi chieu /status. Co selftest.
# ----------------------------------------------------------------------

def verify_jpeg(data):
    """Tra (decode_ok, width, height, loi). Khong doi du lieu.

    Image.verify() cua Pillow chi soi cau truc dau tep; JPEG bi cat giua
    chung van qua duoc (selftest da bat duoc). Vi vay: kiem SOI FF D8 dau
    tep, EOI FF D9 cuoi tep, va ep giai ma toan bo pixel bang load().

    GIOI HAN DA BIET, selftest cung da bat: neu du lieu quet bi thieu nhung
    van co EOI o cuoi thi libjpeg giai ma "thanh cong" voi phan duoi mau xam,
    Pillow khong bao loi. Ham nay khong chan duoc ca do. Trong phien chup,
    ca truyen thieu thuc su duoc bat bang Content-Length khop so byte nhan.
    """
    try:
        from PIL import Image
    except ImportError:
        return False, 0, 0, "thieu Pillow"
    if len(data) < 4:
        return False, 0, 0, "qua ngan"
    if data[0] != 0xFF or data[1] != 0xD8:
        return False, 0, 0, "khong bat dau bang SOI FF D8"
    if data[-2] != 0xFF or data[-1] != 0xD9:
        return False, 0, 0, "khong ket thuc bang EOI FF D9, nghi bi cat"
    try:
        im = Image.open(io.BytesIO(data))
        fmt = im.format
        if fmt != "JPEG":
            return False, im.size[0], im.size[1], "dinh dang %s, khong phai JPEG" % fmt
        im.load()  # giai ma that; Pillow bao loi neu du lieu thieu
        w, h = im.size
        return True, w, h, ""
    except Exception as e:
        return False, 0, 0, "giai ma loi: %s" % e


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def parse_x_timestamp(value):
    """'12.345678' -> so mili giay >= 0, hoac None. Khong dung regex."""
    if not value:
        return None
    parts = value.strip().split(".")
    if len(parts) > 2:
        return None
    try:
        sec = int(parts[0])
        usec = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    except ValueError:
        return None
    if sec < 0 or usec < 0:
        return None
    return sec * 1000 + usec // 1000


def normalize_headers(headers):
    """Ten header ve chu thuong de tra cuu khong phan biet hoa/thuong.

    requests tra CaseInsensitiveDict, nhung dict(...) lam mat tinh chat do;
    truoc day 'x-timestamp' hop le bi coi la thieu (review 20/09 R03).
    """
    if not headers:
        return {}
    return {str(k).lower(): v for k, v in headers.items()}


def hget(headers, name, default=""):
    return normalize_headers(headers).get(name.lower(), default) if headers else default


def parse_status(code, body, err):
    """Bien mot phan hoi /status thanh ho so co co 'ok' ro rang.

    ok chi khi HTTP 200, body la JSON object va co du STATUS_REQUIRED.
    reason noi vi sao khong ok; khong bao gio suy 'khong doi' tu ho so
    khong ok (review 20/09 R02).
    """
    text = body.decode("utf-8", errors="replace") if body else ""
    out = {"http_status": code, "error": err, "raw": text, "json": None, "ok": False, "reason": ""}
    if err:
        out["reason"] = "loi ket noi: %s" % err
        return out
    if code != 200:
        out["reason"] = "http %s" % code
        return out
    if not text.strip():
        out["reason"] = "body rong"
        return out
    try:
        parsed = json.loads(text)
    except ValueError as e:
        out["reason"] = "khong phai JSON: %s" % e
        return out
    if not isinstance(parsed, dict):
        out["reason"] = "JSON khong phai object (%s)" % type(parsed).__name__
        return out
    missing = [k for k in STATUS_REQUIRED if k not in parsed]
    if missing:
        out["json"] = parsed
        out["reason"] = "thieu truong %s" % ",".join(missing)
        return out
    out["json"] = parsed
    out["ok"] = True
    return out


def status_dict_from_json(status_json, reason=""):
    """Dung lai dinh dang cua parse_status() tu mot JSON da co san (khong
    doc lai bytes tho), de ghi status_after_set.json khi dung --profile:
    ap_and_verify() cua camera_profile.py da doc va parse /status roi."""
    if status_json is None:
        return {"http_status": 0, "error": "", "raw": "", "json": None, "ok": False, "reason": reason}
    text = json.dumps(status_json, ensure_ascii=False)
    return {"http_status": 200, "error": "", "raw": text, "json": status_json, "ok": True, "reason": ""}


def compare_status(st_a, st_b):
    """Doi chieu hai ho so /status. Tra dict phan biet ro ba tinh huong:
    khong doi chieu duoc / da doi chieu, khong doi / da doi chieu, doi."""
    if not (st_a and st_a.get("ok")) or not (st_b and st_b.get("ok")):
        why = []
        if not (st_a and st_a.get("ok")):
            why.append("dau: %s" % (st_a.get("reason") if st_a else "khong co"))
        if not (st_b and st_b.get("ok")):
            why.append("cuoi: %s" % (st_b.get("reason") if st_b else "khong co"))
        return {"compared": False, "changed": None, "fields_compared": 0, "reason": "; ".join(why)}
    a, b = st_a["json"], st_b["json"]
    keys = set(a) | set(b)
    changed = {k: [a.get(k), b.get(k)] for k in sorted(keys) if a.get(k) != b.get(k)}
    return {"compared": True, "changed": changed, "fields_compared": len(keys), "reason": ""}


def describe_compare(cmp):
    if not cmp["compared"]:
        return "KHONG DOI CHIEU DUOC (%s)" % cmp["reason"]
    if cmp["changed"]:
        return "DOI o %d/%d truong: %s" % (len(cmp["changed"]), cmp["fields_compared"], cmp["changed"])
    return "khong doi (da doi chieu %d truong)" % cmp["fields_compared"]


def classify_capture(code, headers, body, err, expected):
    """Phan loai mot phan hoi /capture. Thuan tuy, thu duoc khong can bo.

    Tra dict: decode_ok, width, height, size_ok, cl_ok, content_length_hdr,
    x_timestamp, ts_ms, error. error rong <=> anh dat.
    """
    d_ok, w, h, derr = (False, 0, 0, "")
    if code == 200 and body:
        d_ok, w, h, derr = verify_jpeg(body)
    size_ok = d_ok and expected is not None and (w, h) == tuple(expected)
    cl_hdr = hget(headers, "Content-Length", "")
    cl_ok = True
    cl_err = ""
    if cl_hdr:
        try:
            cl_ok = int(cl_hdr) == len(body)
            if not cl_ok:
                cl_err = "Content-Length %s khac so byte nhan %d: truyen thieu" % (cl_hdr, len(body))
        except ValueError:
            cl_ok = False
            cl_err = "Content-Length khong phai so: %r" % cl_hdr
    ts_raw = hget(headers, "X-Timestamp", "")
    ts_ms = parse_x_timestamp(ts_raw)
    if err:
        error = err
    elif code != 200:
        error = "http %s" % code
    elif not body:
        error = "body rong"
    elif cl_err:
        error = cl_err
    elif derr:
        error = derr
    elif expected is not None and not size_ok:
        error = "kich thuoc %dx%d khac mong doi %s" % (w, h, tuple(expected))
    elif ts_ms is None:
        error = "thieu hoac sai X-Timestamp %r: khong kiem duoc reset" % ts_raw
    else:
        error = ""
    return {
        "decode_ok": d_ok, "width": w, "height": h, "size_ok": size_ok,
        "cl_ok": cl_ok, "content_length_hdr": cl_hdr,
        "x_timestamp": ts_raw, "ts_ms": ts_ms, "error": error,
    }


def payload_suffix(body):
    """JPEG hay body loi? De dat ten tep luu payload cua lan thu khong dat."""
    return ".jpg" if body[:2] == bytes([0xFF, 0xD8]) else ".bin"


def reserve_dir(path):
    """Tao thu muc moi; tra (ok, ly do). Khong bao gio ghi de (R05)."""
    p = Path(path)
    if p.exists():
        return False, "da ton tai: %s" % p
    try:
        p.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return False, "da ton tai (tao dong thoi): %s" % p
    except OSError as e:
        return False, "khong tao duoc %s: %s" % (p, e)
    return True, ""


def validate_args(args):
    """Tra chuoi loi hoac '' . count 0 tung cho PASS 0/0 (ma tran review 20/09)."""
    if args.count < 1:
        return "--count phai >= 1 (nhan duoc %s)" % args.count
    if args.interval < 0:
        return "--interval phai >= 0"
    if args.warmup < 0:
        return "--warmup phai >= 0"
    if args.max_retries < 0:
        return "--max-retries phai >= 0"
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        return "--timeout phai la so huu han > 0"
    if args.framesize and args.framesize not in FRAMESIZES:
        return "framesize khong hop le. Chon mot trong: " + ", ".join(FRAMESIZES)
    if args.profile and args.framesize:
        return "--profile va --framesize khong dung cung luc: ho so da co framesize"
    return ""


def git_info():
    """Commit, nhanh, working tree ban hay sach."""
    info = {"commit": "khong doc duoc", "branch": "khong doc duoc", "dirty": None}
    try:
        run = lambda a: subprocess.run(a, cwd=REPO_ROOT, capture_output=True, text=True, timeout=10).stdout
        info["commit"] = run(["git", "rev-parse", "HEAD"]).strip()
        info["branch"] = run(["git", "branch", "--show-current"]).strip()
        # chi xet tep duoc theo doi: thu muc ho so phien chua add khong lam
        # "ban" ma nguon, va se lam phien sau bao ban sai (da gap 16/09)
        info["dirty"] = bool(run(["git", "status", "--porcelain", "--untracked-files=no"]).strip())
    except Exception as e:
        info["error"] = str(e)
    return info


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def _make_jpeg(w=320, h=240):
    from PIL import Image
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (x % 256, y % 256, (x + y) % 256)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def selftest():
    """Chay khong can bo. Tra 0 neu dat."""
    ok = True

    def check(cond, label):
        nonlocal ok
        print("  %-60s %s" % (label, "OK" if cond else "FAIL"))
        ok = ok and cond

    # 1. JPEG hop le do Pillow sinh ra
    good = _make_jpeg()
    d_ok, w, h, err = verify_jpeg(good)
    check(d_ok and (w, h) == (320, 240), "verify_jpeg: JPEG 320x240 hop le")

    # 2. Cat cut giua chung -> phai bao loi
    truncated = good[: len(good) // 2]
    d_ok, _, _, _ = verify_jpeg(truncated)
    check(not d_ok, "verify_jpeg: JPEG bi cat phai FAIL")

    # 2b. GIOI HAN DA BIET: cat giua roi dan FF D9 gia vao cuoi thi Pillow van
    #     giai ma duoc (phan duoi xam). Khong the chan bang verify_jpeg; ghi ra
    #     de nguoi doc biet, khong tinh vao PASS/FAIL cua selftest.
    fake_eoi = good[: len(good) // 2] + bytes([0xFF, 0xD9])
    d_ok, _, _, _ = verify_jpeg(fake_eoi)
    print("  %-60s %s" % ("verify_jpeg: cat giua + EOI gia (gioi han, khong chan)", "qua duoc" if d_ok else "chan duoc"))

    # 3. Khong phai JPEG
    d_ok, _, _, _ = verify_jpeg(b"khong phai anh")
    check(not d_ok, "verify_jpeg: du lieu rac phai FAIL")

    # 4. PNG hop le nhung khong phai JPEG -> phai FAIL vi ta doi JPEG nguyen goc
    from PIL import Image
    buf2 = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buf2, format="PNG")
    d_ok, _, _, err = verify_jpeg(buf2.getvalue())
    check(not d_ok, "verify_jpeg: PNG phai FAIL (%s)" % err[:28])

    # 5. Hash on dinh va nhay
    check(sha256_hex(good) == sha256_hex(good), "sha256: cung du lieu cung hash")
    check(sha256_hex(good) != sha256_hex(truncated), "sha256: khac du lieu khac hash")

    # 6. Parse X-Timestamp
    check(parse_x_timestamp("12.345678") == 12345, "parse_x_timestamp: 12.345678 -> 12345 ms")
    check(parse_x_timestamp("7.000000") == 7000, "parse_x_timestamp: 7.000000 -> 7000 ms")
    check(parse_x_timestamp("7") == 7000, "parse_x_timestamp: '7' -> 7000 ms")
    check(parse_x_timestamp("") is None, "parse_x_timestamp: rong -> None")
    check(parse_x_timestamp("abc") is None, "parse_x_timestamp: rac -> None")
    check(parse_x_timestamp("-3.5") is None, "parse_x_timestamp: am -> None")
    check(parse_x_timestamp("1.2.3") is None, "parse_x_timestamp: hai dau cham -> None")

    # 7. Bang framesize khop hai chieu
    check(INDEX_TO_NAME[10] == "VGA" and INDEX_TO_WH[10] == (640, 480), "framesize: VGA = 10 = 640x480")
    check(INDEX_TO_NAME[11] == "SVGA" and INDEX_TO_WH[11] == (800, 600), "framesize: SVGA = 11 = 800x600")
    check(INDEX_TO_NAME[6] == "QVGA", "framesize: QVGA = 6")

    # 8. git_info doc duoc commit trong repo nay
    gi = git_info()
    check(len(gi.get("commit", "")) == 40, "git_info: doc duoc commit 40 ky tu")

    # 9. Header khong phan biet hoa/thuong (R03)
    check(hget({"x-timestamp": "5.0"}, "X-Timestamp") == "5.0", "hget: 'x-timestamp' thuong van doc duoc")
    check(hget({"X-TIMESTAMP": "5.0"}, "x-timestamp") == "5.0", "hget: 'X-TIMESTAMP' hoa van doc duoc")
    check(hget(None, "X-Timestamp", "") == "", "hget: headers None -> mac dinh")

    # 10. parse_status (R02)
    st = parse_status(200, b'{"framesize": 10, "aec": 1}', "")
    check(st["ok"] and st["json"]["framesize"] == 10, "parse_status: JSON object hop le -> ok")
    st = parse_status(200, b"[1]", "")
    check(not st["ok"] and "object" in st["reason"], "parse_status: JSON list -> khong ok")
    st = parse_status(200, b"<html>", "")
    check(not st["ok"] and "JSON" in st["reason"], "parse_status: khong phai JSON -> khong ok")
    st = parse_status(503, b"busy", "")
    check(not st["ok"] and st["reason"] == "http 503", "parse_status: http 503 -> khong ok")
    st = parse_status(200, b'{"quality": 10}', "")
    check(not st["ok"] and "framesize" in st["reason"], "parse_status: thieu framesize -> khong ok")
    st = parse_status(0, b"", "timeout")
    check(not st["ok"] and "ket noi" in st["reason"], "parse_status: loi ket noi -> khong ok")

    # 11. compare_status phan biet ba tinh huong (R02)
    a = parse_status(200, b'{"framesize": 10, "aec": 1}', "")
    b = parse_status(200, b'{"framesize": 10, "aec": 0}', "")
    c = parse_status(200, b"<html>", "")
    cmp1 = compare_status(a, a)
    check(cmp1["compared"] and cmp1["changed"] == {}, "compare_status: hai ho so giong -> khong doi")
    cmp2 = compare_status(a, b)
    check(cmp2["compared"] and cmp2["changed"] == {"aec": [1, 0]}, "compare_status: khac aec -> doi o aec")
    cmp3 = compare_status(a, c)
    check(not cmp3["compared"] and cmp3["changed"] is None, "compare_status: cuoi khong doc duoc -> khong doi chieu")
    check("KHONG DOI CHIEU DUOC" in describe_compare(cmp3), "describe_compare: noi ro khong doi chieu duoc")
    check("khong doi" in describe_compare(cmp1), "describe_compare: khong doi")

    sd = status_dict_from_json({"framesize": 10, "aec": 0})
    check(sd["ok"] and sd["json"]["framesize"] == 10, "status_dict_from_json: JSON hop le -> ok")
    sd = status_dict_from_json(None, "ly do X")
    check(not sd["ok"] and sd["reason"] == "ly do X", "status_dict_from_json: None -> khong ok, giu ly do")

    # 12. classify_capture (R02/R03 + ma tran)
    hdr_good = {"Content-Length": str(len(good)), "X-Timestamp": "12.000000"}
    r = classify_capture(200, hdr_good, good, "", (320, 240))
    check(r["error"] == "" and r["ts_ms"] == 12000, "classify: anh tot + header du -> khong loi")
    r = classify_capture(200, {"content-length": str(len(good)), "x-timestamp": "12.500000"}, good, "", (320, 240))
    check(r["error"] == "" and r["ts_ms"] == 12500, "classify: header chu thuong -> van doc duoc")
    r = classify_capture(200, {"Content-Length": str(len(good))}, good, "", (320, 240))
    check("X-Timestamp" in r["error"], "classify: thieu X-Timestamp -> loi, khong PASS ngam")
    r = classify_capture(200, {"Content-Length": str(len(good)), "X-Timestamp": "rac"}, good, "", (320, 240))
    check("X-Timestamp" in r["error"], "classify: X-Timestamp rac -> loi")
    r = classify_capture(200, {"Content-Length": "abc", "X-Timestamp": "1.0"}, good, "", (320, 240))
    check("khong phai so" in r["error"], "classify: Content-Length khong phai so -> loi")
    r = classify_capture(200, {"Content-Length": str(len(good) + 5), "X-Timestamp": "1.0"}, good, "", (320, 240))
    check("truyen thieu" in r["error"], "classify: Content-Length lech -> loi truyen thieu")
    r = classify_capture(200, {"Content-Length": "0", "X-Timestamp": "1.0"}, b"", "", (320, 240))
    check(r["error"] == "body rong", "classify: HTTP 200 body rong -> loi 'body rong'")
    r = classify_capture(503, {}, b"busy", "", (320, 240))
    check(r["error"] == "http 503", "classify: http 503 -> loi http 503")
    r = classify_capture(0, {}, b"", "timeout", (320, 240))
    check(r["error"] == "timeout", "classify: loi ket noi -> giu chuoi loi")
    r = classify_capture(200, hdr_good, good, "", (640, 480))
    check("kich thuoc" in r["error"], "classify: sai kich thuoc -> loi")
    check(payload_suffix(good) == ".jpg" and payload_suffix(b"busy") == ".bin", "payload_suffix: jpg / bin")

    # 13. reserve_dir tu choi dich da ton tai (R05)
    with tempfile.TemporaryDirectory() as td:
        d1 = Path(td) / "s"
        ok1, _ = reserve_dir(d1)
        (d1 / "session.json").write_text("OLD", encoding="utf-8")
        ok2, why = reserve_dir(d1)
        check(ok1 and not ok2 and (d1 / "session.json").read_text(encoding="utf-8") == "OLD",
              "reserve_dir: lan hai bi tu choi, tep cu con nguyen")

    # 14. validate_args
    class A:
        pass
    a = A()
    a.count, a.interval, a.warmup, a.max_retries, a.timeout, a.framesize, a.profile = 0, 1.0, 2, 3, 15.0, None, None
    check("count" in validate_args(a), "validate_args: count 0 bi chan")
    a.count = 5
    check(validate_args(a) == "", "validate_args: bo tham so hop le qua")
    a.framesize = "ABC"
    check("framesize" in validate_args(a), "validate_args: framesize la bi chan")
    a.framesize = "VGA"
    a.profile = "data/calibration/camera_profiles/cam_VGA_q10_20260922.json"
    check("--profile" in validate_args(a), "validate_args: --profile va --framesize cung luc bi chan")
    a.framesize = None
    check(validate_args(a) == "", "validate_args: chi --profile qua")
    a.profile = None
    a.timeout = float("inf")
    check("huu han" in validate_args(a), "validate_args: timeout Infinity bi chan (khong treo request)")
    a.timeout = float("nan")
    check("huu han" in validate_args(a), "validate_args: timeout NaN bi chan")
    a.timeout = 15.0

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ----------------------------------------------------------------------
# Phan can bo.
# ----------------------------------------------------------------------

def http_get(session, url, timeout):
    """Tra (status_code, headers_chu_thuong, bytes, elapsed_ms, loi)."""
    t0 = time.perf_counter()
    try:
        r = session.get(url, timeout=timeout)
        elapsed = (time.perf_counter() - t0) * 1000.0
        return r.status_code, normalize_headers(r.headers), r.content, elapsed, ""
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000.0
        return 0, {}, b"", elapsed, "%s: %s" % (type(e).__name__, e)


def fetch_status(session, base, timeout):
    code, _, body, _, err = http_get(session, base + "/status", timeout)
    return parse_status(code, body, err)


def set_framesize(session, base, index, timeout):
    url = "%s/control?var=framesize&val=%d" % (base, index)
    code, _, body, _, err = http_get(session, url, timeout)
    return code, err


def run_session(args):
    import requests

    bad = validate_args(args)
    if bad:
        print("Tham so khong hop le:", bad)
        return 2

    base = "http://%s" % args.host
    session_id = args.session_id or datetime.now().strftime("capture_%Y%m%d_%H%M%S")
    out_dir = (REPO_ROOT / args.out / session_id).resolve()
    # R05: kiem CA HAI dich truoc khi thu; khong ghi de ho so cu
    meta_dst = (REPO_ROOT / args.meta_copy / session_id).resolve() if args.meta_copy else None
    if meta_dst is not None and meta_dst.exists():
        print("Thu muc --meta-copy cho phien nay da ton tai, khong ghi de:", meta_dst)
        return 2
    ok, why = reserve_dir(out_dir)
    if not ok:
        print("Thu muc phien khong dung duoc, khong ghi de:", why)
        return 2

    meta = {
        "session_id": session_id,
        "started_at": now_iso(),
        "finished_at": None,
        "host": args.host,
        "requested": {
            "count": args.count, "interval_s": args.interval,
            "framesize": args.framesize or "giu nguyen tren bo",
            "warmup_frames": args.warmup, "max_retries": args.max_retries, "timeout_s": args.timeout,
        },
        "source": git_info(),
        "script": "pc/capture_session.py",
        "firmware_version": "firmware chua in phien ban; dung source.commit va ENVIRONMENT.md",
        "calibration_id": "chua ap dung (tuan 1)",
        "angle_index": "chua ap dung (tuan 1)",
        "laser": "chua ap dung (tuan 1)",
        "note": args.note or "",
        "camera_status_start": None, "camera_status_after_set": None, "camera_status_end": None,
        "expected_size": None,
        "result": None,
    }
    meta_path = out_dir / "session.json"
    attempts_path = out_dir / "attempts.jsonl"

    def write_meta():
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    def fail(reason):
        meta["finished_at"] = now_iso()
        meta["result"] = {"verdict": "FAIL", "reason": reason}
        write_meta()
        print("FAIL:", reason)
        print("Da ghi:", out_dir)
        return 1

    write_meta()  # ghi som de co metadata ke ca khi dung giua chung

    http = requests.Session()
    print("Phien:", session_id)
    print("Thu muc:", out_dir)
    print("Nguon:", meta["source"])

    try:
        return _run_session_body(args, http, base, meta, out_dir, meta_dst, session_id, write_meta, fail)
    except KeyboardInterrupt:
        meta["finished_at"] = now_iso()
        if args.profile:
            meta["status"] = "aborted"
        meta["result"] = {"verdict": "FAIL", "reason": "nguoi dung ngat (KeyboardInterrupt)"}
        write_meta()
        print()
        print("Bi ngat (KeyboardInterrupt). Du lieu da nhan duoc giu nguyen, khong ghi de. Da ghi:", out_dir)
        return 1


def _run_session_body(args, http, base, meta, out_dir, meta_dst, session_id, write_meta, fail):
    attempts_path = out_dir / "attempts.jsonl"

    profile = None
    profile_expected_registers = {}
    cp = None
    if args.profile:
        # L01/L02/L03 (Vong 3, kiem lai cua Tester): doc + kiem ho so TRUOC
        # bat ky HTTP nao - ke ca /status dau phien - de ho so sai dung lai
        # voi 0 request. schema_version ghi ngay khi dung --profile (du sau
        # do that bai); status=running chi sau khi ho so hop le, truoc khi
        # cham bo, de phien bi kill giua chung con lai dau vet "running".
        meta["schema_version"] = 2
        import camera_profile as cp
        try:
            profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            meta["status"] = "error"
            return fail("khong doc duoc ho so camera: %s" % e)
        p_ok, p_errors = cp.validate_profile(profile)
        if not p_ok:
            meta["status"] = "error"
            return fail("ho so camera khong hop le: %s" % "; ".join(p_errors))
        meta["status"] = "running"
        write_meta()

    st = fetch_status(http, base, args.timeout)
    meta["camera_status_start"] = st
    (out_dir / "status_start.json").write_text(st["raw"] or "", encoding="utf-8")
    if not st["ok"]:
        if args.profile:
            meta["status"] = "error"
        return fail("khong doc duoc /status luc bat dau: %s" % st["reason"])
    fs_on_board = st["json"].get("framesize")
    print("/status: framesize tren bo =", fs_on_board, INDEX_TO_NAME.get(fs_on_board, "?"))

    if args.profile:
        # G01: requested phan anh dung ho so dang dung, khong con "giu nguyen tren bo"
        meta["requested"]["framesize"] = profile["framesize"]
        meta["requested"]["quality"] = profile["quality"]

        reg_keys = tuple(profile["expected_registers"]) or cp.DEFAULT_EXPECTED_REGISTER_KEYS
        result = cp.apply_and_verify(
            http, base, profile["framesize"], profile["quality"], profile["controls"], args.timeout, reg_keys,
        )
        for var, val, ok, err in result["applied"]:
            print("/control %s=%s: %s %s" % (var, val, "OK" if ok else "LOI", err))
        st2 = status_dict_from_json(result["status"], "; ".join(result["mismatches"]))
        meta["camera_status_after_set"] = st2
        (out_dir / "status_after_set.json").write_text(st2["raw"] or "", encoding="utf-8")
        if not result["ok"]:
            meta["status"] = "error"
            return fail("ap ho so camera khong khop: %s" % "; ".join(result["mismatches"]))

        # G02: nguon chan ly la CHINH ho so da luu (khong phai gia tri vua
        # doc duoc) - ho so ghi sai thanh ghi phai bi bat NGAY o day, truoc
        # khi chup anh nao, khong doi den cuoi phien moi lo.
        reg_ok, reg_mismatches = cp.compare_registers(profile["expected_registers"], result["status"], reg_keys)
        if not reg_ok:
            meta["status"] = "error"
            return fail("thanh ghi sau khi ap khong khop ho so da luu: %s" % "; ".join(reg_mismatches))

        profile_expected_registers = dict(profile["expected_registers"])
        idx = cp.FRAMESIZES[profile["framesize"]]
        w, h = INDEX_TO_WH[idx]
        meta["expected_size"] = [w, h]
        meta["camera_profile_id"] = profile["camera_profile_id"]
        meta["camera_config"] = {
            "framesize": profile["framesize"], "quality": profile["quality"],
            # API /status hien khong bao co client nao khac dang mo /stream;
            # chua co bang chung de khang dinh true, nen ghi null + ly do
            # thay vi coi day la mot phep do (Vong 3, phan hoi G-review).
            "stream_disabled": None,
            "stream_disabled_reason": "chua co API xac nhan khong con client stream; nguoi dung phai tu dam bao theo huong dan",
            "lens_note": profile["lens_note"],
        }
    elif args.framesize:
        idx, w, h = FRAMESIZES[args.framesize]
        code, err = set_framesize(http, base, idx, args.timeout)
        print("/control framesize=%d (%s): http %s %s" % (idx, args.framesize, code, err))
        time.sleep(1.0)
        st2 = fetch_status(http, base, args.timeout)
        meta["camera_status_after_set"] = st2
        (out_dir / "status_after_set.json").write_text(st2["raw"] or "", encoding="utf-8")
        if not st2["ok"]:
            return fail("khong doc duoc /status sau khi dat framesize: %s" % st2["reason"])
        got = st2["json"].get("framesize")
        if got != idx:
            print("Bo bao framesize =", got, "khac yeu cau", idx, "-> dung, khong chup")
            return fail("framesize khong doi duoc (bo bao %s, yeu cau %d)" % (got, idx))
        meta["expected_size"] = [w, h]
    elif fs_on_board in INDEX_TO_WH:
        meta["expected_size"] = list(INDEX_TO_WH[fs_on_board])
    expected = tuple(meta["expected_size"]) if meta["expected_size"] else None
    print("Kich thuoc mong doi:", expected or "lay theo anh dau tien")
    write_meta()

    warm_rows = []
    for k in range(args.warmup):
        code, hdr, body, ms, err = http_get(http, base + "/capture", args.timeout)
        warm_rows.append({"k": k, "http": code, "bytes": len(body), "ms": round(ms, 1), "err": err})
        time.sleep(0.5)
    if warm_rows:
        print("Lam nong (khong dem):", warm_rows)
    meta["warmup"] = warm_rows

    fields = ["idx", "t_request", "elapsed_ms", "http_status", "bytes", "content_length_hdr",
              "sha256_16", "decode_ok", "width", "height", "size_ok",
              "x_timestamp", "ts_ms", "ts_delta_ms", "identical_to_prev",
              "retries", "failed_attempt_files", "error"]
    rows = []
    prev_hash = None
    prev_ts = None
    n_ok = n_retry_total = n_reset_suspect = n_identical = n_stale_ts = n_conn_err = 0
    n_ts_missing = 0
    n_ts_comparisons = 0
    t_start = time.perf_counter()

    def log_attempt(rec):
        # R04: moi lan thu mot dong, ghi ngay, khong doi thoat vong retry
        with attempts_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + LF)

    for i in range(1, args.count + 1):
        slot_start = time.perf_counter()
        retries = 0
        failed_files = []
        while True:
            t_req = now_iso()
            code, hdr, body, ms, err = http_get(http, base + "/capture", args.timeout)
            if err:
                n_conn_err += 1
            if expected is None and code == 200 and body:
                d_ok0, w0, h0, _ = verify_jpeg(body)
                if d_ok0:
                    expected = (w0, h0)
                    meta["expected_size"] = [w0, h0]
            c = classify_capture(code, hdr, body, err, expected)
            hx = sha256_hex(body) if body else ""
            good = c["error"] == ""
            rec = {
                "idx": i, "try": retries + 1, "t_request": t_req, "http_status": code,
                "bytes": len(body), "elapsed_ms": round(ms, 1), "sha256_16": hx[:16],
                "x_timestamp": c["x_timestamp"], "error": c["error"], "accepted": good, "file": "",
            }
            if not good and retries < args.max_retries:
                # lan thu KHONG dat va con thu tiep: giu payload rieng de dieu tra
                if body:
                    fname = "img_%04d_try%d%s" % (i, retries + 1, payload_suffix(body))
                    (out_dir / fname).write_bytes(body)
                    rec["file"] = fname
                    failed_files.append(fname)
                log_attempt(rec)
                retries += 1
                n_retry_total += 1
                time.sleep(0.5)
                continue
            # lan cuoi (dat, hoac het so lan thu): luu NGUYEN GOC ke ca khi khong dat
            if body:
                rec["file"] = "img_%04d.jpg" % i
                (out_dir / rec["file"]).write_bytes(body)
            log_attempt(rec)
            break

        ts_ms = c["ts_ms"]
        ts_delta = (ts_ms - prev_ts) if (ts_ms is not None and prev_ts is not None) else None
        identical = bool(prev_hash) and hx == prev_hash
        row = {
            "idx": i, "t_request": t_req, "elapsed_ms": round(ms, 1), "http_status": code,
            "bytes": len(body), "content_length_hdr": c["content_length_hdr"],
            "sha256_16": hx[:16], "decode_ok": c["decode_ok"], "width": c["width"], "height": c["height"],
            "size_ok": c["size_ok"],
            "x_timestamp": c["x_timestamp"], "ts_ms": ts_ms if ts_ms is not None else "",
            "ts_delta_ms": ts_delta if ts_delta is not None else "",
            "identical_to_prev": identical, "retries": retries,
            "failed_attempt_files": ";".join(failed_files), "error": c["error"],
        }
        if good:
            n_ok += 1
        if ts_ms is None:
            n_ts_missing += 1
        if identical:
            n_identical += 1
        if ts_delta is not None:
            n_ts_comparisons += 1
            if ts_delta < 0:
                n_reset_suspect += 1
                row["error"] = (row["error"] + "; " if row["error"] else "") + "X-Timestamp lui: nghi reset"
            elif ts_delta == 0:
                n_stale_ts += 1
        if ts_ms is not None:
            prev_ts = ts_ms
        if hx:
            prev_hash = hx
        rows.append(row)

        flag = "OK " if good else "ERR"
        print("[%3d/%d] %s http=%s %6d B %4dx%-4d %6.0f ms ts=%s retries=%d %s" % (
            i, args.count, flag, row["http_status"], row["bytes"], row["width"], row["height"],
            row["elapsed_ms"], row["x_timestamp"] or "-", row["retries"], row["error"]))

        # ghi CSV tung dong de dung giua chung van con du lieu
        with (out_dir / "frames.csv").open("w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=fields)
            wr.writeheader()
            wr.writerows(rows)

        if i < args.count:
            wait = args.interval - (time.perf_counter() - slot_start)
            if wait > 0:
                time.sleep(wait)

    total_s = time.perf_counter() - t_start

    st_end = fetch_status(http, base, args.timeout)
    meta["camera_status_end"] = st_end
    (out_dir / "status_end.json").write_text(st_end["raw"] or "", encoding="utf-8")
    cmp = compare_status(st, st_end)

    # Bang chung kiem reset: can du (count - 1) phep so timestamp lien tiep
    reset_check = {
        "frames_with_timestamp": args.count - n_ts_missing,
        "comparisons": n_ts_comparisons,
        "comparisons_needed": args.count - 1,
        "sufficient": n_ts_missing == 0 and n_ts_comparisons == args.count - 1,
    }

    reasons = []
    if n_ok != args.count:
        reasons.append("anh dat %d/%d" % (n_ok, args.count))
    if n_reset_suspect:
        reasons.append("nghi reset %d lan" % n_reset_suspect)
    if not reset_check["sufficient"]:
        reasons.append("thieu X-Timestamp o %d anh, khong du bang chung kiem reset" % n_ts_missing)
    if not cmp["compared"]:
        reasons.append("/status khong doi chieu duoc: %s" % cmp["reason"])
    if profile is not None:
        if not st_end["ok"]:
            reasons.append("khong doc duoc /status luc ket thuc de doi chieu thanh ghi ho so camera")
        else:
            reg_ok, reg_mismatches = cp.compare_registers(profile_expected_registers, st_end["json"], profile_expected_registers.keys())
            if not reg_ok:
                reasons.append("thanh ghi ho so camera lech trong phien: %s" % "; ".join(reg_mismatches))
            # G03: cuoi phien cung phai kiem lai framesize/quality/14 control,
            # khong chi thanh ghi - control troi ve tu dong (vd aec/agc/awb
            # bat lai) ma thanh ghi tinh co chua doi van phai bi bat.
            ctrl_ok, ctrl_mismatches = cp.diff_controls(st_end["json"], profile["framesize"], profile["quality"], profile["controls"])
            if not ctrl_ok:
                reasons.append("control ho so camera lech luc ket thuc: %s" % "; ".join(ctrl_mismatches))
    verdict = "PASS" if not reasons else "FAIL"
    if profile is not None:
        meta["status"] = "completed" if verdict == "PASS" else "error"
    meta["finished_at"] = now_iso()
    meta["result"] = {
        "verdict": verdict, "reason": "; ".join(reasons),
        "frames_requested": args.count, "frames_ok": n_ok,
        "retries_total": n_retry_total, "connection_errors": n_conn_err,
        "reset_suspected": n_reset_suspect, "reset_check": reset_check,
        "identical_to_prev": n_identical,
        "same_x_timestamp_as_prev": n_stale_ts, "duration_s": round(total_s, 1),
        "status_compare_start_to_end": cmp,
    }
    write_meta()

    src = meta["source"]
    tree = "working tree BAN" if src.get("dirty") else "working tree sach"
    lines = [
        "Phien %s tren %s" % (session_id, args.host),
        "Nguon: %s (%s, %s)" % (src.get("commit"), src.get("branch"), tree),
        "Framesize: %s, kich thuoc mong doi %s" % (meta["requested"]["framesize"], expected),
        "Ket qua: %s%s" % (verdict, (" - " + meta["result"]["reason"]) if reasons else ""),
        "  anh dat/yeu cau       : %d/%d" % (n_ok, args.count),
        "  tong so lan chup lai  : %d" % n_retry_total,
        "  loi ket noi           : %d" % n_conn_err,
        "  nghi reset (ts lui)   : %d" % n_reset_suspect,
        "  bang chung kiem reset : %d/%d phep so timestamp%s" % (
            n_ts_comparisons, args.count - 1, "" if reset_check["sufficient"] else " (THIEU)"),
        "  anh trung anh truoc   : %d" % n_identical,
        "  X-Timestamp trung     : %d" % n_stale_ts,
        "  thoi gian phien       : %.1f s" % total_s,
    ]
    if rows:
        el = [r["elapsed_ms"] for r in rows]
        lines.append("  /capture ms min/tb/max: %.0f / %.0f / %.0f" % (min(el), sum(el) / len(el), max(el)))
    lines.append("  /status doi start->end: %s" % describe_compare(cmp))
    text = LF.join(lines)
    (out_dir / "summary.txt").write_text(text + LF, encoding="utf-8")
    print()
    print(text)
    print()
    print("Da ghi:", out_dir)

    # data/raw khong vao Git; chep rieng phan ho so nho (khong chep anh) de lam bang chung
    if meta_dst is not None:
        ok, why = reserve_dir(meta_dst)
        if not ok:
            print("KHONG chep ho so phien vi dich khong dung duoc (khong ghi de):", why)
        else:
            for name in ("session.json", "frames.csv", "summary.txt", "attempts.jsonl",
                         "status_start.json", "status_after_set.json", "status_end.json"):
                srcf = out_dir / name
                if srcf.exists():
                    (meta_dst / name).write_bytes(srcf.read_bytes())
            print("Da chep ho so phien (khong gom anh) vao:", meta_dst)
    return 0 if verdict == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description="Thu anh thu tu ESP32-S3 CameraWebServer, mot phien co ho so.")
    ap.add_argument("--host", help="IP hoac ten may cua bo, vi du 192.168.31.9")
    ap.add_argument("--count", type=int, default=100, help="so anh (mac dinh 100, toi thieu 1)")
    ap.add_argument("--interval", type=float, default=12.0, help="giay giua hai anh (mac dinh 12; 100 anh = 20 phut)")
    ap.add_argument("--framesize", help="dat do phan giai truoc khi chup: " + ", ".join(FRAMESIZES))
    ap.add_argument("--profile", help="duong dan ho so camera JSON (tu camera_profile.py --create); khoa framesize/quality/control theo ho so, FAIL neu khong khop luc dat hoac thanh ghi doi trong phien. Khong dung cung --framesize")
    ap.add_argument("--warmup", type=int, default=2, help="so khung bo di sau khi doi do phan giai (mac dinh 2)")
    ap.add_argument("--max-retries", type=int, default=3, help="so lan chup lai toi da cho moi anh (mac dinh 3)")
    ap.add_argument("--timeout", type=float, default=15.0, help="timeout HTTP, giay (mac dinh 15)")
    ap.add_argument("--out", default="data/raw", help="thu muc goc cho cac phien (mac dinh data/raw)")
    ap.add_argument("--session-id", help="ID phien; mac dinh capture_YYYYMMDD_HHMMSS")
    ap.add_argument("--note", help="ghi chu tu do vao session.json")
    ap.add_argument("--meta-copy", help="thu muc de chep ho so phien (khong gom anh), vi du docs/logs; tu choi neu da co")
    ap.add_argument("--selftest", action="store_true", help="chay kiem tra noi bo, khong can bo")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.host:
        ap.error("can --host, hoac --selftest")
    return run_session(args)


if __name__ == "__main__":
    sys.exit(main())
