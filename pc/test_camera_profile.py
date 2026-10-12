#!/usr/bin/env python3
"""
test_camera_profile.py - bo kiem doc lap cua Tester cho C2/C2b
(handoff/2026-09-21_c2-camera-profile), kiem pc/camera_profile.py va
pc/capture_session.py --profile qua HTTP that voi pc/mock_camera.py.

Khac voi e2e_capture_mock.py cua Coder: moi kich ban chay MOT tien trinh
mock_camera.py rieng (trang thai control/thanh ghi khong ro tu kich ban
truoc sang kich ban sau) va goi dung CLI that (subprocess), khong goi ham
trong tien trinh. Ba kich ban thiet bi (server cham, dao control giua
phien, ngat cap) dung server nhung trong tien trinh voi handler ke thua
mock_camera.H, khong sua mock_camera.py.

Chay tu goc repo, khong can bo:
  .venv/Scripts/python.exe pc/test_camera_profile.py
  .venv/Scripts/python.exe pc/test_camera_profile.py --only T3g,T4b   # chay mot so kich ban

Ma thoat 0 khi moi kich ban PASS; 1 khi co FAIL. Moi dong in ra la mot
kiem tra con; cuoi cung in bang tong hop theo ma kich ban (T1a..TX5, V3a..V3h).

Lich su:
- Vong 1 (21/09, kiem 6110dbd): 30 kich ban T1a..TX5; TX1/TX2 chi GHI NHAN
  hanh vi (control troi cuoi phien / thanh ghi ho so khac bo -> phien PASS).
- Vong 2 (21/09, kiem commit B 19c2145 theo 01_PLAN.md Vong 3): giu 30 kich
  ban cu; doi ky vong co chu dich theo ke hoach Vong 3: TX1 va TX2 nay PHAI
  FAIL (V3-T3/V3-T4); T2b/T2g/T4c: tham so sai bi chan TRUOC HTTP (rc 2,
  0 request) va /control loi thi dung ngay; T1b: status/schema/requested/
  stream_disabled theo hop dong Q4 moi. Them V3a..V3h bam bang V3-T1..T8.
  Ky vong cu duoc ghi trong chu thich ngay tai cho doi.
- Vong 3 (22/09, kiem commit B 0139dc6 theo 01_PLAN.md Vong 4): R02 buoc
  moi ho so phai co camera_profile_id dung mau cam_<framesize>_q<quality>_
  <YYYYMMDD> khop framesize/quality that, board/sensor dung thiet bi C2,
  created_at ISO8601 co mui gio, source.commit 40 hex. Moi --id tuy tien
  trong cac kich ban cu (q1, dup, ok, bad, v, slow, refused...) doi sang
  ID dung mau; T2g doi ky vong: --id co khoang trang nay BI TU CHOI thay
  vi duoc chap nhan (hop dong ID cua thiet ke thang, khong im lang noi
  test). Them V3i bam buoc 3.3 ke hoach Vong 4 (sau probe R02 cua
  Reviewer, tung truong verified, ID doc duong dan, 0 HTTP).
- Vong 4 (23/09, kiem commit B 925693c theo 01_PLAN.md Phu luc Vong 5):
  hop dong --create doi co chu dich - DEFAULT_CONTROLS BO bon gia tri
  hieu chinh (aec_value/agc_gain/awb_gain/wb_mode), nguoi goi phai truyen
  ro qua --set (REQUIRED_EXPLICIT_CONTROLS, L06); DEFAULT_CONTROLS lay
  vflip=1/brightness=1/saturation=-2 theo firmware OV3660 (L05);
  DEFAULT_EXPECTED_REGISTER_KEYS tu 4 len 7 khoa (L07); --create tu chon
  hau to _rNN khi ID goc da co tep. Moi kich ban cu goi create() nay dung
  FULL_CONTROLS/EXPLICIT_SET; them V5a..V5e bam bang V5-T1..T7.
- Vong 5 (24/09, B b974697): them V6a (tran aec_value 783, L08) va V6b
  (bat bien wb_mode/awb_gain, L10).
- Vong 6 (24/09, B 7cb659e theo 01_PLAN.md Vong 7, L11): hop dong WB DAO
  CHIEU co chu dich. Ho so co dinh nay la aec=0, agc=0, awb=1, awb_gain=1,
  wb_mode 1..4, va expected_registers phai co 0x3406=1 cung ba gain dung
  bang preset. Ly do (03_TEST.md Vong 6, L11): awb=0 tat khoi ap gain nen
  bon preset cho cung mot mau anh. Moi ky vong cu coi "awb=1 la sai/la
  drift" doi thanh "awb=0 la sai/la drift"; fixture EXPLICIT_VALUES doi
  sang awb_gain=1/wb_mode=1; ho so hop le dung GOOD_REGS (thanh ghi sau
  khi ap preset 1) thay mc.DEFAULT_REGISTERS (nay 0x3406=0 = che do tu
  dong). Them V7a..V7e bam V7-T1..T6.
Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_profile as cp  # noqa: E402
import mock_camera as mc  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
CP = str(REPO_ROOT / "pc" / "camera_profile.py")
CS = str(REPO_ROOT / "pc" / "capture_session.py")
MOCK = str(REPO_ROOT / "pc" / "mock_camera.py")
LF = chr(10)

RESULTS = []  # (ma, ten, PASS|FAIL, ghi chu)
_CUR = {"id": "", "name": "", "fails": [], "notes": []}


# ----------------------------------------------------------------------
# Khung
# ----------------------------------------------------------------------

def begin(tid, name):
    _CUR.update({"id": tid, "name": name, "fails": [], "notes": []})
    print("---- %s %s" % (tid, name))


def check(cond, label, actual=""):
    flag = "OK  " if cond else "FAIL"
    line = "  [%s] %s" % (flag, label)
    if actual != "":
        line += "  | thuc te: %s" % (actual,)
    print(line)
    if not cond:
        _CUR["fails"].append(label + ((" | " + str(actual)) if actual != "" else ""))


def note(text):
    print("  (ghi nhan) " + text)
    _CUR["notes"].append(text)


def end():
    status = "PASS" if not _CUR["fails"] else "FAIL"
    RESULTS.append((_CUR["id"], _CUR["name"], status, "; ".join(_CUR["fails"]) or "; ".join(_CUR["notes"])))
    print("==== %s %s" % (_CUR["id"], status))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def wait_http(port, timeout=10.0):
    import requests
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            requests.get("http://127.0.0.1:%d/_counts" % port, timeout=1)  # khong lam tang dem status
            return True
        except Exception:
            time.sleep(0.1)
    return False


class Mock:
    """mock_camera.py trong tien trinh rieng; trang thai moi cho moi kich ban."""

    def __init__(self, *extra):
        self.port = free_port()
        self.proc = subprocess.Popen(
            [PY, MOCK, "--port", str(self.port)] + list(extra),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if not wait_http(self.port):
            raise RuntimeError("mock khong len o cong %d" % self.port)

    @property
    def host(self):
        return "127.0.0.1:%d" % self.port

    def kill(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kill()


class QuietServer(HTTPServer):
    """Khong in traceback khi client ngat/timeout giua chung (test co y gay ra)."""

    def handle_error(self, request, client_address):
        pass


class InProcMock:
    """mock_camera trong tien trinh, cho phep thay handler; reset STATE day du."""

    def __init__(self, handler=None, **state):
        mc.STATE.update({
            "framesize": 6, "quality": 10, "frame": 0, "t0": time.time(), "reset_at": 0,
            "fail_frames": set(), "drop_ts_frames": set(), "lowercase_headers": False,
            "status_mode": "ok", "status_fail_after": 0,
            "controls": dict(mc.DEFAULT_CONTROLS), "registers": dict(mc.DEFAULT_REGISTERS),
            "ignore_controls": set(), "fail_controls": set(),
            "drift_registers": set(), "drift_after": 0, "status_drop_fields": set(),
        })
        for k in [k for k in mc.STATE if k.startswith("_")]:
            del mc.STATE[k]  # khoa rieng cua handler test (vd _slow_at) khong ro sang kich ban sau
        mc.STATE.update(state)
        mc.STATE["counts"] = {"control": 0, "capture": 0, "status": 0}
        self.srv = QuietServer(("127.0.0.1", 0), handler or mc.H)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.th.start()

    @property
    def host(self):
        return "127.0.0.1:%d" % self.port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()


def run_cli(script, *args, timeout=120):
    r = subprocess.run([PY, script] + [str(a) for a in args], cwd=REPO_ROOT,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def create(mock_host, out_dir, framesize, quality, *extra, explicit=True):
    """Vong 4: --create bat buoc bon gia tri hieu chinh. Mac dinh helper tu
    them chung; kich ban nao muon kiem chinh viec THIEU thi truyen
    explicit=False, hoac tu dat lai bang --set trong extra."""
    args = list(extra)
    if explicit:
        already = {a.split("=")[0] for a in args if "=" in a}
        args += [x for k, v in EXPLICIT_VALUES.items() if k not in already
                 for x in ("--set", "%s=%d" % (k, v))]
    return run_cli(CP, "--create", "--host", mock_host, "--framesize", framesize,
                   "--quality", quality, "--out", out_dir, *args)


def capture(mock_host, out_root, sid, profile, count=5, *extra):
    return run_cli(CS, "--host", mock_host, "--profile", profile, "--count", count,
                   "--interval", "0", "--warmup", "0", "--out", out_root, "--session-id", sid, *extra)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# Vong 4 (L06): DEFAULT_CONTROLS khong con du 14 khoa. Bo test dung ban day
# du cho cac ca "ho so hop le", va truyen dung bon gia tri do qua --set cho
# moi lenh --create - giong cach nguoi dung that phai lam sau --probe.
# Vong 6 (L11): awb_gain=1 va wb_mode trong 1..4 - hop dong ho so co dinh moi.
EXPLICIT_VALUES = {"aec_value": 490, "agc_gain": 2, "awb_gain": 1, "wb_mode": 1}
FULL_CONTROLS = dict(cp.DEFAULT_CONTROLS, **EXPLICIT_VALUES)
# Thanh ghi mock SAU KHI ap preset wb_mode=1: bay khoa mac dinh, ba gain mau
# va 0x3406=1 lay tu bang preset. Ho so hop le phai dung bo nay (Vong 6, L11).
GOOD_REGS = dict(mc.DEFAULT_REGISTERS, **cp.WB_MODE_REGISTERS[1])
EXPLICIT_SET = [x for k, v in EXPLICIT_VALUES.items() for x in ("--set", "%s=%d" % (k, v))]


def pid(framesize="VGA", quality=10, day="20260922"):
    """ID dung mau SCAN_SESSION muc 5 (R02, Vong 3 cua Tester): moi --id
    trong bo test phai khop framesize/quality that cua lenh."""
    return "cam_%s_q%d_%s" % (framesize, quality, day)


def counts(mock_host):
    """/_counts cua mock (Vong 3): so request theo loai."""
    import requests
    return requests.get("http://%s/_counts" % mock_host, timeout=5).json()


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jpeg_size(p):
    from PIL import Image
    with Image.open(p) as im:
        return im.size


def one_profile_file(out_dir):
    files = sorted(Path(out_dir).glob("*.json"))
    return str(files[0]) if len(files) == 1 else None


def img_files(sdir):
    return sorted(p.name for p in Path(sdir).glob("img_*"))


TMP = Path(tempfile.mkdtemp(prefix="tester_c2_"))


def tmpdir(name):
    d = TMP / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------------------------------------------------
# T1 binh thuong
# ----------------------------------------------------------------------

def t1a():
    begin("T1a", "camera_profile --create tren mock: rc 0, tep dung luoc do, thanh ghi = mock")
    with Mock() as m:
        out = tmpdir("t1a")
        rc, txt = create(m.host, out, "VGA", 10)
        check(rc == 0, "rc = 0", rc)
        check(txt.count(" OK") >= 16, "stdout co >= 16 dong '/control ... OK' (framesize, quality, 14 control)", txt.count(" OK"))
        pf = one_profile_file(out)
        check(pf is not None, "dung mot tep .json duoc ghi", sorted(os.listdir(out)))
        if pf:
            p = read_json(pf)
            ok, errs = cp.validate_profile(p)
            check(ok, "validate_profile(tep vua tao) hop le", errs)
            check(p["framesize"] == "VGA" and p["quality"] == 10, "framesize/quality dung", (p["framesize"], p["quality"]))
            check(p["controls"] == FULL_CONTROLS, "controls = DEFAULT_CONTROLS + bon gia tri --set", p["controls"])
            # Vong 6 (L11): thanh ghi sau khi ap = bay khoa mac dinh + bon thanh ghi WB cua preset 1
            check(p["expected_registers"] == GOOD_REGS and len(p["expected_registers"]) == 7,
                  "expected_registers = 7 thanh ghi, ba gain + 0x3406=1 dung bang preset 1 (L11)", p["expected_registers"])
            check(p["controls"]["vflip"] == 1 and p["controls"]["brightness"] == 1 and p["controls"]["saturation"] == -2,
                  "L05: vflip=1, brightness=1, saturation=-2 theo firmware OV3660", {k: p["controls"][k] for k in ("vflip", "brightness", "saturation")})
            check(p["verified"] is None, "verified = null", p["verified"])
            check(p["camera_profile_id"] == Path(pf).stem and p["camera_profile_id"].startswith("cam_VGA_q10_"), "ID = ten tep, dung dinh dang", p["camera_profile_id"])
            check(len(p["source"].get("commit", "")) == 40, "source.commit 40 ky tu", p["source"])
            check("sharpness" not in p["controls"], "khong co sharpness trong controls")
        # mock da thuc su bi khoa?
        import requests
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        # Vong 6 (L11): awb=1 (khoi xu ly mau bat), aec/agc van 0
        check(st["aec"] == 0 and st["agc"] == 0 and st["awb"] == 1 and st["aec_value"] == 490 and st["framesize"] == 10 and st["quality"] == 10,
              "/status mock sau --create: aec/agc=0, awb=1 (L11), aec_value=490, framesize 10, quality 10",
              {k: st.get(k) for k in ("aec", "agc", "awb", "aec_value", "framesize", "quality")})
        check(st.get("0x3406") == 1 and st.get("wb_mode") == 1 and st.get("awb_gain") == 1,
              "/status mock sau --create: 0x3406=1 (WB thu cong), wb_mode=1, awb_gain=1 (L11)",
              {k: st.get(k) for k in ("0x3406", "wb_mode", "awb_gain")})
        check(st["vflip"] == 1 and st["brightness"] == 1 and st["saturation"] == -2,
              "/status mock sau --create: vflip=1, brightness=1, saturation=-2 (L05)",
              {k: st.get(k) for k in ("vflip", "brightness", "saturation")})
    end()
    return pf


def t1b(pf):
    begin("T1b", "capture_session --profile 5 anh: rc 0, session.json schema 2, ID/config/status, anh 640x480")
    with Mock() as m:
        root = tmpdir("t1b")
        rc, txt = capture(m.host, root, "s1", pf, 5)
        check(rc == 0, "rc = 0", rc)
        sd = root / "s1"
        sess = read_json(sd / "session.json")
        r = sess["result"]
        check(r["verdict"] == "PASS" and r["reason"] == "", "verdict PASS, reason rong", r.get("reason"))
        check(sess.get("schema_version") == 2, "schema_version = 2", sess.get("schema_version"))
        p = read_json(pf)
        check(sess.get("camera_profile_id") == p["camera_profile_id"], "camera_profile_id = ID ho so", sess.get("camera_profile_id"))
        cfg = sess.get("camera_config") or {}
        # Vong 1: stream_disabled True cung; Vong 3: null + stream_disabled_reason (SCAN_SESSION muc 3 moi)
        check(cfg.get("framesize") == "VGA" and cfg.get("quality") == 10 and cfg.get("lens_note") == p["lens_note"],
              "camera_config framesize/quality/lens_note dung", cfg)
        check("stream_disabled" in cfg and cfg["stream_disabled"] is None and isinstance(cfg.get("stream_disabled_reason"), str) and cfg["stream_disabled_reason"],
              "camera_config.stream_disabled = null kem stream_disabled_reason (Vong 3, khong tu ghi true)", (cfg.get("stream_disabled"), cfg.get("stream_disabled_reason")))
        check(sess.get("status") == "completed", "status = completed (Vong 3, SCAN_SESSION muc 3)", sess.get("status"))
        check(sess["requested"].get("framesize") == "VGA" and sess["requested"].get("quality") == 10,
              "requested.framesize/quality lay tu ho so (Vong 3, G01)", (sess["requested"].get("framesize"), sess["requested"].get("quality")))
        check(sess["expected_size"] == [640, 480], "expected_size [640, 480]", sess["expected_size"])
        for k in ("camera_status_start", "camera_status_after_set", "camera_status_end"):
            check(sess[k] and sess[k]["ok"], "%s ok" % k, (sess[k] or {}).get("reason"))
        st2 = read_json(sd / "status_after_set.json")
        check(st2["framesize"] == 10 and st2["quality"] == 10 and st2["aec"] == 0, "status_after_set.json la JSON co framesize 10, quality 10, aec 0",
              {k: st2.get(k) for k in ("framesize", "quality", "aec")})
        st3 = read_json(sd / "status_end.json")
        check(all(st3[k] == p["expected_registers"][k] for k in p["expected_registers"]), "status_end thanh ghi = expected_registers", {k: st3.get(k) for k in p["expected_registers"]})
        imgs = img_files(sd)
        check(imgs == ["img_%04d.jpg" % i for i in range(1, 6)], "dung 5 tep img_0001..0005.jpg", imgs)
        sizes = {jpeg_size(sd / f) for f in imgs}
        check(sizes == {(640, 480)}, "moi anh giai ma 640x480", sizes)
        check(r["frames_ok"] == 5 and r["reset_check"]["sufficient"], "frames_ok 5, reset_check du", (r["frames_ok"], r["reset_check"]))
        lines = (sd / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
        check(len(lines) == 5 and all(json.loads(x)["accepted"] for x in lines), "attempts.jsonl 5 dong, accepted", len(lines))
        note("truong C5 dang object/mang trong session.json (phai rong): %s" % [k for k in ("motion", "laser", "angle_table", "counts", "protocol_version", "sample") if k in sess and not isinstance(sess[k], str)])
    end()


def t1c(pf):
    begin("T1c", "khong sua anh cu: chay lai cung session-id bi tu choi, sha anh cu giu nguyen")
    with Mock() as m:
        root = tmpdir("t1c")
        rc, _ = capture(m.host, root, "s1", pf, 3)
        check(rc == 0, "phien dau rc 0", rc)
        sd = root / "s1"
        before = {f: sha(sd / f) for f in os.listdir(sd)}
        rc2, txt2 = capture(m.host, root, "s1", pf, 3)
        check(rc2 == 2, "phien hai cung ID rc 2", rc2)
        check("khong ghi de" in txt2, "thong bao 'khong ghi de'", txt2.strip().splitlines()[-1:] )
        after = {f: sha(sd / f) for f in os.listdir(sd)}
        check(before == after, "moi tep phien dau (anh, session.json, csv, jsonl) sha khong doi")
        rc3, _ = capture(m.host, root, "s2", pf, 2)
        after2 = {f: sha(sd / f) for f in os.listdir(sd)}
        check(rc3 == 0 and before == after2, "phien s2 rc 0 va khong cham phien s1", rc3)
    end()


# ----------------------------------------------------------------------
# T2 bien
# ----------------------------------------------------------------------

def t2a():
    begin("T2a", "ma tran VGA/SVGA x q10/q20: 4 ID khac nhau, moi ho so 5 anh dung kich thuoc va quality")
    out = tmpdir("t2a_profiles")
    root = tmpdir("t2a_sessions")
    ids = {}
    for fs in ("VGA", "SVGA"):
        for q in (10, 20):
            with Mock() as m:
                rc, txt = create(m.host, out, fs, q)
                check(rc == 0, "--create %s q%d rc 0" % (fs, q), rc)
    files = sorted(out.glob("*.json"))
    check(len(files) == 4, "4 tep ho so", [f.name for f in files])
    for f in files:
        p = read_json(f)
        ids[p["camera_profile_id"]] = (p["framesize"], p["quality"])
    check(len(ids) == 4 and set(ids.values()) == {("VGA", 10), ("VGA", 20), ("SVGA", 10), ("SVGA", 20)},
          "4 ID khac nhau, (framesize, quality) khong lan", ids)
    want_wh = {"VGA": (640, 480), "SVGA": (800, 600)}
    for f in files:
        p = read_json(f)
        with Mock() as m:
            sid = "s_" + p["camera_profile_id"]
            rc, txt = capture(m.host, root, sid, str(f), 5)
            sd = root / sid
            sess = read_json(sd / "session.json")
            imgs = img_files(sd)
            sizes = {jpeg_size(sd / x) for x in imgs}
            st_end = read_json(sd / "status_end.json")
            check(rc == 0 and len(imgs) == 5 and sizes == {want_wh[p["framesize"]]},
                  "%s: rc 0, 5 anh, kich thuoc %s" % (p["camera_profile_id"], want_wh[p["framesize"]]), (rc, len(imgs), sizes))
            check(st_end["quality"] == p["quality"] and st_end["framesize"] == cp.FRAMESIZES[p["framesize"]],
                  "%s: /status cuoi quality %d, framesize %d" % (p["camera_profile_id"], p["quality"], cp.FRAMESIZES[p["framesize"]]),
                  (st_end["quality"], st_end["framesize"]))
            check(sess["camera_config"]["framesize"] == p["framesize"] and sess["camera_config"]["quality"] == p["quality"]
                  and sess["camera_profile_id"] == p["camera_profile_id"], "%s: session.json camera_config/ID khop" % p["camera_profile_id"])
    note("mock sinh JPEG khong theo quality; 'quality' chi kiem duoc qua /status va ho so, khong qua byte anh (can bo)")
    end()


def t2b():
    begin("T2b", "bien quality: 0 va 63 hop le, -1 va 64 bi tu choi (validate va --create)")
    for q, want in ((0, True), (63, True), (-1, False), (64, False)):
        # Vong 3 (R02): ID phai khop quality that, nen dung build_profile_dict cho tung q
        p = cp.build_profile_dict("VGA", q, FULL_CONTROLS, dict(GOOD_REGS), "x")
        ok, errs = cp.validate_profile(p)
        check(ok == want, "validate_profile quality=%d -> %s" % (q, "hop le" if want else "loi"), errs)
    out = tmpdir("t2b")
    # Vong 1: q64/q-1 rc 1 sau khi da gui len bo; Vong 3 (G04): rc 2 TRUOC HTTP, 0 request
    for q, want_rc in ((0, 0), (63, 0), (64, 2), (-1, 2)):
        with Mock() as m:
            # Vong 3 (R02): --id phai dung mau va khop framesize/quality cua chinh lenh
            # q am khong the co ID khop mau (\d+); dung ID hop le KHAC cac tep da ghi de
            # thong diep loi den tu quality (cmd_create kiem quality truoc ID), khong dung tep cu
            qid = pid("QVGA", q) if q >= 0 else "cam_QVGA_q1_20260922"
            rc, txt = create(m.host, out, "QVGA", q, "--id", qid)
            check(rc == want_rc, "--create quality %d rc %d" % (q, want_rc), (rc, txt.strip().splitlines()[-1:]))
            check((out / (qid + ".json")).exists() == (want_rc == 0), "tep ho so %s (%s)" % ("duoc ghi" if want_rc == 0 else "KHONG duoc ghi", qid))
            if want_rc == 2:
                c = counts(m.host)
                check(c == {"control": 0, "capture": 0, "status": 0}, "quality %d: 0 HTTP request toi bo (Vong 3)" % q, c)
    end()


def t2c():
    begin("T2c", "--create hai lan cung ID: lan hai rc 2, tep cu sha khong doi")
    out = tmpdir("t2c")
    with Mock() as m:
        # Vong 3 (R02): ID phai khop framesize/quality, nen lan 2 dung cung VGA q10 de trung ID
        dup = pid("VGA", 10)
        rc, _ = create(m.host, out, "VGA", 10, "--id", dup)
        check(rc == 0, "lan 1 rc 0", rc)
        h1 = sha(out / (dup + ".json"))
        rc2, txt = create(m.host, out, "VGA", 10, "--id", dup, "--set", "brightness=1")
        check(rc2 == 2 and "da ton tai" in txt, "lan 2 rc 2, bao 'da ton tai'", (rc2, txt.strip().splitlines()[-1:]))
        check(sha(out / (dup + ".json")) == h1, "tep cu khong doi")
    end()


def t2d():
    begin("T2d", "--set: ghi de hop le; sharpness / gia tri khong so / thieu '=' bi chan truoc khi cham bo")
    out = tmpdir("t2d")
    with Mock() as m:
        ok_id = pid("VGA", 10)
        rc, _ = create(m.host, out, "VGA", 10, "--id", ok_id, "--set", "awb_gain=1", "--set", "wb_mode=1")  # hai cai con lai helper tu them
        p = read_json(out / (ok_id + ".json")) if (out / (ok_id + ".json")).exists() else {}
        check(rc == 0 and p.get("controls", {}).get("awb_gain") == 1 and p.get("controls", {}).get("wb_mode") == 1,
              "--set awb_gain=1 wb_mode=1 -> ho so ghi 1/1", (rc, p.get("controls")))
        import requests
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        check(st["awb_gain"] == 1 and st["wb_mode"] == 1, "mock nhan awb_gain=1, wb_mode=1", (st["awb_gain"], st["wb_mode"]))
    for spec, label in (("sharpness=1", "sharpness (firmware khong ho tro)"), ("awb=x", "gia tri khong phai so"), ("awb", "thieu '='"), ("aec=true", "gia tri bool"),
                        ("aec=1", "aec=1 (aec/agc bat buoc 0)"), ("awb=0", "awb=0 (Vong 6 L11: awb bat buoc 1)")):
        with Mock() as m:
            bad_id = pid("SVGA", 20)  # ID hop le nhung khac ok_id: loi phai den tu --set, khong phai ID
            rc, txt = create(m.host, out, "SVGA", 20, "--id", bad_id, "--set", spec)
            check(rc == 2 and not (out / (bad_id + ".json")).exists(), "--set %s -> rc 2, khong ghi tep" % label, (rc, txt.strip().splitlines()[-1:]))
            c = counts(m.host)
            check(c["control"] == 0, "--set %s: 0 /control toi bo" % label, c)
    end()


def t2e(pf):
    begin("T2e", "--count 1 voi --profile: PASS, 1 anh, reset_check du (0 phep so)")
    with Mock() as m:
        root = tmpdir("t2e")
        rc, _ = capture(m.host, root, "s1", pf, 1)
        sess = read_json(root / "s1" / "session.json")
        check(rc == 0 and sess["result"]["verdict"] == "PASS", "rc 0 PASS", (rc, sess["result"]["reason"]))
        check(img_files(root / "s1") == ["img_0001.jpg"], "dung 1 anh", img_files(root / "s1"))
        check(sess["result"]["reset_check"]["sufficient"], "reset_check.sufficient True", sess["result"]["reset_check"])
    end()


def t2f():
    begin("T2f", "ho so co them thanh ghi 0x5580 ma /status mock khong co -> FAIL neu ro thieu 0x5580")
    pfile = tmpdir("t2f") / "extra.json"
    regs = dict(GOOD_REGS, **{"0x5580": 6})  # khoa bo sung mock KHONG tra trong expected (0x3406 nay da la khoa mac dinh)
    pfile.write_text(json.dumps(cp.build_profile_dict("VGA", 10, FULL_CONTROLS, regs, "x")), encoding="utf-8")
    with Mock() as m:
        root = tmpdir("t2f_s")
        rc, txt = capture(m.host, root, "s1", str(pfile), 2)
        sess = read_json(root / "s1" / "session.json")
        check(rc == 1 and "thieu thanh ghi 0x5580" in sess["result"]["reason"], "capture rc 1, reason 'thieu thanh ghi 0x5580'", (rc, sess["result"]["reason"]))
        check(img_files(root / "s1") == [], "khong chup anh nao", img_files(root / "s1"))
        rc2, txt2 = run_cli(CP, "--verify", "--host", m.host, "--profile", str(pfile))
        check(rc2 == 1 and "0x5580" in txt2, "--verify rc 1, neu 0x5580", (rc2, [l for l in txt2.splitlines() if "0x5580" in l]))
    end()


def t2g():
    begin("T2g", "--timeout 0 bi chan truoc HTTP; --id khong dung mau (co khoang trang) bi tu choi, --id dung mau qua")
    out = tmpdir("t2g")
    with Mock() as m:
        rc, txt = create(m.host, out, "VGA", 10, "--id", pid("VGA", 10), "--timeout", "0")
        # Vong 1: rc 1 (ValueError bat nhu loi ket noi); Vong 2 (G04): rc 2 truoc HTTP
        check(rc == 2 and not (out / (pid("VGA", 10) + ".json")).exists() and "timeout" in txt, "--timeout 0 -> rc 2 'timeout', khong ghi tep", (rc, txt.strip().splitlines()[-1:]))
        check(counts(m.host)["control"] == 0, "--timeout 0: 0 /control toi bo", counts(m.host))
        # Vong 1/2 chap nhan ID tuy y ("my custom id"); Vong 3 (R02) hop dong ID cua
        # SCAN_SESSION muc 5 thang: ID co khoang trang bi tu choi TRUOC HTTP.
        rc, txt = create(m.host, out, "VGA", 10, "--id", "my custom id")
        check(rc == 2 and "camera_profile_id" in txt and list(out.glob("*.json")) == [], "--id 'my custom id' -> rc 2, neu camera_profile_id, khong ghi tep (R02)", (rc, txt.strip().splitlines()[-1:]))
        check(counts(m.host)["control"] == 0, "--id sai mau: 0 /control toi bo", counts(m.host))
        rc, txt = create(m.host, out, "VGA", 10, "--id", pid("VGA", 10))
        p = one_profile_file(out)
        check(rc == 0 and p and Path(p).name == pid("VGA", 10) + ".json" and read_json(p)["camera_profile_id"] == pid("VGA", 10),
              "--id dung mau -> tep va ID dung ten", (rc, p))
    end()


# ----------------------------------------------------------------------
# T3 loi dau vao
# ----------------------------------------------------------------------

def t3a_c():
    begin("T3a-c", "ho so la JSON list / khong phai JSON / duong dan khong ton tai -> capture_session FAIL, khong chup")
    d = tmpdir("t3")
    (d / "list.json").write_text("[1, 2]", encoding="utf-8")
    (d / "garbage.json").write_text("{ khong phai json", encoding="utf-8")
    (d / "empty.json").write_text("", encoding="utf-8")
    cases = (
        ("list.json", "ho so camera khong hop le: ho so khong phai object"),
        ("garbage.json", "khong doc duoc ho so camera"),
        ("empty.json", "khong doc duoc ho so camera"),
        ("khong_co.json", "khong doc duoc ho so camera"),
    )
    with Mock() as m:
        root = tmpdir("t3_s")
        for i, (fn, want) in enumerate(cases):
            sid = "s%d" % i
            rc, txt = capture(m.host, root, sid, str(d / fn), 2)
            sess = read_json(root / sid / "session.json")
            check(rc == 1 and sess["result"]["verdict"] == "FAIL" and want in sess["result"]["reason"],
                  "%s: rc 1, FAIL, reason bat dau '%s'" % (fn, want), (rc, sess["result"]["reason"][:90]))
            check(img_files(root / sid) == [], "%s: khong chup anh" % fn)
        # cung cac tep voi --verify
        for fn, want_rc in (("list.json", 1), ("garbage.json", 2), ("khong_co.json", 2)):
            rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / fn))
            check(rc == want_rc, "--verify %s rc %d" % (fn, want_rc), (rc, txt.strip().splitlines()[:1]))
    end()


def t3d(pf):
    begin("T3d", "/control tra 500 (aec_value): --create rc 1 khong ghi tep; capture FAIL, 0 anh, reason neu aec_value")
    out = tmpdir("t3d")
    with Mock("--fail-controls", "aec_value") as m:
        rc, txt = create(m.host, out, "VGA", 10)
        check(rc == 1 and "/control that bai: aec_value (http 500)" in txt, "--create rc 1, neu 'aec_value (http 500)'", (rc, [l for l in txt.splitlines() if "that bai" in l]))
        check(list(out.glob("*.json")) == [], "khong ghi tep ho so")
        check("aec_value" in txt and " LOI " in txt, "stdout co dong '/control aec_value ... LOI'", [l for l in txt.splitlines() if "LOI" in l][:2])
        c = counts(m.host)
        check(c["control"] == 6, "--create dung ngay: 6 /control (framesize, quality, aec, agc, awb, aec_value), khong gui 10 lenh sau (Vong 3 G04)", c)
        root = tmpdir("t3d_s")
        rc, txt = capture(m.host, root, "s1", pf, 3)
        sess = read_json(root / "s1" / "session.json")
        check(rc == 1 and "ap ho so camera khong khop: /control that bai: aec_value (http 500)" in sess["result"]["reason"],
              "capture rc 1, reason dung", (rc, sess["result"]["reason"]))
        check(img_files(root / "s1") == [], "0 anh")
        check(sess["camera_status_after_set"]["ok"] is False and "aec_value" in sess["camera_status_after_set"]["reason"],
              "camera_status_after_set ok=False, giu ly do", sess["camera_status_after_set"])
    end()


def t3e():
    begin("T3e", "/status sau khi ap khong doc duoc (khong JSON / list / 503): --create rc 1 neu ly do, khong ghi tep")
    out = tmpdir("t3e")
    for mode, want in (("invalid", "khong phai JSON"), ("list", "JSON khong phai object"), ("http503", "http 503")):
        with Mock("--status-mode", mode) as m:
            mid = pid("VGA", 10)
            rc, txt = create(m.host, out, "VGA", 10, "--id", mid)
            check(rc == 1 and ("khong doc duoc /status sau khi ap: " + want) in txt, "--status-mode %s: rc 1, '%s'" % (mode, want), (rc, [l for l in txt.splitlines() if "/status" in l]))
            check(not (out / (mid + ".json")).exists(), "khong ghi tep")
    end()


def t3f(pf):
    begin("T3f", "/control OK nhung khong ap (ignore aec,agc): --create va capture deu FAIL, neu dung bien")
    out = tmpdir("t3f")
    # Vong 6 (L11): ho so yeu cau awb=1 = gia tri mac dinh mock, nen "bo qua awb" khong con
    # tao ra lech; doi sang aec,agc (ho so yeu cau 0, mock mac dinh 1).
    with Mock("--ignore-controls", "aec,agc") as m:
        rc, txt = create(m.host, out, "VGA", 10)
        check(rc == 1 and "aec: yeu cau 0, bo bao 1" in txt and "agc: yeu cau 0, bo bao 1" in txt, "--create rc 1, neu aec va agc", (rc, [l for l in txt.splitlines() if "yeu cau" in l]))
        check(list(out.glob("*.json")) == [], "khong ghi tep")
        root = tmpdir("t3f_s")
        rc, txt = capture(m.host, root, "s1", pf, 3)
        sess = read_json(root / "s1" / "session.json")
        check(rc == 1 and "aec: yeu cau 0, bo bao 1" in sess["result"]["reason"], "capture rc 1, reason neu aec", (rc, sess["result"]["reason"]))
        check(img_files(root / "s1") == [], "0 anh")
    with Mock("--ignore-controls", "quality") as m:
        rc, txt = create(m.host, out, "VGA", 20, "--id", pid("VGA", 20))
        check(rc == 1 and "quality: yeu cau 20, bo bao 10" in txt, "ignore quality: rc 1, neu quality", (rc, [l for l in txt.splitlines() if "quality:" in l]))
    with Mock("--ignore-controls", "framesize") as m:
        rc, txt = create(m.host, out, "VGA", 10, "--id", pid("VGA", 10))
        check(rc == 1 and "framesize: yeu cau 10, bo bao 6" in txt, "ignore framesize: rc 1, neu framesize", (rc, [l for l in txt.splitlines() if "framesize:" in l]))
    end()


def t3g(pf):
    begin("T3g", "thanh ghi troi giua phien: FAIL neu dung thanh ghi va gia tri; anh da chup giu nguyen")
    root = tmpdir("t3g")
    with Mock("--drift-registers", "0x3400,0x3404", "--drift-after", "3") as m:
        rc, txt = capture(m.host, root, "s1", pf, 5)
        sess = read_json(root / "s1" / "session.json")
        r = sess["result"]
        check(rc == 1 and r["verdict"] == "FAIL", "rc 1 FAIL", (rc, r["verdict"]))
        # Vong 6 (L11): 0x3400/0x3404 sau ap preset 1 la gia tri bang (1504/1344), khong con mac dinh mock 1362/1697
        check("thanh ghi ho so camera lech trong phien: 0x3400: dau 1504, cuoi 1511; 0x3404: dau 1344, cuoi 1351" in r["reason"], "reason neu 0x3400 va 0x3404 kem gia tri dau/cuoi", r["reason"])
        check(len(img_files(root / "s1")) == 5 and r["frames_ok"] == 5, "5 anh van duoc chup va giu", (len(img_files(root / "s1")), r["frames_ok"]))
        check(sess["camera_status_end"]["json"]["0x3400"] == 1511, "status_end ghi gia tri troi", sess["camera_status_end"]["json"].get("0x3400"))
    with Mock("--drift-registers", "0x350a", "--drift-after", "1") as m:
        rc, txt = capture(m.host, root, "s2", pf, 2)
        r = read_json(root / "s2" / "session.json")["result"]
        check(rc == 1 and "0x350a: dau 248, cuoi 255" in r["reason"] and "0x3400" not in r["reason"], "troi ngay tu anh 1, chi 0x350a: FAIL neu dung mot thanh ghi", r["reason"])
    with Mock("--drift-registers", "0x3500", "--drift-after", "6") as m:
        rc, txt = capture(m.host, root, "s3", pf, 5)
        r = read_json(root / "s3" / "session.json")["result"]
        check(rc == 0 and r["verdict"] == "PASS", "troi sau anh cuoi (drift-after 6, count 5): khong lech -> PASS", (rc, r["reason"]))
    end()


def t3h(pf):
    begin("T3h", "/status thieu thanh ghi 0x3500: --create va capture FAIL 'thieu thanh ghi 0x3500'")
    out = tmpdir("t3h")
    with Mock("--status-drop-fields", "0x3500") as m:
        rc, txt = create(m.host, out, "VGA", 10)
        check(rc == 1 and "thieu thanh ghi 0x3500 trong /status" in txt, "--create rc 1", (rc, [l for l in txt.splitlines() if "thieu" in l]))
        check(list(out.glob("*.json")) == [], "khong ghi tep")
        root = tmpdir("t3h_s")
        rc, txt = capture(m.host, root, "s1", pf, 2)
        r = read_json(root / "s1" / "session.json")["result"]
        check(rc == 1 and "thieu thanh ghi 0x3500 trong /status" in r["reason"], "capture rc 1, reason dung", (rc, r["reason"]))
    with Mock("--status-drop-fields", "framesize") as m:
        rc, txt = create(m.host, out, "VGA", 10, "--id", pid("VGA", 10))
        check(rc == 1 and "framesize: yeu cau 10, bo bao None" in txt, "/status thieu framesize -> --create rc 1", (rc, [l for l in txt.splitlines() if "framesize" in l and "yeu cau" in l]))
    end()


def t3i(pf):
    begin("T3i", "/status cuoi phien tra 503: FAIL, reason co ca 'khong doi chieu duoc' va 'khong doc duoc /status luc ket thuc'")
    root = tmpdir("t3i")
    with Mock("--status-fail-after", "3") as m:
        rc, txt = capture(m.host, root, "s1", pf, 3)
        r = read_json(root / "s1" / "session.json")["result"]
        check(rc == 1 and "/status khong doi chieu duoc: cuoi: http 503" in r["reason"], "reason co 'khong doi chieu duoc'", r["reason"])
        check("khong doc duoc /status luc ket thuc de doi chieu thanh ghi ho so camera" in r["reason"], "reason co dong thanh ghi ho so", r["reason"])
        check(len(img_files(root / "s1")) == 3, "3 anh giu nguyen", img_files(root / "s1"))
    end()


def t3j():
    begin("T3j", "--verify: ho so khop bo rc 0; expected_registers khac bo rc 1 neu thanh ghi; control khac (ignore) rc 1")
    out = tmpdir("t3j")
    with Mock() as m:
        v_id = pid("SVGA", 20)
        rc, _ = create(m.host, out, "SVGA", 20, "--id", v_id)
        check(rc == 0, "--create rc 0", rc)
    with Mock() as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(out / (v_id + ".json")))
        check(rc == 0 and ("Ho so khop bo: " + v_id) in txt, "--verify tren mock moi (cung thanh ghi) rc 0", (rc, txt.strip().splitlines()[-1:]))
        import requests
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        check(st["framesize"] == 11 and st["quality"] == 20 and st["aec"] == 0, "--verify da ap lai ho so len bo", {k: st[k] for k in ("framesize", "quality", "aec")})
    p = read_json(out / (v_id + ".json"))
    p["expected_registers"]["0x3500"] = 99
    (out / "v2.json").write_text(json.dumps(p), encoding="utf-8")  # ten TEP tu do; ID ben trong van dung mau
    with Mock() as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(out / "v2.json"))
        check(rc == 1 and "Thanh ghi lech so voi ho so da luu" in txt and "0x3500: dau 99, cuoi 12544" in txt, "expected_registers khac bo -> rc 1 neu 0x3500", (rc, [l for l in txt.splitlines() if "0x3500" in l or "lech" in l]))
    with Mock("--ignore-controls", "aec") as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(out / (v_id + ".json")))
        check(rc == 1 and "aec: yeu cau 0, bo bao 1" in txt, "bo khong ap aec -> rc 1", (rc, [l for l in txt.splitlines() if "aec:" in l]))
    end()


def t3l():
    begin("T3l", "--create toi cong khong ai nghe: rc 1 'loi ket noi', khong ghi tep, khong treo")
    out = tmpdir("t3l")
    port = free_port()
    t0 = time.time()
    rc, txt = run_cli(CP, "--create", "--host", "127.0.0.1:%d" % port, "--framesize", "VGA", "--quality", "10", "--out", str(out), "--id", pid("VGA", 10), "--timeout", "2", *EXPLICIT_SET)
    dt = time.time() - t0
    check(rc == 1 and "/control that bai: framesize (loi ket noi" in txt, "rc 1, neu 'framesize (loi ket noi'", (rc, [l for l in txt.splitlines() if "that bai" in l]))
    check(list(out.glob("*.json")) == [], "khong ghi tep")
    check(dt < 60, "ket thuc trong < 60 s", round(dt, 1))
    end()


def t3m(pf):
    begin("T3m", "--profile cung --framesize: rc 2 truoc khi cham bo, khong tao thu muc phien")
    with Mock() as m:
        root = tmpdir("t3m")
        rc, txt = capture(m.host, root, "s1", pf, 2, "--framesize", "VGA")
        check(rc == 2 and "--profile va --framesize" in txt, "rc 2, thong bao dung", (rc, txt.strip().splitlines()[:1]))
        check(not (root / "s1").exists(), "khong tao thu muc phien")
    end()


def t3n():
    begin("T3n", "ho so yeu cau control 'sharpness' ma firmware khong ho tro (/control tra 500): tu choi ro rang, khong am tham bo qua")
    d = tmpdir("t3n")
    p = cp.build_profile_dict("VGA", 10, dict(FULL_CONTROLS, sharpness=1), dict(GOOD_REGS), "x")
    (d / "sh.json").write_text(json.dumps(p), encoding="utf-8")
    with Mock() as m:
        root = tmpdir("t3n_s")
        rc, txt = capture(m.host, root, "s1", str(d / "sh.json"), 2)
        r = read_json(root / "s1" / "session.json")["result"]
        check(rc == 1 and "sharpness" in r["reason"] and "khong ro" in r["reason"], "capture rc 1, reason neu sharpness", (rc, r["reason"]))
        rc2, txt2 = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / "sh.json"))
        check(rc2 == 1 and "sharpness" in txt2, "--verify rc 1 neu sharpness", (rc2, [l for l in txt2.splitlines() if "sharpness" in l]))
        import requests
        r5 = requests.get("http://%s/control?var=sharpness&val=1" % m.host, timeout=5)
        check(r5.status_code == 500, "mock /control?var=sharpness -> 500 nhu firmware (cmd_handler khong co nhanh)", r5.status_code)
    end()


# ----------------------------------------------------------------------
# T4 thiet bi
# ----------------------------------------------------------------------

def t4a(pf):
    begin("T4a", "/capture tra 503 tu anh 3 tro di (het retry): FAIL 'anh dat 2/5', anh 1-2 nguyen, payload loi giu rieng")
    root = tmpdir("t4a")
    frames = ",".join(str(i) for i in range(3, 60))
    with Mock("--fail-frames", frames) as m:
        rc, txt = capture(m.host, root, "s1", pf, 5, "--max-retries", "2")
        sess = read_json(root / "s1" / "session.json")
        r = sess["result"]
        check(rc == 1 and r["verdict"] == "FAIL" and r["reason"].startswith("anh dat 2/5"), "rc 1, reason 'anh dat 2/5...'", (rc, r["reason"]))
        imgs = img_files(root / "s1")
        check("img_0001.jpg" in imgs and "img_0002.jpg" in imgs, "img_0001/0002.jpg con", imgs)
        check({jpeg_size(root / "s1" / f) for f in ("img_0001.jpg", "img_0002.jpg")} == {(640, 480)}, "anh 1-2 giai ma duoc 640x480")
        check(any(f.startswith("img_0003_try") for f in imgs), "payload 503 cua anh 3 luu img_0003_try*.bin", [f for f in imgs if "try" in f][:3])
        check(r["frames_ok"] == 2 and r["retries_total"] == 6, "frames_ok 2, retries_total 6 (3 anh x 2)", (r["frames_ok"], r["retries_total"]))
        check(sess["finished_at"] is not None, "finished_at da ghi")
    end()
    return root


def t4b(pf):
    begin("T4b", "ngat cap giua phien (kill mock sau anh 2): FAIL, session.json ghi loi ket noi, anh 1-2 nguyen, chay lai khong ghi de")
    root = tmpdir("t4b")
    m = Mock()
    sd = root / "s1"
    try:
        proc = subprocess.Popen(
            [PY, CS, "--host", m.host, "--profile", pf, "--count", "5", "--interval", "1.5", "--warmup", "0",
             "--out", str(root), "--session-id", "s1", "--max-retries", "1", "--timeout", "2"],
            cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        t0 = time.time()
        while time.time() - t0 < 30 and not (sd / "img_0002.jpg").exists():
            time.sleep(0.05)
        check((sd / "img_0002.jpg").exists(), "co img_0002.jpg truoc khi ngat")
        h = {f: sha(sd / f) for f in ("img_0001.jpg", "img_0002.jpg") if (sd / f).exists()}
        m.kill()
        out, _ = proc.communicate(timeout=120)
        rc = proc.returncode
    finally:
        m.kill()
    sess = read_json(sd / "session.json")
    r = sess["result"]
    check(rc == 1 and r["verdict"] == "FAIL", "rc 1 FAIL", (rc, r["reason"]))
    check(r["frames_ok"] == 2 and r["reason"].startswith("anh dat 2/5"), "frames_ok 2, reason 'anh dat 2/5'", (r["frames_ok"], r["reason"][:60]))
    check(r["connection_errors"] >= 3, "connection_errors >= 3", r["connection_errors"])
    check("khong doc duoc /status luc ket thuc de doi chieu thanh ghi" in r["reason"], "reason neu khong doc duoc /status cuoi (khong ngam hieu 'khong doi')", r["reason"])
    check(sess["camera_status_end"]["ok"] is False, "camera_status_end ok=False")
    check(all(sha(sd / f) == v for f, v in h.items()), "img_0001/0002 sha khong doi sau khi ngat")
    lines = (sd / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
    errs = [json.loads(x)["error"] for x in lines if not json.loads(x)["accepted"]]
    check(len(lines) >= 5 and errs and all("ConnectionError" in e or "Connection" in e for e in errs), "attempts.jsonl ghi tung lan loi ket noi", errs[:2])
    m2 = Mock()
    try:
        rc2, txt2 = capture(m2.host, root, "s1", pf, 2)
        check(rc2 == 2 and all(sha(sd / f) == v for f, v in h.items()), "chay lai cung session-id sau khi ngat: rc 2, anh cu nguyen", rc2)
    finally:
        m2.kill()
    end()


def t4c(pf):
    begin("T4c", "bo phan hoi cham hon timeout: --create rc 1 'loi ket noi ...Timeout', capture FAIL, khong treo")

    class Slow(mc.H):
        def do_GET(self):
            if self.path.startswith("/control") or self.path.startswith("/capture"):
                time.sleep(1.5)
            return mc.H.do_GET(self)

    out = tmpdir("t4c")
    with InProcMock(Slow) as m:
        t0 = time.time()
        rc, txt = create(m.host, out, "VGA", 10, "--timeout", "0.5")
        dt = time.time() - t0
        check(rc == 1 and "/control that bai: framesize (loi ket noi" in txt and "Timeout" in txt, "--create rc 1, neu Timeout", (rc, [l for l in txt.splitlines() if "that bai" in l]))
        check(list(out.glob("*.json")) == [], "khong ghi tep")
        check(dt < 30, "ket thuc < 30 s", round(dt, 1))
        # Vong 3 G04: chi 1 request /control (client) roi dung; server cham xu ly sau nen doi mot nhip roi doc dem
        time.sleep(2.0)
        check(mc.STATE["counts"]["control"] == 1 and "quality" not in txt, "chi gui 1 /control (framesize) roi dung, khong gui quality... (Vong 3)", (mc.STATE["counts"], [l for l in txt.splitlines() if "quality" in l][:1]))
    with InProcMock(Slow) as m:
        root = tmpdir("t4c_s")
        rc, txt = capture(m.host, root, "s1", pf, 2, "--timeout", "0.5", "--max-retries", "1")
        sess = read_json(root / "s1" / "session.json")
        check(rc == 1 and "ap ho so camera khong khop" in sess["result"]["reason"] and "Timeout" in sess["result"]["reason"], "capture: FAIL ngay o buoc ap ho so vi timeout", (rc, sess["result"]["reason"][:120]))
        check(img_files(root / "s1") == [], "0 anh")

    class SlowCapture(mc.H):
        def do_GET(self):
            if self.path.startswith("/capture"):
                time.sleep(1.5)
            return mc.H.do_GET(self)

    with InProcMock(SlowCapture) as m:
        root = tmpdir("t4c_s2")
        rc, txt = capture(m.host, root, "s1", pf, 2, "--timeout", "0.5", "--max-retries", "1")
        r = read_json(root / "s1" / "session.json")["result"]
        check(rc == 1 and r["reason"].startswith("anh dat 0/2") and r["connection_errors"] == 4, "/capture cham: FAIL 'anh dat 0/2', 4 loi ket noi (2 anh x 2 lan)", (rc, r["reason"][:60], r["connection_errors"]))
        lines = (root / "s1" / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
        check(all("Timeout" in json.loads(x)["error"] for x in lines), "attempts.jsonl moi dong ghi Timeout", [json.loads(x)["error"][:40] for x in lines][:1])
    end()


def t4e(pf):
    begin("T4e", "bo reset giua phien (--reset-at 3, X-Timestamp lui) khi dung --profile: FAIL 'nghi reset'")
    root = tmpdir("t4e")
    with Mock("--reset-at", "3") as m:
        rc, txt = capture(m.host, root, "s1", pf, 5)
        r = read_json(root / "s1" / "session.json")["result"]
        check(rc == 1 and "nghi reset 1 lan" in r["reason"], "rc 1, 'nghi reset 1 lan'", (rc, r["reason"]))
        check(r["frames_ok"] == 5, "5 anh van luu de dieu tra", r["frames_ok"])
    end()


# ----------------------------------------------------------------------
# TX kich ban Tester them - ghi nhan hanh vi, doi chieu thiet ke
# ----------------------------------------------------------------------

def tx1(pf):
    begin("TX1", "control troi giua phien (aec/agc=1, awb=0 tu anh 3) nhung thanh ghi KHONG doi: capture_session --profile co bat duoc?")

    class Revert(mc.H):
        def do_GET(self):
            if self.path.startswith("/capture") and mc.STATE["frame"] + 1 >= 3:
                mc.STATE["controls"].update({"aec": 1, "agc": 1, "awb": 0})  # Vong 6 (L11): awb=0 nay moi la drift
            return mc.H.do_GET(self)

    root = tmpdir("tx1")
    with InProcMock(Revert) as m:
        rc, txt = capture(m.host, root, "s1", pf, 5)
        sess = read_json(root / "s1" / "session.json")
        r = sess["result"]
        st_end = sess["camera_status_end"]["json"]
        check(st_end["aec"] == 1 and st_end["awb"] == 0, "tien de: /status cuoi bao aec=1, awb=0 (da troi)", (st_end["aec"], st_end["awb"]))
        # Vong 1: chi ghi nhan (phien PASS). Vong 3 (V3-T4, G03): PHAI FAIL, status error, neu dung truong, anh giu nguyen
        check(rc == 1 and r["verdict"] == "FAIL", "rc 1 FAIL (Vong 3 G03)", (rc, r["reason"]))
        check("control ho so camera lech luc ket thuc" in r["reason"] and "aec: yeu cau 0, bo bao 1" in r["reason"] and "awb: yeu cau 1, bo bao 0" in r["reason"],
              "reason neu 'control ho so camera lech luc ket thuc' voi aec/awb", r["reason"])
        check(sess.get("status") == "error", "status = error", sess.get("status"))
        check(r["frames_ok"] == 5 and len(img_files(root / "s1")) == 5, "5 anh da chup giu nguyen", (r["frames_ok"], len(img_files(root / "s1"))))
    end()


def tx2(pf):
    begin("TX2", "expected_registers trong ho so KHAC thanh ghi bo (bo on dinh o gia tri khac): capture_session --profile PASS hay FAIL?")
    d = tmpdir("tx2")
    p = read_json(pf)
    # Vong 6 (L11): truoc day dat ca bay thanh ghi = 0. Nay bon thanh ghi WB phai dung bang
    # preset nen ho so do bi chan TRUOC HTTP (kiem rieng o V7c). De giu nguyen y nghia G02 -
    # "thanh ghi SAU KHI AP khac ho so da luu" - chi lam lech ba thanh ghi PHOI SANG.
    for k in ("0x3500", "0x350a", "0x3503"):
        p["expected_registers"][k] = 0 if k != "0x3503" else 7
    (d / "zero.json").write_text(json.dumps(p), encoding="utf-8")
    root = tmpdir("tx2_s")
    with Mock() as m:
        h0 = sha(d / "zero.json")
        rc, txt = capture(m.host, root, "s1", str(d / "zero.json"), 2, "--warmup", "2")
        sess = read_json(root / "s1" / "session.json")
        r = sess["result"]
        # Vong 1: chi ghi nhan (phien PASS). Vong 3 (V3-T3, G02): PHAI FAIL ngay sau khi ap, 0 capture ke ca warmup
        check(rc == 1 and r["verdict"] == "FAIL" and "thanh ghi sau khi ap khong khop ho so da luu" in r["reason"], "capture rc 1, reason 'thanh ghi sau khi ap khong khop ho so da luu' (Vong 3 G02)", (rc, r["reason"]))
        check("0x3500: dau 0, cuoi 12544" in r["reason"] and "0x350a: dau 0, cuoi 248" in r["reason"] and "0x3400" not in r["reason"],
              "reason neu dung thanh ghi phoi sang lech, khong keo theo thanh ghi WB dung", r["reason"])
        check(sess.get("status") == "error", "status = error", sess.get("status"))
        c = counts(m.host)
        check(c["capture"] == 0 and img_files(root / "s1") == [], "0 /capture ke ca warmup 2, 0 anh", (c, img_files(root / "s1")))
        check(sha(d / "zero.json") == h0, "ho so goc khong bi sua")
        rc2, txt2 = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / "zero.json"))
        check(rc2 == 1 and "Thanh ghi lech so voi ho so da luu" in txt2, "camera_profile --verify voi cung ho so: rc 1 neu lech", (rc2, [l for l in txt2.splitlines() if "lech" in l]))
    end()


def tx3():
    begin("TX3", "mock /status co du 14 control + 4 thanh ghi voi ten dung nhu status_handler cua firmware")
    with Mock() as m:
        import requests
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        missing = [k for k in cp.CONTROL_ORDER + list(cp.DEFAULT_EXPECTED_REGISTER_KEYS) + ["framesize", "quality"] if k not in st]
        check(missing == [], "khong thieu truong nao", missing)
        check(all(isinstance(st[k], int) for k in cp.CONTROL_ORDER), "control la so nguyen (firmware in %d/%u)")
        # firmware in "0x%04x" chu thuong
        check(all(k == k.lower() for k in st if k.startswith("0x")), "khoa thanh ghi chu thuong nhu firmware")
        # chua co bo: doi chieu tinh voi app_httpd.cpp
        src = (REPO_ROOT / "firmware/esp32s3/CameraWebServerTest/app_httpd.cpp").read_text(encoding="utf-8", errors="replace")
        for var in cp.CONTROL_ORDER + ["framesize", "quality"]:
            check(('!strcmp(variable, "%s")' % var) in src, "cmd_handler co nhanh '%s'" % var)
        check('!strcmp(variable, "sharpness")' not in src, "cmd_handler KHONG co nhanh 'sharpness' (co so cho quyet dinh cua Coder)")
        bs = chr(92)  # firmware viet "\"aec\":%u" -> trong nguon C co dau gach cheo nguoc truoc dau nhay
        for var in cp.CONTROL_ORDER:
            check((bs + '"' + var + bs + '":') in src, "status_handler in '%s'" % var)
    end()


def tx4(pf):
    begin("TX4", "--meta-copy voi --profile: ban sao ho so co schema 2, khong gom anh, tu choi khi da co")
    root = tmpdir("tx4")
    meta = tmpdir("tx4_meta")
    with Mock() as m:
        rc, txt = capture(m.host, root, "s1", pf, 2, "--meta-copy", str(meta))
        check(rc == 0, "rc 0", rc)
        ms = meta / "s1"
        check((ms / "session.json").exists() and read_json(ms / "session.json").get("schema_version") == 2, "ban sao session.json co schema_version 2")
        check((ms / "status_after_set.json").exists(), "ban sao co status_after_set.json")
        check(not any(f.startswith("img_") for f in os.listdir(ms)), "ban sao khong gom anh", os.listdir(ms))
        rc2, txt2 = capture(m.host, root, "s1", pf, 2, "--meta-copy", str(meta))
        check(rc2 == 2, "chay lai: rc 2 (thu muc meta da co)", rc2)
    end()


def tx5():
    begin("TX5", "validate_profile: cac kieu sai them (controls la list, thanh ghi khoa khong '0x', gia tri float, verified la chuoi, source thieu commit)")
    good = cp.build_profile_dict("VGA", 10, FULL_CONTROLS, dict(GOOD_REGS), "x")
    cases = (
        ("controls la list", dict(good, controls=list(cp.CONTROL_ORDER)), "controls phai la object"),
        ("controls gia tri float", dict(good, controls=dict(FULL_CONTROLS, aec_value=490.0)), "aec_value"),
        ("thanh ghi khoa '3500'", dict(good, expected_registers=dict(GOOD_REGS, **{"3500": 1})), "khoa khong hop le"),
        ("thanh ghi gia tri chuoi", dict(good, expected_registers=dict(GOOD_REGS, **{"0x3500": "12544"})), "0x3500"),
        ("verified la chuoi", dict(good, verified="yes"), "verified phai la null hoac object"),
        ("source thieu commit", dict(good, source={"branch": "x"}), "source"),
        ("lens_note la None", dict(good, lens_note=None), "lens_note"),
        ("framesize chu thuong 'vga'", dict(good, framesize="vga"), "framesize"),
        ("ID rong", dict(good, camera_profile_id=""), "camera_profile_id"),
    )
    for name, p, want in cases:
        ok, errs = cp.validate_profile(p)
        check(not ok and any(want in e for e in errs), "%s -> loi co '%s'" % (name, want), errs)
    ok, errs = cp.validate_profile(json.loads(json.dumps(good)))
    check(ok, "ho so tot qua JSON round-trip van hop le", errs)
    end()


# ----------------------------------------------------------------------
# V3 - kich ban Vong 2 cua Tester theo 01_PLAN.md Vong 3 (V3-T1..T8)
# ----------------------------------------------------------------------

C5_ONLY_FIELDS = ("motion", "laser", "angle_table", "counts", "protocol_version", "sample", "abort_reason")


def fabricated_c5(sess):
    """Truong C5 bi 'bia' = co mat DUOI DANG object/mang/so (nhu da do). Chuoi
    tuan 1 'chua ap dung (tuan 1)' o `laser`/`angle_index` la placeholder co
    san tu tuan 1, khong phai gia tri do, khong tinh."""
    return [k for k in C5_ONLY_FIELDS if k in sess and not isinstance(sess[k], str)]


def v3a(pf):
    begin("V3a", "V3-T1 vong doi metadata: schema_version 2, status running TRUOC khi xong, completed khi PASS; requested tu ho so")
    root = tmpdir("v3a")
    m = Mock()
    sd = root / "s1"
    try:
        proc = subprocess.Popen(
            [PY, CS, "--host", m.host, "--profile", pf, "--count", "3", "--interval", "1.5", "--warmup", "0",
             "--out", str(root), "--session-id", "s1"],
            cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        t0 = time.time()
        while time.time() - t0 < 30 and not (sd / "img_0001.jpg").exists():
            time.sleep(0.05)
        check((sd / "img_0001.jpg").exists(), "tien de: dang giua phien (co img_0001.jpg)")
        mid = None
        for _ in range(20):  # session.json co the dang duoc ghi lai giua chung
            try:
                mid = read_json(sd / "session.json")
                break
            except ValueError:
                time.sleep(0.05)
        mid = mid or {}
        check(mid.get("status") == "running", "session.json GIUA phien: status = running", mid.get("status"))
        check(mid.get("schema_version") == 2, "session.json GIUA phien: schema_version = 2", mid.get("schema_version"))
        check(mid.get("camera_profile_id") == read_json(pf)["camera_profile_id"], "giua phien da co camera_profile_id", mid.get("camera_profile_id"))
        out, _ = proc.communicate(timeout=120)
        rc = proc.returncode
    finally:
        m.kill()
    sess = read_json(sd / "session.json")
    check(rc == 0 and sess["result"]["verdict"] == "PASS", "rc 0 PASS", (rc, sess["result"]["reason"]))
    check(sess.get("status") == "completed", "cuoi phien status = completed", sess.get("status"))
    check(sess.get("schema_version") == 2, "cuoi phien schema_version = 2", sess.get("schema_version"))
    check(sess["requested"].get("framesize") == "VGA" and sess["requested"].get("quality") == 10, "requested.framesize/quality tu ho so", sess["requested"])
    check(sess["finished_at"] is not None, "finished_at da ghi")
    present = fabricated_c5(sess)
    check(present == [], "khong bia truong C5 dang object/mang (laser/angle_index chuoi tuan 1 duoc giu)", present)
    end()


def v3b(pf):
    begin("V3b", "V3-T2 dau vao sai bi chan TRUOC HTTP (0 request), khong ghi ho so, khong doi tep cu")
    out = tmpdir("v3b")
    keep = pid("VGA", 10)
    with Mock() as m:
        rc, _ = create(m.host, out, "VGA", 10, "--id", keep)
        check(rc == 0, "tien de: tao ho so '%s' rc 0" % keep, rc)
    h_keep = sha(out / (keep + ".json"))
    # camera_profile --create: quality / timeout sai
    cases = (
        (("--quality", "64"), "quality 64"), (("--quality", "-1"), "quality -1"), (("--quality", "abc"), "quality chuoi"),
        (("--quality", "20", "--timeout", "0"), "timeout 0"), (("--quality", "20", "--timeout", "-3"), "timeout am"),
        (("--quality", "20", "--timeout", "nan"), "timeout NaN"), (("--quality", "20", "--timeout", "inf"), "timeout Infinity"),
    )
    for extra, label in cases:
        with Mock() as m:
            bad_id = pid("SVGA", 20)  # ID hop le: loi phai den tu quality/timeout, khong phai ID
            rc, txt = run_cli(CP, "--create", "--host", m.host, "--framesize", "SVGA", "--out", str(out), "--id", bad_id, *extra)
            c = counts(m.host)
            check(rc == 2 and c == {"control": 0, "capture": 0, "status": 0} and not (out / (bad_id + ".json")).exists(),
                  "--create %s: rc 2, 0 request, khong ghi tep" % label, (rc, c, txt.strip().splitlines()[-1:]))
    # camera_profile --verify: ho so sai -> 0 request; timeout sai -> 0 request
    d = tmpdir("v3b_profiles")
    good = read_json(pf)
    bad_profiles = {
        "thieu_control.json": dict(good, controls={k: v for k, v in good["controls"].items() if k != "dcw"}),
        "thieu_register.json": dict(good, expected_registers={k: v for k, v in good["expected_registers"].items() if k != "0x350a"}),
        "aec_1.json": dict(good, controls=dict(good["controls"], aec=1)),
        "agc_1.json": dict(good, controls=dict(good["controls"], agc=1)),
        "awb_0.json": dict(good, controls=dict(good["controls"], awb=0)),  # Vong 6 (L11): awb=0 nay moi sai
        "sharpness.json": dict(good, controls=dict(good["controls"], sharpness=2)),
        "quality_bool.json": dict(good, quality=True),
        "quality_chuoi.json": dict(good, quality="10"),
    }
    for fn, prof in bad_profiles.items():
        (d / fn).write_text(json.dumps(prof), encoding="utf-8")
    field = {"thieu_control.json": "dcw", "thieu_register.json": "0x350a", "aec_1.json": "aec", "agc_1.json": "agc", "awb_0.json": "awb",
             "sharpness.json": "sharpness", "quality_bool.json": "quality", "quality_chuoi.json": "quality"}
    for fn in bad_profiles:
        with Mock() as m:
            rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / fn))
            c = counts(m.host)
            check(rc == 1 and field[fn] in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "--verify %s: rc 1, neu '%s', 0 request" % (fn, field[fn]), (rc, c, [l for l in txt.splitlines() if field[fn] in l][:1]))
    with Mock() as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", pf, "--timeout", "inf")
        check(rc == 2 and counts(m.host)["control"] == 0, "--verify --timeout inf: rc 2, 0 /control", (rc, counts(m.host)))
    # capture_session --profile: ho so sai -> rc khac 0, 0 HTTP request (ke hoach V3-T2 / buoc 4: 'profile sai ghi loi, khong HTTP')
    root = tmpdir("v3b_s")
    for i, fn in enumerate(("aec_1.json", "sharpness.json", "thieu_register.json")):
        with Mock() as m:
            sid = "s%d" % i
            rc, txt = capture(m.host, root, sid, str(d / fn), 2)
            c = counts(m.host)
            sess = read_json(root / sid / "session.json")
            check(rc == 1 and field[fn] in sess["result"]["reason"], "capture --profile %s: rc 1, reason neu '%s'" % (fn, field[fn]), (rc, sess["result"]["reason"][:100]))
            check(sess.get("status") == "error", "capture --profile %s: status = error" % fn, sess.get("status"))
            check(c == {"control": 0, "capture": 0, "status": 0}, "capture --profile %s: 0 HTTP request (V3-T2, ke hoach buoc 4)" % fn, c)
    for t in ("inf", "nan", "0"):
        with Mock() as m:
            rc, txt = capture(m.host, root, "t_" + t, pf, 2, "--timeout", t)
            check(rc == 2 and counts(m.host) == {"control": 0, "capture": 0, "status": 0} and not (root / ("t_" + t)).exists(),
                  "capture --timeout %s: rc 2, 0 request, khong tao thu muc" % t, (rc, counts(m.host)))
    check(sha(out / (keep + ".json")) == h_keep, "ho so '%s' khong doi sau moi dau vao sai" % keep)
    end()


def v3d(pf):
    begin("V3d", "V3-T4 cuoi phien tung nhom truong troi (aec/agc/awb, control khac, framesize, quality), thanh ghi khong doi -> FAIL neu dung truong")
    root = tmpdir("v3d")
    # Vong 4: ho so nay co brightness=1, saturation=-2, vflip=1 (L05) - ky vong lay theo gia tri that trong ho so
    # Vong 6 (L11): drift awb nay la awb=0 (ho so yeu cau 1); them drift wb_mode ve 0 va awb_gain ve 0
    cases = (("aec=1", "aec: yeu cau 0, bo bao 1"), ("agc=1", "agc: yeu cau 0, bo bao 1"), ("awb=0", "awb: yeu cau 1, bo bao 0"),
             ("wb_mode=0", "wb_mode: yeu cau 1, bo bao 0"), ("awb_gain=0", "awb_gain: yeu cau 1, bo bao 0"),
             ("brightness=2", "brightness: yeu cau 1, bo bao 2"), ("lenc=0", "lenc: yeu cau 1, bo bao 0"),
             ("vflip=0", "vflip: yeu cau 1, bo bao 0"), ("saturation=0", "saturation: yeu cau -2, bo bao 0"),
             ("framesize=6", "framesize: yeu cau 10, bo bao 6"), ("quality=20", "quality: yeu cau 10, bo bao 20"))
    for i, (drift, want) in enumerate(cases):
        with Mock("--control-drift-fields", drift, "--control-drift-after", "2") as m:
            sid = "s%d" % i
            rc, txt = capture(m.host, root, sid, pf, 3)
            sess = read_json(root / sid / "session.json")
            r = sess["result"]
            check(rc == 1 and "control ho so camera lech luc ket thuc" in r["reason"] and want in r["reason"],
                  "%s: rc 1, reason co '%s'" % (drift, want), (rc, r["reason"]))
            check(sess.get("status") == "error", "%s: status = error" % drift, sess.get("status"))
            check("thanh ghi ho so camera lech" not in r["reason"], "%s: khong bao lech thanh ghi (thanh ghi khong doi)" % drift)
            check(r["frames_ok"] == 3 and len(img_files(root / sid)) == 3, "%s: 3 anh giu nguyen" % drift, len(img_files(root / sid)))
            st_after = read_json(root / sid / "status_after_set.json")
            k, v = drift.split("=")
            want = read_json(pf)["controls"].get(k, cp.FRAMESIZES["VGA"] if k == "framesize" else 10)
            check(st_after[k] == want, "%s: snapshot after_set van khop ho so (chi cuoi phien lech)" % drift, (st_after[k], want))
    end()


def v3e(pf):
    begin("V3e", "V3-T5 /status sai kieu (bool thay so) o thanh ghi va control, sau ap va cuoi phien -> FAIL, khong ket luan 'khong doi'")

    class BoolStatus(mc.H):
        """Tu /capture thu >= N, /status tra aec=false (thay 0), dcw=true (thay 1), 0x350a=true."""
        def do_GET(self):
            if self.path.startswith("/status") and mc.STATE["frame"] >= mc.STATE.get("_bool_after", 99):
                d = json.loads(mc.status_body())
                d["aec"] = False
                d["dcw"] = True
                d["0x350a"] = True
                return self._send(200, "application/json", json.dumps(d).encode())
            return mc.H.do_GET(self)

    root = tmpdir("v3e")
    # (a) bool ngay sau khi ap (frame 0 -> _bool_after 0)
    with InProcMock(BoolStatus, _bool_after=0) as m:
        rc, txt = capture(m.host, root, "s_after", pf, 2)
        sess = read_json(root / "s_after" / "session.json")
        r = sess["result"]
        check(rc == 1 and sess.get("status") == "error", "bool sau khi ap: rc 1, status error", (rc, r["reason"][:160]))
        # Vong 2: mong doi 0x350a (luc do control bool loi qua, chi thanh ghi bi bat). Vong 3: diff_controls bat
        # aec/dcw truoc va apply_and_verify dung ngay, chua toi so thanh ghi -> ke hoach chi doi "FAIL voi ten
        # truong, ky vong, thuc nhan" (dat). 0x350a co duoc neu hay khong chi ghi nhan.
        check(("aec: yeu cau 0, bo bao False" in r["reason"]) and ("dcw: yeu cau 1, bo bao True" in r["reason"]),
              "reason neu aec (0 != false) va dcw (1 != true) kem ky vong/thuc nhan - bool khong duoc coi bang so", r["reason"][:200])
        note("0x350a (248 != true) co trong reason sau khi ap? %s (khong bat buoc: control sai dung truoc)" % ("0x350a" in r["reason"]))
        check(mc.STATE["counts"]["capture"] == 0, "0 /capture", mc.STATE["counts"])
    # (b) bool chi o cuoi phien
    with InProcMock(BoolStatus, _bool_after=2) as m:
        rc, txt = capture(m.host, root, "s_end", pf, 2)
        sess = read_json(root / "s_end" / "session.json")
        r = sess["result"]
        check(rc == 1 and sess.get("status") == "error", "bool cuoi phien: rc 1, status error", (rc, r["reason"][:160]))
        check("0x350a" in r["reason"], "reason neu 0x350a", r["reason"][:160])
        check(("aec" in r["reason"]) and ("dcw" in r["reason"]), "reason neu aec va dcw (bool != so)", r["reason"][:200])
        check(len(img_files(root / "s_end")) == 2, "2 anh giu nguyen")
    # (c) thieu mot khoa bo sung trong ho so o cuoi phien (khoa 0x3406 chi co luc dau)
    class DropLater(mc.H):
        """Vong 4: 0x3406 nay la khoa MAC DINH, nen dung 0x5580 lam khoa bo sung."""
        def do_GET(self):
            if self.path.startswith("/status"):
                d = json.loads(mc.status_body())
                if mc.STATE["frame"] < 2:
                    d["0x5580"] = 6
                return self._send(200, "application/json", json.dumps(d).encode())
            return mc.H.do_GET(self)

    d = tmpdir("v3e_p")
    p5 = read_json(pf)
    p5["expected_registers"]["0x5580"] = 6
    (d / "five.json").write_text(json.dumps(p5), encoding="utf-8")
    with InProcMock(DropLater) as m:
        rc, txt = capture(m.host, root, "s_drop", str(d / "five.json"), 2)
        sess = read_json(root / "s_drop" / "session.json")
        r = sess["result"]
        check(rc == 1 and "thieu 0x5580 trong /status moi" in r["reason"] and sess.get("status") == "error",
              "khoa bo sung 0x5580 mat o cuoi phien: rc 1, reason 'thieu 0x5580', status error", (rc, r["reason"]))
    end()


def v3f(pf):
    begin("V3f", "V3-T6 /control thu k loi (500 / ket noi / timeout): dung dung tai k, khong capture, khong ho so moi, diagnostic co ten control")
    out = tmpdir("v3f")
    root = tmpdir("v3f_s")
    order = ["framesize", "quality"] + cp.CONTROL_ORDER
    for var in ("framesize", "awb", "dcw"):
        k = order.index(var) + 1
        with Mock("--fail-controls", var) as m:
            c_id = pid("VGA", 10)
            rc, txt = create(m.host, out, "VGA", 10, "--id", c_id)
            c = counts(m.host)
            check(rc == 1 and c["control"] == k and c["capture"] == 0 and ("/control that bai: %s (http 500)" % var) in txt and not (out / (c_id + ".json")).exists(),
                  "--create fail %s (k=%d): rc 1, control=%d, 0 capture, khong ghi tep, neu ten" % (var, k, k), (rc, c))
            rc2, txt2 = capture(m.host, root, "s_" + var, pf, 2, "--warmup", "1")
            c2 = counts(m.host)
            sess = read_json(root / ("s_" + var) / "session.json")
            check(rc2 == 1 and c2["control"] == 2 * k and c2["capture"] == 0 and var in sess["result"]["reason"] and sess.get("status") == "error",
                  "capture fail %s: rc 1, them dung %d control, 0 capture (ke ca warmup), status error" % (var, k), (rc2, c2, sess["result"]["reason"]))

    class SlowAt(mc.H):
        """/control thu N (theo dem) ngu 1.5 s -> client timeout 0.5 s."""
        def do_GET(self):
            if self.path.startswith("/control") and mc.STATE["counts"]["control"] + 1 == mc.STATE.get("_slow_at", 0):
                time.sleep(1.5)
            return mc.H.do_GET(self)

    with InProcMock(SlowAt, _slow_at=5) as m:  # awb
        t0 = time.time()
        rc, txt = create(m.host, out, "VGA", 10, "--id", pid("VGA", 10), "--timeout", "0.5")
        dt = time.time() - t0
        time.sleep(2.0)
        check(rc == 1 and "/control that bai: awb (loi ket noi" in txt and "Timeout" in txt, "timeout o lenh thu 5 (awb): rc 1, neu awb + Timeout", (rc, [l for l in txt.splitlines() if "that bai" in l]))
        check(mc.STATE["counts"]["control"] == 5 and mc.STATE["counts"]["capture"] == 0, "dung dung tai control 5, khong gui tiep, 0 capture", mc.STATE["counts"])
        check(dt < 6, "khong cho het 16 x timeout (thuc te < 6 s)", round(dt, 1))
        check(not (out / (pid("VGA", 10) + ".json")).exists(), "khong ghi ho so")
    port = free_port()
    rc, txt = run_cli(CP, "--create", "--host", "127.0.0.1:%d" % port, "--framesize", "VGA", "--quality", "10", "--out", str(out), "--id", pid("VGA", 10), "--timeout", "2", *EXPLICIT_SET)
    check(rc == 1 and "/control that bai: framesize (loi ket noi" in txt, "cong dong: dung ngay tai framesize", (rc, txt.strip().splitlines()[-3:]))
    end()


def v3g(pf):
    begin("V3g", "V3-T7 KeyboardInterrupt giua phien: status aborted, finished_at, ly do, rc 1, anh da nhan nguyen; meta-copy va chay lai khong ghi de")
    import capture_session as cs
    root = tmpdir("v3g")
    meta = tmpdir("v3g_meta")
    with InProcMock() as m:
        real = cs.http_get
        hits = {"n": 0}

        def boom(session, url, timeout):
            if url.endswith("/capture"):
                hits["n"] += 1
                if hits["n"] == 3:
                    raise KeyboardInterrupt()
            return real(session, url, timeout)

        cs.http_get = boom
        try:
            class NS:
                pass
            a = NS()
            a.host = m.host; a.count = 5; a.interval = 0.0; a.framesize = None; a.profile = pf
            a.warmup = 0; a.max_retries = 1; a.timeout = 5.0; a.out = str(root); a.session_id = "s1"
            a.note = ""; a.meta_copy = str(meta)
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cs.run_session(a)
        finally:
            cs.http_get = real
    sd = root / "s1"
    sess = read_json(sd / "session.json")
    check(rc == 1, "rc 1", rc)
    check(sess.get("status") == "aborted", "status = aborted", sess.get("status"))
    check(sess["finished_at"] is not None and "KeyboardInterrupt" in (sess["result"] or {}).get("reason", ""), "finished_at + reason KeyboardInterrupt", sess.get("result"))
    imgs = img_files(sd)
    check(imgs == ["img_0001.jpg", "img_0002.jpg"], "img_0001/0002 con nguyen", imgs)
    check("Bi ngat" in buf.getvalue(), "in thong bao bi ngat, du lieu giu nguyen")
    note("meta-copy khi bi ngat: thu muc ban sao %s" % ("CO" if (meta / "s1").exists() else "KHONG co (chi chep khi ket thuc binh thuong)"))
    h = {f: sha(sd / f) for f in os.listdir(sd)}
    # chay lai cung ID (CLI that): raw da co -> rc 2, khong ghi de
    with Mock() as m2:
        rc2, txt2 = capture(m2.host, root, "s1", pf, 2, "--meta-copy", str(meta))
        check(rc2 == 2 and {f: sha(sd / f) for f in os.listdir(sd)} == h, "chay lai cung session-id: rc 2, moi tep raw sha khong doi", rc2)
        # meta-copy da co, raw moi -> rc 2 truoc khi chup, ban sao khong bi dong
        (meta / "s9").mkdir(parents=True, exist_ok=True)
        (meta / "s9" / "session.json").write_text("OLD", encoding="utf-8")
        rc3, txt3 = capture(m2.host, root, "s9", pf, 2, "--meta-copy", str(meta))
        check(rc3 == 2 and (meta / "s9" / "session.json").read_text(encoding="utf-8") == "OLD" and not (root / "s9").exists(),
              "meta-copy dich da co: rc 2, ban sao cu nguyen, khong tao raw", rc3)
        # phien loi (error) van chep ban sao, khong gom anh
        with Mock("--drift-registers", "0x3500", "--drift-after", "1") as m3:
            rc4, txt4 = capture(m3.host, root, "s_err", pf, 2, "--meta-copy", str(meta))
            sess4 = read_json(root / "s_err" / "session.json")
            cp_dir = meta / "s_err"
            check(rc4 == 1 and sess4.get("status") == "error" and (cp_dir / "session.json").exists() and not any(f.startswith("img_") for f in os.listdir(cp_dir)),
                  "phien error: ban sao ho so co, khong gom anh, status error", (rc4, sess4.get("status"), sorted(os.listdir(cp_dir)) if cp_dir.exists() else None))
            check(read_json(cp_dir / "session.json").get("status") == "error", "ban sao session.json cung ghi status error")
    end()


def v3h(pf):
    begin("V3h", "V3-T8 hoi quy nhanh khong --profile: schema 1 (khong status/schema_version), snapshot ten cu; ban --profile khong bia truong C5")
    root = tmpdir("v3h")
    with Mock() as m:
        rc, txt = run_cli(CS, "--host", m.host, "--count", "2", "--interval", "0", "--warmup", "0", "--out", str(root), "--session-id", "s_plain")
        sess = read_json(root / "s_plain" / "session.json")
        check(rc == 0 and sess["result"]["verdict"] == "PASS", "khong profile: rc 0 PASS", (rc, sess["result"]["reason"]))
        check("status" not in sess and "schema_version" not in sess and "camera_profile_id" not in sess, "khong profile: khong co status/schema_version/camera_profile_id (tuan 1 = schema 1)", [k for k in ("status", "schema_version", "camera_profile_id") if k in sess])
        check(sess["requested"]["framesize"] == "giu nguyen tren bo", "khong profile: requested.framesize 'giu nguyen tren bo'", sess["requested"]["framesize"])
        check((root / "s_plain" / "status_start.json").exists() and (root / "s_plain" / "status_end.json").exists() and (root / "s_plain" / "attempts.jsonl").exists(),
              "snapshot status_start/status_end.json va attempts.jsonl ton tai")
        rc, txt = run_cli(CS, "--host", m.host, "--count", "2", "--interval", "0", "--warmup", "0", "--out", str(root), "--session-id", "s_fs", "--framesize", "VGA")
        sess = read_json(root / "s_fs" / "session.json")
        check(rc == 0 and "status" not in sess and (root / "s_fs" / "status_after_set.json").exists() and sess["expected_size"] == [640, 480],
              "--framesize VGA (tuan 1): rc 0, khong status, co status_after_set.json, expected_size 640x480", (rc, sess.get("expected_size")))
    with Mock() as m:
        rc, txt = capture(m.host, root, "s_prof", pf, 2)
        sess = read_json(root / "s_prof" / "session.json")
        present = fabricated_c5(sess)
        check(rc == 0 and present == [], "--profile: khong co truong C5 bia dang object/mang", present)
        for f in ("status_start.json", "status_after_set.json", "status_end.json"):
            st = read_json(root / "s_prof" / f)
            check(isinstance(st, dict) and "framesize" in st, "--profile: %s la JSON /status" % f)
        st0 = read_json(root / "s_prof" / "status_start.json")
        st1 = read_json(root / "s_prof" / "status_after_set.json")
        check(st0["aec"] == 1 and st1["aec"] == 0, "start = TRUOC ap (aec 1), after_set = SAU ap (aec 0)", (st0["aec"], st1["aec"]))
        check(sess["camera_config"].get("stream_disabled") is None and sess["camera_config"].get("stream_disabled_reason"), "stream_disabled null + ly do, khong bia phep do")
        check("firmware" not in sess or "nucleo" not in (sess.get("firmware") or {}), "khong co firmware.nucleo")
    end()


def v3i(pf):
    begin("V3i", "R02 (04_REVIEW.md Vong 2): danh tinh ho so - ID/board/sensor/created_at/source.commit/verified sai deu bi tu choi TRUOC HTTP")
    good = read_json(pf)
    d = tmpdir("v3i")

    # (1) sau probe cua Reviewer, nguyen van theo 04_REVIEW.md Vong 2
    probes = (
        ("created_at=123", dict(good, created_at=123), "created_at"),
        ("source.commit=False", dict(good, source=dict(good["source"], commit=False)), "source.commit"),
        ("board='some-other-board'", dict(good, board="some-other-board"), "board"),
        ("sensor='OV2640'", dict(good, sensor="OV2640"), "sensor"),
        ("camera_profile_id='../outside'", dict(good, camera_profile_id="../outside"), "camera_profile_id"),
        ("verified sai ca ba kieu", dict(good, verified={"session_id": 123, "mean_drift_pct": "nan", "registers_stable": "yes"}), "verified."),
    )
    for label, prof, field in probes:
        ok, errs = cp.validate_profile(prof)
        check(not ok and any(field in e for e in errs), "probe Reviewer %s -> validate_profile bao loi '%s'" % (label, field), errs)

    # (2) tung truong verified sai rieng le (ke hoach Vong 4 buoc 3.3)
    for label, v, field in (
        ("session_id la so", {"session_id": 1, "mean_drift_pct": 0.5, "registers_stable": True}, "verified.session_id"),
        ("session_id rong", {"session_id": "", "mean_drift_pct": 0.5, "registers_stable": True}, "verified.session_id"),
        ("mean_drift_pct la chuoi", {"session_id": "s", "mean_drift_pct": "0.5", "registers_stable": True}, "verified.mean_drift_pct"),
        ("mean_drift_pct am", {"session_id": "s", "mean_drift_pct": -0.1, "registers_stable": True}, "verified.mean_drift_pct"),
        ("mean_drift_pct NaN", {"session_id": "s", "mean_drift_pct": float("nan"), "registers_stable": True}, "verified.mean_drift_pct"),
        ("mean_drift_pct Infinity", {"session_id": "s", "mean_drift_pct": float("inf"), "registers_stable": True}, "verified.mean_drift_pct"),
        ("mean_drift_pct bool", {"session_id": "s", "mean_drift_pct": True, "registers_stable": True}, "verified.mean_drift_pct"),
        ("registers_stable la chuoi", {"session_id": "s", "mean_drift_pct": 0.5, "registers_stable": "true"}, "verified.registers_stable"),
        ("registers_stable la so 1", {"session_id": "s", "mean_drift_pct": 0.5, "registers_stable": 1}, "verified.registers_stable"),
    ):
        ok, errs = cp.validate_profile(dict(good, verified=v))
        check(not ok and any(field in e for e in errs), "verified %s -> loi '%s'" % (label, field), errs)
    ok, errs = cp.validate_profile(dict(good, verified={"session_id": "capture_20260922_101010", "mean_drift_pct": 1.2, "registers_stable": True}))
    check(ok, "verified du va dung kieu -> hop le", errs)
    ok, errs = cp.validate_profile(dict(good, verified={"session_id": "s", "mean_drift_pct": 0, "registers_stable": False}))
    check(ok, "verified mean_drift_pct = 0 va registers_stable False -> hop le (0 va False la gia tri that)", errs)

    # (3) ID: doc duong dan, sai mau, sai ngay, khong khop framesize/quality
    for label, pid_val, want in (
        ("chua '..'", "../outside", "camera_profile_id"),
        ("chua '/'", "cam_VGA_q10_20260922/x", "camera_profile_id"),
        ("chua dau gach cheo nguoc", "cam_VGA" + chr(92) + "q10", "camera_profile_id"),
        ("khong dung mau", "my custom id", "camera_profile_id"),
        ("ngay 6 chu so", "cam_VGA_q10_260922", "camera_profile_id"),
        ("framesize la", "cam_MEGA_q10_20260922", "camera_profile_id"),
        ("khac framesize that", "cam_SVGA_q10_20260922", "camera_profile_id"),
        ("khac quality that", "cam_VGA_q20_20260922", "camera_profile_id"),
        ("ID rong", "", "camera_profile_id"),
    ):
        ok, errs = cp.validate_profile(dict(good, camera_profile_id=pid_val))
        check(not ok and any(want in e for e in errs), "camera_profile_id %s -> loi" % label, errs)
    for label, commit in (("ngan hon 40", "a" * 39), ("dai hon 40", "a" * 41), ("co chu hoa", "A" * 40), ("khong hex", "g" * 40), ("la so", 123)):
        ok, errs = cp.validate_profile(dict(good, source=dict(good["source"], commit=commit)))
        check(not ok and any("source.commit" in e for e in errs), "source.commit %s -> loi" % label, errs)
    for label, ca in (("thieu mui gio", "2026-09-22T10:00:00"), ("khong phai ngay", "hom nay"), ("chuoi rong", ""), ("la None", None)):
        ok, errs = cp.validate_profile(dict(good, created_at=ca))
        check(not ok and any("created_at" in e for e in errs), "created_at %s -> loi" % label, errs)

    # (4) 0 HTTP: --verify va capture --profile voi ho so sai danh tinh
    bad_files = {
        "id_traversal.json": dict(good, camera_profile_id="../outside"),
        "board_khac.json": dict(good, board="some-other-board"),
        "sensor_khac.json": dict(good, sensor="OV2640"),
        "created_at_so.json": dict(good, created_at=123),
        "commit_bool.json": dict(good, source=dict(good["source"], commit=False)),
        "verified_sai.json": dict(good, verified={"session_id": 123, "mean_drift_pct": "nan", "registers_stable": "yes"}),
        "id_khac_framesize.json": dict(good, camera_profile_id="cam_SVGA_q10_20260922"),
    }
    field = {"id_traversal.json": "camera_profile_id", "board_khac.json": "board", "sensor_khac.json": "sensor",
             "created_at_so.json": "created_at", "commit_bool.json": "source.commit", "verified_sai.json": "verified.",
             "id_khac_framesize.json": "camera_profile_id"}
    for fn, prof in bad_files.items():
        (d / fn).write_text(json.dumps(prof), encoding="utf-8")
    root = tmpdir("v3i_s")
    for i, fn in enumerate(bad_files):
        with Mock() as m:
            rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / fn))
            c = counts(m.host)
            check(rc == 1 and field[fn] in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "--verify %s: rc 1, neu '%s', 0 HTTP request" % (fn, field[fn]), (rc, c, [l for l in txt.splitlines() if field[fn] in l][:1]))
            sid = "s%d" % i
            rc2, txt2 = capture(m.host, root, sid, str(d / fn), 2, "--warmup", "1")
            c2 = counts(m.host)
            sess = read_json(root / sid / "session.json")
            check(rc2 == 1 and field[fn] in sess["result"]["reason"] and sess.get("status") == "error",
                  "capture --profile %s: rc 1, status error, reason neu '%s'" % (fn, field[fn]), (rc2, sess["result"]["reason"][:110]))
            check(c2 == {"control": 0, "capture": 0, "status": 0}, "capture --profile %s: 0 HTTP request" % fn, c2)
            check(img_files(root / sid) == [], "capture --profile %s: 0 anh" % fn)

    # (5) --create voi --id sai: rc 2, 0 HTTP, khong tao tep
    out = tmpdir("v3i_out")
    for label, id_val, fs, q in (
        ("'../evil'", "../evil", "VGA", 10),
        ("co khoang trang", "my custom id", "VGA", 10),
        ("khac framesize cua lenh", "cam_SVGA_q10_20260922", "VGA", 10),
        ("khac quality cua lenh", "cam_VGA_q20_20260922", "VGA", 10),
        ("ngay sai dinh dang", "cam_VGA_q10_2026-09-22", "VGA", 10),
    ):
        with Mock() as m:
            rc, txt = create(m.host, out, fs, q, "--id", id_val)
            c = counts(m.host)
            check(rc == 2 and "camera_profile_id" in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "--create --id %s: rc 2, neu camera_profile_id, 0 HTTP request" % label, (rc, c, txt.strip().splitlines()[-1:]))
    check(list(out.glob("*.json")) == [], "khong tep ho so nao duoc ghi", sorted(x.name for x in out.glob("*")))
    # (6) duong tot van chay: ID mac dinh do make_profile_id sinh ra phai hop le
    with Mock() as m:
        rc, txt = run_cli(CP, "--create", "--host", m.host, "--framesize", "SVGA", "--quality", "20", "--out", str(out), *EXPLICIT_SET)
        f = one_profile_file(out)
        check(rc == 0 and f is not None, "--create khong --id: rc 0 (ID mac dinh hop le)", (rc, txt.strip().splitlines()[-1:]))
        if f:
            prof = read_json(f)
            ok, errs = cp.validate_profile(prof)
            check(ok and cp.validate_camera_profile_id(prof["camera_profile_id"], "SVGA", 20) == "", "ho so tu sinh qua ca hop dong ID moi", errs)
            check(prof["board"] == cp.BOARD_NAME and prof["sensor"] == cp.SENSOR_NAME and len(prof["source"]["commit"]) == 40,
                  "board/sensor/source.commit tu sinh dung hop dong", (prof["board"], prof["sensor"]))
    end()


# ----------------------------------------------------------------------
# V5 - Vong 4 cua Tester theo 01_PLAN.md Phu luc Vong 5 (V5-T1..T7)
# ----------------------------------------------------------------------

def v5a(pf):
    begin("V5a", "V5-T3 bon gia tri hieu chinh bat buoc: thieu bat ky truong nao -> rc 2, 0 HTTP, khong tep; du bon -> rc 0")
    out = tmpdir("v5a")
    # thieu ca bon
    with Mock() as m:
        rc, txt = create(m.host, out, "VGA", 10, explicit=False)
        c = counts(m.host)
        check(rc == 2 and c == {"control": 0, "capture": 0, "status": 0} and list(out.glob("*.json")) == [],
              "thieu ca bon: rc 2, 0 HTTP, khong tep", (rc, c, txt.strip().splitlines()[-1:]))
        for k in cp.REQUIRED_EXPLICIT_CONTROLS:
            check(k in txt, "thong diep neu ten truong '%s'" % k)
    # thieu dung MOT truong, lan luot
    for miss in cp.REQUIRED_EXPLICIT_CONTROLS:
        with Mock() as m:
            sets = [x for k, v in EXPLICIT_VALUES.items() if k != miss for x in ("--set", "%s=%d" % (k, v))]
            rc, txt = create(m.host, out, "VGA", 10, *sets, explicit=False)
            c = counts(m.host)
            check(rc == 2 and miss in txt and c["control"] == 0,
                  "thieu rieng '%s': rc 2, neu dung ten, 0 /control" % miss, (rc, c, txt.strip().splitlines()[-1:]))
            others = [k for k in cp.REQUIRED_EXPLICIT_CONTROLS if k != miss]
            check(not any(("%s," % o) in txt or txt.rstrip().endswith(o) for o in others) or txt.count(miss) >= 1,
                  "thong diep tap trung vao truong thieu, khong liet ke truong da co", [l for l in txt.splitlines() if "thieu" in l][:1])
    # du bon -> chay duoc
    with Mock() as m:
        rc, txt = create(m.host, out, "VGA", 10)
        f = one_profile_file(out)
        check(rc == 0 and f is not None, "du bon gia tri: rc 0, ghi tep", (rc, f))
        if f:
            prof = read_json(f)
            check(all(prof["controls"][k] == v for k, v in EXPLICIT_VALUES.items()),
                  "ho so luu dung bon gia tri da truyen", {k: prof["controls"].get(k) for k in EXPLICIT_VALUES})
    end()


def v5b(pf):
    begin("V5b", "V5-T2/T3 mien CONTROL_DOMAINS: dau mut hop le, ngoai mien bi chan TRUOC HTTP, ca --create lan doc ho so")
    out = tmpdir("v5b")
    # dau mut hop le qua duoc
    # Vong 5 (Tester) doi ky vong theo hai bat bien moi cua Coder Vong 6:
    #  L08 - aec_value co tran 783 cho VGA/SVGA (1200 khong con la dau mut hop le o VGA)
    #  L10 - wb_mode > 0 doi awb_gain=1 (cap wb_mode=4 + awb_gain=0 nay la mo ho)
    # Vong 6 (L11): wb_mode hop le chi con 1..4 (dau mut 1 va 4), awb_gain chi con 1.
    # wb_mode=0 va awb_gain=0 chuyen sang nhom BI CHAN ngay duoi.
    for k, v, extra in (("aec_value", 0, ()), ("aec_value", 783, ()), ("agc_gain", 0, ()), ("agc_gain", 30, ()),
                        ("wb_mode", 1, ()), ("wb_mode", 4, ()), ("awb_gain", 1, ())):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--set", "%s=%d" % (k, v), *extra)
            check(rc == 0, "dau mut %s=%d -> rc 0" % (k, v), (rc, txt.strip().splitlines()[-1:]))
    # ngoai mien bi chan, 0 HTTP
    for k, v in (("aec_value", -1), ("aec_value", 1201), ("agc_gain", -1), ("agc_gain", 31),
                 ("wb_mode", -1), ("wb_mode", 5), ("awb_gain", -1), ("awb_gain", 2)):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--set", "%s=%d" % (k, v))
            c = counts(m.host)
            check(rc == 2 and k in txt and "mien" in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "%s=%d -> rc 2, neu mien, 0 HTTP" % (k, v), (rc, c, txt.strip().splitlines()[-1:]))
    # Vong 6 (L11): trong MIEN phan cung nhung trai hop dong ho so co dinh -> bi chan, ly do L11 chu khong phai "mien"
    for k, v in (("wb_mode", 0), ("awb_gain", 0)):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--set", "%s=%d" % (k, v))
            c = counts(m.host)
            check(rc == 2 and k in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "%s=%d (trong mien, trai hop dong L11) -> rc 2, neu ten truong, 0 HTTP" % (k, v), (rc, c, txt.strip().splitlines()[-1:]))
    # doc ho so co control ngoai mien: --verify va capture deu chan, 0 HTTP
    d = tmpdir("v5b_p")
    root = tmpdir("v5b_s")
    for i, (k, v) in enumerate((("agc_gain", 31), ("wb_mode", 5), ("aec_value", 1201), ("vflip", 2), ("brightness", 3), ("saturation", -3))):
        prof = cp.build_profile_dict("VGA", 10, dict(FULL_CONTROLS, **{k: v}), dict(GOOD_REGS), "x")
        fn = d / ("%s_%d.json" % (k, i))
        fn.write_text(json.dumps(prof), encoding="utf-8")
        with Mock() as m:
            rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(fn))
            c = counts(m.host)
            check(rc == 1 and k in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "--verify ho so %s=%d: rc 1, neu ten, 0 HTTP" % (k, v), (rc, c, [l for l in txt.splitlines() if k in l][:1]))
            rc2, _ = capture(m.host, root, "s%d" % i, str(fn), 2)
            sess = read_json(root / ("s%d" % i) / "session.json")
            check(rc2 == 1 and k in sess["result"]["reason"] and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
                  "capture --profile %s=%d: rc 1, status error, 0 HTTP" % (k, v), (rc2, sess["result"]["reason"][:90]))
    end()


def v5c(pf):
    begin("V5c", "V5-T2 ID retry _rNN: --create lien tiep cung cau hinh/ngay khong ghi de; --id nguoi dung tu dat van bi tu choi khi trung")
    out = tmpdir("v5c")
    ids = []
    for i in range(3):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10)
            f = sorted(out.glob("*.json"))
            check(rc == 0, "lan %d: rc 0" % (i + 1), (rc, txt.strip().splitlines()[-1:]))
            ids = [x.stem for x in f]
    check(len(ids) == 3, "ba tep rieng biet, khong ghi de", ids)
    base = cp.make_profile_id("VGA", 10)
    check(base in ids and (base + "_r01") in ids and (base + "_r02") in ids,
          "dung thu tu goc, _r01, _r02", ids)
    for x in ids:
        prof = read_json(out / (x + ".json"))
        ok, errs = cp.validate_profile(prof)
        check(ok and prof["camera_profile_id"] == x, "ho so '%s' hop le, ID = ten tep" % x, errs)
    # --id nguoi dung tu dat: trung thi tu choi, KHONG tu them hau to
    with Mock() as m:
        rc, txt = create(m.host, out, "VGA", 10, "--id", base)
        check(rc == 2 and "da ton tai" in txt, "--id tu dat va trung -> rc 2 'da ton tai', khong tu them hau to", (rc, txt.strip().splitlines()[-1:]))
    # --id tu dat co hau to _rNN hop le van dung duoc
    with Mock() as m:
        rc, txt = create(m.host, out, "VGA", 10, "--id", base + "_r50")
        check(rc == 0 and (out / (base + "_r50.json")).exists(), "--id voi hau to _r50 hop le -> rc 0", (rc, txt.strip().splitlines()[-1:]))
    for bad in (base + "_r0", base + "_r1", base + "_r100", base + "_rAB"):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--id", bad)
            check(rc == 2 and "camera_profile_id" in txt and counts(m.host)["control"] == 0,
                  "--id hau to sai '%s' -> rc 2, 0 /control" % bad.split("_")[-1], (rc, txt.strip().splitlines()[-1:]))
    end()


def v5d(pf):
    begin("V5d", "V5-T4/T5 --probe: duong tot, cong thuc ung vien, khong tao ho so; loi thieu register / JSON hong / 503 giua chung / control bi tu choi")
    out = tmpdir("v5d")
    # (a) duong tot: mock mac dinh 0x3500=12544, 0x350a=248
    with Mock() as m:
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "5", "--interval", "0", "--out", str(out))
        c = counts(m.host)
        check(rc == 0, "probe rc 0", (rc, txt.strip().splitlines()[-3:]))
        # Vong 6 (L11): probe dat du 5 control (aec, agc, awb, awb_gain, wb_mode=0 cuoi) de thuc su ve tu dong
        check(c["control"] == 5 and c["status"] == 5, "dung 5 /control (aec/agc/awb/awb_gain=1, wb_mode=0) va 5 /status", c)
        check(list(out.glob("probe_*.json")), "co tep log probe_*.json", sorted(x.name for x in out.glob("*")))
        logf = sorted(out.glob("probe_*.json"))[0]
        lg = read_json(logf)
        check(lg["ok"] is True and len(lg["samples"]) == 5, "log ghi du 5 mau, ok=True", (lg["ok"], len(lg["samples"])))
        cand = lg["candidates"]
        # Vong 6 (L08): probe kep ung vien ve tran thiet bi 783 va ghi ro da kep
        check(cand["median_0x3500"] == 12544 and cand.get("aec_value_raw") == 784
              and cand["aec_value"] == 783 and cand.get("aec_value_effective") == 783
              and cand.get("aec_value_cap") == 783 and cand.get("aec_value_clamped") is True,
              "ung vien tho 784 -> kep ve tran 783, co aec_value_clamped (L08)", cand)
        check("DA KEP" in txt and "783" in txt, "stdout noi ro da kep ve tran", [l for l in txt.splitlines() if "KEP" in l][:1])
        check(cand["median_0x350a"] == 248 and cand["agc_gain"] == round((248 + 1) / 16),
              "ung vien agc_gain = round((0x350a+1)/16)", cand)
        check(lg.get("verified") is None and "verified" not in str(cand).lower(), "probe khong tu danh dau da xac minh")
        # khong tao ho so camera nao
        check(list(out.glob("cam_*.json")) == [], "probe KHONG tao ho so camera", sorted(x.name for x in out.glob("*")))
        # camera con o trang thai tu dong sau probe (probe khong tu tra ve)
        import requests
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        check(st["aec"] == 1 and st["agc"] == 1 and st["awb"] == 1 and st.get("wb_mode") == 0 and st.get("0x3406") == 0,
              "sau probe camera CON o trang thai tu dong (tai lieu da canh bao)", {k: st[k] for k in ("aec", "agc", "awb")})
        check("CANH BAO" in txt and "tu dong" in txt.lower(), "stdout co canh bao trang thai tu dong", [l for l in txt.splitlines() if "CANH BAO" in l])
    # (b) cong thuc voi gia tri khac
    with Mock("--registers", "0x3500=8000,0x350a=31") as m:
        out2 = tmpdir("v5d_b")
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0", "--out", str(out2))
        lg = read_json(sorted(out2.glob("probe_*.json"))[0])
        check(rc == 0 and lg["candidates"]["aec_value"] == 500 and lg["candidates"]["agc_gain"] == 2,
              "0x3500=8000 -> aec_value 500; 0x350a=31 -> agc_gain 2", lg["candidates"])
    # (c) thieu thanh ghi trong /status
    with Mock("--status-drop-fields", "0x350a") as m:
        out3 = tmpdir("v5d_c")
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0", "--out", str(out3))
        check(rc == 1 and "0x350a" in txt and "thieu" in txt, "thieu 0x350a -> rc 1, neu ten thanh ghi", (rc, [l for l in txt.splitlines() if "0x350a" in l][:1]))
        lg = read_json(sorted(out3.glob("probe_*.json"))[0])
        check(lg["ok"] is False and lg["error"] and lg["candidates"] is None, "log ghi that bai, khong co ung vien", (lg["ok"], lg["candidates"]))
    # (d) /status khong phai JSON
    with Mock("--status-mode", "invalid") as m:
        out4 = tmpdir("v5d_d")
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0", "--out", str(out4))
        check(rc == 1 and "JSON" in txt, "/status khong phai JSON -> rc 1", (rc, [l for l in txt.splitlines() if "JSON" in l][:1]))
    # (e) 503 o mau thu 3, giu nguyen mau da nhan
    with Mock("--status-fail-at-count", "3") as m:
        out5 = tmpdir("v5d_e")
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "5", "--interval", "0", "--out", str(out5))
        lg = read_json(sorted(out5.glob("probe_*.json"))[0])
        check(rc == 1 and "mau 3/5" in txt and "503" in txt, "503 o mau 3 -> rc 1, neu dung so mau", (rc, [l for l in txt.splitlines() if "mau 3" in l][:1]))
        check(len(lg["samples"]) == 2 and lg["ok"] is False, "hai mau da nhan duoc GIU NGUYEN trong log", (len(lg["samples"]), lg["ok"]))
    # (f) /control bi tu choi ngay dau
    with Mock("--fail-controls", "aec") as m:
        out6 = tmpdir("v5d_f")
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0", "--out", str(out6))
        c = counts(m.host)
        check(rc == 1 and "aec" in txt and c["status"] == 0, "control aec bi 500 -> rc 1, khong doc /status nao", (rc, c))
    # (g) tham so sai bi chan truoc HTTP
    for extra, label in ((("--samples", "0"), "samples 0"), (("--timeout", "0"), "timeout 0"), (("--timeout", "inf"), "timeout inf")):
        with Mock() as m:
            rc, txt = run_cli(CP, "--probe", "--host", m.host, "--interval", "0", *extra)
            check(rc == 2 and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
                  "probe %s -> rc 2, 0 HTTP" % label, (rc, counts(m.host)))
    end()


def v5e(pf):
    begin("V5e", "V5-T6 thong ke mau RGB cua sharpness.py: anh xam / am tung kenh / toi / bao hoa; chi so do net cu khong hoi quy")
    import numpy as np
    from PIL import Image
    import importlib
    sp = importlib.import_module("sharpness")
    d = tmpdir("v5e")

    def synth(name, rgb):
        a = np.zeros((64, 64, 3), dtype=np.uint8)
        a[:, :] = rgb
        Image.fromarray(a).save(d / name, quality=95)
        return np.asarray(Image.open(d / name).convert("RGB"))

    # metrics_rgb_on_roi() nhan ROI DA CAT (HxWx3 float), khong nhan toa do
    def met(name, rgb):
        return sp.metrics_rgb_on_roi(synth(name, rgb).astype(float))

    r = met("gray.jpg", (128, 128, 128))
    check(abs(r["mean_r"] - r["mean_g"]) < 3 and abs(r["mean_g"] - r["mean_b"]) < 3, "anh xam: ba kenh gan bang nhau", (round(r["mean_r"],1), round(r["mean_g"],1), round(r["mean_b"],1)))
    check(r["channel_spread_pct"] < 5, "anh xam: channel_spread_pct gan 0", round(r["channel_spread_pct"], 3))
    check(r["dark_frac_rgb"] == 0 and r["sat_frac_rgb"] == 0, "anh xam: khong clipping", (r["dark_frac_rgb"], r["sat_frac_rgb"]))

    r = met("green.jpg", (40, 160, 40))
    check(r["channel_spread_pct"] > 50, "am luc: channel_spread_pct > 50%", round(r["channel_spread_pct"], 1))
    check(r["mean_g"] > r["mean_r"] and r["mean_g"] > r["mean_b"], "am luc: kenh G troi nhat", (round(r["mean_r"],1), round(r["mean_g"],1), round(r["mean_b"],1)))

    r = met("dark.jpg", (2, 2, 2))
    check(r["dark_frac_rgb"] > 0.9 and r["sat_frac_rgb"] == 0, "anh toi: dark_frac_rgb > 0.9, sat 0", (r["dark_frac_rgb"], r["sat_frac_rgb"]))

    r = met("white.jpg", (254, 254, 254))
    check(r["sat_frac_rgb"] > 0.9 and r["dark_frac_rgb"] == 0, "anh trang: sat_frac_rgb > 0.9, dark 0", (r["sat_frac_rgb"], r["dark_frac_rgb"]))

    r = met("redsat.jpg", (254, 100, 100))
    check(r["sat_frac_rgb"] > 0.9, "chi kenh R bao hoa: van tinh vao sat_frac_rgb (bat ky kenh nao)", r["sat_frac_rgb"])

    # spread khi mean = 0 (anh den tuyet doi): khong chia cho 0
    import numpy as _np
    r = sp.metrics_rgb_on_roi(_np.zeros((8, 8, 3), dtype=float))
    check(r["channel_spread_pct"] == 0.0 and r["dark_frac_rgb"] == 1.0, "anh den tuyet doi: spread 0 (khong chia 0), dark_frac 1", (r["channel_spread_pct"], r["dark_frac_rgb"]))

    for bad, label in ((_np.zeros((8, 8), dtype=float), "mang 2 chieu"), (_np.zeros((8, 8, 4), dtype=float), "mang 4 kenh")):
        try:
            sp.metrics_rgb_on_roi(bad)
            check(False, "%s -> phai bao ValueError" % label)
        except ValueError:
            check(True, "%s -> bao ValueError dung" % label)

    # khong hoi quy chi so cu: chay tren phien that 17/09
    rc, txt = run_cli(str(REPO_ROOT / "pc" / "sharpness.py"), "capture_qh_250mm", "--roi", "center")
    check(rc == 0 and "11.2" in txt, "phien 17/09 giu nguyen lap_var trung vi 11.2 (khong hoi quy)", [l for l in txt.splitlines() if "capture_qh_250mm" in l][:1])
    check("mean_r" in txt or "spread" in txt.lower(), "bang tom tat co cot mau moi", [l for l in txt.splitlines()[:3]])
    end()


# ----------------------------------------------------------------------
# V6 - Vong 5 cua Tester theo 01_PLAN.md Phu luc Vong 6 (L08, L10)
# ----------------------------------------------------------------------

def v6a(pf):
    begin("V6a", "L08 tran aec_value 783: chan truoc HTTP cho VGA/SVGA, KHONG chan framesize khac; ho so co aec_value>783 bi tu choi ca khi doc")
    out = tmpdir("v6a")
    # (1) --create: tran ap dung cho VGA va SVGA
    for fs in ("VGA", "SVGA"):
        with Mock() as m:
            rc, txt = create(m.host, out, fs, 10, "--set", "aec_value=784")
            c = counts(m.host)
            check(rc == 2 and "783" in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "%s aec_value=784 -> rc 2, neu tran 783, 0 HTTP" % fs, (rc, c, txt.strip().splitlines()[-1:]))
        with Mock() as m:
            rc, txt = create(m.host, out, fs, 10, "--set", "aec_value=783")
            check(rc == 0, "%s aec_value=783 (dung tran) -> rc 0" % fs, (rc, txt.strip().splitlines()[-1:]))
    # (2) framesize ngoai danh sach cap: KHONG bi chan o tang validate (tran 783 moi
    # chi do tren VGA/SVGA, khong suy dien cho framesize chua do). Lenh van di toi
    # HTTP; o mock thi readback kep 783 nen truot o buoc doi chieu - dung nhu the,
    # vi do la su that thiet bi bao chu khong phai gia dinh cua ma.
    with Mock() as m:
        rc, txt = create(m.host, out, "QVGA", 10, "--set", "aec_value=1200")
        c = counts(m.host)
        check(rc != 2 and "vuot tran" not in txt, "QVGA aec_value=1200: KHONG bi chan o tang validate (khong suy dien tran)", (rc, txt.strip().splitlines()[-1:]))
        check(c["control"] > 0, "QVGA: lenh di toi HTTP that", c)
        check(rc == 1 and "aec_value: yeu cau 1200" in txt, "QVGA: truot o doi chieu readback voi gia tri bo bao lai", [l for l in txt.splitlines() if "yeu cau 1200" in l][:1])
    # (3) doc ho so co aec_value > tran
    d = tmpdir("v6a_p")
    root = tmpdir("v6a_s")
    prof = cp.build_profile_dict("VGA", 10, dict(FULL_CONTROLS, aec_value=900), dict(GOOD_REGS), "x")
    (d / "over.json").write_text(json.dumps(prof), encoding="utf-8")
    with Mock() as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / "over.json"))
        check(rc == 1 and "aec_value" in txt and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
              "--verify ho so aec_value=900: rc 1, 0 HTTP", (rc, [l for l in txt.splitlines() if "aec_value" in l][:1]))
        rc2, _ = capture(m.host, root, "s1", str(d / "over.json"), 2)
        sess = read_json(root / "s1" / "session.json")
        check(rc2 == 1 and "aec_value" in sess["result"]["reason"] and sess.get("status") == "error"
              and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
              "capture --profile ho so aec_value=900: rc 1, status error, 0 HTTP", (rc2, sess["result"]["reason"][:90]))
    end()


def v6b(pf):
    begin("V6b", "L10 bat bien wb_mode/awb_gain: wb_mode>0 doi awb_gain=1; bon preset cho bon bo thanh ghi gain mau khac nhau")
    out = tmpdir("v6b")
    # (1) cap mo ho bi chan truoc HTTP
    for w in (1, 2, 3, 4):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--set", "wb_mode=%d" % w, "--set", "awb_gain=0")
            c = counts(m.host)
            check(rc == 2 and "awb_gain" in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "wb_mode=%d + awb_gain=0 -> rc 2, 0 HTTP" % w, (rc, c, txt.strip().splitlines()[-1:]))
    # (2) Vong 5: wb_mode=0 + awb_gain=0 la cap hop le (khong chon preset). Vong 6 (L11):
    # ho so co dinh bat buoc chon mot preset 1..4, nen cap nay BI CHAN truoc HTTP.
    with Mock() as m:
        rc, txt = create(m.host, out, "VGA", 10, "--set", "wb_mode=0", "--set", "awb_gain=0")
        check(rc == 2 and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
              "wb_mode=0 + awb_gain=0 -> rc 2, 0 HTTP (L11: ho so co dinh phai chon preset)", (rc, txt.strip().splitlines()[-1:]))
    # (3) bon preset cho bon bo thanh ghi KHAC NHAU (mock mo phong bang driver)
    regs = {}
    for w in (1, 2, 3, 4):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--set", "wb_mode=%d" % w, "--set", "awb_gain=1")
            check(rc == 0, "preset wb_mode=%d + awb_gain=1 -> rc 0" % w, (rc, txt.strip().splitlines()[-1:]))
            import requests
            st = requests.get("http://%s/status" % m.host, timeout=5).json()
            regs[w] = (st.get("0x3400"), st.get("0x3402"), st.get("0x3404"), st.get("0x3406"))
            check(st.get("0x3406") == 1, "preset %d: 0x3406=1 (AWB manual)" % w, st.get("0x3406"))
    check(len(set(regs.values())) == 4, "bon preset cho BON bo thanh ghi gain mau khac nhau", regs)
    for w, v in regs.items():
        check(all(x is not None for x in v), "preset %d co du ba thanh ghi gain mau" % w, v)
    # (4) doc ho so co cap mo ho
    d = tmpdir("v6b_p")
    root = tmpdir("v6b_s")
    prof = cp.build_profile_dict("VGA", 10, dict(FULL_CONTROLS, wb_mode=2, awb_gain=0), dict(mc.DEFAULT_REGISTERS, **cp.WB_MODE_REGISTERS[2]), "x")
    (d / "amb.json").write_text(json.dumps(prof), encoding="utf-8")
    with Mock() as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / "amb.json"))
        check(rc == 1 and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
              "--verify ho so wb_mode=2/awb_gain=0: rc 1, 0 HTTP", (rc, [l for l in txt.splitlines() if "awb_gain" in l][:1]))
        rc2, _ = capture(m.host, root, "s1", str(d / "amb.json"), 2)
        sess = read_json(root / "s1" / "session.json")
        check(rc2 == 1 and sess.get("status") == "error" and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
              "capture --profile ho so mo ho: rc 1, status error, 0 HTTP", (rc2, sess["result"]["reason"][:90]))
    end()


# ----------------------------------------------------------------------
# V7 - Vong 6 cua Tester theo 01_PLAN.md Vong 7 (L11, V7-T1..T6)
# ----------------------------------------------------------------------

def _wb_of(st):
    return {k: st.get(k) for k in ("0x3400", "0x3402", "0x3404", "0x3406")}


def v7a(pf):
    begin("V7a", "V7-T1 VGA/SVGA x preset 1..4 voi awb=1/awb_gain=1: create -> verify -> capture 5 anh rc 0; bon thanh ghi WB dung bang, 0x3406=1, verified=null")
    out = tmpdir("v7a")
    root = tmpdir("v7a_s")
    for fs, w in (("VGA", 1), ("VGA", 4), ("SVGA", 2), ("SVGA", 3)):
        with Mock() as m:
            rc, txt = create(m.host, out, fs, 10, "--set", "wb_mode=%d" % w, "--set", "awb_gain=1", "--set", "awb=1")
            files = sorted(out.glob("cam_%s_q10_*.json" % fs))
            check(rc == 0 and files, "%s preset %d: --create rc 0" % (fs, w), (rc, txt.strip().splitlines()[-1:]))
            if not files:
                continue
            f = max(files, key=lambda x: x.stat().st_mtime)
            prof = read_json(f)
            ok, errs = cp.validate_profile(prof)
            check(ok and prof["verified"] is None, "%s preset %d: ho so hop le, verified=null" % (fs, w), errs)
            check(prof["controls"]["awb"] == 1 and prof["controls"]["awb_gain"] == 1 and prof["controls"]["wb_mode"] == w
                  and prof["controls"]["aec"] == 0 and prof["controls"]["agc"] == 0,
                  "%s preset %d: controls aec=agc=0, awb=awb_gain=1, wb_mode=%d" % (fs, w, w),
                  {k: prof["controls"][k] for k in ("aec", "agc", "awb", "awb_gain", "wb_mode")})
            check(_wb_of(prof["expected_registers"]) == cp.WB_MODE_REGISTERS[w],
                  "%s preset %d: expected_registers WB = bang preset" % (fs, w), _wb_of(prof["expected_registers"]))
            rc2, txt2 = run_cli(CP, "--verify", "--host", m.host, "--profile", str(f))
            check(rc2 == 0, "%s preset %d: --verify rc 0" % (fs, w), (rc2, txt2.strip().splitlines()[-1:]))
            sid = "s_%s_%d" % (fs, w)
            rc3, _ = capture(m.host, root, sid, str(f), 5)
            sess = read_json(root / sid / "session.json")
            check(rc3 == 0 and sess.get("status") == "completed" and len(img_files(root / sid)) == 5,
                  "%s preset %d: capture 5 anh rc 0, completed" % (fs, w), (rc3, sess["result"].get("reason")))
            end_st = sess["camera_status_end"]["json"]
            check(_wb_of(end_st) == cp.WB_MODE_REGISTERS[w] and end_st.get("awb") == 1,
                  "%s preset %d: status_end WB dung bang, awb=1" % (fs, w), _wb_of(end_st))
    end()


def v7b(pf):
    begin("V7b", "V7-T2 control sai hop dong L11 bi chan TRUOC HTTP o ca --create, --verify va capture --profile")
    out = tmpdir("v7b")
    # (1) --create: tung tri sai qua --set
    for spec, field in (("aec=1", "aec"), ("agc=1", "agc"), ("awb=0", "awb"), ("awb=2", "awb"),
                        ("awb_gain=0", "awb_gain"), ("wb_mode=0", "wb_mode"), ("wb_mode=5", "wb_mode")):
        with Mock() as m:
            rc, txt = create(m.host, out, "VGA", 10, "--set", spec)
            c = counts(m.host)
            check(rc == 2 and field in txt and c == {"control": 0, "capture": 0, "status": 0},
                  "--create --set %s -> rc 2, neu '%s', 0 HTTP" % (spec, field), (rc, c, txt.strip().splitlines()[-1:]))
    check(list(out.glob("*.json")) == [], "khong tep ho so nao duoc ghi", sorted(x.name for x in out.glob("*")))
    # (2) doc ho so sai: kiem ca kieu bool ma CLI --set khong the tao ra
    good = read_json(pf)
    d = tmpdir("v7b_p")
    root = tmpdir("v7b_s")
    bad = {
        "awb0_cu.json": (dict(good, controls=dict(good["controls"], awb=0)), "awb"),
        "awb_true.json": (dict(good, controls=dict(good["controls"], awb=True)), "awb"),
        "awb2.json": (dict(good, controls=dict(good["controls"], awb=2)), "awb"),
        "wb0.json": (dict(good, controls=dict(good["controls"], wb_mode=0)), "wb_mode"),
        "gain0.json": (dict(good, controls=dict(good["controls"], awb_gain=0)), "awb_gain"),
        "aec1.json": (dict(good, controls=dict(good["controls"], aec=1)), "aec"),
    }
    for i, (fn, (prof, field)) in enumerate(bad.items()):
        (d / fn).write_text(json.dumps(prof), encoding="utf-8")
        h0 = sha(d / fn)
        with Mock() as m:
            rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / fn))
            check(rc == 1 and field in txt and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
                  "--verify %s: rc 1, neu '%s', 0 HTTP" % (fn, field), (rc, [l for l in txt.splitlines() if field in l][:1]))
            rc2, _ = capture(m.host, root, "s%d" % i, str(d / fn), 2)
            sess = read_json(root / ("s%d" % i) / "session.json")
            check(rc2 == 1 and sess.get("status") == "error" and field in sess["result"]["reason"]
                  and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
                  "capture --profile %s: rc 1, status error, 0 HTTP" % fn, (rc2, sess["result"]["reason"][:100]))
        check(sha(d / fn) == h0, "%s: tep nguon khong bi sua" % fn)
    # ho so awb=0 CU phai duoc bao ly do L11 va de nghi tao ho so moi, khong tu sua
    with Mock() as m:
        rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / "awb0_cu.json"))
        check("L11" in txt, "ho so awb=0 cu: thong diep neu L11 (de nguoi dung biet vi sao)", [l for l in txt.splitlines() if "awb" in l][:1])
    end()


def v7c(pf):
    begin("V7c", "V7-T3 ho so dung controls nhung thanh ghi WB sai (0x3406=0, thieu, bool, gain khac preset): rc != 0, 0 HTTP, tep nguon nguyen")
    good = read_json(pf)
    d = tmpdir("v7c")
    root = tmpdir("v7c_s")
    r_ok = dict(good["expected_registers"])
    missing = {k: v for k, v in r_ok.items() if k != "0x3406"}
    cases = {
        "manual0.json": dict(r_ok, **{"0x3406": 0}),
        "manual_true.json": dict(r_ok, **{"0x3406": True}),
        "gain_bool.json": dict(r_ok, **{"0x3400": True}),
        "preset3_trong_ho_so_preset1.json": dict(r_ok, **cp.WB_MODE_REGISTERS[3]),
        "mot_gain_lech.json": dict(r_ok, **{"0x3404": r_ok["0x3404"] + 16}),
        "thieu_0x3406.json": missing,
    }
    for i, (fn, regs) in enumerate(cases.items()):
        prof = dict(good, expected_registers=regs)
        (d / fn).write_text(json.dumps(prof), encoding="utf-8")
        h0 = sha(d / fn)
        ok, errs = cp.validate_profile(prof)
        check(not ok, "%s: validate_profile bao loi" % fn, errs[:2])
        with Mock() as m:
            rc, txt = run_cli(CP, "--verify", "--host", m.host, "--profile", str(d / fn))
            check(rc == 1 and counts(m.host) == {"control": 0, "capture": 0, "status": 0},
                  "--verify %s: rc 1, 0 HTTP" % fn, (rc, counts(m.host)))
            rc2, _ = capture(m.host, root, "s%d" % i, str(d / fn), 2)
            sess = read_json(root / ("s%d" % i) / "session.json")
            check(rc2 == 1 and sess.get("status") == "error" and counts(m.host) == {"control": 0, "capture": 0, "status": 0}
                  and img_files(root / ("s%d" % i)) == [],
                  "capture --profile %s: rc 1, status error, 0 HTTP, 0 anh" % fn, (rc2, sess["result"]["reason"][:100]))
        check(sha(d / fn) == h0, "%s: tep nguon khong bi sua (hash giu nguyen)" % fn)
    end()


def v7d(pf):
    begin("V7d", "V7-T4 thiet bi: control bao OK nhung thanh ghi WB khong doi; wb_mode 500; timeout; /status khong JSON sau ap -> FAIL, khong ghi ho so")
    out = tmpdir("v7d")
    # (1) thanh ghi WB ket: HTTP 200, /status echo control dung, nhung 0x3406/gain khong doi
    with Mock("--wb-registers-stuck") as m:
        rc, txt = create(m.host, out, "VGA", 10)
        c = counts(m.host)
        check(rc == 1 and "KHONG tao ho so" in txt and "L11" in txt, "--wb-registers-stuck: rc 1, 'KHONG tao ho so' kem dong (L11)",
              (rc, [l for l in txt.splitlines() if "L11" in l][:2]))
        check(c["control"] == 16 and c["status"] == 1, "da gui du 16 /control roi doc 1 /status moi phat hien", c)
        check(list(out.glob("*.json")) == [], "KHONG co tep ho so nao duoc ghi")
    # (2) wb_mode tra 500 -> dung dung o lenh do, khong gui lenh sau
    order = ["framesize", "quality"] + cp.CONTROL_ORDER
    k = order.index("wb_mode") + 1
    with Mock("--fail-controls", "wb_mode") as m:
        rc, txt = create(m.host, out, "VGA", 10)
        c = counts(m.host)
        check(rc == 1 and c["control"] == k and c["status"] == 0 and "wb_mode" in txt,
              "wb_mode 500: rc 1, dung o lenh thu %d, 0 /status" % k, (rc, c))
    # (3) timeout o awb_gain
    class SlowAt(mc.H):
        def do_GET(self):
            if self.path.startswith("/control") and "var=awb_gain" in self.path:
                time.sleep(1.5)
            return mc.H.do_GET(self)
    with InProcMock(SlowAt) as m:
        rc, txt = create(m.host, out, "VGA", 10, "--timeout", "0.5")
        time.sleep(2.0)
        k2 = order.index("awb_gain") + 1
        check(rc == 1 and "awb_gain" in txt and "Timeout" in txt and mc.STATE["counts"]["control"] == k2,
              "timeout o awb_gain: rc 1, dung dung lenh thu %d" % k2, (rc, mc.STATE["counts"]))
    # (4) /status khong phai JSON sau khi ap
    with Mock("--status-mode", "invalid") as m:
        rc, txt = create(m.host, out, "VGA", 10)
        check(rc == 1 and "JSON" in txt, "/status khong JSON sau ap: rc 1", (rc, [l for l in txt.splitlines() if "JSON" in l][:1]))
    check(list(out.glob("*.json")) == [], "sau bon ca loi: van KHONG co tep ho so nao")
    end()


def v7e(pf):
    begin("V7e", "V7-T5 drift WB giua phien (0x3406, mot gain) va V7-T6 chuyen trang thai preset 4 -> probe -> preset 1")
    root = tmpdir("v7e_s")
    # (1) V7-T5: drift rieng 0x3406, rieng mot gain mau
    for i, reg in enumerate(("0x3406", "0x3402")):
        with Mock("--drift-registers", reg, "--drift-after", "3") as m:
            sid = "d%d" % i
            rc, _ = capture(m.host, root, sid, pf, 5)
            sess = read_json(root / sid / "session.json")
            r = sess["result"]
            check(rc == 1 and sess.get("status") == "error" and reg in r["reason"],
                  "drift %s tu anh 3: capture rc 1, status error, reason neu %s" % (reg, reg), (rc, r["reason"][:110]))
            check(len(img_files(root / sid)) == 5, "drift %s: 5 anh da chup van giu" % reg, len(img_files(root / sid)))
            # khong ap lai truoc status cuoi de che drift: so /control trong phien = 16 (mot lan ap)
            check(counts(m.host)["control"] == 16, "drift %s: chi ap ho so MOT lan (16 /control), khong ap lai de che" % reg, counts(m.host))
    # (2) V7-T6: tu preset 4 -> probe -> preset 1, cung mot tien trinh mock
    out = tmpdir("v7e_out")
    with Mock() as m:
        import requests
        rc, _ = create(m.host, out, "VGA", 10, "--set", "wb_mode=4")
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        check(rc == 0 and st.get("0x3406") == 1 and st.get("wb_mode") == 4, "tien de: bo dang o preset 4, 0x3406=1", _wb_of(st))
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0", "--out", str(out))
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        check(rc == 0, "probe tu preset 4: rc 0", (rc, txt.strip().splitlines()[-2:]))
        check(st.get("0x3406") == 0 and st.get("wb_mode") == 0 and st.get("awb") == 1 and st.get("aec") == 1 and st.get("agc") == 1,
              "sau probe: THUC SU ve tu dong (0x3406=0, wb_mode=0, aec/agc/awb=1)", {k: st.get(k) for k in ("0x3406", "wb_mode", "aec", "agc", "awb")})
        lg = read_json(sorted(out.glob("probe_*.json"))[-1])
        check(lg.get("auto_state") is not None and lg["ok"] is True, "log probe co auto_state, ok=True", lg.get("auto_state"))
        rc, _ = create(m.host, out, "VGA", 10, "--set", "wb_mode=1")
        st = requests.get("http://%s/status" % m.host, timeout=5).json()
        check(rc == 0 and _wb_of(st) == cp.WB_MODE_REGISTERS[1], "tao preset 1 sau probe: ve lai 0x3406=1 va dung bang preset 1", _wb_of(st))
    # (3) reset bi bo qua: 0x3406 ket o 1 -> probe FAIL, khong phat ung vien
    with Mock("--registers", "0x3406=1", "--wb-registers-stuck") as m:
        out3 = tmpdir("v7e_stuck")
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0", "--out", str(out3))
        check(rc == 1 and "0x3406" in txt, "0x3406 ket o 1: probe rc 1, neu 0x3406", (rc, [l for l in txt.splitlines() if "0x3406" in l][:1]))
        logs = sorted(out3.glob("probe_*.json"))
        check(logs and read_json(logs[-1]).get("candidates") is None, "khong phat ung vien khi chua ve tu dong", read_json(logs[-1]).get("candidates") if logs else None)
    # (4) lenh reset loi HTTP
    with Mock("--fail-controls", "wb_mode") as m:
        rc, txt = run_cli(CP, "--probe", "--host", m.host, "--samples", "3", "--interval", "0")
        c = counts(m.host)
        check(rc == 1 and c["control"] == 5 and c["status"] == 0, "wb_mode 500 o lenh reset: probe rc 1, dung o lenh thu 5, 0 /status", (rc, c))
    end()


# ----------------------------------------------------------------------

ALL = [
    ("T1a", lambda c: c.__setitem__("pf", t1a())),
    ("T1b", lambda c: t1b(c["pf"])),
    ("T1c", lambda c: t1c(c["pf"])),
    ("T2a", lambda c: t2a()),
    ("T2b", lambda c: t2b()),
    ("T2c", lambda c: t2c()),
    ("T2d", lambda c: t2d()),
    ("T2e", lambda c: t2e(c["pf"])),
    ("T2f", lambda c: t2f()),
    ("T2g", lambda c: t2g()),
    ("T3a-c", lambda c: t3a_c()),
    ("T3d", lambda c: t3d(c["pf"])),
    ("T3e", lambda c: t3e()),
    ("T3f", lambda c: t3f(c["pf"])),
    ("T3g", lambda c: t3g(c["pf"])),
    ("T3h", lambda c: t3h(c["pf"])),
    ("T3i", lambda c: t3i(c["pf"])),
    ("T3j", lambda c: t3j()),
    ("T3l", lambda c: t3l()),
    ("T3m", lambda c: t3m(c["pf"])),
    ("T3n", lambda c: t3n()),
    ("T4a", lambda c: t4a(c["pf"])),
    ("T4b", lambda c: t4b(c["pf"])),
    ("T4c", lambda c: t4c(c["pf"])),
    ("T4e", lambda c: t4e(c["pf"])),
    ("TX1", lambda c: tx1(c["pf"])),
    ("TX2", lambda c: tx2(c["pf"])),
    ("TX3", lambda c: tx3()),
    ("TX4", lambda c: tx4(c["pf"])),
    ("TX5", lambda c: tx5()),
    ("V3a", lambda c: v3a(c["pf"])),
    ("V3b", lambda c: v3b(c["pf"])),
    ("V3d", lambda c: v3d(c["pf"])),
    ("V3e", lambda c: v3e(c["pf"])),
    ("V3f", lambda c: v3f(c["pf"])),
    ("V3g", lambda c: v3g(c["pf"])),
    ("V3h", lambda c: v3h(c["pf"])),
    ("V3i", lambda c: v3i(c["pf"])),
    ("V5a", lambda c: v5a(c["pf"])),
    ("V5b", lambda c: v5b(c["pf"])),
    ("V5c", lambda c: v5c(c["pf"])),
    ("V5d", lambda c: v5d(c["pf"])),
    ("V5e", lambda c: v5e(c["pf"])),
    ("V6a", lambda c: v6a(c["pf"])),
    ("V6b", lambda c: v6b(c["pf"])),
    ("V7a", lambda c: v7a(c["pf"])),
    ("V7b", lambda c: v7b(c["pf"])),
    ("V7c", lambda c: v7c(c["pf"])),
    ("V7d", lambda c: v7d(c["pf"])),
    ("V7e", lambda c: v7e(c["pf"])),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="danh sach ma kich ban, cach nhau boi dau phay (T1a luon chay truoc de co ho so)")
    ap.add_argument("--keep", action="store_true", help="giu thu muc tam sau khi chay")
    a = ap.parse_args()
    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    ctx = {}
    print("Python", sys.version.split()[0], "| tam:", TMP)
    t_all = time.time()
    try:
        for tid, fn in ALL:
            if only is not None and tid not in only and tid != "T1a":
                continue
            try:
                fn(ctx)
            except Exception as e:  # loi cua chinh bo test cung la FAIL, khong nuot
                import traceback
                traceback.print_exc()
                _CUR["fails"].append("ngoai le trong test: %s: %s" % (type(e).__name__, e))
                end()
    finally:
        if not a.keep:
            shutil.rmtree(TMP, ignore_errors=True)
    print()
    print("%-6s %-4s %s" % ("Ma", "KQ", "Kich ban"))
    n_pass = n_fail = 0
    for tid, name, status, detail in RESULTS:
        n_pass += status == "PASS"
        n_fail += status == "FAIL"
        print("%-6s %-4s %s" % (tid, status, name))
        if status == "FAIL":
            print("       -> %s" % detail)
    print()
    print("TONG: %d PASS, %d FAIL, %d kich ban, %.0f s" % (n_pass, n_fail, len(RESULTS), time.time() - t_all))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
