#!/usr/bin/env python3
"""
camera_profile.py - tao, ap va doi chieu ho so camera co dinh cho ESP32-S3
CameraWebServerTest, theo docs/design/SCAN_SESSION.md muc 5 (C2/C2b).

Ho so khoa framesize, quality va cac control tu dong (aec/agc/awb...) de
anh cap OFF/ON tuan 2 so sanh duoc voi nhau. Khong sua firmware; chi goi
/control va /status da co san trong app_httpd.cpp.

QUAN TRONG - lech giua ho so thiet ke va firmware that: firmware hien tai
(app_httpd.cpp ham cmd_handler) KHONG co nhanh xu ly bien "sharpness"
trong /control (chi doc duoc qua /status, khong dat duoc). SCAN_SESSION.md
muc 5 liet ke "sharpness" trong truong "controls", nhung o day no CO Y
khong dua vao CONTROL_ORDER: ap dung dung muc 7 cua ke hoach C2 ("Coder
chi them truong khi co bang chung tu payload that hoac firmware hien co").
Muon khoa sharpness phai sua firmware truoc, thuoc mot ke hoach khac.

Vong 5 (L05-L07, xem 03_TEST.md Vong 4 va 01_PLAN.md Phu luc ky thuat
Vong 5): T5 tren OV3660 that cho anh lat nguoc va am luc vi DEFAULT_CONTROLS
truoc day dat "de xuat, chua do" lam mac dinh im lang cho --create.
vflip/brightness/saturation nay CHAC CHAN (bang chung firmware, xem
DEFAULT_CONTROLS); aec_value/agc_gain/awb_gain/wb_mode CHUA co gia tri
xac minh nen KHONG con mac dinh - --create bat buoc nguoi goi truyen ro
qua --set (REQUIRED_EXPLICIT_CONTROLS), hoac dung --probe de lay ung vien
truoc. Ho so tao ra luon co "verified": null cho toi khi nguoi dung chay
duoc phien tren bo that va Tester ghi lai (T5 trong ke hoach).

Vong 7 (L11, 03_TEST.md Vong 6): awb=0 tat KHOI xu ly can bang trang
(bit 0 cua 0x5001 theo driver ov3660.c), nen gain thu cong cua wb_mode
duoc ghi vao thanh ghi nhung khong ap len anh. Ho so co dinh nay la
aec=0, agc=0, awb=1, awb_gain=1, wb_mode 1..4 (0x3406=1: che do thu cong,
khong phai WB tu dong). Ho so awb=0 cu khong con ap/verify duoc.

Cach dung, chay tu goc repo:
  .venv/Scripts/python.exe pc/camera_profile.py --selftest
  .venv/Scripts/python.exe pc/camera_profile.py --probe --host 127.0.0.1:8081
  .venv/Scripts/python.exe pc/camera_profile.py --create --host 127.0.0.1:8081 \
      --framesize VGA --quality 10 --set awb=1 \
      --set aec_value=490 --set agc_gain=2 --set awb_gain=1 --set wb_mode=1
  .venv/Scripts/python.exe pc/camera_profile.py --verify --host 127.0.0.1:8081 \
      --profile data/calibration/camera_profiles/cam_VGA_q10_20260922.json

Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LF = chr(10)

# Bang framesize: TRUNG VOI capture_session.py (cung nguon sensor.h cua
# esp32 core 3.3.11). Trung lap co y: chieu phu thuoc chi mot phia
# (capture_session.py dung camera_profile.py, khong nguoc lai) de tranh
# import vong giua hai tep deu chay duoc doc lap bang __main__.
FRAMESIZES = {
    "QVGA": 6, "VGA": 10, "SVGA": 11, "XGA": 12, "HD": 13, "SXGA": 14, "UXGA": 15,
}

# Thu tu ap dung qua /control?var=...&val=...; framesize/quality ap truoc
# vi doi kich thuoc bo dem anh. Danh sach lay theo nhanh xu ly that trong
# app_httpd.cpp ham cmd_handler VA theo SCAN_SESSION.md muc 5, TRU
# "sharpness" (xem doan QUAN TRONG o docstring dau tep).
CONTROL_ORDER = [
    "aec", "agc", "awb", "aec_value", "agc_gain", "awb_gain", "wb_mode",
    "brightness", "contrast", "saturation", "hmirror", "vflip", "lenc", "dcw",
]

# Thanh ghi toi thieu phai giu nguyen trong phien, theo SCAN_SESSION.md muc 5.
# Vong 5 (L07): them 0x3402/0x3406/0x3503 de chung minh ba gain mau va che
# do manual AEC/AGC thuc su on dinh, khong chi bon thanh ghi phoi sang cu.
DEFAULT_EXPECTED_REGISTER_KEYS = (
    "0x3500", "0x350a", "0x3400", "0x3404", "0x3402", "0x3406", "0x3503",
)

# Thanh ghi doc trong pha --probe de de xuat ung vien aec_value/agc_gain
# (Vong 5, L07): 0x3500/16 va (0x350a+1)/16, xem cmd_probe().
PROBE_REGISTER_KEYS = ("0x3500", "0x350a")

# Vong 7 (L11): --probe dat va doi doc lai dung trang thai tu dong nay truoc
# khi phat ung vien. Thu tu dat = thu tu dict; wb_mode=0 dat CUOI vi
# awb_gain goi lai bo chon mode (co the ap lai preset cu), mode 0 moi xoa
# che do thu cong (0x3406=0).
PROBE_AUTO_CONTROLS = {"aec": 1, "agc": 1, "awb": 1, "awb_gain": 1, "wb_mode": 0}
PROBE_AUTO_REGISTERS = {"0x3406": 0}

# Bang thanh ghi WB thu cong theo wb_mode (driver OV3660 chuan, 01_PLAN.md
# Phu luc Vong 6 muc 2; Tester doi chieu dat tren bo 24/09). Vong 7: la hop
# dong - ho so luu va /status sau khi ap deu phai khop dung dong cua
# wb_mode. mock_camera.py co ban rieng (gia lap phan cung), co y khong
# import cheo.
WB_MODE_REGISTERS = {
    1: {"0x3400": 0x05e0, "0x3402": 0x0410, "0x3404": 0x0540, "0x3406": 1},
    2: {"0x3400": 0x0650, "0x3402": 0x0410, "0x3404": 0x04f0, "0x3406": 1},
    3: {"0x3400": 0x0520, "0x3402": 0x0410, "0x3404": 0x0660, "0x3406": 1},
    4: {"0x3400": 0x0420, "0x3402": 0x03f0, "0x3404": 0x0710, "0x3406": 1},
}

# Thang chat luong JPEG cua esp32-camera (0 net nhat .. 63 nen nhieu nhat);
# khop cac gia tri 10/20 da dung trong du an (pc/README.md, STATUS.md).
QUALITY_MIN, QUALITY_MAX = 0, 63

REQUIRED_FIELDS = (
    "camera_profile_id", "created_at", "source", "board", "sensor",
    "framesize", "quality", "controls", "expected_registers", "lens_note", "verified",
)

# R02 (Reviewer Vong 2, 04_REVIEW.md): danh tinh bo/sensor co dinh cua C2,
# theo SCAN_SESSION.md muc 5 - mot ho so tu nhan thuoc thiet bi khac phai
# bi tu choi truoc HTTP, khong duoc coi hop le chi vi la chuoi khong rong.
BOARD_NAME = "ESP32-S3 N16R8"
SENSOR_NAME = "OV3660 PID 0x3660"

# Mau camera_profile_id theo SCAN_SESSION.md muc 5: cam_<framesize>_q<quality>_<YYYYMMDD>,
# co the co hau to retry "_rNN" hai chu so (Vong 5 muc 3: nhieu lan thu cung
# cau hinh/ngay khong duoc ghi de nhau, xem pick_next_profile_id()).
CAMERA_PROFILE_ID_RE = re.compile(
    r"^cam_(?P<framesize>[A-Za-z0-9]+)_q(?P<quality>\d+)_(?P<date>\d{8})(?:_r(?P<retry>\d{2}))?$"
)

# source.commit phai la hash Git day du (40 hex), khong chap nhan gia tri
# ngan/sai kieu lam bang chung nguon goc ho so.
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

# L05 (Tester Vong 4, 03_TEST.md): ba gia tri nay CHAC CHAN dung cho OV3660 -
# CameraWebServerTest.ino dong ~147-150 tu dat s->set_vflip(1),
# s->set_brightness(1), s->set_saturation(-2) khi PID == OV3660_PID; /status
# doi chung 17/09 xac nhan vflip=1, brightness=1, saturation=-2. Khoa nham
# ve 0 (ban truoc) lam anh lat nguoc (L05).
#
# aec_value/agc_gain/awb_gain/wb_mode KHONG dat mac dinh o day: Vong 4 tung
# dat mac dinh CHUA DO (aec_value=490, agc_gain=2 suy tu /status truoc khi
# tat AEC/AGC; awb_gain=0/wb_mode=0 doan) khien --create tao duoc ho so "hop
# le" nhung anh toi 12,8 lan va am luc (L06). REQUIRED_EXPLICIT_CONTROLS
# duoi bat buoc nguoi goi --create truyen ro bon gia tri nay qua --set;
# dung --probe de lay ung vien truoc khi chon.
#
# Vong 7 (L11): awb=1 (bat khoi xu ly mau), KHONG phai WB tu dong - che do
# thu cong do wb_mode 1..4 / 0x3406=1 quyet dinh. awb=0 cua Vong 3-6 lam
# gain preset khong ap len anh.
DEFAULT_CONTROLS = {
    "aec": 0, "agc": 0, "awb": 1,
    "brightness": 1, "contrast": 0, "saturation": -2,
    "hmirror": 0, "vflip": 1, "lenc": 1, "dcw": 1,
}

# Bon gia tri hieu chinh CHUA co so do xac minh tren bo; cmd_create() tu
# choi truoc HTTP neu thieu bat ky truong nao (L06, Vong 5).
REQUIRED_EXPLICIT_CONTROLS = ("aec_value", "agc_gain", "awb_gain", "wb_mode")

# Mien gia tri da co bang chung firmware/Espressif cho tung control (Vong 5,
# L05-L07): aec_value/agc_gain/wb_mode theo header cuc bo cua Espressif
# (sensor.h); awb_gain la co bat/tat gain AWB thu cong (0/1); vflip/
# brightness/saturation la ba gia tri chac chan cua OV3660 o tren. Cac
# control con lai (contrast/hmirror/lenc/dcw) chua co bang chung mien
# rieng, khong kiem o day - khong doan them mien khi chua co nguon.
CONTROL_DOMAINS = {
    "aec_value": (0, 1200),
    "agc_gain": (0, 30),
    "awb_gain": (0, 1),
    "wb_mode": (0, 4),
    "vflip": (0, 1),
    "brightness": (-2, 2),
    "saturation": (-2, 2),
}

# L08 (Vong 6, do tren bo that): dat aec_value qua set_aec_value() (duong
# --create/--verify di qua) bi KEP cung o 0x3500=12528 (783 dong) du gui
# 784..1200 - khac voi luc AEC tu dong ghi thang thanh ghi, khong bi kep
# (--probe doc duoc 784 tu do). Tran nay CHI xac nhan cho VGA va SVGA (hai
# framesize C2 dung); framesize khac chua do, khong ap dung o day.
AEC_VALUE_HARD_CAP = 783
AEC_VALUE_CAP_FRAMESIZES = ("VGA", "SVGA")


# ----------------------------------------------------------------------
# Phan khong can bo: luoc do, so sanh thanh ghi, ID. Co selftest.
# ----------------------------------------------------------------------

def validate_camera_profile_id(profile_id, framesize_name=None, quality=None):
    """Tra chuoi loi hoac ''. R02 (04_REVIEW.md Vong 2): dung mau
    cam_<framesize>_q<quality>_<YYYYMMDD> cua SCAN_SESSION.md muc 5, khong
    duoc chua dau phan cach duong dan hay '..'. Khi biet framesize/quality
    thuc te (goi tu validate_profile hoac cmd_create), ID phai khop hai
    truong do - khong duoc tu nhan mot cau hinh khac voi du lieu that."""
    if not isinstance(profile_id, str) or not profile_id:
        return "camera_profile_id phai la chuoi khong rong"
    if "/" in profile_id or "\\" in profile_id or ".." in profile_id:
        return "camera_profile_id khong duoc chua dau phan cach duong dan hoac '..'"
    m = CAMERA_PROFILE_ID_RE.match(profile_id)
    if not m:
        return "camera_profile_id '%s' khong dung mau cam_<framesize>_q<quality>_<YYYYMMDD>" % profile_id
    if m.group("framesize") not in FRAMESIZES:
        return "camera_profile_id co framesize '%s' ngoai mien" % m.group("framesize")
    if framesize_name is not None and m.group("framesize") != framesize_name:
        return "camera_profile_id ghi framesize '%s' khac truong framesize '%s'" % (m.group("framesize"), framesize_name)
    if quality is not None and int(m.group("quality")) != quality:
        return "camera_profile_id ghi quality '%s' khac truong quality '%s'" % (m.group("quality"), quality)
    return ""


def validate_board(b):
    """Tra chuoi loi hoac ''. R02: board phai dung thiet bi C2, khong chi
    la mot chuoi khong rong bat ky."""
    if not isinstance(b, str) or b != BOARD_NAME:
        return "board phai la '%s', nhan %r" % (BOARD_NAME, b)
    return ""


def validate_sensor(s):
    """Tra chuoi loi hoac ''. R02: sensor phai dung thiet bi C2."""
    if not isinstance(s, str) or s != SENSOR_NAME:
        return "sensor phai la '%s', nhan %r" % (SENSOR_NAME, s)
    return ""


def validate_created_at(v):
    """Tra chuoi loi hoac ''. R02: phai la chuoi ISO8601 co mui gio (dung
    dinh dang now_iso() sinh ra), khong chap nhan so hay chuoi thieu offset."""
    if not isinstance(v, str) or not v:
        return "created_at phai la chuoi ISO8601 co mui gio, nhan %r" % (v,)
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return "created_at khong phai ISO8601 hop le: %r" % (v,)
    if dt.tzinfo is None:
        return "created_at thieu mui gio (ISO8601 phai co offset)"
    return ""


def validate_git_commit(v):
    """Tra chuoi loi hoac ''. R02: source.commit phai la hash Git day du
    (40 ky tu hex), khong chap nhan gia tri ngan/sai kieu."""
    if not isinstance(v, str) or not GIT_COMMIT_RE.match(v):
        return "source.commit phai la hash Git day du (40 ky tu hex), nhan %r" % (v,)
    return ""


def validate_profile(p):
    """Tra (ok, errors). Kiem dung SCAN_SESSION.md muc 5: thieu ID, sai
    kieu, framesize/quality ngoai mien, control thieu hoac la; R02: danh
    tinh ID/board/sensor/created_at/source.commit dung, khong chi dung kieu."""
    if not isinstance(p, dict):
        return False, ["ho so khong phai object"]

    errors = [("thieu truong '%s'" % k) for k in REQUIRED_FIELDS if k not in p]
    if errors:
        return False, errors  # thieu truong bat buoc thi khong kiem sau duoc

    fs = p["framesize"]
    fs_ok = isinstance(fs, str) and fs in FRAMESIZES
    if not fs_ok:
        errors.append("framesize '%s' ngoai mien, phai la mot trong: %s" % (fs, ", ".join(FRAMESIZES)))

    q = p["quality"]
    q_ok = isinstance(q, int) and not isinstance(q, bool) and (QUALITY_MIN <= q <= QUALITY_MAX)
    if not q_ok:
        errors.append("quality '%s' ngoai mien [%d, %d]" % (q, QUALITY_MIN, QUALITY_MAX))

    id_err = validate_camera_profile_id(p["camera_profile_id"], fs if fs_ok else None, q if q_ok else None)
    if id_err:
        errors.append(id_err)
    board_err = validate_board(p["board"])
    if board_err:
        errors.append(board_err)
    sensor_err = validate_sensor(p["sensor"])
    if sensor_err:
        errors.append(sensor_err)
    if not isinstance(p["lens_note"], str):
        errors.append("lens_note phai la chuoi")
    if not isinstance(p["source"], dict) or "commit" not in p["source"]:
        errors.append("source phai la object co truong 'commit'")
    else:
        commit_err = validate_git_commit(p["source"]["commit"])
        if commit_err:
            errors.append(commit_err)
    created_err = validate_created_at(p["created_at"])
    if created_err:
        errors.append(created_err)

    controls = p["controls"]
    if not isinstance(controls, dict):
        errors.append("controls phai la object")
    else:
        missing = [k for k in CONTROL_ORDER if k not in controls]
        if missing:
            errors.append("controls thieu truong: %s" % ", ".join(missing))
        for k, v in controls.items():
            if k not in CONTROL_ORDER:
                errors.append("controls co truong khong ro '%s' (khong ap qua /control o day)" % k)
            elif not isinstance(v, int) or isinstance(v, bool):
                errors.append("controls['%s'] phai la so nguyen, nhan %r" % (k, v))
        errors.extend(validate_control_domains(controls))
        if fs_ok:
            cap_err = validate_aec_value_cap(fs, controls.get("aec_value"))
            if cap_err:
                errors.append(cap_err)
        wb_err = validate_wb_invariant(controls)
        if wb_err:
            errors.append(wb_err)

    regs = p["expected_registers"]
    if not isinstance(regs, dict):
        errors.append("expected_registers phai la object")
    else:
        missing = [k for k in DEFAULT_EXPECTED_REGISTER_KEYS if k not in regs]
        if missing:
            errors.append("expected_registers thieu thanh ghi: %s" % ", ".join(missing))
        for k, v in regs.items():
            if not isinstance(k, str) or not k.startswith("0x"):
                errors.append("expected_registers co khoa khong hop le '%s'" % k)
            elif not isinstance(v, int) or isinstance(v, bool):
                errors.append("expected_registers['%s'] phai la so nguyen, nhan %r" % (k, v))
        if isinstance(controls, dict):
            errors.extend(validate_wb_registers(controls, regs))

    if isinstance(controls, dict):
        errors.extend(_locked_control_errors(controls))

    verified = p["verified"]
    if verified is not None:
        if not isinstance(verified, dict):
            errors.append("verified phai la null hoac object")
        else:
            for k in ("session_id", "mean_drift_pct", "registers_stable"):
                if k not in verified:
                    errors.append("verified thieu truong '%s'" % k)
            # R02: cac truong co mat phai dung kieu - "verified" la bang
            # chung do tren bo, khong duoc coi hop le neu sai kieu tinh co
            # ep duoc (vd chuoi "nan" khong phai NaN, "yes" khong phai bool).
            if "session_id" in verified and (not isinstance(verified["session_id"], str) or not verified["session_id"]):
                errors.append("verified.session_id phai la chuoi khong rong, nhan %r" % (verified["session_id"],))
            if "mean_drift_pct" in verified:
                mdp = verified["mean_drift_pct"]
                if not isinstance(mdp, (int, float)) or isinstance(mdp, bool) or not math.isfinite(mdp) or mdp < 0:
                    errors.append("verified.mean_drift_pct phai la so huu han >= 0, nhan %r" % (mdp,))
            if "registers_stable" in verified and not isinstance(verified["registers_stable"], bool):
                errors.append("verified.registers_stable phai la bool, nhan %r" % (verified["registers_stable"],))

    return (len(errors) == 0), errors


def validate_control_domains(controls):
    """Tra list loi (rong neu hop le). Kiem mien cac truong da co bang
    chung firmware/Espressif (CONTROL_DOMAINS, Vong 5 L05-L07). Chi bao loi
    khi gia tri dung kieu so nguyen (khac kieu da bi validate_profile() bao
    rieng, tranh hai thong diep chong nhau cho cung mot truong, cung nguyen
    tac voi _locked_control_errors())."""
    errors = []
    for k, (lo, hi) in CONTROL_DOMAINS.items():
        if k not in controls:
            continue
        v = controls[k]
        if isinstance(v, int) and not isinstance(v, bool) and not (lo <= v <= hi):
            errors.append("controls['%s'] phai trong mien [%d, %d], nhan %d" % (k, lo, hi, v))
    return errors


def validate_aec_value_cap(framesize_name, aec_value):
    """Tra chuoi loi hoac ''. L08 (Vong 6): voi VGA/SVGA (da do tren bo),
    aec_value > AEC_VALUE_HARD_CAP khong bao gio ap duoc - set_aec_value()
    kep cung o tran, gui cao hon chi lam that bai o buoc doi chieu sau
    HTTP. Tu choi som hon o day. Framesize khac AEC_VALUE_CAP_FRAMESIZES
    chua co bang chung mien, khong kiem."""
    if framesize_name not in AEC_VALUE_CAP_FRAMESIZES:
        return ""
    if not isinstance(aec_value, int) or isinstance(aec_value, bool):
        return ""  # sai kieu da bi validate_profile()/CONTROL_DOMAINS bao rieng
    if aec_value > AEC_VALUE_HARD_CAP:
        return "aec_value %d vuot tran da do cho %s (toi da %d, L08)" % (aec_value, framesize_name, AEC_VALUE_HARD_CAP)
    return ""


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_wb_invariant(controls):
    """Tra chuoi loi hoac ''. Ho so co dinh phai la WB thu cong: awb_gain=1
    va wb_mode la mot preset 1..4 (L10 Vong 6; Vong 7 L11 cam them
    wb_mode=0 vi do la che do tu dong). Chi bao cac gia tri dung kieu va
    trong mien phan cung - sai kieu/ngoai mien da bi validate_profile()/
    CONTROL_DOMAINS bao rieng, tranh hai thong diep chong nhau."""
    errs = []
    awb_gain = controls.get("awb_gain")
    wb_mode = controls.get("wb_mode")
    if _is_int(awb_gain) and awb_gain == 0:
        errs.append("awb_gain=0 (L10/L11) - ho so co dinh phai dat awb_gain=1 de preset wb_mode co tac dung")
    if _is_int(wb_mode) and wb_mode == 0:
        errs.append("wb_mode=0 la che do can bang trang tu dong (L11) - ho so co dinh phai chon preset 1..4")
    return "; ".join(errs)


def validate_wb_registers(controls, regs):
    """Tra list loi. Vong 7 (L11): ho so WB thu cong phai co 0x3406=1 va ba
    gain dung dong WB_MODE_REGISTERS cua chinh controls.wb_mode - khong
    chap nhan gia tri bo dang tu chinh lam moc. Thanh ghi thieu/sai kieu va
    wb_mode sai da bi bao rieng, khong lap lai o day."""
    wb_mode = controls.get("wb_mode")
    if not _is_int(wb_mode) or wb_mode not in WB_MODE_REGISTERS:
        return []
    errs = []
    for k, want in WB_MODE_REGISTERS[wb_mode].items():
        got = regs.get(k)
        if _is_int(got) and got != want:
            errs.append("expected_registers['%s']=%d khac bang preset wb_mode=%d (phai %d, L11)" % (k, got, wb_mode, want))
    return errs


def _locked_control_errors(controls):
    """Vong 3: aec/agc bat buoc = 0 trong moi ho so co dinh - khong duoc de
    camera tu dong phoi sang. Vong 7 (L11): awb bat buoc = 1 (bat khoi xu ly
    mau; che do thu cong do wb_mode/0x3406 quyet dinh) - awb=0 cua Vong 3-6
    tat khoi ap gain nen preset khong len anh. Chi bao loi khi gia tri dung
    kieu so nguyen (khac kieu da bi validate_profile() bao rieng)."""
    errs = []
    for k in ("aec", "agc"):
        v = controls.get(k)
        if _is_int(v) and v != 0:
            errs.append("controls['%s'] phai bang 0 (ho so co dinh khong duoc bat tu dong)" % k)
    v = controls.get("awb")
    if _is_int(v) and v != 1:
        errs.append("controls['awb'] phai bang 1, nhan %d (L11: awb=0 tat khoi ap gain can bang trang, preset khong len anh)"
                    " - ho so awb=0 cu khong con dung duoc, tao ho so moi" % v)
    return errs


def validate_quality(q):
    """Tra chuoi loi hoac ''. Dung TRUOC khi goi HTTP (G04)."""
    if not isinstance(q, int) or isinstance(q, bool) or not (QUALITY_MIN <= q <= QUALITY_MAX):
        return "quality phai la so nguyen [%d, %d], nhan %r" % (QUALITY_MIN, QUALITY_MAX, q)
    return ""


def validate_timeout(t):
    """Tra chuoi loi hoac ''. Chan ca so am, 0, NaN va Infinity truoc HTTP
    (Infinity lam request cho vo han, khong bao gio bao loi)."""
    if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t) or t <= 0:
        return "timeout phai la so huu han > 0, nhan %r" % (t,)
    return ""


def _values_match(expected, got):
    """So gia tri VA kieu: bool tu JSON (true/false) khong duoc coi bang
    so 1/0 (Vong 3 L04) - bo tra sai kieu cho mot thanh ghi/control la loi
    that, du gia tri so trung ngau nhien (True==1, False==0 trong Python)."""
    if isinstance(expected, bool) or isinstance(got, bool):
        return isinstance(expected, bool) and isinstance(got, bool) and expected == got
    return expected == got


def compare_registers(expected, status_json, keys):
    """Doi chieu thanh ghi giua ho so (expected) va mot /status moi doc.
    Tra (ok, mismatches). Khong doc duoc mot ben thi FAIL, khong ngam hieu
    'khong doi' (cung nguyen tac voi capture_session.compare_status)."""
    if not isinstance(status_json, dict):
        return False, ["khong doc duoc /status de doi chieu thanh ghi"]
    mismatches = []
    for key in keys:
        if key not in expected:
            mismatches.append("thieu %s trong ho so" % key)
            continue
        if key not in status_json:
            mismatches.append("thieu %s trong /status moi" % key)
            continue
        if not _values_match(expected[key], status_json[key]):
            mismatches.append("%s: dau %s, cuoi %s" % (key, expected[key], status_json[key]))
    return (len(mismatches) == 0), mismatches


def make_profile_id(framesize_name, quality, when=None):
    d = (when or datetime.now()).strftime("%Y%m%d")
    return "cam_%s_q%d_%s" % (framesize_name, quality, d)


def pick_next_profile_id(out_dir, framesize_name, quality, when=None):
    """Tra ID ho so CHUA co tep .json trong out_dir: ID goc (khong hau to)
    truoc, roi lan luot _r01.._r99 (Vong 5 muc 3, L05-L07: nhieu lan thu
    cung cau hinh/ngay khong duoc ghi de lan thu truoc, vd file that bai
    23/09 phai con nguyen). None neu het 99 lan thu trong ngay."""
    base_id = make_profile_id(framesize_name, quality, when)
    if not (out_dir / (base_id + ".json")).exists():
        return base_id
    for n in range(1, 100):
        cand = "%s_r%02d" % (base_id, n)
        if not (out_dir / (cand + ".json")).exists():
            return cand
    return None


def git_info():
    info = {"commit": "khong doc duoc", "branch": "khong doc duoc", "dirty": None}
    try:
        run = lambda a: subprocess.run(a, cwd=REPO_ROOT, capture_output=True, text=True, timeout=10).stdout
        info["commit"] = run(["git", "rev-parse", "HEAD"]).strip()
        info["branch"] = run(["git", "branch", "--show-current"]).strip()
        info["dirty"] = bool(run(["git", "status", "--porcelain", "--untracked-files=no"]).strip())
    except Exception as e:
        info["error"] = str(e)
    return info


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def build_profile_dict(framesize_name, quality, controls, expected_registers, lens_note, profile_id=None, verified=None):
    return {
        "camera_profile_id": profile_id or make_profile_id(framesize_name, quality),
        "created_at": now_iso(),
        "source": git_info(),
        "board": BOARD_NAME,
        "sensor": SENSOR_NAME,
        "framesize": framesize_name,
        "quality": quality,
        "controls": dict(controls),
        "expected_registers": dict(expected_registers),
        "lens_note": lens_note,
        "verified": verified,
    }


def selftest():
    """Chay khong can bo. Tra 0 neu dat."""
    ok = True

    def check(cond, label):
        nonlocal ok
        print("  %-64s %s" % (label, "OK" if cond else "FAIL"))
        ok = ok and cond

    # Vong 5 (L06): DEFAULT_CONTROLS khong con du 14 khoa (bo bon gia tri
    # hieu chinh chua do) - selftest dung ban day du rieng cho cac ca "ho
    # so hop le", giong cach cmd_create() phai nhan --set cho bon truong do.
    # Vong 7 (L11): ho so hop le la WB thu cong (awb=1 tu DEFAULT_CONTROLS,
    # awb_gain=1, wb_mode=1) va thanh ghi WB dung bang preset 1.
    SELFTEST_CONTROLS = dict(DEFAULT_CONTROLS, aec_value=490, agc_gain=2, awb_gain=1, wb_mode=1)
    SELFTEST_REGISTERS = dict({k: 0 for k in DEFAULT_EXPECTED_REGISTER_KEYS}, **WB_MODE_REGISTERS[1])

    good = build_profile_dict("VGA", 10, SELFTEST_CONTROLS, SELFTEST_REGISTERS, "ong kinh goc, tieu diem xa")
    v_ok, errs = validate_profile(good)
    check(v_ok and errs == [], "validate_profile: ho so hop le -> khong loi")

    missing_id = dict(good)
    del missing_id["camera_profile_id"]
    v_ok, errs = validate_profile(missing_id)
    check(not v_ok and any("camera_profile_id" in e for e in errs), "validate_profile: thieu camera_profile_id -> loi")

    bad_type = dict(good)
    bad_type["quality"] = "10"
    v_ok, errs = validate_profile(bad_type)
    check(not v_ok and any("quality" in e for e in errs), "validate_profile: quality la chuoi -> loi")

    bad_type2 = dict(good)
    bad_type2["quality"] = True
    v_ok, errs = validate_profile(bad_type2)
    check(not v_ok and any("quality" in e for e in errs), "validate_profile: quality la bool -> loi (bool la subclass cua int)")

    out_range = dict(good)
    out_range["quality"] = 64
    v_ok, errs = validate_profile(out_range)
    check(not v_ok and any("quality" in e for e in errs), "validate_profile: quality 64 ngoai mien -> loi")

    out_range2 = dict(good)
    out_range2["framesize"] = "MEGA"
    v_ok, errs = validate_profile(out_range2)
    check(not v_ok and any("framesize" in e for e in errs), "validate_profile: framesize la -> loi")

    missing_ctrl = dict(good)
    missing_ctrl["controls"] = {k: v for k, v in SELFTEST_CONTROLS.items() if k != "awb"}
    v_ok, errs = validate_profile(missing_ctrl)
    check(not v_ok and any("controls thieu" in e and "awb" in e for e in errs), "validate_profile: controls thieu 'awb' -> loi")

    extra_ctrl = dict(good)
    extra_ctrl["controls"] = dict(SELFTEST_CONTROLS, sharpness=2)
    v_ok, errs = validate_profile(extra_ctrl)
    check(not v_ok and any("sharpness" in e for e in errs), "validate_profile: controls co 'sharpness' (khong ho tro /control) -> loi")

    missing_reg = dict(good)
    missing_reg["expected_registers"] = {"0x3500": 1}
    v_ok, errs = validate_profile(missing_reg)
    check(not v_ok and any("expected_registers thieu" in e for e in errs), "validate_profile: thieu thanh ghi bat buoc -> loi")

    bad_verified = dict(good)
    bad_verified["verified"] = {"session_id": "s1"}
    v_ok, errs = validate_profile(bad_verified)
    check(not v_ok and any("verified thieu" in e for e in errs), "validate_profile: verified thieu truong -> loi")

    ok_verified = dict(good)
    ok_verified["verified"] = {"session_id": "s1", "mean_drift_pct": 0.5, "registers_stable": True}
    v_ok, errs = validate_profile(ok_verified)
    check(v_ok, "validate_profile: verified du truong -> hop le")

    locked_bad = dict(good)
    locked_bad["controls"] = dict(SELFTEST_CONTROLS, aec=1)
    v_ok, errs = validate_profile(locked_bad)
    check(not v_ok and any("aec" in e and "bang 0" in e for e in errs), "validate_profile: aec=1 (Vong 3) -> loi, phai bang 0")
    locked_bad2 = dict(good)
    locked_bad2["controls"] = dict(SELFTEST_CONTROLS, agc=1, awb=0)
    v_ok, errs = validate_profile(locked_bad2)
    check(not v_ok and any("'agc'" in e and "bang 0" in e for e in errs) and any("'awb'" in e and "bang 1" in e for e in errs),
          "validate_profile: agc=1 va awb=0 cung luc -> hai loi rieng (Vong 7: awb phai 1)")

    # Vong 7 (L11): awb phai bang 1; ho so awb=0 cu bi tu choi kem ly do L11.
    for bad_awb in (0, 2):
        v_ok, errs = validate_profile(dict(good, controls=dict(SELFTEST_CONTROLS, awb=bad_awb)))
        check(not v_ok and any("'awb'" in e and "L11" in e for e in errs), "validate_profile: awb=%d -> loi, nhac L11 va tao ho so moi" % bad_awb)
    v_ok, errs = validate_profile(dict(good, controls=dict(SELFTEST_CONTROLS, awb=True)))
    check(not v_ok and any("'awb'" in e and "so nguyen" in e for e in errs), "validate_profile: awb=true (bool) -> loi kieu")

    # R02 (04_REVIEW.md Vong 2): danh tinh ho so - probe cua Reviewer phai
    # bi tu choi thay vi qua vi chi dung kieu chuoi/object chung chung.
    bad_id_traversal = dict(good)
    bad_id_traversal["camera_profile_id"] = "../outside"
    v_ok, errs = validate_profile(bad_id_traversal)
    check(not v_ok and any("camera_profile_id" in e for e in errs), "validate_profile: camera_profile_id '../outside' -> loi (R02)")

    bad_id_mismatch = dict(good)
    bad_id_mismatch["camera_profile_id"] = "cam_SVGA_q10_20260922"  # framesize thuc la VGA
    v_ok, errs = validate_profile(bad_id_mismatch)
    check(not v_ok and any("camera_profile_id" in e for e in errs), "validate_profile: camera_profile_id ghi SVGA nhung framesize la VGA -> loi (R02)")

    bad_board = dict(good)
    bad_board["board"] = "some-other-board"
    v_ok, errs = validate_profile(bad_board)
    check(not v_ok and any("board" in e for e in errs), "validate_profile: board khac thiet bi C2 -> loi (R02)")

    bad_sensor = dict(good)
    bad_sensor["sensor"] = "OV2640"
    v_ok, errs = validate_profile(bad_sensor)
    check(not v_ok and any("sensor" in e for e in errs), "validate_profile: sensor khac thiet bi C2 -> loi (R02)")

    bad_created = dict(good)
    bad_created["created_at"] = 123
    v_ok, errs = validate_profile(bad_created)
    check(not v_ok and any("created_at" in e for e in errs), "validate_profile: created_at la so -> loi (R02)")

    bad_created2 = dict(good)
    bad_created2["created_at"] = "2026-09-22T10:00:00"  # thieu mui gio
    v_ok, errs = validate_profile(bad_created2)
    check(not v_ok and any("created_at" in e for e in errs), "validate_profile: created_at thieu mui gio -> loi (R02)")

    bad_commit = dict(good)
    bad_commit["source"] = {"commit": False}
    v_ok, errs = validate_profile(bad_commit)
    check(not v_ok and any("source.commit" in e for e in errs), "validate_profile: source.commit la bool -> loi (R02)")

    bad_commit2 = dict(good)
    bad_commit2["source"] = {"commit": "abc123"}  # ngan hon 40 hex
    v_ok, errs = validate_profile(bad_commit2)
    check(not v_ok and any("source.commit" in e for e in errs), "validate_profile: source.commit ngan hon 40 hex -> loi (R02)")

    bad_verified_types = dict(good)
    bad_verified_types["verified"] = {"session_id": 123, "mean_drift_pct": "nan", "registers_stable": "yes"}
    v_ok, errs = validate_profile(bad_verified_types)
    check(not v_ok and sum("verified." in e for e in errs) == 3, "validate_profile: verified sai kieu ca ba truong -> ba loi rieng (R02)")

    check(validate_camera_profile_id("cam_VGA_q10_20260922") == "", "validate_camera_profile_id: dung mau -> hop le")
    check(validate_camera_profile_id("cam_VGA_q10_20260922", "VGA", 10) == "", "validate_camera_profile_id: khop framesize/quality thuc -> hop le")
    check(validate_camera_profile_id("cam_VGA_q10_20260922", "SVGA", 10) != "", "validate_camera_profile_id: sai framesize thuc -> loi")
    check(validate_camera_profile_id("cam_VGA_q10_20260922", "VGA", 20) != "", "validate_camera_profile_id: sai quality thuc -> loi")
    check(validate_camera_profile_id("../outside") != "", "validate_camera_profile_id: chua '..' -> loi")
    check(validate_camera_profile_id("a/b") != "", "validate_camera_profile_id: chua dau '/' -> loi")
    check(validate_board(BOARD_NAME) == "" and validate_board("khac") != "", "validate_board: dung/sai thiet bi C2")
    check(validate_sensor(SENSOR_NAME) == "" and validate_sensor("khac") != "", "validate_sensor: dung/sai thiet bi C2")
    check(validate_created_at(now_iso()) == "", "validate_created_at: now_iso() -> hop le")
    check(validate_created_at("2026-09-22T10:00:00") != "", "validate_created_at: thieu mui gio -> loi")
    check(validate_git_commit("a" * 40) == "", "validate_git_commit: 40 hex -> hop le")
    check(validate_git_commit("a" * 39) != "" and validate_git_commit("g" * 40) != "", "validate_git_commit: sai do dai/ky tu -> loi")

    # Vong 5 (L05-L07): mau ID co hau to retry _rNN.
    check(validate_camera_profile_id("cam_VGA_q10_20260922_r01") == "", "validate_camera_profile_id: hau to _r01 -> hop le")
    check(validate_camera_profile_id("cam_VGA_q10_20260922_r99") == "", "validate_camera_profile_id: hau to _r99 -> hop le")
    check(validate_camera_profile_id("cam_VGA_q10_20260922_r0") != "", "validate_camera_profile_id: hau to _r0 (1 chu so) -> loi")
    check(validate_camera_profile_id("cam_VGA_q10_20260922_r1") != "", "validate_camera_profile_id: hau to _r1 (1 chu so) -> loi")
    check(validate_camera_profile_id("cam_VGA_q10_20260922_r100") != "", "validate_camera_profile_id: hau to _r100 (3 chu so) -> loi")

    # Vong 5: L05 ba gia tri chac chan cua OV3660 trong DEFAULT_CONTROLS.
    check(DEFAULT_CONTROLS["vflip"] == 1 and DEFAULT_CONTROLS["brightness"] == 1 and DEFAULT_CONTROLS["saturation"] == -2,
          "DEFAULT_CONTROLS: vflip=1, brightness=1, saturation=-2 (L05, bang chung firmware)")
    check(all(k not in DEFAULT_CONTROLS for k in REQUIRED_EXPLICIT_CONTROLS),
          "DEFAULT_CONTROLS: khong con aec_value/agc_gain/awb_gain/wb_mode mac dinh (L06)")

    # Vong 5: mien gia tri CONTROL_DOMAINS - dau mut hop le, ngoai mien la loi.
    check(validate_control_domains({"aec_value": 0}) == [] and validate_control_domains({"aec_value": 1200}) == [],
          "validate_control_domains: aec_value dau mut 0/1200 -> hop le")
    check(validate_control_domains({"aec_value": -1}) != [] and validate_control_domains({"aec_value": 1201}) != [],
          "validate_control_domains: aec_value ngoai mien -> loi")
    check(validate_control_domains({"agc_gain": 0}) == [] and validate_control_domains({"agc_gain": 30}) == [],
          "validate_control_domains: agc_gain dau mut 0/30 -> hop le")
    check(validate_control_domains({"agc_gain": 31}) != [], "validate_control_domains: agc_gain 31 ngoai mien -> loi")
    check(validate_control_domains({"wb_mode": 0}) == [] and validate_control_domains({"wb_mode": 4}) == [],
          "validate_control_domains: wb_mode dau mut 0/4 -> hop le")
    check(validate_control_domains({"wb_mode": 5}) != [], "validate_control_domains: wb_mode 5 ngoai mien -> loi")
    check(validate_control_domains({"awb_gain": 0}) == [] and validate_control_domains({"awb_gain": 1}) == [],
          "validate_control_domains: awb_gain 0/1 -> hop le")
    check(validate_control_domains({"awb_gain": 2}) != [], "validate_control_domains: awb_gain 2 ngoai mien -> loi")
    check(validate_control_domains({"vflip": 0}) == [] and validate_control_domains({"vflip": 1}) == [],
          "validate_control_domains: vflip 0/1 -> hop le")
    check(validate_control_domains({"brightness": -2}) == [] and validate_control_domains({"brightness": 2}) == [],
          "validate_control_domains: brightness dau mut -2/2 -> hop le")
    check(validate_control_domains({"brightness": 3}) != [], "validate_control_domains: brightness 3 ngoai mien -> loi")
    check(validate_control_domains({"saturation": -3}) != [], "validate_control_domains: saturation -3 ngoai mien -> loi")
    check(validate_control_domains({"aec_value": "490"}) == [], "validate_control_domains: sai kieu bo qua (validate_profile bao rieng), khong chong loi")
    v_ok, errs = validate_profile(dict(good, controls=dict(SELFTEST_CONTROLS, agc_gain=31)))
    check(not v_ok and any("agc_gain" in e and "mien" in e for e in errs), "validate_profile: agc_gain 31 trong ho so -> loi mien (Vong 5)")

    # Vong 5 muc 3: pick_next_profile_id - goc truoc, roi _r01.._r99, khong ghi de.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        check(pick_next_profile_id(d, "VGA", 10, datetime(2026, 9, 23)) == "cam_VGA_q10_20260923",
              "pick_next_profile_id: thu muc rong -> ID goc, khong hau to")
        (d / "cam_VGA_q10_20260923.json").write_text("{}", encoding="utf-8")
        check(pick_next_profile_id(d, "VGA", 10, datetime(2026, 9, 23)) == "cam_VGA_q10_20260923_r01",
              "pick_next_profile_id: ID goc da co tep -> _r01")
        (d / "cam_VGA_q10_20260923_r01.json").write_text("{}", encoding="utf-8")
        check(pick_next_profile_id(d, "VGA", 10, datetime(2026, 9, 23)) == "cam_VGA_q10_20260923_r02",
              "pick_next_profile_id: goc va _r01 da co -> _r02")
        check(pick_next_profile_id(d, "SVGA", 20, datetime(2026, 9, 23)) == "cam_SVGA_q20_20260923",
              "pick_next_profile_id: cau hinh khac ngay khong bi anh huong")

    # Vong 6 (L08): tran aec_value da do tren bo, chi VGA/SVGA.
    check(validate_aec_value_cap("VGA", 0) == "" and validate_aec_value_cap("VGA", 783) == "",
          "validate_aec_value_cap: VGA 0 va 783 (tran) -> hop le")
    check(validate_aec_value_cap("VGA", 784) != "", "validate_aec_value_cap: VGA 784 (vuot tran) -> loi")
    check(validate_aec_value_cap("SVGA", 783) == "" and validate_aec_value_cap("SVGA", 784) != "",
          "validate_aec_value_cap: SVGA cung tran nhu VGA")
    check(validate_aec_value_cap("QVGA", 900) == "", "validate_aec_value_cap: framesize chua do (QVGA) -> khong kiem")
    check(validate_aec_value_cap("VGA", "784") == "", "validate_aec_value_cap: sai kieu bo qua (validate_profile bao rieng)")
    profile_over_cap = dict(good, framesize="VGA", controls=dict(SELFTEST_CONTROLS, aec_value=784))
    v_ok, errs = validate_profile(profile_over_cap)
    check(not v_ok and any("aec_value" in e and "tran" in e for e in errs), "validate_profile: VGA aec_value=784 trong ho so -> loi tran (L08)")

    # Vong 6 (L10) + Vong 7 (L11): WB thu cong = awb_gain=1 va wb_mode 1..4.
    check(validate_wb_invariant({"wb_mode": 1, "awb_gain": 0}) != "", "validate_wb_invariant: wb_mode=1, awb_gain=0 -> loi (L10)")
    check(validate_wb_invariant({"wb_mode": 1, "awb_gain": 1}) == "" and validate_wb_invariant({"wb_mode": 4, "awb_gain": 1}) == "",
          "validate_wb_invariant: wb_mode=1/4, awb_gain=1 -> hop le")
    check("wb_mode=0" in validate_wb_invariant({"wb_mode": 0, "awb_gain": 1}), "validate_wb_invariant: wb_mode=0 (tu dong) -> loi (Vong 7, L11)")
    check(validate_wb_invariant({"wb_mode": 0, "awb_gain": 0}).count(";") == 1, "validate_wb_invariant: wb_mode=0 va awb_gain=0 -> hai loi rieng (Vong 7)")
    check(validate_wb_invariant({"wb_mode": 5, "awb_gain": 2}) == "", "validate_wb_invariant: ngoai mien bo qua (CONTROL_DOMAINS bao rieng)")
    profile_wb_ambiguous = dict(good, controls=dict(SELFTEST_CONTROLS, awb_gain=0))
    v_ok, errs = validate_profile(profile_wb_ambiguous)
    check(not v_ok and any("awb_gain=0" in e for e in errs), "validate_profile: awb_gain=0 trong ho so -> loi (L10)")
    v_ok, errs = validate_profile(dict(good, controls=dict(SELFTEST_CONTROLS, wb_mode=0)))
    check(not v_ok and any("wb_mode=0" in e for e in errs), "validate_profile: wb_mode=0 trong ho so -> loi (Vong 7, L11)")

    # Vong 7 (L11): thanh ghi WB trong ho so phai khop bang preset cua wb_mode.
    for n in (1, 2, 3, 4):
        regs_n = dict(SELFTEST_REGISTERS, **WB_MODE_REGISTERS[n])
        v_ok, errs = validate_profile(dict(good, controls=dict(SELFTEST_CONTROLS, wb_mode=n), expected_registers=regs_n))
        check(v_ok, "validate_profile: wb_mode=%d voi thanh ghi dung bang -> hop le" % n)
    v_ok, errs = validate_profile(dict(good, expected_registers=dict(SELFTEST_REGISTERS, **{"0x3406": 0})))
    check(not v_ok and any("0x3406" in e and "L11" in e for e in errs), "validate_profile: 0x3406=0 (khong thu cong) -> loi")
    v_ok, errs = validate_profile(dict(good, expected_registers=dict(SELFTEST_REGISTERS, **{"0x3400": WB_MODE_REGISTERS[2]["0x3400"]})))
    check(not v_ok and any("0x3400" in e and "L11" in e for e in errs), "validate_profile: gain R cua preset 2 trong ho so preset 1 -> loi")
    v_ok, errs = validate_profile(dict(good, controls=dict(SELFTEST_CONTROLS, wb_mode=3)))
    check(not v_ok and sum("L11" in e for e in errs) == 2,
          "validate_profile: wb_mode=3 nhung thanh ghi preset 1 -> lech R va B (G trung 0x0410)")
    v_ok, errs = validate_profile(dict(good, expected_registers=dict(SELFTEST_REGISTERS, **{"0x3406": True})))
    check(not v_ok and any("0x3406" in e and "so nguyen" in e for e in errs) and not any("0x3406" in e and "L11" in e for e in errs),
          "validate_profile: 0x3406=true (bool) -> loi kieu, khong chong loi bang preset")
    check(validate_wb_registers({"wb_mode": 9}, {}) == [], "validate_wb_registers: wb_mode ngoai bang -> bo qua (bao rieng)")

    check(validate_quality(10) == "", "validate_quality: 10 hop le")
    check(validate_quality(0) == "" and validate_quality(63) == "", "validate_quality: bien 0 va 63 hop le")
    check(validate_quality(64) != "" and validate_quality(-1) != "", "validate_quality: 64/-1 bi chan")
    check(validate_quality(True) != "", "validate_quality: bool (subclass int) bi chan")
    check(validate_quality("10") != "", "validate_quality: chuoi bi chan")

    check(validate_timeout(15.0) == "", "validate_timeout: 15.0 hop le")
    check(validate_timeout(0) != "" and validate_timeout(-1) != "", "validate_timeout: 0 va am bi chan")
    check(validate_timeout(float("inf")) != "", "validate_timeout: Infinity bi chan (khong treo request)")
    check(validate_timeout(float("nan")) != "", "validate_timeout: NaN bi chan")
    check(validate_timeout(True) != "", "validate_timeout: bool bi chan")

    dc_ok, dc_mism = diff_controls({"framesize": 10, "quality": 10, "aec": 0}, "VGA", 10, {"aec": 0})
    check(dc_ok and dc_mism == [], "diff_controls: status khop -> khong lech")
    dc_ok, dc_mism = diff_controls({"framesize": 10, "quality": 10, "aec": 1}, "VGA", 10, {"aec": 0})
    check(not dc_ok and any("aec" in m for m in dc_mism), "diff_controls: aec troi tu 0 sang 1 -> bao lech (G03)")
    dc_ok, dc_mism = diff_controls(None, "VGA", 10, {"aec": 0})
    check(not dc_ok and "khong doc duoc" in dc_mism[0], "diff_controls: status None -> FAIL, khong ngam hieu khong doi")
    dc_ok, dc_mism = diff_controls({"framesize": 10, "quality": 10, "aec": False}, "VGA", 10, {"aec": 0})
    check(not dc_ok and any("aec" in m for m in dc_mism), "diff_controls: bo tra bool False thay so 0 -> bao lech (L04)")

    exp = {"0x3500": 12544, "0x350a": 248}
    same = {"0x3500": 12544, "0x350a": 248, "framesize": 10}
    diff = {"0x3500": 12544, "0x350a": 999, "framesize": 10}
    c_ok, mism = compare_registers(exp, same, exp.keys())
    check(c_ok and mism == [], "compare_registers: thanh ghi giong nhau -> khong lech")
    c_ok, mism = compare_registers(exp, diff, exp.keys())
    check(not c_ok and any("0x350a" in m for m in mism), "compare_registers: 0x350a lech -> bao lech")
    c_ok, mism = compare_registers(exp, None, exp.keys())
    check(not c_ok and "khong doc duoc" in mism[0], "compare_registers: /status None -> FAIL, khong ngam hieu khong doi")
    c_ok, mism = compare_registers({"0x3500": 1}, {"0x3500": True}, ["0x3500"])
    check(not c_ok and any("0x3500" in m for m in mism), "compare_registers: bo tra bool True thay so 1 -> bao lech (L04)")

    check(make_profile_id("VGA", 10, datetime(2026, 9, 22)) == "cam_VGA_q10_20260922", "make_profile_id: dung dinh dang")

    check(CONTROL_ORDER == list(dict.fromkeys(CONTROL_ORDER)), "CONTROL_ORDER: khong trung, thu tu xac dinh")
    check("sharpness" not in CONTROL_ORDER, "CONTROL_ORDER: khong co 'sharpness' (firmware khong ho tro)")

    gi = git_info()
    check(len(gi.get("commit", "")) == 40, "git_info: doc duoc commit 40 ky tu")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ----------------------------------------------------------------------
# Phan can bo (that hoac mock_camera.py).
# ----------------------------------------------------------------------

def http_get(session, url, timeout):
    """Tra (status_code, body_bytes, loi)."""
    try:
        r = session.get(url, timeout=timeout)
        return r.status_code, r.content, ""
    except Exception as e:
        return 0, b"", "%s: %s" % (type(e).__name__, e)


def fetch_status(session, base, timeout):
    """Tra (ok, json_or_None, reason)."""
    code, body, err = http_get(session, base + "/status", timeout)
    if err:
        return False, None, "loi ket noi: %s" % err
    if code != 200:
        return False, None, "http %s" % code
    text = body.decode("utf-8", errors="replace")
    if not text.strip():
        return False, None, "body rong"
    try:
        parsed = json.loads(text)
    except ValueError as e:
        return False, None, "khong phai JSON: %s" % e
    if not isinstance(parsed, dict):
        return False, None, "JSON khong phai object"
    return True, parsed, ""


def set_control(session, base, var, val, timeout):
    url = "%s/control?var=%s&val=%s" % (base, var, val)
    code, _body, err = http_get(session, url, timeout)
    if err:
        return False, "loi ket noi: %s" % err
    if code != 200:
        return False, "http %s" % code
    return True, ""


def diff_controls(status_json, framesize_name, quality, controls):
    """So framesize/quality/14 control (KHONG goi HTTP, khong ap lai) voi
    mot /status da doc san. Tra (ok, mismatches). Dung chung cho
    apply_and_verify() (status vua doc ngay sau khi ap) va cho kiem cuoi
    phien trong capture_session.py (G03: bat control troi tro lai tu dong
    ma khong can ap lai)."""
    if not isinstance(status_json, dict):
        return False, ["khong doc duoc /status de doi chieu"]
    mismatches = []
    fs_val = FRAMESIZES[framesize_name]
    got_fs = status_json.get("framesize")
    if not _values_match(fs_val, got_fs):
        mismatches.append("framesize: yeu cau %s, bo bao %s" % (fs_val, got_fs))
    got_q = status_json.get("quality")
    if not _values_match(quality, got_q):
        mismatches.append("quality: yeu cau %s, bo bao %s" % (quality, got_q))
    for var in CONTROL_ORDER:
        if var not in controls:
            continue
        want = controls[var]
        got = status_json.get(var)
        if not _values_match(want, got):
            mismatches.append("%s: yeu cau %s, bo bao %s" % (var, want, got))
    return (len(mismatches) == 0), mismatches


def apply_and_verify(session, base, framesize_name, quality, controls, timeout,
                      expected_register_keys=DEFAULT_EXPECTED_REGISTER_KEYS):
    """Ap framesize, quality, controls (thu tu CONTROL_ORDER) len bo, doc
    lai /status, doi chieu tung gia tri da yeu cau voi gia tri bo bao cao.

    G04: dung NGAY khi mot /control loi (HTTP/ket noi) - khong gui tiep
    cac lenh con lai, khong doi het timeout cho tung lenh sau do.

    Tra dict: ok (bool), applied (list [(var, val, http_ok, err)]),
    status (json hoac None), mismatches (list str), expected_registers
    (dict thanh ghi hien co trong /status cho cac khoa yeu cau - CHI la
    gia tri vua doc, KHONG doi chieu voi ho so da luu; goi
    compare_registers() rieng o ngoai cho viec do).
    """
    applied = []

    def _apply_fail(reason):
        return {"ok": False, "applied": applied, "status": None, "mismatches": [reason], "expected_registers": {}}

    fs_val = FRAMESIZES[framesize_name]
    ok, err = set_control(session, base, "framesize", fs_val, timeout)
    applied.append(("framesize", fs_val, ok, err))
    if not ok:
        return _apply_fail("/control that bai: framesize (%s)" % err)

    ok, err = set_control(session, base, "quality", quality, timeout)
    applied.append(("quality", quality, ok, err))
    if not ok:
        return _apply_fail("/control that bai: quality (%s)" % err)

    for var in CONTROL_ORDER:
        if var not in controls:
            continue
        val = controls[var]
        ok, err = set_control(session, base, var, val, timeout)
        applied.append((var, val, ok, err))
        if not ok:
            return _apply_fail("/control that bai: %s (%s)" % (var, err))

    time.sleep(1.0)  # cho bo ap xong, giong capture_session.py khi doi framesize
    st_ok, st_json, st_reason = fetch_status(session, base, timeout)
    if not st_ok:
        return {
            "ok": False, "applied": applied, "status": None,
            "mismatches": ["khong doc duoc /status sau khi ap: %s" % st_reason],
            "expected_registers": {},
        }

    _ctrl_ok, mismatches = diff_controls(st_json, framesize_name, quality, controls)
    mismatches = list(mismatches)

    # Vong 7 (L11): WB thu cong phai thuc su vao thanh ghi - HTTP 200 va
    # control echo dung chua du; doi chieu 0x3406 va ba gain voi bang preset
    # TRUOC khi coi gia tri doc duoc la moc hop le cho ho so.
    wb_mode = controls.get("wb_mode")
    if _is_int(wb_mode) and wb_mode in WB_MODE_REGISTERS:
        for key, want in WB_MODE_REGISTERS[wb_mode].items():
            got = st_json.get(key)
            if not _values_match(want, got):
                mismatches.append("%s: preset wb_mode=%d yeu cau %s, bo bao %s (L11)" % (key, wb_mode, want, got))

    expected_registers = {}
    for key in expected_register_keys:
        if key not in st_json:
            mismatches.append("thieu thanh ghi %s trong /status" % key)
        else:
            expected_registers[key] = st_json[key]

    return {
        "ok": len(mismatches) == 0, "applied": applied, "status": st_json,
        "mismatches": mismatches, "expected_registers": expected_registers,
    }


def cmd_create(args):
    import requests

    base = "http://%s" % args.host
    controls = dict(DEFAULT_CONTROLS)
    for spec in (args.set or []):
        k, sep, v = spec.partition("=")
        if not sep or k not in CONTROL_ORDER:
            print("Loi: --set dung bien khong ro '%s'. Chon trong: %s" % (k, ", ".join(CONTROL_ORDER)))
            return 2
        try:
            controls[k] = int(v)
        except ValueError:
            print("Loi: --set %s gia tri khong phai so nguyen: %r" % (k, v))
            return 2

    out_dir = (REPO_ROOT / (args.out or "data/calibration/camera_profiles")).resolve()

    if args.id:
        profile_id = args.id
    else:
        profile_id = pick_next_profile_id(out_dir, args.framesize, args.quality)
        if profile_id is None:
            print("Loi: da qua 99 lan thu cho cau hinh nay trong ngay, dat --id rieng.")
            return 2

    # L06 (Vong 5): bon gia tri hieu chinh phai duoc truyen ro qua --set -
    # DEFAULT_CONTROLS khong con mac dinh cho chung, xem REQUIRED_EXPLICIT_CONTROLS.
    missing_explicit = [k for k in REQUIRED_EXPLICIT_CONTROLS if k not in controls]

    # G04: kiem tham so TRUOC khi cham HTTP - quality/timeout sai, thieu gia
    # tri hieu chinh, ngoai mien, hoac aec/agc/awb bi bat lai khong duoc gui
    # len bo roi moi bi tu choi.
    # R02: --id nguoi dung tu nhap cung phai dung mau/khop framesize-quality
    # truoc HTTP, khong doi den luc ho so hoan chinh moi phat hien danh tinh sai.
    err = (
        validate_quality(args.quality)
        or validate_timeout(args.timeout)
        or ("thieu gia tri phai truyen ro qua --set (chua co so do xac minh): %s" % ", ".join(missing_explicit) if missing_explicit else "")
        or "; ".join(_locked_control_errors(controls))
        or "; ".join(validate_control_domains(controls))
        or validate_aec_value_cap(args.framesize, controls.get("aec_value"))
        or validate_wb_invariant(controls)
        or validate_camera_profile_id(profile_id, args.framesize, args.quality)
    )
    if err:
        print("Tham so khong hop le:", err)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (profile_id + ".json")
    if out_path.exists():
        print("Ho so da ton tai, khong ghi de:", out_path)
        return 2

    session = requests.Session()
    print("Ap ho so len bo tai", base)
    result = apply_and_verify(session, base, args.framesize, args.quality, controls, args.timeout)
    for var, val, ok, err in result["applied"]:
        print("  /control %-12s = %-6s %s %s" % (var, val, "OK" if ok else "LOI", err))
    if not result["ok"]:
        print("KHONG tao ho so, lech:")
        for m in result["mismatches"]:
            print("  -", m)
        return 1

    profile = build_profile_dict(args.framesize, args.quality, controls, result["expected_registers"], args.lens_note, profile_id)
    v_ok, errors = validate_profile(profile)
    if not v_ok:
        print("Ho so vua tao khong dung luoc do (loi noi bo, bao Planner):")
        for e in errors:
            print("  -", e)
        return 1

    out_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Da tao va xac minh ho so:", out_path)
    print("Thanh ghi luu lam moc:", result["expected_registers"])
    return 0


def cmd_probe(args):
    """Vong 5 (L07): dua camera ve tu dong, doc PROBE_REGISTER_KEYS nhieu
    lan, de xuat UNG VIEN aec_value/agc_gain tu trung vi. KHONG tao/danh
    dau profile - nguoi goi phai --create voi gia tri nay roi doc lai
    /status de xac minh that su. Vong 7 (L11): reset day du ve tu dong
    (PROBE_AUTO_CONTROLS, wb_mode=0 cuoi) va kiem 0x3406=0 o moi mau. Sau
    khi chay, camera CON O TRANG THAI TU DONG cho toi khi --create ap lai
    control khoa."""
    import requests

    t_err = validate_timeout(args.timeout)
    if t_err:
        print("Tham so khong hop le:", t_err)
        return 2
    if args.samples < 1:
        print("Tham so khong hop le: --samples phai >= 1, nhan %r" % (args.samples,))
        return 2
    if args.warmup < 0:
        print("Tham so khong hop le: --warmup phai >= 0, nhan %r" % (args.warmup,))
        return 2

    log = {
        "started_at": now_iso(), "host": args.host, "warmup": args.warmup,
        "samples_requested": args.samples, "samples": [], "ok": False,
        "error": None, "candidates": None, "finished_at": None,
        "auto_state": None,
    }
    log_path = None
    if args.out:
        out_dir = (REPO_ROOT / args.out).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / ("probe_%s.json" % datetime.now().strftime("%Y%m%d_%H%M%S"))

    def write_log():
        if log_path is not None:
            log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

    def fail(reason):
        log["error"] = reason
        log["finished_at"] = now_iso()
        write_log()
        print("Probe THAT BAI:", reason)
        if log_path is not None:
            print("Log (mau da nhan duoc giu nguyen):", log_path)
        return 1

    base = "http://%s" % args.host
    session = requests.Session()

    print("CANH BAO: --probe dua camera ve TU DONG hoan toan (AEC/AGC/AWB bat,")
    print("wb_mode=0 xoa preset thu cong) de camera tu chinh. Sau khi chay, camera")
    print("CON O TRANG THAI TU DONG cho toi khi --create ap lai control khoa.")

    # Vong 7 (L11): chi bat aec/agc/awb nhu truoc la chua du - neu vua tao
    # ho so preset, 0x3406=1 van giu gain thu cong. Dat du PROBE_AUTO_CONTROLS,
    # wb_mode=0 cuoi cung.
    for var, val in PROBE_AUTO_CONTROLS.items():
        ok, err = set_control(session, base, var, val, args.timeout)
        print("  /control %s=%d: %s %s" % (var, val, "OK" if ok else "LOI", err))
        if not ok:
            return fail("khong dat duoc %s=%d de ve tu dong (%s)" % (var, val, err))

    for k in range(args.warmup):
        code, _body, err = http_get(session, base + "/capture", args.timeout)
        if err or code != 200:
            return fail("lam nong lan %d/%d that bai (http=%s %s)" % (k + 1, args.warmup, code, err))

    auto_expected = dict(PROBE_AUTO_CONTROLS, **PROBE_AUTO_REGISTERS)
    for i in range(args.samples):
        st_ok, st_json, st_reason = fetch_status(session, base, args.timeout)
        if not st_ok:
            return fail("mau %d/%d khong doc duoc /status: %s" % (i + 1, args.samples, st_reason))
        # Vong 7: moi mau phai dung trang thai tu dong - khong phat ung vien
        # tu mot /status con sot preset thu cong hay control bi bo qua.
        auto_state = {key: st_json.get(key) for key in auto_expected}
        if log["auto_state"] is None:
            log["auto_state"] = auto_state
        bad = ["%s: yeu cau %s, bo bao %s" % (key, want, auto_state[key])
               for key, want in auto_expected.items() if not _values_match(want, auto_state[key])]
        if bad:
            return fail("mau %d/%d chua o trang thai tu dong: %s" % (i + 1, args.samples, "; ".join(bad)))
        missing = [key for key in PROBE_REGISTER_KEYS if key not in st_json]
        if missing:
            return fail("mau %d/%d thieu thanh ghi: %s" % (i + 1, args.samples, ", ".join(missing)))
        sample = {key: st_json[key] for key in PROBE_REGISTER_KEYS}
        log["samples"].append(sample)
        write_log()
        print("  mau %d/%d: %s" % (i + 1, args.samples, sample))
        if i + 1 < args.samples:
            time.sleep(args.interval)

    def median(vals):
        s = sorted(vals)
        return s[len(s) // 2]

    med_3500 = median(s["0x3500"] for s in log["samples"])
    med_350a = median(s["0x350a"] for s in log["samples"])
    # L08 (Vong 6): luc AEC tu dong, sensor ghi thang 0x3500, khong qua
    # set_aec_value() nen khong bi kep - ung vien tho co the vuot tran
    # thiet bi (784+). Kep ve AEC_VALUE_HARD_CAP truoc khi dua ra ung vien
    # dung duoc ngay cho --create (04_5 tan cua ke hoach Vong 6).
    aec_value_raw = round(med_3500 / 16)
    aec_value_effective = min(aec_value_raw, AEC_VALUE_HARD_CAP)
    aec_value_clamped = aec_value_effective != aec_value_raw
    agc_gain_cand = round((med_350a + 1) / 16)

    log["ok"] = True
    log["finished_at"] = now_iso()
    log["candidates"] = {
        "aec_value": aec_value_effective, "aec_value_raw": aec_value_raw,
        "aec_value_effective": aec_value_effective, "aec_value_cap": AEC_VALUE_HARD_CAP,
        "aec_value_clamped": aec_value_clamped, "median_0x3500": med_3500,
        "agc_gain": agc_gain_cand, "median_0x350a": med_350a,
    }
    write_log()

    print()
    print("UNG VIEN (CHUA XAC MINH - phai --create voi gia tri nay roi doc")
    print("lai /status; --probe khong tu tao ho so):")
    if aec_value_clamped:
        print("  aec_value =", aec_value_effective, " (DA KEP tu ung vien tho", aec_value_raw,
              "ve tran thiet bi", AEC_VALUE_HARD_CAP, "- xem L08, chi ap dung VGA/SVGA)")
    else:
        print("  aec_value =", aec_value_effective, " (trung vi 0x3500 =", med_3500, ")")
    print("  agc_gain  =", agc_gain_cand, " (trung vi 0x350a =", med_350a, ")")
    if log_path is not None:
        print("Log:", log_path)
    return 0


def cmd_verify(args):
    import requests

    base = "http://%s" % args.host
    try:
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("Khong doc duoc ho so:", e)
        return 2
    v_ok, errors = validate_profile(profile)
    if not v_ok:
        print("Ho so khong hop le:")
        for e in errors:
            print("  -", e)
        return 1

    t_err = validate_timeout(args.timeout)
    if t_err:
        print("Tham so khong hop le:", t_err)
        return 2

    session = requests.Session()
    reg_keys = tuple(profile["expected_registers"]) or DEFAULT_EXPECTED_REGISTER_KEYS
    result = apply_and_verify(session, base, profile["framesize"], profile["quality"], profile["controls"], args.timeout, reg_keys)
    for var, val, ok, err in result["applied"]:
        print("  /control %-12s = %-6s %s %s" % (var, val, "OK" if ok else "LOI", err))
    if not result["ok"]:
        print("Ap ho so THAT BAI:")
        for m in result["mismatches"]:
            print("  -", m)
        return 1

    reg_ok, reg_mismatches = compare_registers(profile["expected_registers"], result["status"], reg_keys)
    if not reg_ok:
        print("Thanh ghi lech so voi ho so da luu:")
        for m in reg_mismatches:
            print("  -", m)
        return 1

    print("Ho so khop bo:", profile["camera_profile_id"])
    return 0


def main():
    ap = argparse.ArgumentParser(description="Tao/ap/doi chieu ho so camera co dinh cho ESP32-S3 CameraWebServerTest.")
    ap.add_argument("--selftest", action="store_true", help="chay kiem tra noi bo, khong can bo")
    ap.add_argument("--create", action="store_true", help="tao ho so moi: ap control len bo roi luu neu khop")
    ap.add_argument("--verify", action="store_true", help="ap mot ho so co san len bo va doi chieu")
    ap.add_argument("--probe", action="store_true", help="bat AEC/AGC/AWB tu dong, doc nhieu mau /status, de xuat ung vien aec_value/agc_gain (Vong 5 L07) - KHONG tao ho so")
    ap.add_argument("--host", help="IP:port hoac ten may cua bo, vi du 192.168.31.9 hoac 127.0.0.1:8081")
    ap.add_argument("--framesize", choices=list(FRAMESIZES), help="dung voi --create")
    ap.add_argument("--quality", type=int, help="dung voi --create, 0-63")
    ap.add_argument("--set", action="append", metavar="VAR=VAL", help="ghi de mot control mac dinh, lap lai duoc; bon gia tri hieu chinh (aec_value/agc_gain/awb_gain/wb_mode) BAT BUOC truyen qua day, khong con mac dinh (L06)")
    ap.add_argument("--lens-note", default="ong kinh goc, tieu diem xa", help="theo D016; dung voi --create")
    ap.add_argument("--id", help="ten ho so; mac dinh cam_<framesize>_q<quality>_<ngay>, tu dong them hau to _rNN neu ten do da co tep (Vong 5 muc 3)")
    ap.add_argument("--out", help="dung voi --create: thu muc luu ho so (mac dinh data/calibration/camera_profiles); dung voi --probe: thu muc ghi log probe (bo qua thi khong ghi log)")
    ap.add_argument("--profile", help="duong dan ho so JSON, dung voi --verify")
    ap.add_argument("--timeout", type=float, default=15.0, help="timeout HTTP, giay (mac dinh 15)")
    ap.add_argument("--samples", type=int, default=5, help="dung voi --probe, so mau /status (mac dinh 5)")
    ap.add_argument("--interval", type=float, default=0.5, help="dung voi --probe, giay giua hai mau (mac dinh 0.5)")
    ap.add_argument("--warmup", type=int, default=2, help="dung voi --probe, so khung /capture bo qua truoc khi doc mau (mac dinh 2)")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.create:
        if not args.host or not args.framesize or args.quality is None:
            ap.error("--create can --host, --framesize va --quality")
        return cmd_create(args)
    if args.verify:
        if not args.host or not args.profile:
            ap.error("--verify can --host va --profile")
        return cmd_verify(args)
    if args.probe:
        if not args.host:
            ap.error("--probe can --host")
        return cmd_probe(args)
    ap.error("can mot trong --selftest, --create, --verify, --probe")


if __name__ == "__main__":
    sys.exit(main())
