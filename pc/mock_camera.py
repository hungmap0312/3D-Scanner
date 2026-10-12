#!/usr/bin/env python3
"""
mock_camera.py - server gia lap CameraWebServer de thu capture_session.py
va camera_profile.py khi khong co bo. KHONG thay the bo that; chi de thu
luong script.

Gia lap: /status (JSON co framesize, quality, cac control aec/agc/awb...
va thanh ghi hex nhu firmware that bao qua app_httpd.cpp), /control?var=
...&val=... cho toan bo bien trong camera_profile.CONTROL_ORDER cong
framesize/quality, /capture (JPEG do Pillow sinh, moi khung khac nhau,
header X-Timestamp la thoi gian tu luc server chay). Tuy chon --reset-at N:
tu khung N tro di, X-Timestamp tinh lai tu 0 de thu bo phat hien reset.

Tiem loi (them 20/09 de tai hien cac nhanh trong review R02-R05):
  --fail-frames 2,5      /capture thu 2 va 5 tra 503 body "busy" (lan sau OK)
  --drop-ts-frames 3     /capture thu 3 khong co header X-Timestamp
  --lowercase-headers    gui "x-timestamp" chu thuong
  --status-mode M        /status: ok | invalid (200, khong phai JSON) |
                         list (200, JSON list) | http503
  --status-fail-after N  sau N lan /capture, /status tra 503 (thu status cuoi)

Tiem loi cho ho so camera (them 21/09 cho C2, xem pc/camera_profile.py):
  --ignore-controls VAR[,VAR...]     /control tra 200 OK nhung KHONG doi
                                      gia tri, gia lap firmware am tham
                                      khong ap (camera_profile.py phai bat
                                      duoc bang doi chieu /status)
  --fail-controls VAR[,VAR...]       /control tra 500 cho cac bien nay du
                                      la bien firmware co ho tro (khac voi
                                      bien la, luon tra 500 nhu firmware
                                      that voi "Unknown command")
  --drift-registers 0xNNNN[,...]     danh sach thanh ghi se doi gia tri
  --drift-after N                    tu lan /capture thu N tro di, cac
                                      thanh ghi trong --drift-registers
                                      doi (+7), gia lap AEC/AGC/AWB tu
                                      chinh lai giua phien
  --status-drop-fields NAME[,...]    bo cac truong nay khoi JSON /status,
                                      gia lap firmware thieu truong

Tiem loi vong 3 (them 21/09, xu ly G03/G04 cua Tester):
  --control-drift-fields VAR=VAL[,...]  tu lan /capture thu N (xem duoi),
                                      cac bien nay doi thang gia tri moi -
                                      gia lap AEC/AGC/AWB tu bat lai giua
                                      phien MA thanh ghi tinh co khong doi
                                      (--drift-registers rieng, co the
                                      dung ca hai cung luc hoac tach biet)
  --control-drift-after N            nguong lan /capture cho drift control
  /_counts (GET)                     JSON dem so request da nhan theo
                                      loai {"control": N, "capture": N,
                                      "status": N} - Tester doi chieu "dung
                                      ngay khi loi" (G04) va "0 request"
                                      bang so nay, khong doan tu thoi gian

Tiem loi cho --probe (them Vong 5, xu ly L05-L07):
  --registers 0xNNNN=V[,...]         ghi de gia tri thanh ghi hex ban dau,
                                      vi du 0x3500=8000,0x350a=32 - dung de
                                      kiem cong thuc ung vien aec_value/
                                      agc_gain cua camera_profile.py --probe
  --status-fail-at-count N           /status lan thu N (dem theo
                                      /_counts.status, khong phu thuoc so
                                      /capture) tra 503 mot lan - mo phong
                                      loi giua chung mot phien probe nhieu
                                      mau, khac --status-fail-after (dem
                                      theo /capture)

Gia lap phan cung Vong 6 (L08, L10 - xem 01_PLAN.md Phu luc Vong 6 muc 2):
  /control?var=aec_value  gui > AEC_VALUE_HARD_CAP (783) chi echo lai 783
                                      trong /status, gia lap set_aec_value()
                                      kep cung o tran thiet bi da do
  /control?var=wb_mode    gui 1..4 doi thang ba thanh ghi gain mau
                                      (0x3400/0x3402/0x3404) va dat
                                      0x3406=1 theo bang WB_MODE_REGISTERS
                                      (driver OV3660 chuan), khong chi doi
                                      truong status

Gia lap chuyen trang thai WB Vong 7 (L11):
  /control?var=wb_mode=0  chi xoa che do thu cong (0x3406=0), gain giu
                                      nguyen; khoi dong mock cung o 0x3406=0
  /control?var=awb_gain   goi lai bo chon mode hien tai (nhu
                                      set_awb_gain_dsp() cua driver)
  --wb-registers-stuck               wb_mode/awb_gain tra 200 va echo trong
                                      /status nhung khong doi thanh ghi nao
                                      - HTTP OK ma khong ap (Tester V7-T4)
  Mock KHONG gia lap mau anh: awb bat/tat khong doi JPEG; chi giao thuc.

  .venv/Scripts/python.exe pc/mock_camera.py --port 8081
  .venv/Scripts/python.exe pc/mock_camera.py --port 8081 --reset-at 3

Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import io
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

SIZES = {6: (320, 240), 10: (640, 480), 11: (800, 600), 15: (1600, 1200)}

# Bien /control ho tro, TRUNG voi camera_profile.CONTROL_ORDER cong
# framesize/quality; "sharpness" CO Y khong co o day vi firmware that
# (app_httpd.cpp cmd_handler) cung khong co nhanh xu ly bien nay.
CMD_VARS = (
    "framesize", "quality", "aec", "agc", "awb", "aec_value", "agc_gain",
    "awb_gain", "wb_mode", "brightness", "contrast", "saturation",
    "hmirror", "vflip", "lenc", "dcw",
)

# Gia tri control mac dinh khi server khoi dong: mo phong bo CHUA khoa
# (aec/agc/awb tu dong bat, giong /status that doc 17/09 truoc khi C2 tat).
# Vong 5 (L05): vflip/brightness/saturation khoi dong = 1/1/-2, dung theo
# firmware that (CameraWebServerTest.ino dat rieng cho OV3660_PID ngay tu
# luc boot, khong phu thuoc AEC/AGC/AWB) - truoc day mock khoi dong ca ba o
# 0, khong khop hanh vi that.
DEFAULT_CONTROLS = {
    "aec": 1, "agc": 1, "awb": 1, "aec_value": 0, "agc_gain": 0,
    "awb_gain": 1, "wb_mode": 0, "brightness": 1, "contrast": 0,
    "saturation": -2, "hmirror": 0, "vflip": 1, "lenc": 1, "dcw": 1,
}

# Thanh ghi hex mac dinh, gia tri gan voi /status that doc 17/09
# (STATUS.md: 0x3500=12544, 0x350a=248, 0x3400~1362, 0x3404~1697).
# Vong 5 (L07): them 0x3402/0x3406/0x3503 (gain mau/che do manual), gia tri
# on dinh gia lap - --registers ghi de duoc cho tung kich ban Tester.
# Vong 7 (L11): 0x3406 khoi dong = 0 cho khop wb_mode=0 luc boot (che do
# WB tu dong); truoc la 1, mau thuan voi DEFAULT_CONTROLS.
DEFAULT_REGISTERS = {
    "0x3400": 1362, "0x3404": 1697, "0x3500": 12544, "0x350a": 248,
    "0x3402": 256, "0x3406": 0, "0x3503": 0,
}

# L08 (Vong 6, do tren bo that): dat aec_value qua /control?var=aec_value
# bi KEP cung o tran nay - gia lap dung hanh vi set_aec_value() thay vi
# echo lai nguyen gia tri gui len.
AEC_VALUE_HARD_CAP = 783

# L10 (Vong 6, 01_PLAN.md Phu luc Vong 6 muc 2, bang driver OV3660 chuan):
# gia lap /control?var=wb_mode doi ba thanh ghi gain mau va dat 0x3406=1,
# khong chi doi truong status - de Tester kiem duoc bon preset cho bon bo
# thanh ghi khac nhau qua mock truoc khi do tren bo that.
WB_MODE_REGISTERS = {
    1: {"0x3400": 0x05e0, "0x3402": 0x0410, "0x3404": 0x0540, "0x3406": 1},
    2: {"0x3400": 0x0650, "0x3402": 0x0410, "0x3404": 0x04f0, "0x3406": 1},
    3: {"0x3400": 0x0520, "0x3402": 0x0410, "0x3404": 0x0660, "0x3406": 1},
    4: {"0x3400": 0x0420, "0x3402": 0x03f0, "0x3404": 0x0710, "0x3406": 1},
}


def apply_wb_mode(mode):
    """Vong 7 (L11): gia lap set_wb_mode() cua driver OV3660 - mode 1..4
    ghi ba gain va dat 0x3406=1 (thu cong); mode 0 chi xoa bit thu cong
    (0x3406=0), gain de nguyen cho WB tu dong. --wb-registers-stuck: khong
    doi thanh ghi nao (gia lap HTTP 200 nhung khong ap)."""
    if STATE["wb_registers_stuck"]:
        return
    if mode == 0:
        STATE["registers"]["0x3406"] = 0
    elif mode in WB_MODE_REGISTERS:
        STATE["registers"].update(WB_MODE_REGISTERS[mode])


import secrets

DEFAULT_BOOT_ID = secrets.token_hex(16)

STATE = {
    "framesize": 6, "quality": 10, "frame": 0, "t0": time.time(), "reset_at": 0,
    "fail_frames": set(), "drop_ts_frames": set(), "lowercase_headers": False,
    "status_mode": "ok", "status_fail_after": 0,
    "controls": dict(DEFAULT_CONTROLS), "registers": dict(DEFAULT_REGISTERS),
    "ignore_controls": set(), "fail_controls": set(),
    "drift_registers": set(), "drift_after": 0, "status_drop_fields": set(),
    "control_drift_fields": {}, "control_drift_after": 0,
    "counts": {"control": 0, "capture": 0, "status": 0, "capture_fresh": 0},
    "status_fail_at_count": 0,
    "wb_registers_stuck": False,
    # D043: /capture_fresh simulation state & fault injections
    "boot_id": DEFAULT_BOOT_ID,
    "fresh_frame_id": 0,
    "fresh_stream_busy": False,
    "fresh_capture_busy": False,
    "fresh_no_buffer": False,
    "fresh_timeout_stale": False,
    "fresh_unsupported_format": False,
    "fresh_overflow": False,
    "fresh_discard_frames": 0,
    "fresh_reboot_at": 0,
    "fresh_corrupt_jpeg": False,
    "fresh_drop_headers": set(),
}


def make_jpeg(w, h, n):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (n * 7 % 256, n * 13 % 256, n * 29 % 256))
    d = ImageDraw.Draw(im)
    d.rectangle([n % w, n % h, (n % w) + 20, (n % h) + 20], fill=(255, 255, 255))
    d.text((5, 5), "frame %d" % n, fill=(0, 0, 0))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def effective_registers():
    regs = dict(STATE["registers"])
    if STATE["drift_after"] and STATE["frame"] >= STATE["drift_after"]:
        for k in STATE["drift_registers"]:
            if k in regs:
                regs[k] = regs[k] + 7
    return regs


def effective_controls():
    ctrl = dict(STATE["controls"])
    if STATE["control_drift_after"] and STATE["frame"] >= STATE["control_drift_after"]:
        ctrl.update(STATE["control_drift_fields"])
    return ctrl


def status_body():
    d = {"xclk": 20, "pixformat": 4, "framesize": STATE["framesize"], "quality": STATE["quality"]}
    d.update(effective_controls())
    d.update(effective_registers())
    d["mock"] = True
    for f in STATE["status_drop_fields"]:
        d.pop(f, None)
    return json.dumps(d).encode()


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("mock: " + (fmt % a) + chr(10))

    def _send(self, code, ctype, body, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/_counts":
            return self._send(200, "application/json", json.dumps(STATE["counts"]).encode())
        if u.path == "/status":
            STATE["counts"]["status"] += 1
            mode = STATE["status_mode"]
            if STATE["status_fail_after"] and STATE["frame"] >= STATE["status_fail_after"]:
                mode = "http503"
            if STATE["status_fail_at_count"] and STATE["counts"]["status"] == STATE["status_fail_at_count"]:
                mode = "http503"
            if mode == "http503":
                return self._send(503, "text/plain", b"busy")
            if mode == "invalid":
                return self._send(200, "application/json", b"<html>not json</html>")
            if mode == "list":
                return self._send(200, "application/json", b"[1]")
            return self._send(200, "application/json", status_body())
        if u.path == "/control":
            STATE["counts"]["control"] += 1
            q = parse_qs(u.query)
            var = q.get("var", [""])[0]
            val_raw = q.get("val", ["0"])[0]
            if var not in CMD_VARS:
                return self._send(500, "text/plain", b"Unknown command")
            if var in STATE["fail_controls"]:
                return self._send(500, "text/plain", b"control rejected")
            try:
                val = int(val_raw)
            except ValueError:
                return self._send(400, "text/plain", b"bad val")
            if var in STATE["ignore_controls"]:
                return self._send(200, "text/plain", b"OK")  # nhan nhung khong doi, gia lap khong ap
            if var == "framesize":
                STATE["framesize"] = val
            elif var == "quality":
                STATE["quality"] = val
            elif var == "aec_value":
                # L08: gia lap set_aec_value() kep cung o tran, khong echo
                # lai nguyen gia tri gui len (khac luc AEC tu dong ghi
                # thang thanh ghi, khong qua duong nay).
                STATE["controls"][var] = min(val, AEC_VALUE_HARD_CAP)
            else:
                STATE["controls"][var] = val
                if var == "wb_mode":
                    apply_wb_mode(val)
                elif var == "awb_gain":
                    # driver: set_awb_gain_dsp() goi lai set_wb_mode(mode hien tai)
                    apply_wb_mode(STATE["controls"].get("wb_mode", 0))
            return self._send(200, "text/plain", b"OK")
        if u.path == "/capture":
            STATE["counts"]["capture"] += 1
            STATE["frame"] += 1
            n = STATE["frame"]
            if STATE["reset_at"] and n == STATE["reset_at"]:
                STATE["t0"] = time.time()  # gia reset: thoi gian tu boot ve 0
            up = time.time() - STATE["t0"]
            ts = "%d.%06d" % (int(up), int((up - int(up)) * 1000000))
            w, h = SIZES.get(STATE["framesize"], (320, 240))
            if n in STATE["fail_frames"]:
                STATE["fail_frames"].discard(n)  # chi loi mot lan, lan thu lai se OK
                return self._send(503, "text/plain", b"busy")
            extra = {}
            if n not in STATE["drop_ts_frames"]:
                extra["x-timestamp" if STATE["lowercase_headers"] else "X-Timestamp"] = ts
            return self._send(200, "image/jpeg", make_jpeg(w, h, n), extra)

        if u.path == "/capture_fresh":
            STATE["counts"]["capture_fresh"] += 1
            n_fresh = STATE["counts"]["capture_fresh"]
            if STATE["fresh_reboot_at"] and n_fresh >= STATE["fresh_reboot_at"]:
                # Gia lap bo reboot: doi boot_id moi, reset frame_id
                STATE["boot_id"] = secrets.token_hex(16)
                STATE["fresh_frame_id"] = 0
                STATE["t0"] = time.time()
                STATE["last_req_sec"] = 0.0
                STATE["fresh_reboot_at"] = 0

            if STATE["fresh_stream_busy"]:
                return self._send(503, "text/plain", b"ERROR CAMERA_BUSY_STREAM")
            if STATE["fresh_capture_busy"]:
                return self._send(503, "text/plain", b"ERROR CAMERA_BUSY_CAPTURE")
            if STATE["fresh_no_buffer"]:
                return self._send(503, "text/plain", b"ERROR CAMERA_NO_BUFFER")
            if STATE["fresh_timeout_stale"]:
                return self._send(503, "text/plain", b"ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME")
            if STATE["fresh_unsupported_format"]:
                return self._send(500, "text/plain", b"ERROR CAMERA_UNSUPPORTED_FORMAT")
            if STATE["fresh_overflow"]:
                return self._send(500, "text/plain", b"ERROR FRAME_ID_OVERFLOW")

            STATE["fresh_frame_id"] += 1
            fid = STATE["fresh_frame_id"]

            now_sec = time.time() - STATE["t0"]
            if "last_req_sec" not in STATE or now_sec <= STATE["last_req_sec"]:
                now_sec = STATE.get("last_req_sec", 0.0) + 0.001
            STATE["last_req_sec"] = now_sec
            t_req_sec = now_sec
            t_frame_sec = t_req_sec + 0.033

            str_fid = str(fid)
            str_boot_id = STATE["boot_id"]
            str_ts = "%d.%06d" % (int(t_frame_sec), int((t_frame_sec - int(t_frame_sec)) * 1000000))
            str_req_ts = "%d.%06d" % (int(t_req_sec), int((t_req_sec - int(t_req_sec)) * 1000000))
            str_discarded = str(STATE["fresh_discard_frames"])

            extra = {
                "Content-Disposition": "inline; filename=capture_fresh.jpg",
                "Access-Control-Allow-Origin": "*",
            }
            drop = STATE["fresh_drop_headers"]
            if "X-Frame-Id" not in drop:
                extra["X-Frame-Id"] = str_fid
            if "X-Boot-Id" not in drop:
                extra["X-Boot-Id"] = str_boot_id
            if "X-Timestamp" not in drop:
                extra["X-Timestamp"] = str_ts
            if "X-Request-Timestamp" not in drop:
                extra["X-Request-Timestamp"] = str_req_ts
            if "X-Discarded-Frames" not in drop:
                extra["X-Discarded-Frames"] = str_discarded

            w, h = SIZES.get(STATE["framesize"], (320, 240))
            jpeg_body = make_jpeg(w, h, fid)
            if STATE["fresh_corrupt_jpeg"]:
                jpeg_body = jpeg_body[:10]

            return self._send(200, "image/jpeg", jpeg_body, extra)

        return self._send(404, "text/plain", b"not found")


def _split_csv(s):
    return set(x.strip() for x in s.split(",") if x.strip())


def _split_kv(s):
    """'aec=1,awb=1' -> {'aec': 1, 'awb': 1}."""
    out = {}
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        k, sep, v = part.partition("=")
        if sep:
            out[k.strip()] = int(v.strip())
    return out


def apply_options(a):
    """Dat STATE tu argparse Namespace; dung duoc ca khi nhung server vao test."""
    STATE["reset_at"] = a.reset_at
    STATE["fail_frames"] = set(int(x) for x in a.fail_frames.split(",") if x.strip())
    STATE["drop_ts_frames"] = set(int(x) for x in a.drop_ts_frames.split(",") if x.strip())
    STATE["lowercase_headers"] = bool(a.lowercase_headers)
    STATE["status_mode"] = a.status_mode
    STATE["status_fail_after"] = a.status_fail_after
    STATE["ignore_controls"] = _split_csv(getattr(a, "ignore_controls", "") or "")
    STATE["fail_controls"] = _split_csv(getattr(a, "fail_controls", "") or "")
    STATE["drift_registers"] = _split_csv(getattr(a, "drift_registers", "") or "")
    STATE["drift_after"] = getattr(a, "drift_after", 0) or 0
    STATE["status_drop_fields"] = _split_csv(getattr(a, "status_drop_fields", "") or "")
    STATE["control_drift_fields"] = _split_kv(getattr(a, "control_drift_fields", "") or "")
    STATE["control_drift_after"] = getattr(a, "control_drift_after", 0) or 0
    STATE["counts"] = {"control": 0, "capture": 0, "status": 0, "capture_fresh": 0}
    STATE["registers"] = dict(DEFAULT_REGISTERS)
    STATE["registers"].update(_split_kv(getattr(a, "registers", "") or ""))
    STATE["status_fail_at_count"] = getattr(a, "status_fail_at_count", 0) or 0
    STATE["wb_registers_stuck"] = bool(getattr(a, "wb_registers_stuck", False))

    # D043: Fresh capture options
    STATE["fresh_stream_busy"] = bool(getattr(a, "fresh_stream_busy", False))
    STATE["fresh_capture_busy"] = bool(getattr(a, "fresh_capture_busy", False))
    STATE["fresh_no_buffer"] = bool(getattr(a, "fresh_no_buffer", False))
    STATE["fresh_timeout_stale"] = bool(getattr(a, "fresh_timeout_stale", False))
    STATE["fresh_unsupported_format"] = bool(getattr(a, "fresh_unsupported_format", False))
    STATE["fresh_overflow"] = bool(getattr(a, "fresh_overflow", False))
    STATE["fresh_discard_frames"] = getattr(a, "fresh_discard_frames", 0) or 0
    STATE["fresh_reboot_at"] = getattr(a, "fresh_reboot_at", 0) or 0
    STATE["fresh_corrupt_jpeg"] = bool(getattr(a, "fresh_corrupt_jpeg", False))
    STATE["fresh_drop_headers"] = _split_csv(getattr(a, "fresh_drop_headers", "") or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--reset-at", type=int, default=0, help="gia reset o khung thu N (0 = khong)")
    ap.add_argument("--fail-frames", default="", help="danh sach khung tra 503 mot lan, vi du 2,5")
    ap.add_argument("--drop-ts-frames", default="", help="danh sach khung khong gui X-Timestamp")
    ap.add_argument("--lowercase-headers", action="store_true", help="gui x-timestamp chu thuong")
    ap.add_argument("--status-mode", default="ok", choices=["ok", "invalid", "list", "http503"])
    ap.add_argument("--status-fail-after", type=int, default=0, help="sau N lan /capture, /status tra 503")
    ap.add_argument("--ignore-controls", default="", help="danh sach bien /control nhan OK nhung khong doi, vi du awb,agc")
    ap.add_argument("--fail-controls", default="", help="danh sach bien /control luon tra 500, vi du aec")
    ap.add_argument("--drift-registers", default="", help="danh sach thanh ghi hex se doi gia tri, vi du 0x3400,0x3404")
    ap.add_argument("--drift-after", type=int, default=0, help="tu lan /capture thu N, cac thanh ghi trong --drift-registers doi (+7)")
    ap.add_argument("--status-drop-fields", default="", help="danh sach truong bi bo khoi JSON /status, vi du aec,0x3500")
    ap.add_argument("--control-drift-fields", default="", help="cap VAR=VAL doi thang gia tri tu lan /capture thu N, vi du aec=1,awb=1")
    ap.add_argument("--control-drift-after", type=int, default=0, help="nguong lan /capture cho --control-drift-fields")
    ap.add_argument("--registers", default="", help="ghi de gia tri thanh ghi hex ban dau, vi du 0x3500=8000,0x350a=32 (Vong 5, kich ban --probe)")
    ap.add_argument("--status-fail-at-count", type=int, default=0, help="/status lan thu N (dem theo /_counts.status) tra 503, khong phu thuoc so /capture (Vong 5, kich ban --probe giua chung loi)")
    ap.add_argument("--wb-registers-stuck", action="store_true", help="wb_mode/awb_gain tra 200 va echo trong /status nhung KHONG doi 0x3400/0x3402/0x3404/0x3406 (Vong 7, L11: HTTP OK ma khong ap)")

    # D043: Fresh capture arguments
    ap.add_argument("--fresh-stream-busy", action="store_true", help="tra 503 ERROR CAMERA_BUSY_STREAM")
    ap.add_argument("--fresh-capture-busy", action="store_true", help="tra 503 ERROR CAMERA_BUSY_CAPTURE")
    ap.add_argument("--fresh-no-buffer", action="store_true", help="tra 503 ERROR CAMERA_NO_BUFFER")
    ap.add_argument("--fresh-timeout-stale", action="store_true", help="tra 503 ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME")
    ap.add_argument("--fresh-unsupported-format", action="store_true", help="tra 500 ERROR CAMERA_UNSUPPORTED_FORMAT")
    ap.add_argument("--fresh-overflow", action="store_true", help="tra 500 ERROR FRAME_ID_OVERFLOW")
    ap.add_argument("--fresh-discard-frames", type=int, default=0, help="so stale frames mo phong bo qua")
    ap.add_argument("--fresh-reboot-at", type=int, default=0, help="doi boot_id va reset ID o lan fresh thu N")
    ap.add_argument("--fresh-corrupt-jpeg", action="store_true", help="tra JPEG bi cat cut")
    ap.add_argument("--fresh-drop-headers", default="", help="danh sach headers bo qua, vi du X-Boot-Id,X-Frame-Id")

    a = ap.parse_args()
    apply_options(a)
    srv = HTTPServer(("127.0.0.1", a.port), H)
    print("mock camera tren http://127.0.0.1:%d  reset_at=%d" % (a.port, a.reset_at), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
