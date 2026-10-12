#!/usr/bin/env python3
"""Tester C5a - kiem bang chung bo that co the tai lap (01_PLAN Vong 7 muc 3, Vong 8 muc 5: V8-B1..V8-B4).

Chi doc tep bang chung da luu trong repo/build; khong mo COM/HTTP toi bo.
- E1 (V8-B1/R09): nguon log_4-10.docx (nguyen bytes, SHA, ban trich tai lap), lenh/output nap 04/10 (COM9, FQBN,
     --input-dir build/q6, 4 anh/offset/kich thuoc, 4x 'Hash of data verified'), SHA app = manifest 2 phien 04/10
     = bo luu archive_20261004_q6.
- E2 (V8-B2): 60 dong bo trong DOCX (loai selftest mock) doi chieu summary.json 3 luot Q6-T9 + 16 dong luot hong;
     tai kiem 60 JPEG 800x600, 5 header, Content-Length, t_frame > t_req, ID lien tuc, 1 Boot ID khop Serial,
     6 snapshot khop profile.
- E3 (V8-B3/R10): phien RST moi: chuoi bo luu -> upload (log goc) -> Serial boot -> 3 cap RST (truoc: anh/boot/ID;
     sau: Serial boot moi, /status, profile ap lai, JPEG hoi phuc 800x600 boot moi ID 1), thu tu thoi diem.
- E4 (V8-B4): ca am tren BAN SAO TAM (khong sua nguon that): DOCX doi byte, app trong bo luu bi doi, bo bang chung
     sau RST3, tron boot, thieu log nap, chi co dong mock -> checker phai bao loi.

Chay tu goc repo:  .venv/Scripts/python.exe pc/test_c5a_evidence.py
Bien moi truong: C5A_RST_SESSION (mac dinh docs/logs/c5a_q6_rst_20261006_201614). Thoat 0 khi khong co FAIL.
"""
import glob
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)
sys.path.insert(0, str(REPO))
from pc.camera_profile import diff_controls, compare_registers  # noqa: E402

R09 = Path("docs/logs/c5a-r09-recovered-20261005")
S_BAD = Path("docs/logs/c5a_q6_20261004_221728")
S_T9 = Path("docs/logs/c5a_q6_20261004_225200")
RST = Path(os.environ.get("C5A_RST_SESSION", "docs/logs/c5a_q6_rst_20261006_201614"))
DOCX_SHA = "94045e82421ed6895ea2d6c34fc0b29dbd1fc184caf2f2d8cb8b5124c36d9a2d"
APP_SHA = "e9dcc182af2e1c48a853c2c118878d5a96feb5bbe17c67f95ad6f68b2b847b3c"
PROFILE_SHA = "5c32b27b4e52a2518cba01caee03d19d95db1c31a0e8dde4fa315635ad85dbe6"
BOOT_0410 = "a37295f27df1a53a5b08d3d81544fb4b"
FLASH = [("0x00000000", 19968), ("0x00008000", 3072), ("0x0000e000", 8192), ("0x00010000", 1004880)]
HDR5 = ("x-frame-id", "x-boot-id", "x-timestamp", "x-request-timestamp", "x-discarded-frames")
RES = []


def check(cid, ok, title, detail=""):
    RES.append("PASS" if ok else "FAIL")
    print("  [%s] %s %s  | %s" % ("PASS" if ok else "FAIL", cid, title, detail))


def note(cid, title, detail=""):
    RES.append("NOTE")
    print("  [NOTE] %s %s  | %s" % (cid, title, detail))


def text(p):
    b = Path(p).read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16")
    return b.decode("utf-8-sig", errors="replace")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def docx_paras(b):
    xml = zipfile.ZipFile(io.BytesIO(b)).read("word/document.xml").decode("utf-8")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        t = "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, re.S))
        t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")
        if t.strip():
            out.append(t)
    return out


def headers(p):
    h = {}
    for ln in text(p).splitlines()[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            h.setdefault(k.strip().lower(), []).append(v.strip())
    return h


def jpeg(p, size=None):
    try:
        with Image.open(p) as im:
            im.load()
            return size is None or im.size == size, im.size
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# ---------------------------------------------------------------------------- E1 / E2: nguon R09 va 60 anh 04/10
def chk_r09(r09, s_bad, s_t9, archive_root=Path(".")):
    """Tra (van_de, so_lieu). Doc chi tu cac duong dan truyen vao (de chay ca am tren ban sao)."""
    bad, facts = [], {}
    docx = r09 / "log_4-10.docx"
    if not docx.exists():
        return ["thieu log_4-10.docx"], facts
    b = docx.read_bytes()
    meta = json.loads(text(r09 / "nguon.json"))
    if hashlib.sha256(b).hexdigest() != DOCX_SHA or meta.get("sha256") != DOCX_SHA or meta.get("kich_thuoc_byte") != len(b):
        bad.append("SHA/kich thuoc DOCX khong khop ke hoach/nguon.json (%s, %d byte)" % (hashlib.sha256(b).hexdigest()[:12], len(b)))
    try:
        paras = docx_paras(b)
    except Exception as e:  # noqa: BLE001  DOCX hong -> loi bang chung, khong doc tiep
        return bad + ["DOCX khong doc duoc: %s" % e], facts
    trich ="".join("== P%d (%d ky tu)\n%s\n" % (i + 1, len(p), p) for i, p in enumerate(paras))
    if trich != text(r09 / "log_4-10_trich.txt"):
        bad.append("ban trich log_4-10_trich.txt khong tai lap duoc tu DOCX")
    t = "\n".join(paras)
    facts["doan"] = len(paras)
    # lenh/output nap
    if not re.search(r"upload -p COM9 --fqbn esp32:esp32:esp32s3:PSRAM=opi --input-dir firmware/esp32s3/Ca ?meraWebServerTest/build/q6", t):
        bad.append("khong thay lenh upload COM9/FQBN/--input-dir build/q6")
    wrote = re.findall(r"Wrote (\d+) bytes \(\d+ compressed\) at (0x[0-9a-f]{8})", t)
    if [(o, int(n)) for n, o in wrote] != FLASH:
        bad.append("anh nap/offset/kich thuoc khac %s: %s" % (FLASH, wrote))
    nver = t.count("Hash of data verified")
    if nver != 4:
        bad.append("'Hash of data verified' x%d (can 4)" % nver)
    if APP_SHA not in t:
        bad.append("DOCX khong co SHA app %s" % APP_SHA[:12])
    facts["upload"] = "COM9, 4 anh %s, verified x%d" % (wrote, nver)
    # SHA app: manifest 2 phien + bo luu archive_20261004_q6
    for s in (s_bad, s_t9):
        m = json.loads(text(s / "manifest.json"))
        if m.get("binary_sha256") != APP_SHA:
            bad.append("%s/manifest.json binary_sha256 khac" % s.name)
    am = json.loads(text(archive_root / "build/c5a-artifacts/archive_20261004_q6/manifest.json"))
    arts = {a["offset"]: a for a in am["artifacts"]}
    for off, n in FLASH:
        a = arts.get(off)
        f = archive_root / "build/c5a-artifacts/archive_20261004_q6" / a["file"] if a else None
        if not a or a.get("size") != n or not f.exists() or sha(f) != a.get("sha256"):
            bad.append("bo luu archive_20261004_q6 lech o %s" % off)
    if arts.get("0x00010000", {}).get("sha256") != APP_SHA:
        bad.append("bo luu archive_20261004_q6 app khac SHA lich su")
    # 60 dong bo trong DOCX (loai selftest mock boot khac) doi chieu summary
    rows = [(int(i), float(rtt), int(fid), boot, int(st), int(by)) for i, rtt, fid, boot, st, by in re.findall(
        r"\[(\d+)/20\] HTTP 200 RTT=([\d.]+)ms ID=(\d+) Boot=([0-9a-f]{8})\.\.\. Stale=(\d+) Bytes=(\d+)", t)]
    board = [r for r in rows if r[3] == BOOT_0410[:8]]
    mock = [r for r in rows if r[3] != BOOT_0410[:8]]
    t9 = [r for r in board if 18 <= r[2] <= 77]
    bad_run = [r for r in board if r[2] <= 16]
    facts["dong"] = "bo %d (Q6-T9 %d, luot hong %d), mock bi loai %d" % (len(board), len(t9), len(bad_run), len(mock))
    summ = []
    for k in (1, 2, 3):
        p = s_t9 / ("probe_q6_t9_run%d/summary.json" % k)
        summ += json.loads(text(p))["frames"] if p.exists() else []
    if len(t9) != 60 or len(summ) != 60:
        bad.append("so dong bo Q6-T9 trong DOCX %d / summary %d (can 60/60)" % (len(t9), len(summ)))
    else:
        mism = [(r[2], f["frame_id"]) for r, f in zip(t9, summ) if not (
            r[0] == f["index"] and r[2] == f["frame_id"] and abs(r[1] - round(f["rtt_ms"], 1)) < 0.06 and r[4] == f["discarded"] and
            r[5] == f["body_len"] and f["boot_id"] == BOOT_0410)]
        if mism:
            bad.append("%d dong DOCX lech summary: %s" % (len(mism), mism[:3]))
    sb = json.loads(text(s_bad / "probe_q6_t9_run1/summary.json"))["frames"] if (s_bad / "probe_q6_t9_run1/summary.json").exists() else []
    okb = [f for f in sb if f["status"] == 200]
    if [(r[2], r[5]) for r in bad_run] != [(f["frame_id"], f["body_len"]) for f in okb]:
        bad.append("16 dong luot hong trong DOCX khong khop summary phien %s" % s_bad.name)
    return bad, facts


def chk_t9(s_t9):
    bad, ids, nimg = [], [], 0
    prof = json.loads(text(s_t9 / "cam_SVGA_q20_20260928.json"))
    if sha(s_t9 / "cam_SVGA_q20_20260928.json") != PROFILE_SHA:
        bad.append("ban sao profile sai SHA")
    if ("Boot ID: " + BOOT_0410) not in text(s_t9 / "boot_serial.log"):
        bad.append("Serial khong co Boot ID %s" % BOOT_0410[:8])
    for k in (1, 2, 3):
        s = json.loads(text(s_t9 / ("probe_q6_t9_run%d/summary.json" % k)))
        if s["verdict"] != "PASS" or s["success_count"] != 20:
            bad.append("luot %d %s %d/20" % (k, s["verdict"], s["success_count"]))
        for f in s["frames"]:
            i = f["index"]
            jp = s_t9 / ("probe_q6_t9_run%d/frame_%04d.jpg" % (k, i))
            ok, sz = jpeg(jp, (800, 600))
            h = headers(s_t9 / ("probe_q6_t9_run%d/headers_%04d.txt" % (k, i)))
            good = (ok and all(len(h.get(x, [])) == 1 for x in HDR5) and int(h["content-length"][0]) == jp.stat().st_size and
                    f["boot_id"] == BOOT_0410 and f["t_frame_us"] > f["t_req_us"])
            if not good:
                bad.append("luot %d anh %d: %s" % (k, i, sz))
            ids.append(f["frame_id"])
            nimg += 1
        for w in ("before", "after"):
            st = json.loads(text(s_t9 / ("status_%s_run%d.json" % (w, k))))
            c_ok, _ = diff_controls(st, prof["framesize"], prof["quality"], prof["controls"])
            r_ok, _ = compare_registers(prof["expected_registers"], st, prof["expected_registers"].keys())
            if not (c_ok and r_ok):
                bad.append("snapshot %s luot %d lech profile" % (w, k))
    if ids != list(range(18, 78)):
        bad.append("Frame ID khong lien tuc 18..77")
    return bad, "%d anh, ID %s..%s" % (nimg, ids[0] if ids else None, ids[-1] if ids else None)


# ---------------------------------------------------------------------------- E3: bo 3 RST moi
BOOT_RE = r"Boot ID: ([0-9a-f]{32})"


def chk_rst(sess, archive_root=Path(".")):
    bad, rows = [], []
    if not (sess / "upload_output.log").exists():
        return ["thieu upload_output.log"], rows
    m = json.loads(text(sess / "manifest.json"))
    arch = archive_root / m["artifact_archive_dir"].replace("\\", "/")
    for a in m["artifacts"]:
        f = arch / a["file"]
        if not f.exists() or sha(f) != a["sha256"] or f.stat().st_size != a["size"]:
            bad.append("bo luu %s: %s thieu/lech SHA" % (arch.name, a["file"]))
    if {a["offset"]: a["size"] for a in m["artifacts"]} != dict(FLASH):
        bad.append("manifest offset/kich thuoc khac %s" % FLASH)
    if [a for a in m["artifacts"] if a["name"] == "app"][0]["sha256"] != APP_SHA:
        bad.append("app trong bo luu khac SHA lich su")
    up = text(sess / "upload_output.log")
    wrote = re.findall(r"Wrote (\d+) bytes \(\d+ compressed\) at (0x[0-9a-f]{8})", up)
    if ("Serial port COM9" not in up or up.count("Hash of data verified") != 4 or [(o, int(n)) for n, o in wrote] != FLASH or
            ("%s/CameraWebServerTest.ino.bin' at 0x00010000" % m["artifact_archive_dir"]).replace("\\", "/") not in up.replace("\\", "/")):
        bad.append("log nap khong du: COM9/4 verified/anh/offset/nap tu bo luu %s" % arch.name)
    bs = text(sess / "boot_serial.log")
    b0 = re.findall(BOOT_RE, bs)
    if "Camera Init OK: fb_count=1, grab_mode=1, fb_location=0" not in bs or len(b0) != 1:
        bad.append("boot_serial.log thieu cau hinh 1 buffer hoac Boot ID")
    prev = b0[-1] if b0 else None
    boots = [prev]
    for k in (1, 2, 3):
        try:
            r = json.loads(text(sess / ("probe_q6_t10_reboot_run%d/summary.json" % k)))
            v = json.loads(text(sess / ("probe_q6_t10_rst%d_recovered/summary.json" % k)))
            sl = text(sess / ("boot_serial_rst%d.log" % k))
            t_b = text(sess / ("status_before_rst%d_time.txt" % k)).strip()
            t_a = text(sess / ("rst%d_action_time.txt" % k)).strip()
            t_s = text(sess / ("status_after_rst%d_time.txt" % k)).strip()
            sa = json.loads(text(sess / ("status_after_rst%d.json" % k)))
        except Exception as e:  # noqa: BLE001
            bad.append("RST%d thieu bang chung: %s" % (k, e))
            continue
        okf = [f for f in r["frames"] if f["status"] == 200 and f.get("valid")]
        imgs = all(jpeg(sess / ("probe_q6_t10_reboot_run%d/frame_%04d.jpg" % (k, f["index"])))[0] for f in okf)
        ids = [f["frame_id"] for f in okf]
        if r["verdict"] != "INVALID" or not okf or not imgs or {f["boot_id"] for f in okf} != {prev} or ids != list(range(ids[0], ids[0] + len(ids))):
            bad.append("RST%d: luot truoc RST khong INVALID/giu anh/cung boot truoc (%s)/ID lien tuc" % (k, (prev or "")[:8]))
        nb = re.findall(BOOT_RE, sl)
        if len(nb) != 1 or nb[0] in boots or "fb_count=1" not in sl:
            bad.append("RST%d: Serial sau RST khong co Boot ID moi duy nhat" % k)
        new = nb[-1] if nb else None
        f = v["frames"][0] if v.get("frames") else {}
        ok, sz = jpeg(sess / ("probe_q6_t10_rst%d_recovered/frame_0001.jpg" % k), (800, 600))
        h = headers(sess / ("probe_q6_t10_rst%d_recovered/headers_0001.txt" % k)) if ok else {}
        if not (v.get("verdict") == "PASS" and f.get("status") == 200 and f.get("boot_id") == new and f.get("frame_id") == 1 and ok and
                all(len(h.get(x, [])) == 1 for x in HDR5)):
            bad.append("RST%d: hoi phuc khong PASS/200/boot moi/ID 1/800x600/5 header (boot %s, %s)" % (k, (f.get("boot_id") or "")[:8], sz))
        if not isinstance(sa.get("framesize"), int):
            bad.append("RST%d: /status sau RST khong phai JSON hop le" % k)
        tf = [re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", x) for x in (t_b, t_a, t_s)]
        if not all(tf) or not (t_b <= t_a <= t_s):
            bad.append("RST%d: thu tu thoi diem truoc/RST/sau sai (%s, %s, %s)" % (k, t_b, t_a, t_s))
        rows.append("RST%d: %s ID%s -> RST %s -> boot %s, fs sau RST %s, hoi phuc ID%s %s" % (
            k, (prev or "")[:8], ids, t_a, (new or "")[:8], sa.get("framesize"), f.get("frame_id"), sz))
        boots.append(new)
        prev = new
    return bad, rows


# ---------------------------------------------------------------------------- chay
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:  # noqa: BLE001
        pass
    print("Tester C5a - kiem bang chung bo that (R09, Q6-T9 lich su, bo 3 RST: %s)" % RST)
    print("---- E1/E2: nguon R09 va 60 anh ngay 04/10")
    b, facts = chk_r09(R09, S_BAD, S_T9)
    check("E1", not b, "V8-B1/R09: DOCX nguyen bytes + ban trich tai lap; lenh/output nap COM9/FQBN/4 anh/offset/verified; SHA app = manifest 04/10 = bo luu archive_20261004_q6; 60+16 dong bo khop summary (mock bi loai)",
          "%s; van de: %s" % (facts, b))
    b, f2 = chk_t9(S_T9)
    check("E2", not b, "V8-B2: tai kiem 60 JPEG 800x600, 5 header, Content-Length, t_frame>t_req, ID 18..77, 1 boot = Serial, 6 snapshot khop profile",
          "%s; van de: %s" % (f2, b[:3]))
    print("---- E3: bo 3 RST moi")
    b, rows = chk_rst(RST)
    for ln in rows:
        print("    " + ln)
    check("E3", not b, "V8-B3/R10: bo luu -> log nap goc (4 verified) -> boot; 3 cap RST du truoc/sau (ke ca sau RST3): INVALID giu anh, boot moi moi lan, /status, hoi phuc PASS 800x600 boot moi ID 1, thu tu thoi diem",
          "van de: %s" % b)
    print("---- E4: ca am tren ban sao tam (nguon that khong doi)")
    td = Path(tempfile.mkdtemp(prefix="c5a_ev_"))
    res = []

    def case(name, fn):
        try:
            res.append((name, bool(fn())))
        except Exception as e:  # noqa: BLE001  phien nguon thieu tep -> khong dung duoc ca am nay
            res.append((name + " (khong dung duoc: %s)" % type(e).__name__, False))

    def c1():
        r1 = td / "r09"
        shutil.copytree(R09, r1)
        bb = bytearray((r1 / "log_4-10.docx").read_bytes())
        bb[-10] ^= 1
        (r1 / "log_4-10.docx").write_bytes(bytes(bb))
        return chk_r09(r1, S_BAD, S_T9)[0]

    def c2():
        r2 = td / "r09_mock"
        shutil.copytree(R09, r2)
        (r2 / "log_4-10_trich.txt").write_text(text(R09 / "log_4-10_trich.txt").replace("Boot=a37295f2", "Boot=0d1ad930"), encoding="utf-8")
        return chk_r09(r2, S_BAD, S_T9)[0]

    def c3():
        a3 = td / "a3"
        ad = json.loads(text(RST / "manifest.json"))["artifact_archive_dir"].replace("\\", "/")
        shutil.copytree(ad, a3 / ad)
        (a3 / ad / "CameraWebServerTest.ino.bin").write_bytes(b"BI DOI")
        return chk_rst(RST, a3)[0]

    def c4():
        s4 = td / "s4"
        shutil.copytree(RST, s4)
        shutil.rmtree(s4 / "probe_q6_t10_rst3_recovered")
        (s4 / "boot_serial_rst3.log").unlink()
        return chk_rst(s4)[0]

    def c5():
        s5 = td / "s5"
        shutil.copytree(RST, s5)
        p5 = s5 / "probe_q6_t10_rst2_recovered/summary.json"
        j = json.loads(text(p5))
        j["frames"][0]["boot_id"] = json.loads(text(RST / "probe_q6_t10_reboot_run2/summary.json"))["frames"][0]["boot_id"]
        p5.write_text(json.dumps(j), encoding="utf-8")
        return chk_rst(s5)[0]

    def c6():
        s6 = td / "s6"
        shutil.copytree(RST, s6)
        (s6 / "upload_output.log").unlink()
        return chk_rst(s6)[0]

    def c7():
        s7 = td / "s7"
        shutil.copytree(RST, s7)
        Image.new("RGB", (320, 240)).save(s7 / "probe_q6_t10_rst1_recovered/frame_0001.jpg", "JPEG")
        return chk_rst(s7)[0]
    try:
        for n, fn in (("docx_doi_byte", c1), ("trich_chi_con_dong_mock", c2), ("app_bo_luu_bi_doi", c3), ("bo_bang_chung_sau_RST3", c4),
                      ("tron_boot_hoi_phuc", c5), ("thieu_log_nap", c6), ("hoi_phuc_320x240", c7)):
            case(n, fn)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    check("E4", all(x[1] for x in res), "V8-B4: moi ca am deu bi checker bao loi (khong chi dem kich thuoc app/tong PASS)",
          "; ".join("%s: %s" % (n, "BAT" if d else "LOT") for n, d in res))
    print("\nTONG: %d PASS, %d FAIL, %d NOTE" % (RES.count("PASS"), RES.count("FAIL"), RES.count("NOTE")))
    sys.exit(1 if "FAIL" in RES else 0)


if __name__ == "__main__":
    main()
