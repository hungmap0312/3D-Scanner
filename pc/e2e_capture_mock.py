"""Chay capture_session.run_session voi mock_camera nhung trong tien trinh, tung tinh huong."""
import sys, io, json, threading, tempfile, contextlib, time
from pathlib import Path
from http.server import HTTPServer
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import capture_session as cs
import mock_camera as mc
import camera_profile as cp

class NS: pass

def ns(**kw):
    a = NS()
    a.reset_at = 0; a.fail_frames = ""; a.drop_ts_frames = ""; a.lowercase_headers = False
    a.status_mode = "ok"; a.status_fail_after = 0
    for k, v in kw.items(): setattr(a, k, v)
    return a

def run(name, mock_opts, cap_opts, pre=None):
    mc.apply_options(ns(**mock_opts))
    mc.STATE["frame"] = 0; mc.STATE["t0"] = time.time(); mc.STATE["framesize"] = 6
    srv = HTTPServer(("127.0.0.1", 0), mc.H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "raw"; meta = Path(td) / "mirror"
        a = NS()
        a.host = "127.0.0.1:%d" % port; a.count = 3; a.interval = 0.0; a.framesize = None
        a.warmup = 0; a.max_retries = 3; a.timeout = 5.0; a.out = str(out); a.session_id = "s"
        a.note = ""; a.meta_copy = str(meta); a.profile = None
        for k, v in cap_opts.items(): setattr(a, k, v)
        if pre: pre(out, meta)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cs.run_session(a)
        sd = out / "s"
        sess = json.loads((sd / "session.json").read_text(encoding="utf-8")) if (sd / "session.json").exists() else None
        att = (sd / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if (sd / "attempts.jsonl").exists() else []
        files = sorted(p.name for p in sd.iterdir()) if sd.exists() else []
        res = (sess or {}).get("result") or {}
        old = (meta / "s" / "session.json").read_text(encoding="utf-8") if (meta / "s" / "session.json").exists() else None
        print("== %-22s rc=%s verdict=%s reason=%s" % (name, rc, res.get("verdict"), res.get("reason")))
        print("   attempts=%d files=%s" % (len(att), [f for f in files if f.startswith("img")]))
        if res.get("status_compare_start_to_end"):
            print("   status:", cs.describe_compare(res["status_compare_start_to_end"]))
        if old is not None:
            print("   mirror session.json:", old[:12])
    srv.shutdown(); srv.server_close()

run("baseline", {}, {})
run("retry_recovers", {"fail_frames": "2"}, {})
run("missing_timestamp", {"drop_ts_frames": "2"}, {})
run("lowercase_headers", {"lowercase_headers": True}, {})
run("status_invalid", {"status_mode": "invalid"}, {})
run("status_list", {"status_mode": "list"}, {})
run("status_end_503", {"status_fail_after": 3}, {})
run("reset_at_2", {"reset_at": 2}, {})
run("count_0", {}, {"count": 0})
def pre(out, meta):
    (meta / "s").mkdir(parents=True); (meta / "s" / "session.json").write_text("OLD_METADATA", encoding="utf-8")
run("metadata_collision", {}, {}, pre=pre)
run("exhaust_retries", {"fail_frames": "1"}, {"max_retries": 0})


# --- Kich ban ho so camera (C2), them 21/09 -------------------------------

# Vong 5 (L06): cp.DEFAULT_CONTROLS khong con du 14 khoa (bo bon gia tri
# hieu chinh chua do) - e2e dung ban day du rieng cho ho so "hop le", giong
# cach cmd_create() phai nhan --set cho bon truong do.
# Vong 7 (L11): hop dong WB thu cong - awb=1 (mac dinh moi cua
# cp.DEFAULT_CONTROLS), awb_gain=1, wb_mode=1; thanh ghi mong doi la
# DEFAULT_REGISTERS cua mock chong bang preset 1 (0x3406=1), dung trang
# thai mock sau khi ap ho so.
E2E_CONTROLS = dict(cp.DEFAULT_CONTROLS, aec_value=490, agc_gain=2, awb_gain=1, wb_mode=1)
E2E_REGISTERS = dict(mc.DEFAULT_REGISTERS, **mc.WB_MODE_REGISTERS[1])


def make_profile_file(path, controls=None, expected_registers=None):
    # Gia tri mac dinh KHOP dung STATE["registers"] cua mock_camera.py de
    # phien "duong tot" thuc su di qua duoc doi chieu G02 (khong con dung
    # so 0 gia); kich ban muon lech thi tu truyen expected_registers khac.
    profile = cp.build_profile_dict(
        "VGA", 10, controls or E2E_CONTROLS,
        expected_registers if expected_registers is not None else dict(E2E_REGISTERS),
        "ong kinh goc, tieu diem xa gia lap e2e",
    )
    Path(path).write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    return str(path)


_profile_dir = tempfile.mkdtemp(prefix="camera_profile_e2e_")
_good_profile = make_profile_file(Path(_profile_dir) / "good.json")

_invalid_profile = Path(_profile_dir) / "invalid.json"
_invalid_profile.write_text(json.dumps({"camera_profile_id": "x"}), encoding="utf-8")  # thieu hau het truong bat buoc

_mismatch_profile = make_profile_file(
    Path(_profile_dir) / "mismatch.json",
    expected_registers=dict(E2E_REGISTERS, **{"0x3500": 0}),
)

_locked_bad_profile = make_profile_file(
    Path(_profile_dir) / "locked_bad.json",
    controls=dict(E2E_CONTROLS, aec=1),
)

run("profile_baseline", {}, {"profile": _good_profile})
run("profile_register_drift", {"drift_registers": "0x3400,0x3404", "drift_after": 2}, {"profile": _good_profile})
run("profile_control_rejected", {"fail_controls": "awb"}, {"profile": _good_profile})
run("profile_status_missing_field", {"status_drop_fields": "aec"}, {"profile": _good_profile})
run("profile_invalid_schema", {}, {"profile": str(_invalid_profile)})
run("profile_and_framesize_conflict", {}, {"profile": _good_profile, "framesize": "VGA"})

# Vong 3 - kiem truc tiep G02/G03/G04 (04_REVIEW.md R01 ngoai le, xem 01_PLAN.md Vong 3)
run("profile_register_mismatch_at_start_G02", {}, {"profile": _mismatch_profile})
# Vong 7: awb=1 la gia tri dung nen drift G03 gio la aec ve 1 va awb ve 0.
run("profile_control_drift_at_end_G03", {"control_drift_fields": "aec=1,awb=0", "control_drift_after": 2}, {"profile": _good_profile})
run("profile_locked_control_rejected_G04", {}, {"profile": _locked_bad_profile})
run("profile_first_control_fails_fast_G04", {"fail_controls": "framesize"}, {"profile": _good_profile})


# --- Vong 5 (L05-L07): camera_profile.py --create / --probe qua HTTP ------

def _cp_ns(**kw):
    a = NS()
    a.set = None; a.lens_note = "ong kinh goc, tieu diem xa gia lap e2e"
    a.id = None; a.out = None; a.timeout = 5.0
    a.samples = 3; a.interval = 0.0; a.warmup = 0
    for k, v in kw.items():
        setattr(a, k, v)
    return a


def run_cp(name, mock_opts, cmd, args_kw):
    """Chay cp.cmd_create()/cp.cmd_probe() qua mock trong tien trinh (khac
    run() o tren goi cs.run_session()). In rc, /_counts va tep .json sinh ra
    (out la mot thu muc tam rieng cho tung kich ban)."""
    mc.apply_options(ns(**mock_opts))
    mc.STATE["frame"] = 0; mc.STATE["t0"] = time.time(); mc.STATE["framesize"] = 6
    srv = HTTPServer(("127.0.0.1", 0), mc.H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    with tempfile.TemporaryDirectory() as td:
        a = _cp_ns(host="127.0.0.1:%d" % port, out=td, **args_kw)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd(a)
        files = sorted(p.name for p in Path(td).glob("*.json"))
        print("== %-38s rc=%s counts=%s files=%s" % (name, rc, dict(mc.STATE["counts"]), files))
    srv.shutdown(); srv.server_close()


run_cp("cp_create_missing_explicit", {}, cp.cmd_create, {"framesize": "VGA", "quality": 10})
run_cp("cp_create_explicit_ok", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=490", "agc_gain=2", "awb_gain=1", "wb_mode=1"]})
run_cp("cp_create_domain_out_of_range", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=490", "agc_gain=31", "awb_gain=1", "wb_mode=1"]})
run_cp("cp_probe_ok", {}, cp.cmd_probe, {})
run_cp("cp_probe_missing_register", {"status_drop_fields": "0x3500"}, cp.cmd_probe, {})
run_cp("cp_probe_status_fail_at_count", {"status_fail_at_count": 2}, cp.cmd_probe, {})
run_cp("cp_probe_control_reject", {"fail_controls": "aec"}, cp.cmd_probe, {})


def scenario_id_retry():
    """Hai lan --create lien tiep cung cau hinh/ngay, khong --id: lan hai
    phai tu chon hau to _r01, khong tu choi va khong ghi de lan dau
    (Vong 5 muc 3)."""
    mc.apply_options(ns())
    mc.STATE["frame"] = 0; mc.STATE["t0"] = time.time(); mc.STATE["framesize"] = 6
    srv = HTTPServer(("127.0.0.1", 0), mc.H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    with tempfile.TemporaryDirectory() as td:
        common = {
            "host": "127.0.0.1:%d" % port, "out": td, "framesize": "VGA", "quality": 10,
            "set": ["aec_value=490", "agc_gain=2", "awb_gain=1", "wb_mode=1"],
        }
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc1 = cp.cmd_create(_cp_ns(**common))
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = cp.cmd_create(_cp_ns(**common))
        files = sorted(p.name for p in Path(td).glob("*.json"))
        print("== %-38s rc1=%s rc2=%s files=%s" % ("cp_create_id_retry", rc1, rc2, files))
    srv.shutdown(); srv.server_close()


scenario_id_retry()


# --- Vong 6 (L08-L10): tran aec_value va bat bien wb_mode/awb_gain --------

run_cp("cp_create_aec_over_cap", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=784", "agc_gain=2", "awb_gain=1", "wb_mode=1"]})
run_cp("cp_create_aec_at_cap", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=783", "agc_gain=2", "awb_gain=1", "wb_mode=1"]})
run_cp("cp_create_wb_ambiguous", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=490", "agc_gain=2", "awb_gain=0", "wb_mode=2"]})


def scenario_wb_registers():
    """L10: --create voi wb_mode=N, awb_gain=1 phai cho dung bo thanh ghi
    mau theo WB_MODE_REGISTERS cua mock (bang driver OV3660 chuan,
    01_PLAN.md Phu luc Vong 6 muc 2)."""
    mc.apply_options(ns())
    mc.STATE["frame"] = 0; mc.STATE["t0"] = time.time(); mc.STATE["framesize"] = 6
    srv = HTTPServer(("127.0.0.1", 0), mc.H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    with tempfile.TemporaryDirectory() as td:
        ok_all = True
        for n in (1, 2, 3, 4):
            # khong dat --id: mac dinh trung cau hinh/ngay, dua vao hau to
            # retry tu dong (Vong 5 muc 3) de khong ghi de giua bon lan tao.
            before = set(Path(td).glob("*.json"))
            a = _cp_ns(host="127.0.0.1:%d" % port, out=td, framesize="VGA", quality=10,
                       set=["aec_value=490", "agc_gain=2", "awb_gain=1", "wb_mode=%d" % n])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cp.cmd_create(a)
            after = set(Path(td).glob("*.json"))
            new_files = after - before
            regs = json.loads(next(iter(new_files)).read_text(encoding="utf-8"))["expected_registers"] if new_files else {}
            want = mc.WB_MODE_REGISTERS[n]
            match = all(regs.get(k) == v for k, v in want.items())
            ok_all = ok_all and (rc == 0) and match
            print("   wb_mode=%d rc=%s regs_match=%s got=%s" % (n, rc, match, {k: regs.get(k) for k in want}))
        print("== %-38s ok=%s" % ("cp_create_wb_registers_L10", ok_all))
    srv.shutdown(); srv.server_close()


scenario_wb_registers()


def scenario_probe_clamp():
    """L08: --probe voi 0x3500 tuong duong aec_value=784 (tren muc kep)
    phai tra ung vien effective=783 va co ma clamped=True."""
    mc.apply_options(ns(registers="0x3500=12544,0x350a=248"))
    mc.STATE["frame"] = 0; mc.STATE["t0"] = time.time(); mc.STATE["framesize"] = 6
    srv = HTTPServer(("127.0.0.1", 0), mc.H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    with tempfile.TemporaryDirectory() as td:
        a = _cp_ns(host="127.0.0.1:%d" % port, out=td)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cp.cmd_probe(a)
        log_file = next(Path(td).glob("probe_*.json"))
        log = json.loads(log_file.read_text(encoding="utf-8"))
        cand = log["candidates"]
        ok = (rc == 0 and cand["aec_value_raw"] == 784 and cand["aec_value_effective"] == 783
              and cand["aec_value_clamped"] is True)
        print("== %-38s rc=%s candidates=%s ok=%s" % ("cp_probe_clamp_L08", rc, cand, ok))
    srv.shutdown(); srv.server_close()


scenario_probe_clamp()


# --- Vong 7 (L11): WB thu cong phai kem awb=1, preset ap that len thanh ghi --

run_cp("cp_create_awb0_rejected_L11", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["awb=0", "aec_value=490", "agc_gain=2", "awb_gain=1", "wb_mode=1"]})
run_cp("cp_create_wb_mode0_rejected_L11", {}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=490", "agc_gain=2", "awb_gain=1", "wb_mode=0"]})
run_cp("cp_create_wb_registers_stuck_L11", {"wb_registers_stuck": True}, cp.cmd_create,
       {"framesize": "VGA", "quality": 10, "set": ["aec_value=490", "agc_gain=2", "awb_gain=1", "wb_mode=2"]})
run_cp("cp_probe_reset_control_fails_L11", {"fail_controls": "wb_mode"}, cp.cmd_probe, {})
# 0x3406 con 1 (preset cu) va wb_mode=0 tra 200 ma khong xoa: probe phai dung,
# khong phat ung vien tu /status con sot WB thu cong.
run_cp("cp_probe_stuck_manual_wb_L11", {"registers": "0x3406=1", "wb_registers_stuck": True}, cp.cmd_probe, {})

# Ho so cu kieu Vong 3-6 (awb=0) phai bi tu choi truoc HTTP, khong dung lai.
_legacy_awb0_profile = make_profile_file(
    Path(tempfile.mkdtemp()) / "legacy_awb0.json",
    controls=dict(E2E_CONTROLS, awb=0),
)
run("profile_awb0_legacy_rejected_L11", {}, {"profile": _legacy_awb0_profile})


def scenario_probe_after_preset():
    """L11: tao ho so preset 4 (0x3406=1) roi --probe tren cung bo: probe
    phai tu dua ve tu dong (aec=agc=awb=awb_gain=1, wb_mode=0, 0x3406=0)
    truoc khi lay mau; tao lai preset 1 sau do phai ve 0x3406=1."""
    mc.apply_options(ns())
    mc.STATE["frame"] = 0; mc.STATE["t0"] = time.time(); mc.STATE["framesize"] = 6
    srv = HTTPServer(("127.0.0.1", 0), mc.H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    host = "127.0.0.1:%d" % port
    with tempfile.TemporaryDirectory() as td:
        sets = ["aec_value=490", "agc_gain=2", "awb_gain=1"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc1 = cp.cmd_create(_cp_ns(host=host, out=td, framesize="VGA", quality=10, set=sets + ["wb_mode=4"]))
            reg_after_create = mc.STATE["registers"]["0x3406"]
            rc2 = cp.cmd_probe(_cp_ns(host=host, out=td))
            reg_after_probe = mc.STATE["registers"]["0x3406"]
            rc3 = cp.cmd_create(_cp_ns(host=host, out=td, framesize="VGA", quality=10, set=sets + ["wb_mode=1"]))
            reg_after_recreate = {k: mc.STATE["registers"][k] for k in mc.WB_MODE_REGISTERS[1]}
        log = json.loads(next(Path(td).glob("probe_*.json")).read_text(encoding="utf-8"))
        auto = log.get("auto_state") or {}
        auto_ok = auto == dict(cp.PROBE_AUTO_CONTROLS, **cp.PROBE_AUTO_REGISTERS)
        ok = (rc1 == 0 and reg_after_create == 1 and rc2 == 0 and reg_after_probe == 0 and auto_ok
              and rc3 == 0 and reg_after_recreate == mc.WB_MODE_REGISTERS[1])
        print("== %-38s rc=%s/%s/%s 0x3406=%s->%s auto_state_ok=%s recreate=%s ok=%s" % (
            "cp_probe_after_preset_L11", rc1, rc2, rc3, reg_after_create, reg_after_probe,
            auto_ok, reg_after_recreate, ok))
    srv.shutdown(); srv.server_close()


scenario_probe_after_preset()
