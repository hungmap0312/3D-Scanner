#!/usr/bin/env python3
"""Tester C5a Q6 - kiem doc lap ma /capture_fresh tai commit B (handoff/2026-09-21_c5a-s3-fresh-capture).

Hop dong: 01_PLAN.md Vong 5 muc 4-5 (Q6-T1..Q6-T8), Vong 6 muc 5 (V6-T1..V6-T6), Vong 7/8 muc 5 (V7-A1..A5), Vong 9 muc 5 (V9-T2..T4). Q6-T9/T10, V6-T7 can bo
that -> CAN BO, khong kiem o day.
Ky vong lay tu ke hoach, KHONG lay tu ma; mot FAIL la mot sai lech so voi ke hoach.

Nhom kiem:
- H: harness C++ (firmware/esp32s3/CameraWebServerTest/test/) bien dich NGUYEN VAN cac handler trich tu
     app_httpd.cpp tai B voi API ESP-IDF gia; hai bien the khong LED (cau hinh bo) va co LED.
- P: parser/tinh lien tuc cua pc/fresh_capture_probe.py tai B voi may chu HTTP tho do test dung.
- D: han tong 10 s cua probe voi may chu nho giot (slow-drip), connect treo.
- E: luu bang chung cua probe (thu muc rieng, khong ghi de).
- M: mock /capture_fresh 20 luot; hop dong mock cu (/capture, /status) giu nguyen so voi base.
- R: hoi quy selftest cu + probe --selftest.
- S: doi chieu ma voi rang buoc ke hoach khong chay duoc tren may tinh (dong bo co stream, duong khong-JPEG, log cau hinh).
- J: JSON /status do harness H in ra (status_handler that, heap gia) parse bang json, doi chieu truong/gia tri (V6-T1..T3).
- S7: cac khoi lenh Git Bash cua quy trinh bo Vong 6 chay NGUYEN VAN tren thu muc tam (khong HTTP toi bo) (V6-T4, V6-T5).
- T: nhan timeout hai lop cua probe (TIMEOUT_SOCKET / TIMEOUT_TOTAL_DEADLINE / loi mang), ke ca dua bien han tong (V7-A2, V7-A3).
- U: R15 phan loai loi sat han tong bang dong ho gia/watchdog gia (V9-T2, V9-T3).
- S8: quy trinh Vong 7/8: niem phong artifact, nap tu bo luu, exit code nap, chu trinh RST (V7-A4, V8-B3).

Khong mo COM/HTTP toi bo, khong nap firmware. May chu chi nghe 127.0.0.1.

Chay tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/test_c5a_runtime.py
Bien moi truong: C5A_Q6_B (commit B, mac dinh 3a69599), C5A_Q6_BASE (mac dinh e92867e),
C5A_GPP (g++ MinGW, mac dinh D:/MinGW/bin/g++.exe). Thoat 0 khi khong co FAIL.
"""
import http.client
import importlib.util
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import math
import time
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
B = os.environ.get("C5A_Q6_B", "5092910b23dbffeb50eed751fca362f96efb2d9b")
BASE = os.environ.get("C5A_Q6_BASE", "e92867eecf5eaad308ab1a222069de07d964e6fb")
GPP = os.environ.get("C5A_GPP", "D:/MinGW/bin/g++.exe")
SKETCH = "firmware/esp32s3/CameraWebServerTest/"
HARNESS = REPO / SKETCH / "test"
PY = sys.executable

RESULTS = []


def check(cid, ok, title, detail=""):
    tag = "PASS" if ok else "FAIL"
    RESULTS.append((cid, tag))
    print("  [%s] %s %s%s" % (tag, cid, title, ("  | " + detail) if detail else ""))
    sys.stdout.flush()
    return ok


def note(cid, title, detail=""):
    RESULTS.append((cid, "NOTE"))
    print("  [NOTE] %s %s%s" % (cid, title, ("  | " + detail) if detail else ""))


def show(rev, path):
    r = subprocess.run(["git", "-C", str(REPO), "show", "%s:%s" % (rev, path)], capture_output=True)
    if r.returncode:
        raise RuntimeError("git show %s:%s that bai" % (rev, path))
    return r.stdout


# ============================================================================ H: harness C++
def extract_handlers(src):
    """Chep nguyen van tu app_httpd.cpp: tu sau #include "fresh_capture_core.h" toi truoc parse_get
    (bien/khoa/boot ID, LED, bmp, capture, capture_fresh, stream) + parse_get, xclk_handler, index_handler
    + (Vong 6) cac ham /status co trong ban dang kiem: status_json_append, print_reg_safe | print_reg, status_handler."""
    lines = src.replace("\r\n", "\n").split("\n")
    start = lines.index('#include "fresh_capture_core.h"') + 1
    end = next(i for i, ln in enumerate(lines) if ln.startswith("static esp_err_t parse_get("))
    body = [ln for ln in lines[start:end] if not ln.lstrip().startswith("#include")]

    def func(sig):
        i = next(k for k, ln in enumerate(lines) if ln.startswith(sig))
        j = next(k for k in range(i, len(lines)) if lines[k] == "}")
        return lines[i:j + 1]
    out = ["// SINH TU DONG boi pc/test_c5a_runtime.py tu app_httpd.cpp - KHONG SUA TAY", '#include "fresh_capture_core.h"']
    out += body
    sigs = ["static esp_err_t parse_get(", "static esp_err_t xclk_handler(", "static esp_err_t index_handler("]
    for sig in ("static bool status_json_append(", "static bool print_reg_safe(", "static int print_reg(", "static esp_err_t status_handler("):
        if any(ln.startswith(sig) for ln in lines):
            sigs.append(sig)
    if "static bool status_json_append(" in sigs:
        out.append("#define HAVE_STATUS_JSON_APPEND 1")
    for sig in sigs:
        out += func(sig)
    return "\n".join(out) + "\n", len(body)


def group_h(td):
    print("---- H: harness C++ chay ma handler that tai B (Q6-T1..T5, T8)")
    src = show(B, SKETCH + "app_httpd.cpp").decode("utf-8")
    inc, n = extract_handlers(src)
    gen = Path(td) / "gen"
    gen.mkdir()
    (gen / "app_httpd_extract.inc").write_text(inc, encoding="utf-8", newline="\n")
    (gen / "fresh_capture_core.h").write_bytes(show(B, SKETCH + "fresh_capture_core.h"))
    print("  trich %d dong tu app_httpd.cpp@%s (+parse_get, xclk_handler, index_handler, ham /status)" % (n, B[:7]))
    group_h.jsons = {}
    for name, extra in (("khong_LED", []), ("co_LED", ["-DLED_GPIO_NUM=4"])):
        exe = Path(td) / ("fresh_host_%s.exe" % name)
        # -D_ISOC99_SOURCE: MinGW dung printf C99 (%llu dung khi chay); -Wno-format: bo canh bao kiem dinh dang
        # cua msvcrt (thuoc moi truong host, khong phai ma bi kiem)
        cmd = [GPP, "-std=gnu++11", "-Wall", "-Wno-format", "-O0", "-D_ISOC99_SOURCE"] + extra + [
            "-I" + str(gen), "-I" + str(HARNESS), str(HARNESS / "test_fresh_host.cpp"), "-o", str(exe)]
        c = subprocess.run(cmd, capture_output=True, text=True)
        warn = [ln for ln in c.stderr.splitlines() if "warning" in ln]
        if not check("H.build.%s" % name, c.returncode == 0, "bien dich harness (%s)" % name,
                     "rc=%d; canh bao %d%s" % (c.returncode, len(warn), ("; " + c.stderr[-600:]) if c.returncode else "")):
            continue
        r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=180)
        jsons = {}
        for ln in r.stdout.splitlines():
            j = re.match(r"\s+@JSON (\S+) (.*)$", ln)
            if j:
                jsons[j.group(1)] = j.group(2)
                continue
            m = re.match(r"\s+\[(PASS|FAIL)\] (H\d+) (.*)$", ln)
            if m:
                RESULTS.append(("%s.%s" % (m.group(2), name), m.group(1)))
                print("  [%s] %s.%s %s" % (m.group(1), m.group(2), name, m.group(3)))
            elif ln.startswith("=="):
                print("  " + ln)
        if r.returncode not in (0, 1):
            check("H.run.%s" % name, False, "harness ket thuc bat thuong", "rc=%d stderr=%s" % (r.returncode, r.stderr[-400:]))
        if name == "khong_LED":
            group_h.jsons = jsons
            print("  JSON /status mau (H36, khong LED): %s" % jsons.get("H36", "<khong co>"))
        json_checks(name, jsons, td)


# ============================================================================ may chu HTTP tho
def jpeg_bytes():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (16, 16), (40, 90, 160)).save(b, "JPEG")
    return b.getvalue()


JPEG = None
BOOT_A = "0123456789abcdef0123456789abcdef"
BOOT_B = "fedcba9876543210fedcba9876543210"


def resp(headers, body=None, status="200 OK", ctype="image/jpeg"):
    body = JPEG if body is None else body
    h = ["HTTP/1.1 %s" % status, "Content-Type: %s" % ctype, "Content-Length: %d" % len(body), "Connection: close"]
    h += ["%s: %s" % (k, v) for k, v in headers]
    return ("\r\n".join(h) + "\r\n\r\n").encode("latin-1") + body


def hdrs(fid="1", boot=BOOT_A, ts="10.500000", req="10.400000", disc="0"):
    return [("X-Frame-Id", fid), ("X-Boot-Id", boot), ("X-Timestamp", ts), ("X-Request-Timestamp", req), ("X-Discarded-Frames", disc)]


class RawServer:
    """Moi ket noi: doc het header request roi goi action(conn, i): gui bytes hoac nho giot."""

    def __init__(self, actions):
        self.actions = list(actions)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self.stop = False
        self.accepted = 0
        self.t = threading.Thread(target=self._loop, daemon=True)
        self.t.start()

    def _loop(self):
        i = 0
        while not self.stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            self.accepted += 1
            conn.settimeout(5)
            data = b""
            try:
                while b"\r\n\r\n" not in data:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                act = self.actions[min(i, len(self.actions) - 1)]
                if isinstance(act, bytes):
                    conn.sendall(act)
                else:
                    act(conn)
            except OSError:
                pass
            finally:
                i += 1
                try:
                    conn.close()
                except OSError:
                    pass

    def close(self):
        self.stop = True
        self.sock.close()


def load_b_module(td, name):
    p = Path(td) / "pcB" / (name + ".py")
    p.parent.mkdir(exist_ok=True)
    p.write_bytes(show(B, "pc/%s.py" % name))
    if str(p.parent) not in sys.path:
        sys.path.insert(0, str(p.parent))
    spec = importlib.util.spec_from_file_location(name + "_B", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_client(probe, responses):
    srv = RawServer(responses)
    c = probe.FreshCaptureClient("127.0.0.1", srv.port, timeout=5.0)
    out = [c.capture_fresh() for _ in responses]
    srv.close()
    return out


# ============================================================================ P: parser va lien tuc
def group_p(td):
    print("---- P: parser/tinh lien tuc cua fresh_capture_probe.py tai B (Q6-T3, Q6-T6)")
    probe = load_b_module(td, "fresh_capture_probe")
    ok_cases = [
        ("binh thuong", hdrs()),
        ("ID = UINT64_MAX", hdrs(fid="18446744073709551615")),
        ("giay = UINT32_MAX", hdrs(ts="4294967295.999999", req="4294967295.000000")),
        ("usec 000000 / 999999", hdrs(ts="11.000000", req="10.999999")),
        ("discarded = 4", hdrs(disc="4")),
    ]
    for name, hh in ok_cases:
        r = run_client(probe, [resp(hh)])[0]
        check("P.ok.%s" % name.split()[0], r["error"] is None, "Q6-T3 bien hop le duoc nhan: %s" % name, "error=%r" % r["error"])
    bad_cases = [
        ("usec 5 chu so", hdrs(ts="10.50000")),
        ("usec 7 chu so", hdrs(ts="10.5000000")),
        ("giay > UINT32_MAX", hdrs(ts="4294967296.000001", req="4294967296.000000")),
        ("timestamp am", hdrs(ts="-1.000000")),
        ("timestamp NaN", hdrs(ts="nan")),
        ("timestamp Inf", hdrs(ts="inf")),
        ("timestamp mu", hdrs(ts="1e1.000000")),
        ("ID = 0", hdrs(fid="0")),
        ("ID > UINT64_MAX", hdrs(fid="18446744073709551616")),
        ("ID am", hdrs(fid="-1")),
        ("ID co dau +", hdrs(fid="+1")),
        ("ID thap phan", hdrs(fid="1.0")),
        ("discarded = 5", hdrs(disc="5")),
        ("discarded am", hdrs(disc="-1")),
        ("boot 31 hex", hdrs(boot=BOOT_A[:31])),
        ("boot chu HOA", hdrs(boot=BOOT_A.upper())),
        ("header rong", hdrs(fid="")),
        ("X-Frame-Id lap khac gia tri", hdrs() + [("X-Frame-Id", "2")]),
        ("X-Boot-Id lap cung gia tri", hdrs() + [("X-Boot-Id", BOOT_A)]),
        ("X-Discarded-Frames lap", hdrs() + [("X-Discarded-Frames", "0")]),
    ]
    for name, hh in bad_cases:
        r = run_client(probe, [resp(hh)])[0]
        check("P.bad.%s" % name.replace(" ", "_"), r["error"] is not None,
              "Q6-T3 header sai/vuot mien/lap phai INVALID: %s" % name, "error=%r" % r["error"])
    # tinh lien tuc tren cung mot client
    seq = [
        ("C1", "cung boot, ID nhay coc 1 -> 3 phai dung (ke hoach 4.4: gap thi dung)",
         [resp(hdrs(fid="1")), resp(hdrs(fid="3", ts="11.500000", req="11.400000"))], True),
        ("C2", "cung boot, ID trung 1 -> 1 phai loi", [resp(hdrs(fid="1")), resp(hdrs(fid="1", ts="11.500000", req="11.400000"))], True),
        ("C3", "doi boot du ID va timestamp deu TANG -> CAMERA_REBOOT",
         [resp(hdrs(fid="1")), resp(hdrs(fid="2", boot=BOOT_B, ts="20.500000", req="20.400000"))], True),
        ("C4", "cung boot, timestamp lui -> loi", [resp(hdrs(fid="1")), resp(hdrs(fid="2", ts="10.450000", req="10.300000"))], True),
        ("C5", "luot dau nhan ID duong bat ky (server da phuc vu truoc)",
         [resp(hdrs(fid="57")), resp(hdrs(fid="58", ts="11.500000", req="11.400000"))], False),
    ]
    for cid, title, rs, want_err in seq:
        out = run_client(probe, rs)
        r2 = out[1]
        got_err = r2["error"] is not None
        ok = (got_err == want_err) and out[0]["error"] is None
        if cid == "C3":
            ok = ok and "CAMERA_REBOOT" in (r2["error"] or "")
        check("P.%s" % cid, ok, "Q6-T6 %s" % title, "luot1=%r luot2 error=%r canh_bao=%r" % (out[0]["error"], r2["error"], r2.get("warning_gap")))
    # loi mang / noi dung
    def cut(conn):
        conn.sendall(resp(hdrs())[:-len(JPEG) + 40])
    misc = [
        ("TCP dut giua body", [cut]),
        ("HTTP 200 nhung body HTML", [resp(hdrs(), body=b"<html>busy</html>", ctype="text/html")]),
        ("HTTP 503", [resp([], body=b"ERROR CAMERA_BUSY_CAPTURE", status="503 Service Unavailable", ctype="text/plain")]),
    ]
    for name, rs in misc:
        r = run_client(probe, rs)[0]
        check("P.err.%s" % name.split()[0], r["error"] is not None, "Q6-T4/T7 %s -> INVALID" % name, "error=%r" % r["error"])


# ============================================================================ D: han tong cua probe
def run_probe_cli(td, args, timeout=90):
    p = Path(td) / "pcB" / "fresh_capture_probe.py"
    t0 = time.monotonic()
    r = subprocess.run([PY, str(p)] + args, capture_output=True, text=True, timeout=timeout, cwd=str(Path(td)))
    return r, time.monotonic() - t0


def group_d(td):
    print("---- D: han tong 10 s cua probe (Q6-T7; ke hoach 4.3: tinh tu dau luot, gom connect/header/body)")
    probe = load_b_module(td, "fresh_capture_probe")   # cung ghi pcB/fresh_capture_probe.py cho cac lan chay CLI
    head = resp(hdrs(), body=b"x" * 25)
    split = head.index(b"\r\n\r\n") + 4

    def drip_body(conn):
        conn.sendall(head[:split])
        for i in range(25):
            time.sleep(0.8)
            conn.sendall(head[split + i:split + i + 1])

    def drip_head(conn):
        for i in range(0, split, 6):
            conn.sendall(head[i:i + 6])
            time.sleep(0.8)
        conn.sendall(head[split:])

    def silent(conn):
        time.sleep(12)

    for cid, act, title in (("D1", drip_body, "body nho giot 1 byte/0,8 s (~20 s), moi lan doc < 5 s"),
                            ("D2", drip_head, "header nho giot 6 byte/0,8 s (~20 s)")):
        srv = RawServer([act])
        r, dt = run_probe_cli(td, ["--host", "127.0.0.1", "--port", str(srv.port), "--count", "1"])
        srv.close()
        check("D.%s" % cid, r.returncode != 0 and dt <= 12.0,
              "Q6-T7 %s -> probe dung luot trong <= 10 s (+2 s du phong), thoat khac 0" % title,
              "rc=%d thoi gian=%.1f s; cuoi: %s" % (r.returncode, dt, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""))
    srv = RawServer([silent])
    r, dt = run_probe_cli(td, ["--host", "127.0.0.1", "--port", str(srv.port), "--count", "1"])
    srv.close()
    check("D.D3", r.returncode != 0 and dt <= 12.0, "Q6-T7 may chu nhan ket noi nhung im lang -> thoat khac 0 trong han",
          "rc=%d thoi gian=%.1f s" % (r.returncode, dt))
    # 20 luot, moi luot 0,35 s + nghi 0,2 s nhu lenh quy trinh (~11 s ca chuoi): moi luot deu trong han
    def slow_ok(i):
        def act(conn):
            time.sleep(0.35)
            conn.sendall(resp(hdrs(fid=str(i + 1), ts="%d.500000" % (10 + i), req="%d.400000" % (10 + i))))
        return act
    srv = RawServer([slow_ok(i) for i in range(20)])
    r, dt = run_probe_cli(td, ["--host", "127.0.0.1", "--port", str(srv.port), "--count", "20", "--interval", "0.2"])
    srv.close()
    tail = [ln for ln in r.stdout.splitlines() if "DEADLINE" in ln or "Thanh cong" in ln]
    check("D.D4", r.returncode == 0, "Q6-T7/T9 lenh quy trinh '--count 20 --interval 0.2', moi luot 0,35 s (trong han tung luot) -> khong bi cat",
          "rc=%d thoi gian=%.1f s; %s" % (r.returncode, dt, " / ".join(tail)))
    # D5: trong tien trinh - het han 2 s giua body: quyet dinh dung han, khong de lai luong/worker nen (ke hoach 4.3)
    srv = RawServer([drip_body])
    c = probe.FreshCaptureClient("127.0.0.1", srv.port, timeout=5.0)
    t0 = time.monotonic()
    try:
        r5 = c.capture_fresh(deadline=2.0)
    except TypeError:
        r5 = c.capture_fresh()
    dt = time.monotonic() - t0
    time.sleep(0.5)
    left = [t.name for t in threading.enumerate() if isinstance(t, threading.Timer) and t.is_alive()]
    srv.close()
    check("D.D5", bool(r5.get("error")) and "TIMEOUT" in (r5.get("error") or "") and dt <= 3.5 and not left,
          "Q6-T7 (trong tien trinh, han 2 s): body nho giot -> loi TIMEOUT trong <= 2 s + 1,5 s, khong con luong watchdog/worker song",
          "%.2f s; error=%r; luong Timer con song=%s" % (dt, r5.get("error"), left))
    # D6: trong tien trinh - het han 2 s khi may chu IM LANG giua body (khong co byte nao toi nua trong 6 s)
    full = resp(hdrs())
    sp = full.index(b"\r\n\r\n") + 4

    def stall(conn):
        conn.sendall(full[:sp + 100])
        time.sleep(6)
    srv = RawServer([stall])
    c = probe.FreshCaptureClient("127.0.0.1", srv.port, timeout=5.0)
    t0 = time.monotonic()
    try:
        r6 = c.capture_fresh(deadline=2.0)
    except TypeError:
        r6 = c.capture_fresh()
    dt6 = time.monotonic() - t0
    srv.close()
    check("D.D6", bool(r6.get("error")) and dt6 <= 3.5,
          "Q6-T7 (trong tien trinh, han 2 s): may chu im lang giua body -> luot dung trong <= 2 s + 1,5 s (han doc lap inactivity, khong cho timeout socket 5 s)",
          "luot ket thuc sau %.2f s; error=%r" % (dt6, r6.get("error")))

    # D7: CLI han mac dinh 10 s; body 1 byte moi 4,5 s (moi lan doc < 5 s socket) ~ 27 s
    def gap45(conn):
        conn.sendall(head[:split])
        for i in range(6):
            time.sleep(4.5)
            conn.sendall(head[split + i:split + i + 1])
    srv = RawServer([gap45])
    r, dt = run_probe_cli(td, ["--host", "127.0.0.1", "--port", str(srv.port), "--count", "1"])
    srv.close()
    last = [ln for ln in r.stdout.splitlines() if "FAIL" in ln or "TIMEOUT" in ln][:1]
    check("D.D7", r.returncode != 0 and dt <= 12.0,
          "Q6-T7 (CLI, han 10 s): body 1 byte / 4,5 s -> probe dung luot trong <= 10 s + 2 s",
          "rc=%d thoi gian=%.1f s; %s" % (r.returncode, dt, last[0][:160] if last else ""))


# ============================================================================ E: bang chung
OUT_OPTS = ("--output", "--out", "--out-dir", "--outdir", "--session-dir", "--evidence")


def group_e(td):
    print("---- E: luu bang chung cua probe (ke hoach 4.4; Q6-T8 'tung loi co raw evidence')")
    r, _ = run_probe_cli(td, ["--help"], timeout=30)
    opts = sorted(set(re.findall(r"--[a-z][a-z0-9-]+", r.stdout)))
    opt = next((o for o in OUT_OPTS if o in opts), None)
    check("E.E1", opt is not None, "probe co tuy chon thu muc output de luu header/raw JPEG/so do/JSON tom tat",
          "tuy chon hien co: %s" % opts)
    if not opt:
        return
    import json as _json

    def run_out(actions, name, extra=(), pre_create=False, timeout=60):
        out = Path(td) / ("out_" + name)
        if pre_create:
            out.mkdir()
            (out / "giu_nguyen.txt").write_text("bang chung cu", encoding="utf-8")
        srv = RawServer(actions)
        rr, dt = run_probe_cli(td, ["--host", "127.0.0.1", "--port", str(srv.port), "--count", str(len(actions)), "--interval", "0",
                                    opt, str(out)] + list(extra), timeout=timeout)
        srv.close()
        files = sorted(p.name for p in out.iterdir()) if out.exists() else []
        summ = None
        if (out / "summary.json").exists():
            summ = _json.loads((out / "summary.json").read_text(encoding="utf-8"))
        return rr, dt, out, files, summ, srv

    # E2: phien hop le 3 luot, luu raw JPEG trung tung byte, header nguyen, so do tung luot, tom tat co commit/build khai bao
    acts = [resp(hdrs(fid=str(i + 1), ts="%d.500000" % (10 + i), req="%d.400000" % (10 + i))) for i in range(3)]
    rr, dt, out, files, summ, _ = run_out(acts, "ok", ["--commit", "abc1234", "--build-sha", "deadbeef"])
    jpgs = [f for f in files if f.endswith(".jpg")]
    same = all((out / f).read_bytes() == JPEG for f in jpgs)
    hdr_ok = any("X-Frame-Id: 1" in (out / f).read_text(encoding="utf-8", errors="replace") for f in files if f.startswith("headers"))
    fr = (summ or {}).get("frames") or []
    keys = {"frame_id", "boot_id", "t_frame_us", "t_req_us", "discarded", "rtt_ms"}
    ok = (rr.returncode == 0 and len(jpgs) == 3 and same and hdr_ok and summ is not None and summ.get("verdict") == "PASS"
          and len(fr) == 3 and all(keys <= set(x) for x in fr) and "abc1234" in _json.dumps(summ) and "deadbeef" in _json.dumps(summ))
    check("E.E2", ok, "phien hop le: 3 raw JPEG trung tung byte, header nguyen, summary.json co boot/ID/timestamp/discarded/rtt va commit/build khai bao",
          "rc=%d tep=%s verdict=%s" % (rr.returncode, files, (summ or {}).get("verdict")))
    # E3: thu muc da ton tai -> tu choi TRUOC request, khong xoa/ghi de
    rr, dt, out, files, summ, srv = run_out(acts[:1], "exist", pre_create=True)
    kept = (out / "giu_nguyen.txt").read_text(encoding="utf-8") == "bang chung cu"
    check("E.E3", rr.returncode != 0 and files == ["giu_nguyen.txt"] and kept and srv.accepted == 0,
          "thu muc output da ton tai -> tu choi truoc khi gui request, khong xoa/ghi de",
          "rc=%d tep=%s so ket noi toi may chu=%d" % (rr.returncode, files, srv.accepted))
    # E4: loi giua phien (ID nhay coc) -> phien INVALID, giu bang chung cac luot hop le truoc loi va luot loi
    acts4 = [resp(hdrs(fid="1")), resp(hdrs(fid="2", ts="11.500000", req="11.400000")), resp(hdrs(fid="4", ts="12.500000", req="12.400000"))]
    rr, dt, out, files, summ, _ = run_out(acts4, "gap")
    fr = (summ or {}).get("frames") or []
    ok = (rr.returncode != 0 and summ is not None and summ.get("verdict") not in ("PASS", None) and len(fr) == 3
          and fr[2].get("error") and all(f in files for f in ("frame_0001.jpg", "frame_0002.jpg")) and any(f.startswith("frame_0003") for f in files))
    check("E.E4", ok, "loi giua phien -> toan phien INVALID, giu ca bang chung luot hop le truoc loi va luot loi",
          "rc=%d tep=%s verdict=%s loi luot 3=%r" % (rr.returncode, files, (summ or {}).get("verdict"), fr[2].get("error") if len(fr) > 2 else None))
    # E5: header lap phai duoc luu NGUYEN (ca hai dong), vi do chinh la bang chung cua loi
    rr, dt, out, files, summ, _ = run_out([resp(hdrs() + [("X-Frame-Id", "2")])], "dup")
    txt = "".join((out / f).read_text(encoding="utf-8", errors="replace") for f in files if f.startswith("headers"))
    n = len(re.findall(r"(?im)^x-frame-id:", txt))
    check("E.E5", rr.returncode != 0 and n == 2, "header lap -> tep header luu nguyen ca hai dong X-Frame-Id (bang chung loi)",
          "rc=%d so dong X-Frame-Id trong tep header=%d" % (rr.returncode, n))
    # E6/E7: phan body da nhan truoc khi het han / dut ket noi phai duoc luu vao tep rieng, khong danh dau JPEG hop le
    full = resp(hdrs(), body=JPEG)
    split = full.index(b"\r\n\r\n") + 4

    def drip(conn):
        conn.sendall(full[:split + 100])
        time.sleep(6)
    rr, dt, out, files, summ, _ = run_out([drip], "drip", ["--deadline", "3"])
    part = [f for f in files if f.startswith("frame_0001")]
    size = (out / part[0]).stat().st_size if part else -1
    check("E.E6", rr.returncode != 0 and part and not part[0].endswith(".jpg") and size == 100,
          "het han giua body -> luu 100 byte da nhan vao tep rieng (khong .jpg), phien INVALID (ke hoach 4.3)",
          "rc=%d %.1f s tep=%s kich thuoc=%d" % (rr.returncode, dt, part, size))

    def cut(conn):
        conn.sendall(full[:split + 100])
    rr, dt, out, files, summ, _ = run_out([cut], "cut")
    part = [f for f in files if f.startswith("frame_0001")]
    size = (out / part[0]).stat().st_size if part else -1
    check("E.E7", rr.returncode != 0 and part and not part[0].endswith(".jpg") and size == 100,
          "TCP dut giua body -> luu 100 byte da nhan vao tep rieng (khong .jpg), phien INVALID",
          "rc=%d tep=%s kich thuoc=%d" % (rr.returncode, part, size))
    # E8: khong truyen thu muc output va thu muc lam viec khong co docs/logs -> probe phai van luu bang chung hoac tu choi
    srv = RawServer(acts[:1])
    empty = Path(td) / "cwd_rong"
    empty.mkdir()
    p = Path(td) / "pcB" / "fresh_capture_probe.py"
    r8 = subprocess.run([PY, str(p), "--host", "127.0.0.1", "--port", str(srv.port), "--count", "1"], capture_output=True,
                        text=True, timeout=60, cwd=str(empty))
    srv.close()
    made = [str(x.relative_to(empty)) for x in empty.rglob("*")]
    if r8.returncode == 0 and not made:
        note("E.E8", "khong truyen --output va chay ngoai goc repo -> probe chay, KHONG luu bang chung, khong canh bao (ke hoach 4.4: luon tao thu muc output)",
             "rc=%d; tep tao ra: %s" % (r8.returncode, made))
    else:
        check("E.E8", True, "khong truyen --output ngoai goc repo -> van luu bang chung hoac tu choi", "rc=%d tep=%s" % (r8.returncode, made[:5]))


# ============================================================================ M: mock
def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_mock(path, args=()):
    port = free_port()
    p = subprocess.Popen([PY, str(path), "--port", str(port)] + list(args), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p, port
        except OSError:
            time.sleep(0.05)
    p.kill()
    raise RuntimeError("mock khong len")


def get(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request("GET", path)
    r = c.getresponse()
    body = r.read()
    h = {k.lower(): v for k, v in r.getheaders() if k.lower() not in ("date", "server")}
    c.close()
    return r.status, h, body


def group_m(td):
    print("---- M: mock /capture_fresh va hop dong mock cu (Q6-T1 mock, Q6-T8)")
    probe = load_b_module(td, "fresh_capture_probe")
    mb = Path(td) / "pcB" / "mock_camera.py"
    mb.write_bytes(show(B, "pc/mock_camera.py"))
    m0 = Path(td) / "pc0" / "mock_camera.py"
    m0.parent.mkdir(exist_ok=True)
    m0.write_bytes(show(BASE, "pc/mock_camera.py"))
    p, port = start_mock(mb)
    try:
        c = probe.FreshCaptureClient("127.0.0.1", port)
        rs = [c.capture_fresh() for _ in range(20)]
    finally:
        p.kill()
    ids = [r["frame_id"] for r in rs]
    boots = set(r["boot_id"] for r in rs)
    ok = all(r["error"] is None and r["jpeg_valid"] and r["discarded"] == 0 for r in rs) and ids == list(range(1, 21)) and len(boots) == 1
    check("M.M1", ok, "Q6-T1 (mock): 20 luot lien tiep -> 20/20 JPEG hop le, 5 header, ID 1..20, cung boot, discarded 0",
          "ID %s..%s; boot %d gia tri; loi %s" % (ids[0], ids[-1], len(boots), [r["error"] for r in rs if r["error"]][:2]))
    pa, porta = start_mock(m0)
    pb, portb = start_mock(mb)
    try:
        diffs = []
        for path in ("/status", "/capture", "/capture", "/control?var=framesize&val=5", "/status", "/capture", "/_counts"):
            a, b = get(porta, path), get(portb, path)
            if path == "/_counts":
                continue
            ha = {k: v for k, v in a[1].items() if k != "x-timestamp"}
            hb = {k: v for k, v in b[1].items() if k != "x-timestamp"}
            if a[0] != b[0] or ha != hb or (path != "/capture" and a[2] != b[2]) or (path == "/capture" and len(a[2]) != len(b[2])):
                diffs.append(path)
            if path == "/capture" and ("x-timestamp" in a[1]) != ("x-timestamp" in b[1]):
                diffs.append(path + " X-Timestamp")
    finally:
        pa.kill()
        pb.kill()
    check("M.M2", not diffs, "Q6-T8: mock cu (/status, /capture, /control) giu nguyen hop dong so voi base %s" % BASE[:7], "lech: %s" % diffs)


# ============================================================================ R: hoi quy
def group_r():
    print("---- R: hoi quy selftest (Q6-T8; ke hoach buoc 3-4)")
    # chi tep san pham: tep test cua Tester (pc/test_c5a_*.py) do Tester dang sua/them trong vong nay
    clean = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", B, "--", "pc/", ":!pc/test_c5a_*.py"]).returncode == 0
    check("R.R0", clean, "tep san pham pc/ cua cay lam viec trung B (cac lenh duoi chay ma B)",
          "git diff --quiet %s -- pc/ ':!pc/test_c5a_*.py'" % B[:7])
    for cid, args in (("R1", ["pc/camera_profile.py", "--selftest"]), ("R2", ["pc/capture_session.py", "--selftest"]),
                      ("R3", ["pc/e2e_capture_mock.py"]), ("R4", ["pc/fresh_capture_probe.py", "--selftest"])):
        t0 = time.monotonic()
        r = subprocess.run([PY] + args, capture_output=True, text=True, cwd=str(REPO), timeout=600,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        last = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-1:] or [""]
        check("R.%s" % cid, r.returncode == 0, " ".join(args), "rc=%d %.1f s; cuoi: %s" % (r.returncode, time.monotonic() - t0, last[0][:120]))


# ============================================================================ S: rang buoc ma
def group_s():
    print("---- S: rang buoc ke hoach Vong 5 kiem tren ma nguon tai B (khong chay duoc tren may tinh)")
    src = show(B, SKETCH + "app_httpd.cpp").decode("utf-8")
    decl = re.search(r"^static\s+(.*?)\s*s_stream_active\b", src, re.M)
    synced = bool(re.search(r"std::atomic|_Atomic|__atomic_|portENTER_CRITICAL|taskENTER_CRITICAL|portMUX", src))
    check("S.S1", decl is not None and ("volatile" not in decl.group(1) or synced),
          "ke hoach 4.2: chu so huu khoa (STREAM/OTHER) doc/ghi co dong bo (atomic/critical), khong chi 'volatile'",
          "khai bao: %r; co atomic/critical: %s" % (decl.group(0) if decl else None, synced))
    ino0 = show(BASE, SKETCH + "CameraWebServerTest.ino").decode("utf-8").replace("\r\n", "\n")
    ino = show(B, SKETCH + "CameraWebServerTest.ino").decode("utf-8").replace("\r\n", "\n")

    def non_jpeg(t):
        i = t.find("// Best option for face detection/recognition")
        return t[i:t.find("#endif", i)] if i >= 0 else ""
    check("S.S2", non_jpeg(ino0) == non_jpeg(ino),
          "ke hoach 3 (.ino): khong doi duong khong-JPEG ngoai nhu cau (chi chot 1 buffer cho JPEG PSRAM)",
          "base: %r -> B: %r" % (" ".join(non_jpeg(ino0).split())[-40:], " ".join(non_jpeg(ino).split())[-40:]))
    logs = re.findall(r"Serial\.print[a-z]*\(([^;]*)\);", ino)
    cfg = [l for l in logs if re.search(r"fb_count|grab_mode|fb_location|GRAB_LATEST", l)]
    check("S.S3", bool(cfg), "ke hoach 3 (.ino) va Q6-T9: log cau hinh camera thuc da init (fb_count, grab_mode)",
          "lenh Serial co fb_count/grab_mode: %s" % cfg)
    i = ino.find("static void startServerAndReport()")
    body = ino[i:ino.find("\n}\n", i)] if i >= 0 else ""
    a, s = body.find("fresh_capture_init_boot_id()"), body.find("startCameraServer()")
    check("S.S4", 0 <= a < s, "ke hoach 4.4: Boot ID tao (sau Wi-Fi) TRUOC khi server nhan request; khong tao lai khi retry",
          "vi tri init=%d, startCameraServer=%d trong startServerAndReport" % (a, s))
    # S5: quy trinh bo phai du noi dung ke hoach Vong 5 muc 5 (doan cuoi) cho Q6-T9/Q6-T10 (CAN BO)
    proc = show(B, "docs/procedures/quy-trinh-c5a-fresh-capture.md").decode("utf-8")
    need = {
        "luu firmware/binary cu truoc khi nap": r"(lưu|sao lưu|backup)[^\n]{0,60}(firmware|binary|\.bin|bản)[^\n]{0,20}(cũ|trước|baseline)",
        "ghi SHA build/nap (--build-sha/--commit)": r"--build-sha|--commit",
        "kiem log cau hinh 1 buffer (fb_count=1)": r"fb_count\s*=\s*1",
        "probe luu bang chung (--output)": r"--output|--out\b|--out-dir",
        "3 luot x 20 capture (Q6-T9)": r"3 lượt|ba lượt|3 lần[^\n]{0,30}20|lặp lại[^\n]{0,30}3",
        "ap/doi chieu profile C2 truoc/sau (Q6-T9)": r"profile",
        "luu log Serial": r"(lưu|chép|ghi)[^\n]{0,40}Serial|Serial[^\n]{0,60}(lưu|tệp|log)",
        "Q6-T10: legacy//capture hoac config khi stream mo": r"/stream[\s\S]{0,600}(/capture\b|/control|/bmp)",
        "Q6-T10: ngat Wi-Fi/PC giua luot": r"Wi-Fi[^\n]{0,60}(ngắt|tắt|mất)|(ngắt|tắt)[^\n]{0,40}Wi-Fi",
        "dung .venv/Scripts/python.exe (ENVIRONMENT)": r"\.venv/Scripts/python\.exe",
        "Q6-T10: moi ca >= 3 lan (R7)": r"(≥|>=)\s*3 lần|ít nhất 3 lần|lặp[^\n]{0,30}3 lần|3 lần cho mỗi|mỗi ca[^\n]{0,30}3",
        "thong tin bo nho (heap) truoc/sau": r"heap|bộ nhớ (còn )?trống|free heap",
        "chup anh bo tri khi do": r"ảnh bố trí|chụp ảnh[^\n]{0,40}(bố trí|bàn đo|setup)",
    }
    missing = [k for k, rx in need.items() if not re.search(rx, proc, re.I)]
    check("S.S5", not missing, "quy trinh bo (docs/procedures/quy-trinh-c5a-fresh-capture.md) du noi dung ke hoach Vong 5 muc 5 cho Q6-T9/T10",
          "thieu %d/%d: %s" % (len(missing), len(need), missing))
    group_s6(proc, ino)


def group_s6(proc, ino):
    """S6: lenh va ky vong trong quy trinh bo dung voi cong cu/firmware tai B (nguoi dung lam theo tren bo)."""
    import shlex
    bad = []
    td = tempfile.mkdtemp(prefix="c5a_s6_")
    try:
        pcdir = Path(td) / "pc"
        pcdir.mkdir()
        for name in ("camera_profile", "fresh_capture_probe", "mock_camera"):
            (pcdir / (name + ".py")).write_bytes(show(B, "pc/%s.py" % name))
        # (a) moi lenh python pc/<tool>.py trong quy trinh phai duoc argparse cua tool chap nhan
        cmds = sorted(set(m.group(1).strip("` ") for m in re.finditer(r"\.venv/Scripts/python\.exe (pc/(?:camera_profile|fresh_capture_probe)\.py[^\n`]*)", proc)))
        for c in cmds:
            line = c.replace("<IP_ESP32>", "127.0.0.1").replace("$COMMIT_SHA", "abc1234").replace("$BUILD_SHA", "deadbeef")
            args = shlex.split(line)[1:]
            args = [a if not a.startswith("docs/logs/") else str(Path(td) / "out" / Path(a).name) for a in args]
            if "fresh_capture_probe" in line and "--port" in args:
                args[args.index("--port") + 1] = "1"   # cong dong: tu choi ngay, khong gui gi ra mang
            r = subprocess.run([PY, str(pcdir / Path(shlex.split(line)[0]).name)] + args, capture_output=True, text=True, timeout=60, cwd=td)
            if re.search(r"unrecognized arguments|error: argument|the following arguments are required", r.stderr):
                bad.append("%s -> %s" % (line[:90], r.stderr.strip().splitlines()[-1][:120]))
        # (b) dong Serial 'thay gi la dung' phai khop printf cua .ino voi gia tri enum that (cau hinh JPEG + PSRAM)
        fmt = re.search(r'Serial\.printf\("Camera Init OK: ([^"]*?)\\n"', ino)
        want = None
        if fmt:
            want = fmt.group(1).replace("%d", "{}").format(1, 1, 0)   # fb_count=1, CAMERA_GRAB_LATEST=1, CAMERA_FB_IN_PSRAM=0
            if ("Camera Init OK: " + want) not in proc:
                got = re.findall(r"Camera Init OK:[^\n`]*", proc)
                bad.append("dong Serial ky vong %r, quy trinh ghi %s" % ("Camera Init OK: " + want, got[:2]))
        # (c) arduino-cli khong co trong PATH thi quy trinh phai dung duong dan that
        if re.search(r"(?m)^\s*arduino-cli ", proc) and shutil.which("arduino-cli") is None and "arduino-cli.exe" not in proc:
            bad.append("lenh 'arduino-cli' tran khi PATH khong co arduino-cli (ENVIRONMENT: chua co trong PATH)")
        # (d) SHA build phai lay tu binary vua build, khong gan cung
        hard = re.findall(r'BUILD_SHA\s*=\s*"[0-9a-f]{6,64}"', proc)
        if hard:
            bad.append("BUILD_SHA gan cung %s (SHA .bin doi moi lan build)" % hard[:1])
        # (e) buoc sao luu: nguon phai ton tai hoac do chinh quy trinh tao ra; khong nuot loi bang '|| true'
        for src in re.findall(r"cp -f (\S+\.bin) ", proc):
            made = re.search(r"--output-dir[^\n]*%s|--export-binaries" % re.escape(str(Path(src).parent)), proc)
            if not (REPO / src).exists() and not made:
                bad.append("sao luu tu %s: tep khong ton tai va khong buoc nao tao ra%s" % (src, "; loi bi nuot bang '|| true'" if "|| true" in proc else ""))
        # (f) ca lap >= 3 lan ma lenh probe dung cung mot --output co dinh -> lan 2 bi probe tu choi (thu muc da co)
        for sec in re.split(r"\n(?=#{2,3} )", proc):
            if re.search(r"lặp lại|≥\s*3 lần|>=\s*3 lần", sec) and not re.search(r"đổi output|đổi thư mục", sec):
                for o in set(x.strip("`") for x in re.findall(r"--output (\S+)", sec)):
                    if not re.search(r"\$|<|%", o):
                        bad.append("ca lap >= 3 lan dung --output co dinh %s: tu lan 2 probe tu choi vi thu muc da ton tai" % o)
        # (g) chuoi 'thay gi la dung' cua camera_profile phai co that trong cong cu
        cp_src = show(B, "pc/camera_profile.py").decode("utf-8")
        for s in set(re.findall(r"`(Ap ho so[^`]*|Ho so khop[^`]*|VERIFY[^`]*)`", proc)):
            if s.split(":")[0].strip() not in cp_src:
                bad.append("chuoi ky vong %r khong co trong pc/camera_profile.py" % s)
        # (h) buoc doc heap qua /status: status_handler cua firmware phai tra truong heap
        if re.search(r"heap[^\n]{0,80}/status|/status[^\n]{0,80}heap", proc, re.I):
            src = show(B, SKETCH + "app_httpd.cpp").decode("utf-8")
            i = src.find("static esp_err_t status_handler(")
            body = src[i:src.find("\n}\n", i)] if i >= 0 else ""
            if not re.search(r"heap", body, re.I):
                bad.append("quy trinh doc heap qua /status nhung status_handler khong tra truong heap nao")
        # (i) 'sao luu firmware cu' khong duoc chep chinh ban vua build trong cung quy trinh
        for src_bin in re.findall(r"cp -f (\S+\.bin) ", proc):
            outdir = str(Path(src_bin).parent).replace("\\", "/")
            i_build = proc.find("--output-dir " + outdir)
            i_cp = proc.find("cp -f " + src_bin)
            if 0 <= i_build < i_cp:
                bad.append("buoc 'sao luu firmware cu' chep %s do chinh lenh compile phia truoc vua tao (ban MOI), khong phai firmware cu tren bo" % src_bin)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    check("S.S6", not bad, "lenh va ky vong trong quy trinh bo chay/khop voi cong cu va firmware tai B",
          "%d van de: %s" % (len(bad), bad))


# ============================================================================ J: JSON /status cua harness (Vong 6 V6-T1..T3)
HEX_OV3660 = (["0x%04x" % r for r in range(0x3400, 0x3406, 2)] + ["0x3406", "0x3500", "0x3503", "0x350a", "0x350c"] +
              ["0x%04x" % r for r in range(0x5480, 0x5491)] + ["0x%04x" % r for r in range(0x5380, 0x538c)] +
              ["0x%04x" % r for r in range(0x5580, 0x558b)])
HEX_OV2640 = ["0x00d3", "0x0111", "0x0132"]
HEAP_KEYS = ("heap_internal_free_bytes", "heap_psram_free_bytes")
# gia tri sensor_defaults() cua harness (trung control profile cam_SVGA_q20_20260928)
SENSOR_DEF = {"xclk": 20, "pixformat": 4, "framesize": 11, "quality": 20, "brightness": 1, "contrast": 0, "saturation": -2,
              "sharpness": 0, "special_effect": 0, "wb_mode": 2, "awb": 1, "awb_gain": 1, "aec": 0, "aec2": 0, "ae_level": 0,
              "aec_value": 783, "agc": 0, "agc_gain": 8, "gainceiling": 0, "bpc": 0, "wpc": 1, "raw_gma": 1, "lenc": 1,
              "hmirror": 0, "vflip": 1, "dcw": 1, "colorbar": 0}


def base_status_keys():
    """Ten truong sensor (khong phai thanh ghi) ma status_handler o base main in ra."""
    src = show(BASE, SKETCH + "app_httpd.cpp").decode("utf-8")
    i = src.find("static esp_err_t status_handler(")
    body = src[i:src.find("\n}\n", i)]
    return set(re.findall(r'\\"([a-z_][a-z0-9_]*)\\":', body))


def json_checks(name, jsons, td):
    import json
    led = name == "co_LED"
    old = base_status_keys()
    want_nonhex = old | set(HEAP_KEYS)

    def load(tag):
        try:
            return json.loads(jsons[tag]), ""
        except KeyError:
            return None, "harness khong in JSON %s" % tag
        except ValueError as e:
            return None, "JSON khong hop le: %s" % e
    d, err = load("H36")
    if d is not None:
        nonhex = set(k for k in d if not k.startswith("0x"))
        hexk = [k for k in d if k.startswith("0x")]
        types_ok = all(type(v) is int for v in d.values())
        exp = dict(SENSOR_DEF, led_intensity=0 if led else -1)
        vals_bad = {k: (d.get(k), v) for k, v in exp.items() if d.get(k) != v}
        ok = (nonhex == want_nonhex and sorted(hexk) == sorted(HEX_OV3660) and types_ok and not vals_bad and
              d["heap_internal_free_bytes"] == 123456 and d["heap_psram_free_bytes"] == 654321)
        err = ("truong thua %s thieu %s; thanh ghi %d/%d; kieu int=%s; gia tri lech %s; heap %s/%s" %
               (sorted(nonhex - want_nonhex), sorted(want_nonhex - nonhex), len(hexk), len(HEX_OV3660), types_ok, vals_bad,
                d.get("heap_internal_free_bytes"), d.get("heap_psram_free_bytes")))
    else:
        ok = False
    check("J1.%s" % name, ok, "V6-T1: JSON /status parse duoc; truong = truong sensor cua base main + dung 2 truong heap; 48 thanh ghi OV3660; moi gia tri so nguyen, gia tri sensor giu nguyen", err)
    a, ea = load("H37a")
    b, eb = load("H37b")
    ok = (a is not None and b is not None and a.get("heap_internal_free_bytes") == 0 and a.get("heap_psram_free_bytes") == 4294967295 and
          b.get("heap_internal_free_bytes") == 4294967295 and b.get("heap_psram_free_bytes") == 0)
    check("J2.%s" % name, ok, "V6-T2: JSON bien heap 0 / UINT32_MAX parse duoc, so khong am", ea or eb or "a=%s/%s b=%s/%s" % (
        a.get("heap_internal_free_bytes"), a.get("heap_psram_free_bytes"), b.get("heap_internal_free_bytes"), b.get("heap_psram_free_bytes")))
    det = []
    ok = True
    for tag in ("H38a", "H38b"):
        x, e = load(tag)
        good = x is not None and all(x[k] == -2147483648 for k in HEX_OV3660) and x.get("aec_value") == 65535 and x.get("brightness") == -128
        ok = ok and good
        det.append("%s %s len=%d" % (tag, "ok" if good else (e or "sai gia tri"), len(jsons.get(tag, ""))))
    check("J3.%s" % name, ok, "V6-T2: JSON gia tri cuc tri parse duoc, so am/lon in dung", "; ".join(det))
    o, e = load("H39")
    check("J4.%s" % name, o is not None and sorted(k for k in o if k.startswith("0x")) == HEX_OV2640 and all(k in o for k in HEAP_KEYS),
          "V6-T2: JSON nhanh OV2640 parse duoc, 3 thanh ghi + 2 truong heap", e or str(sorted(k for k in o if k.startswith("0x"))))
    # V6-T3: heap doi giua cac mau khong thanh troi cau hinh khi doi chieu bang ham cua quy trinh (camera_profile tai B)
    cp = load_b_module(td, "camera_profile")
    cs = load_b_module(td, "capture_session")
    snaps = [load(t)[0] for t in ("H44a", "H44b", "H44c")]
    ctrls = {k: SENSOR_DEF[k] for k in ("aec", "agc", "awb", "brightness", "contrast", "saturation", "hmirror", "vflip", "lenc",
                                         "dcw", "aec_value", "agc_gain", "awb_gain", "wb_mode")}
    res = []
    ok = all(s is not None for s in snaps)
    if ok:
        strip = [{k: v for k, v in s.items() if k not in HEAP_KEYS} for s in snaps]
        ok = strip[0] == strip[1] == strip[2] and len(set(s["heap_internal_free_bytes"] for s in snaps)) == 3
        for s in snaps:
            c_ok, mm = cp.diff_controls(s, "SVGA", 20, ctrls)
            r_ok, rm = cp.compare_registers({k: s[k] for k in HEX_OV3660[:7]}, snaps[0], HEX_OV3660[:7])
            ok = ok and c_ok and r_ok
            res.append("%s/%s" % (c_ok, r_ok))
        cmp = cs.compare_status({"ok": True, "json": snaps[0]}, {"ok": True, "json": snaps[1]})
        res.append("capture_session.compare_status bao doi: %s" % sorted(cmp["changed"]))
    check("J5.%s" % name, ok, "V6-T3: 3 mau heap khac nhau, phan sensor giong het; diff_controls/compare_registers (SVGA q20) khong bao troi vi heap",
          "; ".join(res))
    if ok and sorted(cmp["changed"]) == sorted(HEAP_KEYS):
        d3 = show(B, "docs/design/S3_FRESH_CAPTURE.md").decode("utf-8")
        note("J5n.%s" % name, "capture_session.compare_status() (C2/C3, khong sua theo ke hoach) van liet ke 2 truong heap la 'doi'; verdict phien khong dua vao 'changed'",
             "ke hoach Vong 6 muc 2 da luong truoc; S3_FRESH_CAPTURE.md 4.3 %s" % (
                 "ghi 'khong dung trong ... compare_status' (mo ta khong chinh xac)" if "không dùng trong đối chiếu bắt trôi cấu hình (`compare_status`)" in d3
                 else "da mo ta dung: compare_status co the liet ke heap, khong anh huong verdict"))


# ============================================================================ S7: quy trinh Vong 6 chay nguyen van (V6-T4, V6-T5)
def git_bash():
    g = shutil.which("git")
    for c in ([Path(g).resolve().parents[1] / "bin" / "bash.exe"] if g else []) + [Path("C:/Program Files/Git/bin/bash.exe")]:
        if c.exists():
            return str(c)
    return None


def proc_blocks(proc):
    """[(vi_tri, ngon_ngu, ma, tieu_de_gan_nhat)] cua moi khoi ``` trong quy trinh (bo thut le)."""
    out = []
    for m in re.finditer(r"(?m)^([ \t]*)```(bash|powershell|text)?[ \t]*\n(.*?)^[ \t]*```", proc, re.S):
        ind = len(m.group(1))
        code = "\n".join(ln[ind:] if ln[:ind].strip() == "" else ln for ln in m.group(3).split("\n"))
        heads = [h for h in re.finditer(r"(?m)^(#{2,3} .*|\d+\. \*\*.*)$", proc[:m.start()])]
        out.append((m.start(), m.group(2) or "", code, heads[-1].group(1) if heads else ""))
    return out


def find_block(blocks, lang, *needles):
    for b in blocks:
        if b[1] == lang and all(n in b[2] for n in needles):
            return b[2]
    return None


def group_s7(proc, td):
    import json
    import hashlib
    print("---- S7: quy trinh bo Vong 6 - lenh chay nguyen van tren may tinh/thu muc tam (V6-T4, V6-T5)")
    blocks = proc_blocks(proc)
    bash = git_bash()
    s7 = Path(td) / "s7"
    s7.mkdir()

    def run_bash(code, env_extra, cwd=REPO):
        r = subprocess.run([bash, "-c", code], capture_output=True, text=True, cwd=str(cwd), timeout=120,
                           env=dict(os.environ, **env_extra), encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout + r.stderr).strip()

    # S7.1 bien K cua 'lap cho tung luot/lan K' phai duoc gan bang lenh; khong gan thi ${K} rong -> moi lan cung output
    uses_k = [b for b in blocks if b[1] == "bash" and re.search(r"\$\{K\}|\$K\b", b[2])]
    assign = re.search(r"(?m)^\s*(K=\d|for K in|export K=)", proc)
    rc, out = run_bash('SESSION_DIR=/tmp/phien; echo "$SESSION_DIR/probe_q6_t10_busy_run${K}" "$SESSION_DIR/status_before_run${K}.json"', {"K": ""})
    check("S7.1", not uses_k or bool(assign),
          "L24/ke hoach 4.2: lenh Git Bash dung ${K} cho tung luot/lan phai co lenh gan K (K=1, K=2, ...) de moi lan co output rieng",
          "%d khoi bash dung ${K}; lenh gan K trong quy trinh: %s; khi K chua gan, Git Bash mo rong thanh: %s" % (
              len(uses_k), assign.group(0).strip() if assign else "KHONG CO", out))
    # S7.2 Q6-T9 bat buoc 3x20 JPEG 800x600: phai co lenh doc kich thuoc JPEG that tu thu muc probe
    i4, i5 = proc.find("## 4."), proc.find("## 5.")
    size_cmd = [b for b in blocks if b[1] in ("bash", "powershell") and i4 <= b[0] < i5 and
                re.search(r"Image\.open|\.size\b|identify|SOF|width|height|800", b[2])]
    check("S7.2", bool(size_cmd),
          "ke hoach muc 2/V6-T4: quy trinh co lenh kiem kich thuoc JPEG that 800x600 cua 3x20 anh (ten profile/log khong du)",
          "khoi lenh doc kich thuoc anh: %d%s" % (len(size_cmd), "" if size_cmd else "; muc 4 chi ghi ky vong '800x600' bang loi (probe PASS voi JPEG 320x240 cua mock)"))
    # S7.3 khao sat heap: luu thoi diem PC va delta vao tep (khong chi in man hinh)
    hb = find_block(blocks, "bash", "heap_internal_free_bytes", "delta")
    st_b = find_block(blocks, "bash", "/status", "status_before_run")
    saved = bool(hb and re.search(r"\s(>>?|tee)\s|open\([^)]*['\"][wa]['\"]", hb))
    pc_time = bool(re.search(r"date\b|Get-Date|datetime|time\.time|strftime", (st_b or "") + (hb or "")))
    check("S7.3", saved and pc_time,
          "ke hoach muc 2: moi snapshot heap luu raw JSON + thoi diem PC + so luot; delta sau-truoc duoc LUU (khong chi in)",
          "delta luu vao tep: %s; ghi thoi diem PC luc lay snapshot: %s" % (saved, pc_time))
    # S7.4 /capture,/bmp,/control luc stream: in VA luu status + body
    bb = find_block(blocks, "bash", "/capture", "/bmp", "status_code")
    saved = bool(bb and re.search(r"\s(>>?|tee)\s|open\([^)]*['\"][wa]['\"]", bb))
    check("S7.4", bool(bb) and saved, "ke hoach 4.3: /capture, /bmp, /control khi stream mo phai in va LUU ca status lan body",
          "khoi lenh co: %s; co ghi ra tep: %s" % (bool(bb), saved))
    # S7.5 manifest: baseline (nguon, hash binary day du, core/FQBN) + Q6
    mb = find_block(blocks, "bash", "manifest.json")
    mtxt = mb or ""
    has = {"baseline": "baseline" in mtxt.lower(), "core": bool(re.search(r"core|3\.3\.11|arduino-cli version|version", mtxt)),
           "q6_sha": "binary_sha256" in mtxt}
    check("S7.5", all(has.values()), "ke hoach 4.4-4.5: manifest ghi baseline tai build (nguon main, hash day du) va core/FQBN cung binary Q6",
          "manifest co: %s" % has)
    if not bash:
        check("S7.6", False, "khong tim thay Git Bash de chay nguyen van", "")
        return
    # S7.6 buoc 4.1 nguyen van: profile dung/sai hash/thieu tep
    b41 = find_block(blocks, "bash", "PROF_SRC=", "EXPECTED_SHA")
    prof = REPO / "data/calibration/camera_profiles/cam_SVGA_q20_20260928.json"
    det = []
    ok = bool(b41)
    sess = s7 / "phien"
    sess.mkdir()
    if b41 and prof.exists():
        rc, out = run_bash(b41, {"SESSION_DIR": sess.as_posix()})
        cp_ok = (sess / prof.name).exists() and hashlib.sha256((sess / prof.name).read_bytes()).hexdigest() == hashlib.sha256(prof.read_bytes()).hexdigest()
        ok = ok and rc == 0 and cp_ok
        det.append("dung: rc=%d sao_chep_dung_bytes=%s '%s'" % (rc, cp_ok, out.splitlines()[-1][:80] if out else ""))
        bad_prof = s7 / "sai.json"
        bad_prof.write_bytes(prof.read_bytes().replace(b'"quality": 20', b'"quality": 12'))
        for label, path in (("sai_hash", bad_prof.as_posix()), ("thieu_tep", (s7 / "khong_co.json").as_posix())):
            d2 = s7 / ("phien_" + label)
            d2.mkdir()
            code = re.sub(r'(?m)^PROF_SRC=.*$', 'PROF_SRC="%s"' % path, b41)
            rc, out = run_bash(code, {"SESSION_DIR": d2.as_posix()})
            good = rc != 0 and "LOI" in out and not any(d2.iterdir())
            ok = ok and good
            det.append("%s: rc=%d dung=%s khong_sao_chep=%s" % (label, rc, "LOI" in out, not any(d2.iterdir())))
    elif b41:
        note("S7.6n", "khong co tep profile cua nguoi dung de chay buoc 4.1", str(prof))
    check("S7.6", ok, "V6-T4: buoc 4.1 chay nguyen van: profile dung -> sao chep nguyen bytes; sai hash/thieu tep -> LOI, dung, khong sao chep",
          "; ".join(det) + (" (lenh 'exit 1' trong terminal tuong tac se dong luon cua so Git Bash)" if b41 and "exit 1" in b41 else ""))
    # S7.7 buoc 4.3.4 nguyen van: delta heap tu snapshot; snapshot loi/thieu truong khong thanh so 0
    hj = getattr(group_h, "jsons", {})
    det = []
    ok = bool(hb and hj.get("H44a") and hj.get("H44b"))
    if ok:
        cases = (("binh_thuong", hj["H44a"], hj["H44b"], True),
                 ("truoc_la_503", "ERROR CAMERA_BUSY_STREAM", hj["H44b"], False),
                 ("thieu_truong_heap", json.dumps({k: v for k, v in json.loads(hj["H44a"]).items() if k not in HEAP_KEYS}), hj["H44b"], False))
        for label, bef, aft, expect_ok in cases:
            d2 = s7 / ("heap_" + label)
            d2.mkdir()
            (d2 / "status_before_run1.json").write_text(bef, encoding="utf-8")
            (d2 / "status_after_run1.json").write_text(aft, encoding="utf-8")
            rc, out = run_bash(hb, {"SESSION_DIR": d2.as_posix(), "K": "1"})
            good = (rc == 0 and "100000 -> 99000 (delta: -1000 bytes)" in out and "2000000 -> 1990000 (delta: -10000 bytes)" in out) if expect_ok \
                else (rc != 0 and "delta: " not in out)
            if expect_ok:   # Vong 16 (L26.2): delta + so luot + thoi diem PC duoc LUU vao heap_survey_run${K}.json
                sv = d2 / "heap_survey_run1.json"
                try:
                    j = json.loads(sv.read_text(encoding="utf-8"))
                    sv_ok = (str(j.get("run")) == "1" and j.get("heap_internal_delta") == -1000 and j.get("heap_psram_delta") == -10000 and
                             j.get("heap_internal_before") == 100000 and j.get("heap_psram_after") == 1990000 and bool(j.get("timestamp_pc")))
                except Exception as e:  # noqa: BLE001
                    sv_ok, j = False, str(e)
                good = good and sv_ok
                det.append("heap_survey_run1.json dung: %s" % sv_ok)
            ok = ok and good
            det.append("%s: rc=%d %s" % (label, rc, (out.splitlines() or [""])[-1][:90]))
    check("S7.7", ok, "V6-T5: buoc tinh delta heap chay nguyen van (K=1): so dung va luu heap_survey; snapshot 503/thieu truong -> loi, khong coi la 0", "; ".join(det))
    # S7.8 buoc 4.3.5 nguyen van: doi chieu chi doc tren snapshot
    pb = find_block(blocks, "bash", "diff_controls", "compare_registers")
    det = []
    ok = bool(pb) and (sess / prof.name).exists()
    if pb:
        no_http = not re.search(r"requests|urllib|/control|--verify|apply_and_verify", pb)
        ok = ok and no_http
        det.append("khong goi HTTP/ap lai: %s" % no_http)
    if ok:
        p = json.loads((sess / prof.name).read_text(encoding="utf-8"))
        cpm = load_b_module(td, "camera_profile")
        base = dict(p["controls"], framesize=cpm.FRAMESIZES[p["framesize"]], quality=p["quality"], **p["expected_registers"])
        base.update(xclk=20, pixformat=4, heap_internal_free_bytes=150000, heap_psram_free_bytes=4000000)
        r0 = sorted(p["expected_registers"])[0]
        cases = [("khop", dict(base), 0), ("chi_heap_doi", dict(base, heap_internal_free_bytes=1, heap_psram_free_bytes=0), 0),
                 ("quality_12", dict(base, quality=12), 1), ("framesize_VGA", dict(base, framesize=10), 1),
                 ("aec_bat_lai", dict(base, aec=1), 1), ("thanh_ghi_%s_doi" % r0, dict(base, **{r0: base[r0] + 7}), 1),
                 ("thieu_%s" % r0, {k: v for k, v in base.items() if k != r0}, 1)]
        for label, st, want in cases:
            (sess / "status_after_run1.json").write_text(json.dumps(st), encoding="utf-8")
            rc, out = run_bash(pb, {"SESSION_DIR": sess.as_posix(), "K": "1"})
            good = rc == want and (("khop profile" in out) if want == 0 else ("TROI CAU HINH" in out))
            ok = ok and good
            det.append("%s: rc=%d%s" % (label, rc, "" if good else " SAI '%s'" % out[-160:]))
    check("S7.8", ok, "V6-T4: doi chieu sau luot chay nguyen van: khop/heap doi -> dat; quality/framesize/control/thanh ghi doi hoac thieu -> TROI, exit 1; khong gui /control",
          "; ".join(det))
    # S7.9 khoi PowerShell phai parse duoc (PowerShell 5.1, ENVIRONMENT)
    ps = shutil.which("powershell")
    errs = []
    if ps:
        for i, b in enumerate(x for x in blocks if x[1] == "powershell"):
            f = s7 / ("ps_%02d.ps1" % i)
            # cho giu cho nguoi dung tu thay (<IP_ESP32>, <PORT>) thay bang gia tri mau truoc khi parse
            f.write_text(b[2].replace("<IP_ESP32>", "192.168.1.50").replace("<PORT>", "COM4"), encoding="utf-8-sig")
            r = subprocess.run([ps, "-NoProfile", "-Command",
                                "$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$null,[ref]$e); $e | ForEach-Object { $_.Message }" % str(f)],
                               capture_output=True, text=True, timeout=60)
            if r.stdout.strip():
                errs.append("khoi PS #%d (%s): %s" % (i, b[3][:50], r.stdout.strip().splitlines()[0][:110]))
    check("S7.9", ps is not None and not errs, "khoi lenh PowerShell cua quy trinh parse duoc (Windows PowerShell 5.1)",
          "%d khoi loi: %s" % (len(errs), errs) if ps else "khong co powershell")
    # S7.10 baseline: tai build tu commit main co dinh, thu muc rieng, truoc build Q6 (L24 muc 4 Vong 14)
    i_base = proc.find("git archive e92867eecf5eaad308ab1a222069de07d964e6fb")
    i_q6 = proc.find("--output-dir firmware/esp32s3/CameraWebServerTest/build/q6")
    outs = re.findall(r"--output-dir (\S+)", proc)
    check("S7.10", 0 <= i_base < i_q6 and len(set(o.replace("\\", "/") for o in outs)) >= 2 and "cp -f" not in proc,
          "L24 (i)/ke hoach 4.4: baseline tai build tu main e92867e o thu muc rieng, truoc build Q6; khong cp -f",
          "vi tri baseline=%d q6=%d; output-dir: %s" % (i_base, i_q6, sorted(set(outs))))
    # ---- Vong 16 (sau L24/L26 Vong 15): chay NGUYEN VAN cac khoi moi; chi thay cho giu <IP_ESP32> bang may chu cuc bo
    from PIL import Image
    import http.server

    def jpgs(d, n, size):
        d.mkdir(parents=True, exist_ok=True)
        for i in range(1, n + 1):
            Image.new("RGB", size, (i * 9 % 256, 80, 160)).save(d / ("frame_%04d.jpg" % i), "JPEG")

    # S7.11 buoc kiem kich thuoc JPEG 800x600 (V6-T4): anh tong hop + anh that cua probe qua mock
    zb = find_block(blocks, "bash", "Image.open", "800, 600")
    det = []
    ok = bool(zb)
    if zb:
        for label, n, size, want in (("20x800x600", 20, (800, 600), 0), ("20x640x480", 20, (640, 480), 1),
                                     ("19x800x600", 19, (800, 600), 1), ("20x600x800", 20, (600, 800), 1)):
            d2 = s7 / ("size_" + label)
            jpgs(d2 / "probe_q6_t9_run1", n, size)
            rc, out = run_bash(zb, {"SESSION_DIR": d2.as_posix(), "K": "1"})
            good = rc == want and (("LOI" in out) == (want == 1))
            ok = ok and good
            det.append("%s: rc=%d%s" % (label, rc, "" if good else " SAI '%s'" % out[-120:]))
        for label, fs, want in (("probe+mock_framesize6(320x240)", None, 1), ("probe+mock_framesize11(800x600)", 11, 0)):
            d2 = s7 / ("mock_" + str(fs))
            d2.mkdir()
            mp, port = start_mock(REPO / "pc/mock_camera.py")
            try:
                if fs:
                    get(port, "/control?var=framesize&val=%d" % fs)
                r = subprocess.run([PY, str(REPO / "pc/fresh_capture_probe.py"), "--host", "127.0.0.1", "--port", str(port), "--count", "20",
                                    "--interval", "0", "--output", str(d2 / "probe_q6_t9_run1")], capture_output=True, text=True, timeout=120)
            finally:
                mp.kill()
            rc, out = run_bash(zb, {"SESSION_DIR": d2.as_posix(), "K": "1"})
            good = rc == want and (("LOI" in out) == (want == 1))
            ok = ok and good
            det.append("%s: probe rc=%d, kiem kich thuoc rc=%d '%s'" % (label, r.returncode, rc, (out.splitlines() or [""])[-1][:70]))
    check("S7.11", ok, "V6-T4: buoc kiem 800x600 chay nguyen van: 20 anh SVGA -> dat; 640x480 / thieu anh / xoay 600x800 -> LOI exit 1; anh that cua probe qua mock dung ten frame_*.jpg",
          "; ".join(det))

    # S7.12 buoc 5.1 luu phan hoi busy: may chu cuc bo tra 503 ERROR CAMERA_BUSY_STREAM cho moi duong dan
    class Busy(http.server.BaseHTTPRequestHandler):
        paths = []

        def do_GET(self):
            Busy.paths.append(self.path)
            body = b"ERROR CAMERA_BUSY_STREAM"
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    bb2 = find_block(blocks, "bash", "/capture", "/bmp", "busy_responses")
    det = []
    ok = bool(bb2)
    if bb2:
        srv = http.server.HTTPServer(("127.0.0.1", 0), Busy)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            d2 = s7 / "busy"
            d2.mkdir()
            code = bb2.replace("<IP_ESP32>", "127.0.0.1:%d" % srv.server_address[1])
            outs = {}
            for k in ("1", "2"):
                rc, out = run_bash(code, {"SESSION_DIR": d2.as_posix(), "K": k})
                f = d2 / ("busy_responses_run%s.txt" % k)
                txt = f.read_text(encoding="utf-8") if f.exists() else ""
                lines = [ln for ln in txt.splitlines() if ln.strip()]
                good = (rc == 0 and len(lines) == 3 and all("HTTP 503, Body: ERROR CAMERA_BUSY_STREAM" in ln for ln in lines)
                        and all(ln in out for ln in lines))
                ok = ok and good
                outs[k] = txt
                det.append("K=%s: rc=%d tep %d dong 503+body, in = tep: %s" % (k, rc, len(lines), all(ln in out for ln in lines)))
            det.append("duong dan nhan: %s" % sorted(set(Busy.paths)))
        finally:
            srv.shutdown()
    check("S7.12", ok, "ke hoach 4.3/L26.3: lenh busy 5.1 chay nguyen van in VA luu status + body vao busy_responses_run${K}.txt, moi lan K tep rieng",
          "; ".join(det))

    # S7.13 snapshot /status Git Bash + PowerShell 5.1 chay nguyen van voi mock: luu tho, co thoi diem PC, doc lai duoc bang json.load(open())
    sb = find_block(blocks, "bash", "curl", "status_before_run", "_time.txt")
    psb = find_block(blocks, "powershell", "Invoke-WebRequest", "status_before_run")
    det = []
    ok = bool(sb) and bool(psb)
    if ok:
        mp, port = start_mock(REPO / "pc/mock_camera.py")
        try:
            raw = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            raw.request("GET", "/status")
            ref = json.loads(raw.getresponse().read())
            for label, run in (("bash", lambda d: run_bash(sb.replace("<IP_ESP32>", "127.0.0.1:%d" % port), {"SESSION_DIR": d.as_posix(), "K": "1"})),
                               ("powershell", None)):
                d2 = s7 / ("snap_" + label)
                d2.mkdir()
                if label == "bash":
                    rc, out = run(d2)
                else:
                    ps = shutil.which("powershell")
                    pre = "$SESSION_DIR = '%s'; $K = 1; " % str(d2)
                    r = subprocess.run([ps, "-NoProfile", "-Command", pre + psb.replace("<IP_ESP32>", "127.0.0.1:%d" % port)],
                                       capture_output=True, text=True, timeout=120)
                    rc, out = r.returncode, (r.stdout + r.stderr).strip()
                f, t = d2 / "status_before_run1.json", d2 / "status_before_run1_time.txt"
                b = f.read_bytes() if f.exists() else b""
                try:
                    with open(f) as fh:
                        loaded = json.load(fh)
                    same_keys = sorted(loaded) == sorted(ref)
                except Exception as e:  # noqa: BLE001
                    loaded, same_keys = None, "json.load loi: %s" % e
                ts = t.read_text(encoding="utf-8-sig").strip() if t.exists() else ""
                ts_ok = bool(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", ts))
                good = rc == 0 and b[:3] != b"\xef\xbb\xbf" and same_keys is True and ts_ok
                ok = ok and good
                det.append("%s: rc=%d bom=%s json.load(open()) cung khoa voi GET tho=%s thoi_diem='%s'%s" % (
                    label, rc, b[:3] == b"\xef\xbb\xbf", same_keys, ts, "" if good else " | " + out[-160:]))
        finally:
            mp.kill()
    check("S7.13", ok, "L26.2/L26.5: snapshot /status (Git Bash curl, PowerShell 5.1 Invoke-WebRequest -OutFile) chay nguyen van voi mock: JSON tho khong BOM, doc duoc o buoc doi chieu, co thoi diem PC UTC",
          "; ".join(det))

    # S7.14 manifest buoc 2.3 chay nguyen van (Git Bash): binary gia tai dung duong dan, git rev-parse doc repo qua GIT_DIR
    det = []
    ok = bool(mb)
    if mb:
        d2 = s7 / "manifest"
        bins = {}
        # Vong 23: buoc 2.3 nay doi du bo anh nap (L31) -> du lieu thu ca duong phai co bootloader/partitions (truoc chi co app)
        for sub, payload in (("q6", b"Q6-binary"), ("baseline", b"BASELINE-binary")):
            p = d2 / ("firmware/esp32s3/CameraWebServerTest/build/%s/CameraWebServerTest.ino.bin" % sub)
            p.parent.mkdir(parents=True)
            p.write_bytes(payload)
            bins[sub] = hashlib.sha256(payload).hexdigest()
            for f in ("bootloader", "partitions"):
                (p.parent / ("CameraWebServerTest.ino.%s.bin" % f)).write_bytes(("%s-%s" % (sub, f)).encode())
        (d2 / "phien").mkdir()
        rc, out = run_bash(mb, {"SESSION_DIR": "phien", "GIT_DIR": str(REPO / ".git")}, cwd=d2)
        try:
            m = json.loads((d2 / "phien/manifest.json").read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            m = {"_loi": str(e)}
        want = {"binary_sha256": bins["q6"], "baseline_binary_sha256": bins["baseline"], "esp32_core_version": "3.3.11",
                "baseline_source_commit": BASE,
                "git_commit": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "fqbn": "esp32:esp32:esp32s3:PSRAM=opi"}
        bad = {k: m.get(k) for k, v in want.items() if m.get(k) != v}
        arts = {a.get("name"): a for a in m.get("artifacts", [])} if isinstance(m.get("artifacts"), list) else {}
        exp_art = {"bootloader": hashlib.sha256(b"q6-bootloader").hexdigest(), "partitions": hashlib.sha256(b"q6-partitions").hexdigest(),
                   "app": bins["q6"]}
        art_bad = {k: (arts.get(k) or {}).get("sha256") for k, v in exp_art.items() if (arts.get(k) or {}).get("sha256") != v}
        if "artifacts" in m and (not (arts.get("boot_app0") or {}).get("sha256")):
            art_bad["boot_app0"] = "thieu"
        ok = rc == 0 and not bad and "chưa chứng minh" in m.get("baseline_note", "") and ("artifacts" not in m or not art_bad)
        det.append("rc=%d khoa=%s sai=%s; artifacts lech=%s" % (rc, sorted(m), bad, art_bad))
    check("S7.14", ok, "L26.4: manifest buoc 2.3 chay nguyen van: JSON hop le, SHA day du binary Q6 va baseline dung tep, core 3.3.11, nguon baseline main, ghi chu chua chung minh trung bo",
          "; ".join(det))


# ============================================================================ T: nhan timeout hai lop (01_PLAN Vong 7 R12, V7-A2/A3)
def group_t(td):
    print("---- T: nhan loi timeout cua probe tai B (V7-A2 socket 5 s truoc han, V7-A3 dua bien han tong, loi mang)")
    probe = load_b_module(td, "fresh_capture_probe")
    full = resp(hdrs(), body=b"x" * 200)
    sp = full.index(b"\r\n\r\n") + 4

    def label(r):
        return (r.get("error") or "OK").split(":")[0]

    # T1 (V7-A2): header + 50 byte body roi im lang 7 s; socket 5 s, han 10 s -> TIMEOUT_SOCKET sau ~5 s, giu partial
    def stall7(conn):
        conn.sendall(full[:sp + 50])
        time.sleep(7)
    srv = RawServer([stall7])
    c = probe.FreshCaptureClient("127.0.0.1", srv.port, timeout=5.0)
    t0 = time.monotonic()
    r1 = c.capture_fresh(deadline=10.0)
    dt = time.monotonic() - t0
    time.sleep(0.3)
    left = [t for t in threading.enumerate() if isinstance(t, threading.Timer) and t.is_alive()]
    srv.close()
    check("T.T1", label(r1) == "TIMEOUT_SOCKET" and 4.5 <= dt <= 6.5 and len(r1.get("body") or b"") == 50 and not left,
          "V7-A2: im lang 5 s giua body, con ~5 s truoc han 10 s -> TIMEOUT_SOCKET (khong TOTAL_DEADLINE), giu 50 byte da nhan, khong con Timer",
          "%.2f s; nhan=%s; body giu=%d byte; Timer con song=%d; error=%r" % (dt, label(r1), len(r1.get("body") or b""), len(left), r1.get("error")))
    # T2: may chu dong ket noi giua body (RST/close) truoc han -> nhan loi mang, khong nhan timeout
    def cut(conn):
        conn.sendall(full[:sp + 30])
        conn.close()
    srv = RawServer([cut])
    r2 = probe.FreshCaptureClient("127.0.0.1", srv.port, timeout=5.0).capture_fresh(deadline=10.0)
    srv.close()
    check("T.T2", label(r2) not in ("TIMEOUT_SOCKET", "TIMEOUT_TOTAL_DEADLINE") and r2.get("error"),
          "V7-A3: loi mang truoc han (dong/reset ket noi giua body) giu nhan loi mang/JPEG, khong gan nhan timeout",
          "nhan=%s; error=%r" % (label(r2), (r2.get("error") or "")[:100]))

    # T3 (V7-A3): nho giot (moi khoang < 5 s socket) keo toi han tong -> PHAI la TOTAL_DEADLINE, lap nhieu lan quanh bien
    head = resp(hdrs(), body=b"x" * 5000)
    hsplit = head.index(b"\r\n\r\n") + 4
    lst = socket.socket()
    lst.bind(("127.0.0.1", 0))
    lst.listen(64)
    port = lst.getsockname()[1]
    gap = [0.1]
    stop = [False]

    def handle(conn, g):
        try:
            conn.settimeout(10)
            conn.recv(4096)
            conn.sendall(head[:hsplit])
            i = 0
            while not stop[0]:
                time.sleep(g)
                conn.sendall(head[hsplit + i:hsplit + i + 1])
                i += 1
        except Exception:  # noqa: BLE001
            pass
        finally:
            conn.close()

    def acc():
        while not stop[0]:
            try:
                conn, _ = lst.accept()
            except OSError:
                return
            threading.Thread(target=handle, args=(conn, gap[0]), daemon=True).start()
    threading.Thread(target=acc, daemon=True).start()
    counts = {}
    try:
        for g, dl, n in ((0.1, 0.3, 150), (0.13, 0.35, 150)):
            gap[0] = g
            for _ in range(n):
                r = probe.FreshCaptureClient("127.0.0.1", port, timeout=5.0).capture_fresh(deadline=dl)
                k = "%s@%.2f" % (label(r), dl)
                counts[k] = counts.get(k, 0) + 1
    finally:
        stop[0] = True
        lst.close()
    sock_lbl = sum(v for k, v in counts.items() if k.startswith("TIMEOUT_SOCKET"))
    check("T.T3", sock_lbl == 0 and sum(counts.values()) == 300,
          "V7-A3: 300 luot nho giot (khong lan nao im lang toi 5 s) cham han tong 0,30/0,35 s -> moi luot TIMEOUT_TOTAL_DEADLINE (uu tien han tong o bien)",
          "dem nhan: %s; time.monotonic: %s" % (counts, time.get_clock_info("monotonic").implementation))
    # T4 (V7-A3, CLI han mac dinh 10 s): byte moi 4,5 s -> dung trong han va in nhan TOTAL_DEADLINE
    def gap45(conn):
        conn.sendall(head[:hsplit])
        for i in range(6):
            time.sleep(4.5)
            conn.sendall(head[hsplit + i:hsplit + i + 1])
    srv = RawServer([gap45])
    r, dt = run_probe_cli(td, ["--host", "127.0.0.1", "--port", str(srv.port), "--count", "1"])
    srv.close()
    line = [ln for ln in r.stdout.splitlines() if "FAIL:" in ln][:1]
    check("T.T4", r.returncode != 0 and dt <= 12.0 and bool(line) and "TIMEOUT_TOTAL_DEADLINE" in line[0],
          "V7-A3 (CLI 10 s): body 1 byte / 4,5 s -> dung trong <= 10 s + 2 s, nhan TIMEOUT_TOTAL_DEADLINE",
          "rc=%d %.1f s; %s" % (r.returncode, dt, line[0][:150] if line else "khong co dong FAIL"))


# ============================================================================ U: R15 - phan loai loi o bien han tong bang dong ho gia (01_PLAN Vong 9 V9-T2, V9-T3)
def group_u(td):
    print("---- U: R15/R16 nhan loi gan han tong, dong ho gia (lien tuc va luong tu), watchdog khong tu chay (V9-T2, V9-T3)")
    probe = load_b_module(td, "fresh_capture_probe")
    real_time, real_threading, real_conn = probe.time, probe.threading, probe.TrackedHTTPConnection

    def run(t_req, t_err, exc, watchdog=False, partial=b"", t0=0.0, q=0.0, gain=1.0, dl=10.0, info=None):
        # t_req: thoi gian (tuong doi t0) luc gui request (quyet dinh socket timeout dat cho lan doc); t_err: luc loi.
        # Dong ho that clk tuyet doi bat dau t0; perf_counter = clk (lien tuc); monotonic = clk luong tu q (q=0: lien tuc),
        # lech pha theo t0 (R16 Reviewer Vong 7). sleep tien clk them gain*s (gain<1: sleep tra som).
        clk = [t0]
        timers = []
        sleeps = []
        mono = (lambda: math.floor(clk[0] / q) * q) if q else (lambda: clk[0])

        def sleep(s):
            sleeps.append(s)
            clk[0] += max(0.0, s) * gain
        fake_time = types.SimpleNamespace(monotonic=mono, perf_counter=lambda: clk[0], sleep=sleep)
        m0 = mono()

        class Tm:
            def __init__(self, dl, fn):
                self.fn = fn
                timers.append(self)
                self.daemon = False

            def start(self):
                pass

            def cancel(self):
                pass

        class Resp:
            status, reason, version = 200, "OK", 11

            def getheaders(self):
                return [("Content-Type", "image/jpeg")]

            def read1(self, n):
                if self.fresh:  # luot doc dau tra partial body, luot sau loi
                    self.fresh = False
                    return partial
                clk[0] = t0 + t_err
                if watchdog:
                    timers[0].fn()
                raise exc

            read = read1
            fresh = True

        class Conn:
            sock = active_sock = None

            def __init__(self, *a, **k):
                pass

            def request(self, *a, **k):
                clk[0] = t0 + t_req

            def getresponse(self):
                if partial:
                    return Resp()
                clk[0] = t0 + t_err
                if watchdog:
                    timers[0].fn()
                raise exc

            def close(self):
                pass

        probe.time = fake_time
        probe.threading = types.SimpleNamespace(Timer=Tm)
        probe.TrackedHTTPConnection = Conn
        try:
            c = probe.FreshCaptureClient("127.0.0.1", 9, timeout=5.0)
            r = c.capture_fresh(deadline=dl)
        finally:
            probe.time, probe.threading, probe.TrackedHTTPConnection = real_time, real_threading, real_conn
        if info is not None:  # trang thai dong ho luc phan loai (dong ho gia khong tien sau do)
            info.update(perf_el=clk[0] - t0, mono_el=mono() - m0, sleeps=list(sleeps))
        return (r.get("error") or "OK").split(":")[0], r, clk[0] - t0

    NET, SOCK, TOT = "Socket/Network error", "TIMEOUT_SOCKET", "TIMEOUT_TOTAL_DEADLINE"
    # V9-T2: reset mang o 9,970 / 9,980 s, hai dong ho chinh xac, watchdog chua chay -> giu nhan mang
    for t in (9.970, 9.980):
        lb, r, _ = run(0.0, t, ConnectionResetError(10054, "reset"))
        check("U.T2@%.3f" % t, lb == NET, "V9-T2: ConnectionResetError tai %.3f s (truoc han, watchdog chua chay) -> Socket/Network error, khong TOTAL" % t,
              "nhan=%s; error=%r" % (lb, (r.get("error") or "")[:90]))
    # V9-T2: khong mat partial body khi loi mang sat bien
    lb, r, _ = run(0.0, 9.980, ConnectionResetError(10054, "reset"), partial=b"\xff\xd8abc")
    check("U.T2p", lb == NET and r.get("body") == b"\xff\xd8abc" and r.get("jpeg_valid") is False,
          "V9-T2: loi mang tai 9,980 s sau khi da nhan 5 byte body -> nhan mang, giu partial, khong hop le",
          "nhan=%s; body=%r; jpeg_valid=%r" % (lb, r.get("body"), r.get("jpeg_valid")))
    # V9-T3: bien loi mang 9,975 / 9,999 truoc han -> mang; dung 10,000 va sau han -> TOTAL
    for t, want in ((9.975, NET), (9.999, NET), (10.000, TOT), (10.050, TOT)):
        lb, r, _ = run(0.0, t, ConnectionResetError(10054, "reset"))
        check("U.T3n@%.3f" % t, lb == want, "V9-T3: loi mang tai %.3f s -> %s" % (t, want),
              "nhan=%s; error=%r" % (lb, (r.get("error") or "")[:90]))
    # V9-T3: monotonic luong tu 15,625 ms that su tre (elapsed 0,296875 s < han 0,300 s) nhung perf_counter da qua han
    # -> clock xac nhan TOTAL. (Vong 27: ban Vong 25 cong cung offset vao moc dau va moc sau nen khong tao do tre - Reviewer Vong 7 R16.)
    inf = {}
    lb, r, _ = run(0.0, 0.3005, ConnectionResetError(10054, "reset"), q=0.015625, dl=0.300, info=inf)
    check("U.T3c", lb == TOT and inf["mono_el"] < 0.300 <= inf["perf_el"],
          "V9-T3: perf_counter 0,3005 s da qua han 0,300 s, monotonic luong tu con 0,296875 s -> TOTAL (dong ho xac nhan)",
          "nhan=%s; mono_el=%.6f; perf_el=%.6f" % (lb, inf["mono_el"], inf["perf_el"]))
    # V9-T3: watchdog da phat (dong ho may chua toi han) -> watchdog xac nhan TOTAL
    lb, r, _ = run(0.0, 9.980, ConnectionResetError(10054, "reset"), watchdog=True)
    check("U.T3w", lb == TOT, "V9-T3: watchdog da phat, loi mang tai 9,980 s -> TOTAL (watchdog xac nhan)", "nhan=%s" % lb)
    # V9-T3 (socket timeout kiem rieng):
    #  a) socket da bi thu nho theo han con lai (request 9,0 s -> timeout 1,0 s) va het som 1 tick -> dua bien that cua han tong -> TOTAL
    lb, r, end = run(9.0, 9.985, socket.timeout("timed out"))
    check("U.T3s_shrunk", lb == TOT and end <= 10.0 + 1e-9,
          "V9-T3: socket timeout da thu nho theo han (1,0 s) het tai 9,985 s -> TOTAL; khong keo dai qua han 10 s",
          "nhan=%s; dong ho cuoi=%.4f s" % (lb, end))
    #  b) inactivity day du 5 s (request 0 s) -> TIMEOUT_SOCKET
    lb, r, _ = run(0.0, 5.0, socket.timeout("timed out"))
    check("U.T3s_5s", lb == SOCK, "V9-T4: socket inactivity 5 s tai 5,0 s -> TIMEOUT_SOCKET", "nhan=%s" % lb)
    #  c) inactivity day du 5 s bat dau 4,97 s (socket KHONG thu nho, timeout 5,0 s) het tai 9,970 s:
    #     day la timeout socket that truoc han, watchdog chua chay, hai dong ho chua toi han
    #     -> thiet ke S3 4.x: TIMEOUT_SOCKET; ke hoach V9 muc 2 "socket timeout giu TIMEOUT_SOCKET", V9-T3 "truoc han khong TOTAL chi vi gan bien"
    for tr, te in ((4.970, 9.970), (4.960, 9.960)):
        lb, r, end = run(tr, te, socket.timeout("timed out"))
        check("U.T3s_full@%.3f" % te, lb == SOCK,
              "V9-T3: inactivity socket day du 5,0 s (khong thu nho) het tai %.3f s, truoc han, watchdog chua chay -> TIMEOUT_SOCKET, khong TOTAL chi vi gan bien" % te,
              "nhan=%s; dong ho sau phan loai=%.4f s; error=%r" % (lb, end, (r.get("error") or "")[:90]))

    # U.Q (R16 Reviewer Vong 7): monotonic luong tu 15,625 ms lech pha + perf_counter lien tuc, watchdog khong phat.
    # Bat bien hop dong (01_PLAN Vong 9 muc 2): nhan TOTAL <=> watchdog hoac it nhat mot dong ho (doc luc phan loai) da dat han.
    Qt = 0.015625

    def sweep(kind, dl, gain, errs):
        bad, cnt, maxs, late = [], {}, 0, 0.0
        for k in range(16):
            t0 = 0.010 + k * Qt / 16
            for te in errs:
                inf = {}
                if kind == "net":
                    lb, r, _ = run(0.0, te, ConnectionResetError(10054, "reset"), t0=t0, q=Qt, gain=gain, dl=dl, info=inf)
                elif kind == "shrunk":
                    lb, r, _ = run(dl - 0.100, te, socket.timeout("timed out"), t0=t0, q=Qt, gain=gain, dl=dl, info=inf)
                else:  # full: lan doc cuoi dung 5,0 s truoc loi, socket khong bi thu nho
                    lb, r, _ = run(te - 5.0, te, socket.timeout("timed out"), t0=t0, q=Qt, gain=gain, dl=dl, info=inf)
                conf = inf["mono_el"] >= dl or inf["perf_el"] >= dl
                cnt[lb] = cnt.get(lb, 0) + 1
                maxs = max(maxs, len(inf["sleeps"]))
                late = max(late, inf["perf_el"] - dl)
                want_other = NET if kind == "net" else SOCK
                if (lb == TOT) != conf or lb not in (TOT, want_other):
                    bad.append("t0=%.6f te=%.4f nhan=%s mono_el=%.6f perf_el=%.6f" % (t0, te, lb, inf["mono_el"], inf["perf_el"]))
                elif kind == "shrunk" and gain == 1.0 and te >= dl - 0.05 and lb != TOT:
                    bad.append("dua bien socket thu nho khong con TOTAL: t0=%.6f te=%.4f nhan=%s" % (t0, te, lb))
                elif kind in ("net", "full") and inf["sleeps"]:
                    bad.append("ngu bu cho loi khong phai socket thu nho: t0=%.6f te=%.4f" % (t0, te))
        return bad, cnt, maxs, late

    last = [round(0.240 + i * 0.001, 4) for i in range(60)]   # 60 ms cuoi truoc han 0,300 s
    for cid, kind, dl, gain, errs, title in (
            ("U.Q1", "shrunk", 0.300, 1.0, last, "socket thu nho theo han, sleep du: TOTAL chi khi dong ho xac nhan; trong 50 ms cuoi van TOTAL (giu slow-drip)"),
            ("U.Q2", "shrunk", 0.300, 0.5, last, "socket thu nho, sleep tra som (moi lan chi tien 1/2): TOTAL chi khi dong ho xac nhan; vong cho dung huu han"),
            ("U.Q3", "shrunk", 0.300, 0.0, last, "socket thu nho, sleep khong tien: khong TOTAL khi dong ho chua toi han; vong cho dung huu han"),
            ("U.Q4", "net", 0.300, 1.0, last, "loi mang trong 60 ms cuoi: TOTAL chi khi dong ho xac nhan, con lai Socket/Network error, khong ngu bu"),
            ("U.Q5", "full", 10.0, 1.0, [round(9.940 + i * 0.001, 4) for i in range(60)],
             "inactivity du 5 s het trong 60 ms cuoi truoc han 10 s: TIMEOUT_SOCKET tru khi dong ho xac nhan, khong ngu bu")):
        bad, cnt, maxs, late = sweep(kind, dl, gain, errs)
        check(cid, not bad and maxs <= 12 and late <= 1e-9,
              "R16/V9-T3: %s (16 pha x %d moc)" % (title, len(errs)),
              "dem nhan: %s; so lan sleep toi da/luot: %d; perf vuot han toi da %.2e s; vi pham %d: %s" % (cnt, maxs, late, len(bad), bad[:3]))


# ============================================================================ S8: quy trinh Vong 7/8 (R13, R09, R10)
def group_s8(proc, td):
    import json
    import hashlib
    print("---- S8: quy trinh bo Vong 7/8 - R13 artifact, R09 log nap, R10 RST (V7-A4, V8-B3)")
    blocks = proc_blocks(proc)
    bash = git_bash()
    s8 = Path(td) / "s8"
    s8.mkdir()
    sk = "firmware/esp32s3/CameraWebServerTest/build/"
    # S8.1 buoc 2.3 chay NGUYEN VAN tren cay tam CHI co cac tep ma buoc 2.2 cua quy trinh tao ra (khong co thu muc build cu)
    b23 = find_block(blocks, "bash", "ARCHIVE_DIR", "manifest.json")
    det = []
    ok = bool(b23) and bool(bash)
    if ok:
        root = s8 / "cay"
        files = {}
        for d in ("q6", "baseline"):
            for f in ("CameraWebServerTest.ino.bin", "CameraWebServerTest.ino.bootloader.bin", "CameraWebServerTest.ino.partitions.bin",
                      "CameraWebServerTest.ino.merged.bin"):
                p = root / (sk + d + "/" + f)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(("%s/%s" % (d, f)).encode())
        (root / "phien").mkdir()
        r = subprocess.run([bash, "-c", b23], capture_output=True, text=True, cwd=str(root), timeout=60, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SESSION_DIR="phien", GIT_DIR=str(REPO / ".git")))
        arch = sorted((root / "build/c5a-artifacts").glob("*")) if (root / "build/c5a-artifacts").exists() else []
        have = sorted(x.name for x in arch[0].iterdir()) if arch else []
        try:
            m = json.loads((root / "phien/manifest.json").read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            m = {"_loi": str(e)}
        listed = [a.get("file") for a in m.get("artifacts", [])]
        missing = [f for f in listed if f not in have]
        no_hash = [a.get("name") for a in m.get("artifacts", []) if not (a.get("sha256") and a.get("size"))]
        err = [ln for ln in (r.stdout + r.stderr).splitlines() if "cannot stat" in ln or "No such file" in ln]
        ok = not missing and not no_hash and not err
        det.append("rc=%d; bo luu co %s; manifest liet ke %s; liet ke ma thieu trong bo luu: %s; thanh phan khong co sha256/size: %s; loi: %s" % (
            r.returncode, have, listed, missing, no_hash, err[:1]))
    check("S8.1", ok, "V7-A4/R13: buoc 2.3 chay nguyen van tu ket qua buoc 2.2: bo luu du 4 anh nap, manifest moi thanh phan co SHA-256 + kich thuoc + offset; thieu tep thi dung (khong bao niem phong thanh cong)",
          "; ".join(det))
    # S8.2 khong dung mkdir -p/ghi de cho thu muc export/bo luu; dich da ton tai phai bi tu choi
    p_exp = sorted(set(t for ln in re.findall(r"(?m)^\s*mkdir -p (.*)$", proc) for t in ln.split()
                       if re.search(r"CameraWebServerTest/build/(q6|baseline)|ARCHIVE_DIR", t)))
    refuse = re.search(r"\[ -e \"?\$ARCHIVE_DIR|\[ -d \"?\$ARCHIVE_DIR|test -e|Test-Path", proc)
    check("S8.2", not p_exp and bool(refuse),
          "V7-A4/ke hoach Vong 7 muc 4.4: compile/export va bo luu dung thu muc moi chua ton tai; dich ton tai -> tu choi (khong mkdir -p / -Force roi ghi de)",
          "mkdir -p dich export/bo luu: %s; co buoc kiem ton tai truoc khi ghi: %s" % (p_exp, bool(refuse)))
    # S8.3 nap tu BO LUU (khong tu cache build/q6), kiem hash truoc nap, giu exit code cua cong cu (khong lay exit cua tee)
    up = find_block(blocks, "bash", "upload", "--input-dir") or ""
    from_archive = "ARCHIVE_DIR" in up or "c5a-artifacts" in up
    keep_rc = bool(re.search(r"PIPESTATUS|pipefail|set -o pipefail|\$\?.*>.*exit", up))
    hash_pre = bool(re.search(r"sha256sum", up))
    check("S8.3", from_archive and keep_rc and hash_pre,
          "V7-A4/ke hoach Vong 7 muc 4.5: lenh nap dung bo artifact da niem phong, kiem hash truoc nap, luu output va exit code that cua cong cu",
          "nap tu bo luu: %s; giu exit code (PIPESTATUS/pipefail): %s; kiem hash truoc nap: %s; lenh: %s" % (from_archive, keep_rc, hash_pre, up.strip()[:160]))
    # S8.4 R10: sau MOI RST - Serial boot moi, /status 200, AP LAI PROFILE roi moi chup anh hoi phuc 800x600
    i53 = proc.find("### 5.3")
    sec = proc[i53:] if i53 >= 0 else ""
    reapply = re.search(r"camera_profile\.py[^\n]*--verify", sec)
    serial = re.search(r"(Serial|boot_serial|serial_)[^\n]{0,80}(rst|RST|\$\{K\})", sec)
    expects_svga = "800×600" in sec or "800x600" in sec
    check("S8.4", bool(reapply) and bool(serial),
          "R10/ke hoach Vong 7 muc 4.8, Vong 8 muc 4.7: sau moi RST luu Serial boot moi va ap lai profile truoc anh hoi phuc 800x600",
          "ap lai profile trong 5.3: %s; luu Serial sau RST: %s; ky vong anh hoi phuc 800x600: %s (bo sau RST ve framesize mac dinh 6 = 320x240, xem log [6])" % (
              bool(reapply), bool(serial), expects_svga))
    # ---- Vong 19: ca am cua buoc 2.3/2.4 (V7-A4: thieu/lech artifact phai chan nap) va lenh terminal thu hai (R10)
    def mk_tree(root, drop=None, baseline=True):
        drops = (drop,) if isinstance(drop, str) else tuple(drop or ())
        for d in (("q6", "baseline") if baseline else ("q6",)):
            for f in ("CameraWebServerTest.ino.bin", "CameraWebServerTest.ino.bootloader.bin", "CameraWebServerTest.ino.partitions.bin"):
                if d == "q6" and f in drops:
                    continue
                p = root / (sk + d + "/" + f)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(("%s/%s" % (d, f)).encode())
        (root / "phien").mkdir(exist_ok=True)

    def run23(root):
        return subprocess.run([bash, "-c", b23], capture_output=True, text=True, cwd=str(root), timeout=60, encoding="utf-8", errors="replace",
                              env=dict(os.environ, SESSION_DIR="phien", GIT_DIR=str(REPO / ".git")))
    # S8.5: buoc 2.2 thieu partitions.bin -> buoc 2.3 phai dung, khong bao niem phong, khong de manifest SHA rong
    det, ok = [], bool(b23) and bool(bash)
    for drop in ((("CameraWebServerTest.ino.partitions.bin",), ("CameraWebServerTest.ino.bootloader.bin",),
                  ("CameraWebServerTest.ino.bootloader.bin", "CameraWebServerTest.ino.partitions.bin"),
                  ("CameraWebServerTest.ino.bin",), ("CameraWebServerTest.ino.bootloader.bin", "CameraWebServerTest.ino.partitions.bin", "-baseline")) if ok else ()):
        nob = "-baseline" in drop
        drop = tuple(x for x in drop if x != "-baseline")
        root = s8 / ("thieu_" + "_".join(x.split(".")[-2] for x in drop) + ("_khong_baseline" if nob else ""))
        mk_tree(root, drop=drop, baseline=not nob)
        r = run23(root)
        out = r.stdout + r.stderr
        try:
            m = json.loads((root / "phien/manifest.json").read_text(encoding="utf-8"))
            empty = [a["name"] for a in m.get("artifacts", []) if not a.get("sha256") or not a.get("size")]
        except Exception:  # noqa: BLE001
            m, empty = None, "khong co manifest"
        good = r.returncode != 0 and "niem phong tai" not in out
        ok = ok and good
        det.append("thieu %s%s: rc=%d; in 'niem phong': %s; manifest SHA rong/size 0: %s" % ("+".join(drop), " (chua build baseline)" if nob else "", r.returncode, "niem phong tai" in out, empty))
    check("S8.5", ok, "V7-A4: buoc 2.2 thieu mot anh nap -> buoc 2.3 chay nguyen van phai DUNG (rc != 0), khong bao niem phong, khong ghi manifest SHA rong",
          "; ".join(det))
    # S8.6: buoc 2.4 chay nguyen van voi arduino-cli GIA (chi ghi tham so, khong cham COM): bo luu dung -> goi nap; anh nap bi doi/thieu -> KHONG duoc goi nap
    up = find_block(blocks, "bash", "upload", "--input-dir") or ""
    det, ok = [], bool(up) and bool(b23) and bool(bash)
    if ok:
        fake = s8 / "fake_cli.sh"
        fake.write_text('#!/bin/bash\necho "$@" >> "$FAKE_LOG"\nexit ${FAKE_RC:-0}\n', encoding="utf-8", newline="\n")
        code_up = up.replace("<PORT>", "COM_GIA")
        for label, tamper, rc_fake, want_called, want_rc0 in (("bo_luu_dung", None, 0, True, True), ("cli_loi_rc2", None, 2, True, False),
                                                              ("app_bi_doi", "app", 0, False, False), ("thieu_boot_app0", "boot_app0", 0, False, False),
                                                              ("app_bi_doi_va_mat_SHA256SUMS", "app+sums", 0, False, False)):
            root = s8 / ("nap_" + label)
            mk_tree(root)
            r = run23(root)
            arch = sorted((root / "build/c5a-artifacts").glob("*"))
            if not arch:
                det.append("%s: buoc 2.3 khong tao bo luu (rc=%d)" % (label, r.returncode))
                ok = False
                continue
            a = arch[0]
            if tamper in ("app", "app+sums"):
                (a / "CameraWebServerTest.ino.bin").write_bytes(b"BI DOI SAU KHI NIEM PHONG")
            if tamper == "app+sums" and (a / "SHA256SUMS").exists():
                (a / "SHA256SUMS").unlink()
            elif tamper == "boot_app0" and (a / "boot_app0.bin").exists():
                (a / "boot_app0.bin").unlink()
            flog = s8 / ("fake_%s.log" % label)
            r2 = subprocess.run([bash, "-c", 'ARDUINO_CLI="%s"; ARCHIVE_DIR="%s"; %s' % (fake.as_posix(), a.relative_to(root).as_posix(), code_up)],
                                capture_output=True, text=True, cwd=str(root), timeout=60, encoding="utf-8", errors="replace",
                                env=dict(os.environ, SESSION_DIR="phien", FAKE_LOG=str(flog), FAKE_RC=str(rc_fake)))
            called = flog.exists() and flog.read_text(encoding="utf-8").strip() != ""
            args = flog.read_text(encoding="utf-8").strip() if called else ""
            good = called == want_called and ((r2.returncode == 0) == want_rc0) and (not called or ("--input-dir " + a.relative_to(root).as_posix()) in args)
            if label == "cli_loi_rc2":
                good = good and r2.returncode == 2
            ok = ok and good
            det.append("%s: goi nap=%s rc=%d%s" % (label, called, r2.returncode, "" if good else " (SAI, mong goi=%s rc0=%s)" % (want_called, want_rc0)))
    check("S8.6", ok, "V7-A4/R09: buoc 2.4 chay nguyen van (cli gia): bo luu dung -> nap tu bo luu, exit code cong cu giu nguyen; anh nap bi doi hash hoac thieu -> chan, khong goi nap",
          "; ".join(det))
    # S8.7: lenh ghi gio RST o 'Terminal thu hai' - terminal moi khong co SESSION_DIR/K -> phai huong dan dat bien truoc
    i_t2 = proc.find("Terminal thứ hai")
    seg = proc[i_t2:i_t2 + 900] if i_t2 >= 0 else ""
    sets_vars = bool(re.search(r"SESSION_DIR=|\$SESSION_DIR\s*=", seg)) and bool(re.search(r"(?m)^\s*K=|\$K\s*=", seg))
    rc_, out_ = (None, "")
    if i_t2 >= 0 and bash:
        cmd = find_block(blocks, "bash", "rst${K}_action_time.txt") or ""
        d0 = s8 / "terminal2"
        d0.mkdir()
        rr = subprocess.run([bash, "-c", cmd], capture_output=True, text=True, cwd=str(d0), timeout=30, encoding="utf-8", errors="replace",
                            env={k: v for k, v in os.environ.items() if k not in ("SESSION_DIR", "K")})
        rc_, out_ = rr.returncode, (rr.stdout + rr.stderr).strip()[:120]
    # Ngu nghia: terminal 1 dung SESSION_DIR=<phien>, K=2; terminal 2 moi (khong bien) chay NGUYEN VAN khoi huong dan
    # -> tep gio RST phai nam trong <phien>/rst2_action_time.txt (khong o thu muc hien tai, khong mac dinh K=1)
    # (Vong 22) mo phong dung cach dung that: hai terminal cung dung o goc repo (ten thu muc khong mang so lan),
    # terminal 1 chay NGUYEN VAN khoi buoc 5.3.1 voi SESSION_DIR=docs/logs/c5a_q6_rst_<ngau nhien>, K=1 roi K=3;
    # terminal 2 moi (khong bien) chay NGUYEN VAN khoi huong dan -> tep phai vao <phien>/rst<K>_action_time.txt.
    # Ca am: terminal 1 chua chay 5.3.1 (khong co thong tin phien) -> terminal 2 phai TU CHOI, khong doan thu muc/K.
    import random
    landed, want = [], []
    b531 = find_block(blocks, "bash", "status_before_rst", "date -u") or ""
    neg = []
    if i_t2 >= 0 and bash:
        tag = "%08d_%06d" % (random.randint(20260000, 20269999), random.randint(0, 999999))
        sess_rel = "docs/logs/c5a_q6_rst_%s" % tag
        for kk in (1, 3):
            d1 = s8 / ("repo_mo_phong_%s" % chr(96 + kk))      # ten goc: repo_mo_phong_a / _c (khong chua so lan)
            (d1 / "docs/logs/c5a_q6_20261004_221728").mkdir(parents=True)
            time.sleep(0.05)
            (d1 / sess_rel).mkdir(parents=True)
            subprocess.run([bash, "-c", b531.replace("<IP_ESP32>", "127.0.0.1:1")], capture_output=True, text=True, cwd=str(d1), timeout=30,
                           encoding="utf-8", errors="replace", env=dict(os.environ, SESSION_DIR=sess_rel, K=str(kk)))
            subprocess.run([bash, "-c", cmd], capture_output=True, text=True, cwd=str(d1), timeout=30, encoding="utf-8", errors="replace",
                           env={k: v for k, v in os.environ.items() if k not in ("SESSION_DIR", "K")})
            landed += sorted("k%d:%s" % (kk, str(x.relative_to(d1)).replace("\\", "/")) for x in d1.rglob("rst*_action_time.txt"))
            want.append("k%d:%s/rst%d_action_time.txt" % (kk, sess_rel, kk))
        d2 = s8 / "repo_mo_phong_khong_thong_tin_phien"
        (d2 / "docs/logs/c5a_q6_20261004_221728").mkdir(parents=True)
        (d2 / sess_rel).mkdir(parents=True)
        rr = subprocess.run([bash, "-c", cmd], capture_output=True, text=True, cwd=str(d2), timeout=30, encoding="utf-8", errors="replace",
                            env={k: v for k, v in os.environ.items() if k not in ("SESSION_DIR", "K")})
        neg = sorted(str(x.relative_to(d2)).replace("\\", "/") for x in d2.rglob("rst*_action_time.txt"))
        want.append("am: rc!=0, khong ghi tep (terminal 1 thuc te dang K=3)")
        landed.append("am: rc=%d, ghi %s" % (rr.returncode, neg))
        if rr.returncode != 0 and not neg:
            landed[-1] = want[-1]
    right = landed == want
    check("S8.7", i_t2 < 0 or right,
          "R10: khoi lenh ghi gio RST o terminal thu hai, chay nguyen van trong terminal moi (khong bien), phai ghi dung thu muc phien va dung so lan K cua terminal 1",
          "co dong gan bien: %s; terminal 1 chay buoc 5.3.1 voi SESSION_DIR=docs/logs/c5a_q6_rst_<ngau nhien>, K=1 roi K=3; terminal 2 moi ghi ra: %s (mong: %s); chay lan dau: rc=%s '%s'" % (
              sets_vars, landed, want, rc_, out_))


def main():
    global JPEG
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:  # noqa: BLE001
        pass
    print("Tester C5a Q6 - kiem doc lap /capture_fresh tai B=%s (base %s)" % (B, BASE[:7]))
    JPEG = jpeg_bytes()
    td = tempfile.mkdtemp(prefix="c5a_q6_")
    try:
        for f in (group_s, lambda: group_h(td),
                  lambda: group_s7(show(B, "docs/procedures/quy-trinh-c5a-fresh-capture.md").decode("utf-8"), td),
                  lambda: group_s8(show(B, "docs/procedures/quy-trinh-c5a-fresh-capture.md").decode("utf-8"), td),
                  lambda: group_t(td), lambda: group_u(td), lambda: group_p(td), lambda: group_d(td), lambda: group_e(td),
                  lambda: group_m(td), group_r):
            try:
                f()
            except Exception as e:  # noqa: BLE001
                check("X", False, "ngoai le khi kiem", repr(e))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    nf = sum(1 for _, t in RESULTS if t == "FAIL")
    print("\nTONG: %d PASS, %d FAIL, %d NOTE" % (sum(1 for _, t in RESULTS if t == "PASS"), nf, sum(1 for _, t in RESULTS if t == "NOTE")))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
