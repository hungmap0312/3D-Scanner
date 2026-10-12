#!/usr/bin/env python3
"""Tester C4 - kiem doc lap phan P1 cua pc/nucleo_ping.py (handoff/2026-09-21_c4-nucleo-laser-control).

Noi cong cu PC voi ma firmware THAT (firmware/stm32/NucleoPing/Core/Src/ping_proto.c) qua mot
tien trinh "bo gia" (test/tester_c4_simexe.c + test/tester_c4_hal.c cua Tester), tu build bang
MinGW gcc vao thu muc tam. Khong mo cong COM, khong cham bo. Selftest cua cong cu dung
FakeNucleo viet tay (khong co bo nho chong lap seq), nen chi test nay moi thay duoc cong cu
va firmware noi voi nhau the nao.

Chay tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/test_nucleo_ping_p1.py
Bien moi truong TESTER_GCC doi duong dan gcc (mac dinh D:/MinGW/bin/gcc.exe).
Thoat 0 khi khong co kich ban FAIL.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pc"))
import nucleo_ping as npg  # noqa: E402

FW = REPO / "firmware" / "stm32" / "NucleoPing"
TMP = Path(tempfile.mkdtemp(prefix="tester_c4_"))
REAL_TMPDIR = tempfile.gettempdir()   # thu muc tam that cua may (tep seq that cua cong cu nam o day)
GCC = os.environ.get("TESTER_GCC", "D:/MinGW/bin/gcc.exe")
PY = sys.executable
SUMMARY = []


class Sc:
    def __init__(self, sid, title, note_only=False):
        self.sid, self.title, self.note_only = sid, title, note_only
        self.fails = []
        print("\n---- %s %s" % (sid, title))

    def ok(self, cond, label, actual=""):
        print("  [%s] %s%s" % ("OK  " if cond else "FAIL", label, ("  | " + str(actual)) if actual != "" else ""))
        if not cond:
            self.fails.append(label)
        return cond

    def note(self, label, actual=""):
        print("  [NOTE] %s%s" % (label, ("  | " + str(actual)) if actual != "" else ""))

    def done(self):
        st = "FAIL" if self.fails else ("NOTE" if self.note_only else "PASS")
        SUMMARY.append((self.sid, st, self.title))
        print("==== %s %s" % (self.sid, st))


def xor_hex(s):
    c = 0
    for ch in s.encode("ascii"):
        c ^= ch
    return "%02X" % c


def build_sim():
    exe = TMP / "tester_c4_sim.exe"
    cmd = [GCC, "-std=c99", "-Wall", "-Wextra", "-O0", "-Itest/fake", "-ICore/Inc", '-DFW_GIT_HASH="hosttest"',
           "test/tester_c4_simexe.c", "test/tester_c4_hal.c", "Core/Src/ping_proto.c", "-o", str(exe)]
    r = subprocess.run(cmd, cwd=FW, capture_output=True, text=True, errors="replace")
    return (exe if r.returncode == 0 else None), (r.stdout + r.stderr).strip()


class SimSerial:
    """Gia pyserial cho nucleo_ping.py: write -> byte vao ping_proto.c that (tick tang step_ms moi lan
    ghi); read_until -> byte bo gui; het byte thi tra phan con lai (nhu het timeout)."""

    def __init__(self, exe, door=1, estop=0, tick0=1000, step_ms=5):
        self.p = subprocess.Popen([str(exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.buf = bytearray()
        self.tick = tick0
        self.step = step_ms
        self.timeout = 1.0
        self.sent = []
        self.buf += self._o(self._cmd("R %d %d 2 %d" % (door, estop, tick0)))

    def _cmd(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return self.p.stdout.readline().strip()

    @staticmethod
    def _o(resp):
        if not resp.startswith("O"):
            raise RuntimeError("bo gia tra sai: %r" % resp)
        return bytes.fromhex(resp[2:]) if len(resp) > 2 else b""

    def write(self, data):
        self.sent.append(bytes(data))
        self.tick += self.step
        self._cmd("T %d" % self.tick)
        self.buf += self._o(self._cmd("X " + bytes(data).hex().upper()))
        return len(data)

    def flush(self):
        pass

    def read_until(self, term=b"\n"):
        i = self.buf.find(term)
        if i < 0:
            out = bytes(self.buf)
            self.buf.clear()
            return out
        out = bytes(self.buf[:i + 1])
        del self.buf[:i + 1]
        return out

    def reset_input_buffer(self):
        self.buf.clear()

    def state(self):
        parts = self._cmd("S").split()
        return parts[1], parts[2], int(parts[3]), int(parts[4])

    def set_inputs(self, door, estop):
        """Doi day D8 (cua: 1 = 3V3/dong, 0 = GND/mo) va D9 (estop: 0 = GND/nha, 1 = ho/nhan)."""
        self._cmd("I %d %d" % (door, estop))

    def advance(self, ms):
        """Thoi gian troi tren bo ma PC khong gui gi (bo van poll)."""
        self.tick += ms
        self._cmd("T %d" % self.tick)
        self.buf += self._o(self._cmd("P"))

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(5)
        except Exception:  # noqa: BLE001
            self.p.kill()


def p1_unit():
    s = Sc("P1-U", "ham khung P1 cua cong cu: checksum, format, parse (doi chieu XOR doc lap)")
    for body in ("1 STATUS", "65535 LASER ON", "0 ERROR TOOLONG", "12 DONE IDLE 0 0 1 0 0 4294967295 LASER_TIMEOUT"):
        s.ok(npg.calc_p1_checksum(body) == xor_hex(body), "calc_p1_checksum(%r)" % body, npg.calc_p1_checksum(body))
    s.ok(npg.format_p1_cmd(65535, "LASER ON") == "65535 LASER ON*" + xor_hex("65535 LASER ON"), "format_p1_cmd(65535, LASER ON)",
         npg.format_p1_cmd(65535, "LASER ON"))
    good = "7 DONE ON 5000*" + xor_hex("7 DONE ON 5000")
    s.ok(npg.parse_p1_reply(good) == (7, "DONE ON 5000", True), "parse_p1_reply khung dung", npg.parse_p1_reply(good))
    s.ok(npg.parse_p1_reply("7 DONE ON 5000*00") == (7, "DONE ON 5000", False), "parse_p1_reply bao sai checksum",
         npg.parse_p1_reply("7 DONE ON 5000*00"))
    low = "7 DONE ON 5000*" + xor_hex("7 DONE ON 5000").lower()
    s.ok(npg.parse_p1_reply(low) == (7, "DONE ON 5000", True), "parse_p1_reply nhan hex chu thuong", npg.parse_p1_reply(low))
    for bad in (None, "", "PONG 1 2", "x DONE*00", "7 DONE*0", "7 DONE*000"):
        s.ok(npg.parse_p1_reply(bad) is None, "parse_p1_reply(%r) -> None" % (bad,), npg.parse_p1_reply(bad))
    star = "5 DONE A*B*" + xor_hex("5 DONE A*B")
    s.ok(npg.parse_p1_reply(star) == (5, "DONE A*B", True), "parse_p1_reply lay '*' cuoi cung", npg.parse_p1_reply(star))
    s.done()


def p1_e2e(exe):
    s = Sc("P1-E2E", "run_p1_session (lenh --p1 cua quy trinh muc 4 D1) noi voi ping_proto.c THAT, day D9-GND va cua dong nhu T5")
    logs = []
    ser = SimSerial(exe, door=1, estop=0)
    ok, err = npg.run_p1_session(ser, timeout=0.2, log_print=lambda *a: logs.append(" ".join(str(x) for x in a)))
    st = ser.state()
    ser.close()
    tail = " || ".join(logs[-4:])
    s.ok(ok and err is None, "run_p1_session voi firmware that: PASS nhu quy trinh D1 hua ('TAT CA CAC PHEP THU P1 DEU DAT')",
         "ok=%s err=%r; cuoi log: %s" % (ok, err, tail))
    s.ok(st[2] == 0 and st[3] == 0, "sau phien --p1: PA8 thap, 0 vi pham PA8", st)
    s.done()


def p1_bare(exe):
    # Vong 2: quy trinh moi dat jumper D9-GND/D8-3V3 o muc 1 truoc D1 (L07 muc 1 da xu ly), nen ca nay doi tu
    # "D1 chay truoc khi noi D9 co PASS khong" sang ca an toan: quen/tuot day D9 thi --p1 khong duoc bat laser.
    s = Sc("P1-BARE", "tuot/quen day D9 (PC7 keo len = estop) khi chay --p1: cong cu bao FAIL, PA8 khong bao gio cao")
    logs = []
    ser = SimSerial(exe, door=1, estop=1)
    ok, err = npg.run_p1_session(ser, timeout=0.2, log_print=lambda *a: logs.append(" ".join(str(x) for x in a)))
    st = ser.state()
    ser.close()
    s.ok(not ok and st[2] == 0 and st[3] == 0 and st[0] == "ERROR" and st[1] == "ESTOP",
         "D9 ho: --p1 bao FAIL, bo o ERROR ESTOP, PA8 thap, 0 lan ghi PA8 cao", "ok=%s err=%r; trang thai bo %s" % (ok, err, st))
    s.done()


class _KeepOpen:
    """Cong COM gia cho main(): moi lan '--cmd' mo/dong cong nhung bo (tien trinh gia) van chay, nhu bo that.
    Vong 7: dat port = 'COM3' va KHONG co thuoc tinh _sim/is_sim, de cong cu xu ly nhu cong that (nhanh is_sim
    cua run_test_interlock khong duoc tu xac nhan VOM thay nguoi van hanh trong test nay)."""

    def __init__(self, dev, port="COM3"):
        self._dev = dev
        self.port = port

    def __getattr__(self, n):
        if n in ("_sim", "is_sim"):
            raise AttributeError(n)
        return getattr(self._dev, n)

    def close(self):
        pass


class _FakeStdin:
    """stdin gia: tty=True va tra loi 'answer' (nguoi van hanh go), hoac tty=False (chay khong tuong tac)."""

    def __init__(self, answer=None):
        self.answer = answer
        self.prompts = 0

    def isatty(self):
        return self.answer is not None

    def readline(self):
        self.prompts += 1
        return (self.answer or "") + "\n"


def run_main(sim, argv, clock=True, stdout=None, sleep_hook=None, vom=None, ser_obj=None):
    """Chay main() that cua cong cu voi '--port SIM' + argv. Cong COM la bo gia (van chay giua cac lan mo cong).
    clock=True: time.sleep(s) cua cong cu lam troi s giay tren bo gia (bo van poll); sleep_hook thay cho cach do."""
    import contextlib
    import io
    out = stdout if stdout is not None else io.StringIO()
    old_open, old_sleep, old_argv = npg.open_serial, npg.time.sleep, sys.argv
    npg.open_serial = lambda port, baud, timeout: (ser_obj if ser_obj is not None else _KeepOpen(sim))
    old_stdin = sys.stdin
    sys.stdin = _FakeStdin(vom)
    if sleep_hook is not None:
        npg.time.sleep = sleep_hook
    else:
        npg.time.sleep = (lambda sec: sim.advance(int(round(sec * 1000)))) if clock else (lambda sec: None)
    sys.argv = ["nucleo_ping.py", "--port", "SIM"] + list(argv)
    npg._cmd_auto_seq = 0   # moi lan goi CLI that la mot tien trinh moi: bo dem trong module bat dau lai tu 0
    try:
        with contextlib.redirect_stdout(out):
            rc = npg.main()
    finally:
        npg.open_serial, npg.time.sleep, sys.argv = old_open, old_sleep, old_argv
        sys.stdin = old_stdin
    return rc, (out.getvalue() if hasattr(out, "getvalue") else "")


def run_cmd(sim, text):
    """Dung lenh quy trinh muc 5: 'nucleo_ping.py --port COM3 --cmd "<text>"'."""
    rc, text_out = run_main(sim, ["--cmd", text])
    lines = text_out.splitlines()
    sent = [x[4:].strip() for x in lines if x.startswith("Gui:")]
    got = [x[5:].strip() for x in lines if x.startswith("Nhan:")]
    return rc, (sent[0] if sent else None), (got[0] if got else None)


Q3_STATES = {"IDLE", "HOMING", "MOVING", "SETTLING", "CAPTURING", "PAUSED", "COMPLETED", "ERROR"}


def _st(body):
    """STATUS Q3/D039: DONE state step laser door estop homed uptime last_err remaining -> dict | None."""
    tok = (body or "").split(" ")
    if len(tok) != 10 or tok[0] != "DONE" or tok[1] not in Q3_STATES:
        return None
    try:
        v = [int(x) for x in tok[2:8]] + [int(tok[9])]
    except ValueError:
        return None
    return {"state": tok[1], "laser": v[1], "door": v[2], "estop": v[3], "uptime": v[5], "err": tok[8], "rem": v[6]}


def _body(reply):
    r = npg.parse_p1_reply(reply) if reply else None
    return r[1] if r else (reply or "")


class _SeqFileSandbox:
    """get_next_p1_seq()/record_p1_seq() ghi tempfile.gettempdir()/scanner3d_p1_seq.txt: test doi sang thu muc
    tam rieng, khong dung toi tep seq that cua may nguoi dung."""

    def __enter__(self):
        self.old = tempfile.tempdir
        d = TMP / ("seqdir_%d" % int(time.perf_counter() * 1e6))
        d.mkdir()
        tempfile.tempdir = str(d)
        return self

    def __exit__(self, *a):
        tempfile.tempdir = self.old


def _pt_door_estop_b(s, sim, k, which, delay_ms, label="cach B"):
    """PT5/PT6 cach B (lenh roi rac): nguoi dung doi day sau delay_ms ke tu LASER ON."""
    base = 50 if which == "door" else 60
    code = "DOOR_OPEN" if which == "door" else "ESTOP"
    rc, sent, got = run_cmd(sim, "%d LASER ON" % base)
    on = _body(got) == "DONE ON 5000" and sim.state()[2] == 1
    sim.advance(delay_ms)
    sim.set_inputs(0, 0) if which == "door" else sim.set_inputs(1, 1)
    sim.advance(10)
    pa8_after = sim.state()[2]
    rc, sent, got = run_cmd(sim, "%d STATUS" % (base + 1))
    sd = _st(_body(got))
    st_ok = bool(sd) and sd["state"] == "ERROR" and sd["err"] == code and sd["laser"] == 0 and sd["rem"] == 0
    sim.set_inputs(1, 0)
    rc, sent2, got2 = run_cmd(sim, "%d CLEAR" % (base + 2))
    ok = on and pa8_after == 0 and st_ok and _body(got2) == "DONE IDLE"
    msg = ("lap %d: PT%s %s doi day sau %.1f s: PA8 thap, '%d STATUS' -> DONE ERROR ... %s, '%d CLEAR' -> DONE IDLE"
           % (k, "5" if which == "door" else "6", label, delay_ms / 1000.0, base + 1, code, base + 2))
    if s is not None:
        s.ok(ok, msg, "ON %s | STATUS %s | CLEAR %s" % (on, got, got2))
    if sim.state()[0] != "IDLE":
        sim.set_inputs(1, 0)
        run_cmd(sim, "CLEAR")
    return ok, got


def interlock_run(sim, which, trip_ms, vom="y", ser_obj=None, extra=(), alias=False, restore_ms=None):
    """Chay '--test-door' / '--test-estop' (cach A; alias=True: '--test-interlock door|estop'). Nguoi dung doi day
    o giay trip_ms tinh tu LASER ON (None = khong doi); restore_ms: cam day ve muc binh thuong restore_ms sau trip,
    trong cung lan ngu voi trip (Vong 9, N3/N8). Ghi lai trang thai bo sau moi lan cong cu ngu (truoc khi doi day)."""
    st = {"calls": 0, "elapsed": 0, "tripped": False, "samples": []}

    def hook(sec):
        st["calls"] += 1
        ms = int(round(sec * 1000))
        if st["calls"] == 1:           # sleep(0.05) truoc khi gui LASER ON
            sim.advance(ms)
            return
        if trip_ms is not None and not st["tripped"] and st["elapsed"] + ms >= trip_ms:
            first = trip_ms - st["elapsed"]
            if first > 0:
                sim.advance(first)
            if which == "door":
                sim.set_inputs(0, 0)
            else:
                sim.set_inputs(1, 1)
            st["tripped"] = True
            if restore_ms is not None and ms - first >= restore_ms:
                sim.advance(restore_ms)
                sim.set_inputs(1, 0)
                st["restored"] = True
                sim.advance(ms - first - restore_ms)
            else:
                sim.advance(ms - first)
        else:
            sim.advance(ms)
            if not st["tripped"]:
                st["samples"].append(sim.state())
        st["elapsed"] += ms
    argv = ["--test-interlock", which] if alias else ["--test-door" if which == "door" else "--test-estop"]
    rc, out = run_main(sim, argv + list(extra), sleep_hook=hook, vom=vom, ser_obj=ser_obj)
    return rc, out, st


def _check_interlock(s, sim, k, which, trip_ms):
    code = "DOOR_OPEN" if which == "door" else "ESTOP"
    rc, out, st = interlock_run(sim, which, trip_ms)
    pre_ok = all(x[0] == "CAPTURING" and x[2] == 1 for x in st["samples"])
    after = sim.state()
    s.ok(rc == 0 and "KET LUAN: PHEP THU DAT" in out and "Nguoi van hanh xac nhan VOM" in out and pre_ok and after[2] == 0
         and after[:2] == ("ERROR", code),
         "lap %d: --test-%s, doi day o giay %.1f: truoc do PA8 cao lien tuc (khong LINK_LOST/LASER_TIMEOUT); sau: PA8 thap, ERROR %s; rc 0 'PHEP THU DAT'"
         % (k, "door" if which == "door" else "estop", trip_ms / 1000.0, code),
         "rc %s; %d mau truoc khi doi day, deu CAPTURING+PA8 cao: %s; bo sau %s" % (rc, len(st["samples"]), pre_ok, after))
    sim.set_inputs(1, 0)
    rc2, sent, got = run_cmd(sim, "CLEAR")
    s.ok(_body(got) == "DONE IDLE" and sim.state()[0] == "IDLE", "lap %d: cam lai day, '--cmd \"CLEAR\"' -> DONE IDLE" % k, "gui %s | nhan %s" % (sent, got))
    return out


def p1_proc(exe):
    s = Sc("P1-PROC", "quy trinh muc 4-5 chay NGUYEN VAN bang main() cua cong cu noi ping_proto.c that: D1, PT1-PT6 moi phep thu 3 lan (PT5/PT6 ca cach A va cach B)")
    with _SeqFileSandbox():
        sim = SimSerial(exe, door=1, estop=0)
        ok, err = npg.run_p1_session(sim, timeout=0.2, log_print=lambda *a: None)
        s.ok(ok, "D1 --p1 PASS", err)
        sim.reset_input_buffer()
        for k in range(3):
            # Vong 5 (L14): tai lieu dung lenh noi 'ON; sleep 1; OFF; STATUS' - khoang ON->OFF ~1.5 s (sleep 1 + khoi dong Python)
            rc, sent, got = run_cmd(sim, "10 LASER ON")
            a = _body(got) == "DONE ON 5000" and sim.state()[2] == 1
            sim.advance(1500)
            rc, sent, got2 = run_cmd(sim, "11 LASER OFF")
            p = sim.state()[2]
            rc, sent, got3 = run_cmd(sim, "STATUS")
            sd = _st(_body(got3))
            s.ok(a and _body(got2) == "DONE OFF 0" and p == 0 and bool(sd) and sd["state"] == "IDLE" and sd["laser"] == 0 and sd["err"] == "NONE" and sd["rem"] == 0,
                 "lap %d: PT1 lenh noi: '10 LASER ON' -> ON; sau 1.5 s '11 LASER OFF' -> DONE OFF 0, PA8 thap; STATUS -> DONE IDLE ... NONE" % k,
                 "%s | %s | %s" % (got, got2, got3))
        for k in range(3):
            rc, sent, got = run_cmd(sim, "20 LASER ON")
            a = _body(got) == "DONE ON 5000" and sim.state()[2] == 1
            sim.advance(3500)
            st = sim.state()
            rc, sent, got2 = run_cmd(sim, "21 STATUS")
            rc, sent, got3 = run_cmd(sim, "22 CLEAR")
            sd = _st(_body(got2))
            s.ok(a and st[2] == 0 and st[:2] == ("ERROR", "LINK_LOST") and bool(sd) and sd["state"] == "ERROR"
                 and sd["err"] == "LINK_LOST" and sd["laser"] == 0 and sd["rem"] == 0 and _body(got3) == "DONE IDLE",
                 "lap %d: PT2 ON, im lang 3.5 s -> PA8 thap ERROR LINK_LOST; '21 STATUS' ... LINK_LOST; '22 CLEAR' -> DONE IDLE" % k,
                 "bo %s | %s | %s" % (st, got2, got3))
        for k in range(3):
            rc, out = run_main(sim, ["--test-laser-timeout"])
            bodies = [_body(x.split("Nhan:", 1)[1].split(" -> ")[0].strip()) for x in out.splitlines() if "Nhan:" in x]
            hb = bodies[1:7]
            ok3 = (len(bodies) == 8 and bodies[0] == "DONE ON 5000" and hb[:4] == ["DONE CAPTURING"] * 4
                   and hb[4:] == ["DONE IDLE"] * 2 and bool(_st(bodies[7])) and _st(bodies[7])["state"] == "IDLE"
                   and _st(bodies[7])["err"] == "LASER_TIMEOUT" and _st(bodies[7])["rem"] == 0 and sim.state()[2] == 0 and rc == 0)
            s.ok(ok3, "lap %d: PT3 cach A '--test-laser-timeout': HB 1-4 CAPTURING, tu HB 5 (5.0 s) IDLE; STATUS IDLE ... LASER_TIMEOUT" % k,
                 "rc %s; %s" % (rc, bodies))
        for k in range(3):
            rc, sent, got = run_cmd(sim, "40 LASER ON")
            a = _body(got) == "DONE ON 5000" and sim.state()[2] == 1
            sim.advance(1500)   # Vong 5 (L14): lenh noi 'ON; sleep 1; STOP; CLEAR'
            rc, sent, got2 = run_cmd(sim, "41 STOP")
            p = sim.state()[2]
            rc, sent, got3 = run_cmd(sim, "42 CLEAR")
            s.ok(a and _body(got2) == "DONE PAUSED" and p == 0 and _body(got3) == "DONE IDLE",
                 "lap %d: PT4 ON; '41 STOP' -> DONE PAUSED, PA8 thap; '42 CLEAR' -> DONE IDLE" % k, "%s | %s | %s" % (got, got2, got3))
        for which in ("door", "estop"):
            for k, trip in enumerate((2000, 6000, 10500)):
                _check_interlock(s, sim, k, which, trip)
            for k in range(3):
                _pt_door_estop_b(s, sim, k, which, 1500)
        s.ok(sim.state()[3] == 0, "ca phien: 0 lan ghi PA8 cao ngoai CAPTURING", sim.state())
        sim.close()
    s.done()


def p1_auto(exe):
    s = Sc("P1-AUTO", "hoi quy L09: '--cmd' KHONG ghi seq (moi lan mot tien trinh moi) - lenh thu hai tro di phai duoc thuc thi")
    with _SeqFileSandbox():
        sim = SimSerial(exe, door=1, estop=0)
        npg.run_p1_session(sim, timeout=0.2, log_print=lambda *a: None)
        sim.reset_input_buffer()
        steps = [("LASER ON", "DONE ON 5000", 1), ("LASER OFF", "DONE OFF 0", 0), ("LASER ON", "DONE ON 5000", 1),
                 ("STOP", "DONE PAUSED", 0), ("CLEAR", "DONE IDLE", 0), ("STATUS", "DONE IDLE 0 0 1 0 0 ", 0)]
        seqs = []
        for text, exp, pa8 in steps:
            rc, sent, got = run_cmd(sim, text)
            seqs.append(sent.split(" ")[0] if sent else None)
            s.ok(_body(got).startswith(exp) and sim.state()[2] == pa8, "--cmd \"%s\" -> %s..., PA8=%d" % (text, exp, pa8),
                 "gui %s | nhan %s" % (sent, got))
        s.ok(len(set(seqs)) == len(seqs), "moi lan '--cmd' mot seq khac nhau", seqs)
        sim.close()
    s.done()


def p1_interlock(exe):
    s = Sc("P1-IL", "hoi quy L12: PT5/PT6 cach A khi nguoi dung doi day CHAM (3.5 s, 4.5 s, 11.5 s) va khi khong doi day")
    with _SeqFileSandbox():
        sim = SimSerial(exe, door=1, estop=0)
        npg.run_p1_session(sim, timeout=0.2, log_print=lambda *a: None)
        sim.reset_input_buffer()
        outs = []
        for which in ("door", "estop"):
            for k, trip in enumerate((3500, 4500, 11500)):
                outs.append(_check_interlock(s, sim, k, which, trip))
        for which in ("door", "estop"):
            rc, out, st = interlock_run(sim, which, None)
            pre_ok = all(x[0] == "CAPTURING" and x[2] == 1 for x in st["samples"])
            after = sim.state()
            s.ok(rc == 1 and "KHONG PHAT HIEN" in out and pre_ok and after[2] == 0 and after[0] == "IDLE",
                 "--test-%s, khong doi day: het 12 s rc 1, cong cu gui LASER OFF, PA8 thap, bo IDLE" % which,
                 "rc %s; %d mau deu CAPTURING+PA8 cao: %s; bo sau %s" % (rc, len(st["samples"]), pre_ok, after))
        s.ok(sim.state()[3] == 0, "ca phien: 0 lan ghi PA8 cao ngoai CAPTURING", sim.state())
        warn = sum(1 for o in outs if "CANH BAO" in o)
        okline = sum(1 for o in outs if "[OK] DA PHAT HIEN NGAT LIEN DONG" in o)
        s.ok(warn == 0 and okline == len(outs), "hoi quy L15: lien dong dung thi khong in '[CANH BAO]', moi lan co dong '[OK] DA PHAT HIEN ...'",
             "%d/%d lan co CANH BAO, %d/%d lan co [OK]" % (warn, len(outs), okline, len(outs)))
        hint = [x.strip() for x in outs[0].splitlines() if x.strip().startswith("Huong dan:")]
        s.note("dong huong dan cong cu in sau khi DAT: %s (Git Bash can '.venv/Scripts/python.exe', xem L11; tai lieu da ghi dung)" % (hint[0] if hint else None))
        slow = []
        for which in ("door", "estop"):
            ok, got = _pt_door_estop_b(None, sim, 0, which, 3500)
            slow.append("%s: %s" % (which, got))
        s.note("cach B (lenh roi rac) doi day sau 3.5 s: tai lieu da canh bao phai < 2.5 s; ket qua %s" % "; ".join(slow))
        sim.close()
    s.done()


def p1_mix(exe):
    s = Sc("P1-MIX", "ghi nhan: tron seq tu tang (cach A) va seq ghi san (cach B) - seq co trung khong", note_only=True)
    with _SeqFileSandbox():
        sim = SimSerial(exe, door=1, estop=0)
        npg.run_p1_session(sim, timeout=0.2, log_print=lambda *a: None)
        sim.reset_input_buffer()
        run_cmd(sim, "20 LASER ON")
        sim.advance(3500)
        run_cmd(sim, "21 STATUS")
        run_cmd(sim, "22 CLEAR")
        run_main(sim, ["--test-laser-timeout"])
        rc, sent, got = run_cmd(sim, "30 LASER ON")
        s.note("PT2 (seq cuoi 22) roi PT3 cach A mot lan (seq 23..30), roi cach B '30 LASER ON' -> nhan %r, PA8=%d" % (got, sim.state()[2]))
        run_cmd(sim, "LASER OFF")
        run_cmd(sim, "42 CLEAR")
        rc, out, st = interlock_run(sim, "door", 8000)
        last = [x for x in out.splitlines() if "Kiem tra STATUS" in x]
        sim.set_inputs(1, 0)
        rc, sent, got = run_cmd(sim, "52 CLEAR")
        s.note("PT4 (seq cuoi 42) roi PT5 cach A doi day o giay 8 (%s), roi nguoi dung go '52 CLEAR' cua cach B -> nhan %r, bo %s"
               % (last[0].strip() if last else "?", got, sim.state()[:2]))
        sim.close()
    s.done()


def p1_encoding(exe):
    s = Sc("P1-ENC", "hoi quy L13: '--test-laser-timeout', '--test-door', '--test-estop' khi dau ra ghi vao tep/pipe cp1252 ('| tee log.txt')")
    import io
    with _SeqFileSandbox():
        for argv in (["--test-laser-timeout"], ["--test-door"], ["--test-estop"]):
            sim = SimSerial(exe, door=1, estop=0)
            buf = io.BytesIO()
            w = io.TextIOWrapper(buf, encoding="cp1252", errors="strict", newline="\n")
            try:
                if argv[0] == "--test-laser-timeout":
                    rc, _ = run_main(sim, argv, stdout=w)
                else:
                    import contextlib
                    rc = None
                    trip = {"n": 0}

                    def hook(sec, _sim=sim, _w=argv[0]):
                        trip["n"] += 1
                        _sim.advance(int(round(sec * 1000)))
                        if trip["n"] == 3:
                            _sim.set_inputs(0, 0) if _w == "--test-door" else _sim.set_inputs(1, 1)
                    rc, _ = run_main(sim, argv + ["--confirm-vom-0v"], stdout=w, sleep_hook=hook)
                    del contextlib
                w.flush()
                exc = None
            except Exception as e:  # noqa: BLE001
                exc = "%s: %s" % (type(e).__name__, str(e)[:80])
                rc = None
            st = sim.state()
            sim.close()
            s.ok(exc is None and rc == 0 and st[2] == 0, "%s voi stdout cp1252: khong hong, rc 0, PA8 thap cuoi phien" % argv[0],
                 "exc %s; rc %s; bo %s; %d byte log" % (exc, rc, st, len(buf.getvalue())))
    nonascii = [i + 1 for i, line in enumerate((REPO / "pc" / "nucleo_ping.py").read_text(encoding="utf-8").splitlines())
                if any(ord(c) > 127 for c in line)]
    s.ok(not nonascii, "pc/nucleo_ping.py chi con ky tu ASCII (nhu ban goc)", nonascii[:10])
    s.done()


class _Fault:
    """Cong COM gia co tiem loi, boc quanh SimSerial (bo gia chay ping_proto.c that).
    mutate(dong, lenh) -> dong moi ('' = mat phan hoi, None = giu nguyen) cho phan hoi cua 'lenh';
    dead_after = than lenh ma sau khi gui, moi lan ghi tiep theo nem OSError (mat cong);
    read_raise = (than lenh, ngoai le) nem khi doc phan hoi cua lenh do (mot lan, chi SAU khi da gui LASER ON).
    Vong 9: faults = [(giai doan, than lenh, lan thu n, ngoai le)], moi muc nem MOT lan; giai doan:
      'write_before' (byte chua toi bo), 'write_after' (byte DA toi bo roi write nem), 'flush', 'read'.
    sent = dong DA toi bo; attempts = moi lan goi write (ke ca loi); events = thu tu W/FAULT/MUT/CLOSE."""

    def __init__(self, dev, mutate=None, dead_after=None, read_raise=None, port="COM3", faults=()):
        self._dev = dev
        self.port = port
        self.mutate = mutate
        self.dead_after = dead_after
        self.read_raise = read_raise
        self.dead = False
        self.sent = []
        self.last = None
        self.faults = [list(x) + [False] for x in faults]
        self.count = {}
        self.attempts = []
        self.events = []

    def _hit(self, stage):
        for fl in self.faults:
            if not fl[4] and fl[0] == stage and fl[1] == self.last and fl[2] == self.count.get(self.last, 0):
                fl[4] = True
                self.events.append("FAULT %s %s#%d" % (stage, self.last, fl[2]))
                raise fl[3]

    def __getattr__(self, n):
        if n in ("_sim", "is_sim"):
            raise AttributeError(n)
        return getattr(self._dev, n)

    def write(self, data):
        txt = bytes(data).decode("ascii", "replace").strip()
        self.attempts.append(txt)
        self.events.append("W " + txt)
        if self.dead:
            raise OSError("tiem loi: mat cong COM")
        body = txt.split("*")[0]
        self.last = body.split(" ", 1)[1] if " " in body and body.split(" ", 1)[0].isdigit() else body
        self.count[self.last] = self.count.get(self.last, 0) + 1
        self._hit("write_before")
        self.sent.append(txt)
        n = self._dev.write(data)
        if self.dead_after is not None and self.last == self.dead_after:
            self.dead = True
        self._hit("write_after")
        return n

    def read_until(self, term=b"\n"):
        on_sent = any(_split(x) and _split(x)[1] == "LASER ON" for x in self.sent)
        if self.read_raise is not None and self.last == self.read_raise[0] and on_sent:
            exc = self.read_raise[1]
            self.read_raise = None
            raise exc
        self._hit("read")
        line = self._dev.read_until(term)
        if self.mutate is not None and line:
            new = self.mutate(line.decode("ascii", "replace").rstrip("\n"), self.last)
            if new is not None:
                self.events.append("MUT %s" % self.last)
                line = (new + "\n").encode("ascii") if new != "" else b""
        return line

    def flush(self):
        self._hit("flush")

    def close(self):
        self.events.append("CLOSE")


def _frame(seq, body):
    b = "%s %s" % (seq, body)
    return "%s*%s" % (b, xor_hex(b))


def _split(line):
    """'<seq> <body>*HH' -> (seq, body) | None"""
    if "*" not in line:
        return None
    b = line.rsplit("*", 1)[0]
    seq, _, body = b.partition(" ")
    return seq, body


def _sent_off_after_on(sent):
    """seq cua cac lenh LASER OFF/STOP gui SAU lenh LASER ON dau tien"""
    out, on = [], False
    for x in sent:
        sp = _split(x)
        if not sp:
            continue
        if sp[1] == "LASER ON":
            on = True
        elif on and sp[1] in ("LASER OFF", "STOP"):
            out.append(int(sp[0]))
    return out


def _seq_preset(value):
    """Dat tep seq cua cong cu (trong hop cat) ve 'value' va bo dem module ve 0, nhu mot tien trinh moi."""
    npg._cmd_auto_seq = 0
    f = Path(tempfile.gettempdir()) / "scanner3d_p1_seq.txt"
    if value is None:
        if f.exists():
            f.unlink()
    else:
        f.write_text(str(value))


def p1_r03(exe):
    s = Sc("P1-R03", "R03 (01_PLAN Vong 7 muc 3.3, T3/T4): --p1 loi sau LASER ON -> FAIL va chu dong gui LASER OFF/STOP seq moi, PA8 ha khi cong con; mat cong -> FAIL + canh bao, bo tu ha 3 s")
    cases = [
        ("mat phan hoi STATUS buoc 3", lambda ln, c: "" if c == "STATUS" and ln.startswith("3 ") else None),
        ("phan hoi buoc 3 khong co '*'", lambda ln, c: ln.split("*")[0] if c == "STATUS" and ln.startswith("3 ") else None),
        ("sai checksum buoc 3", lambda ln, c: ln[:-1] + ("0" if ln[-1] != "0" else "1") if c == "STATUS" and ln.startswith("3 ") else None),
        ("sai seq buoc 3 (checksum dung)", lambda ln, c: _frame(99, _split(ln)[1]) if c == "STATUS" and ln.startswith("3 ") else None),
        ("sai noi dung buoc 3 (IDLE)", lambda ln, c: _frame(3, "DONE IDLE 0 0 1 0 0 1 NONE 0") if c == "STATUS" and ln.startswith("3 ") else None),
        ("STATUS buoc 3 thieu token", lambda ln, c: _frame(3, " ".join(_split(ln)[1].split(" ")[:-1])) if c == "STATUS" and ln.startswith("3 ") else None),
        ("sai checksum o chinh phan hoi LASER ON (buoc 2)", lambda ln, c: ln[:-1] + ("0" if ln[-1] != "0" else "1") if c == "LASER ON" else None),
        ("sai noi dung HEARTBEAT buoc 4", lambda ln, c: _frame(4, "DONE IDLE") if c == "HEARTBEAT" else None),
    ]
    with _SeqFileSandbox():
        for name, mut in cases:
            sim = SimSerial(exe, door=1, estop=0)
            f = _Fault(sim, mutate=mut)
            _seq_preset(None)
            logs = []
            ok, err = npg.run_p1_session(f, timeout=0.2, log_print=lambda *a: logs.append(" ".join(str(x) for x in a)))
            st = sim.state()
            offs = _sent_off_after_on(f.sent)
            s.ok(not ok and offs and st[2] == 0 and any("[R03 AN TOAN]" in x for x in logs),
                 "%s: --p1 FAIL, gui LASER OFF seq moi, PA8 thap ngay, bao 'R03 AN TOAN'" % name,
                 "ok=%s; OFF/STOP sau ON: %s; bo %s; %s" % (ok, offs, st, [x for x in logs if "R03" in x][:2]))
            sim.close()
        # loi I/O khi doc phan hoi buoc 3 (cong con song)
        sim = SimSerial(exe, door=1, estop=0)
        f = _Fault(sim, read_raise=("STATUS", OSError("tiem loi: loi doc cong")))
        _seq_preset(None)
        logs = []
        ok, err = npg.run_p1_session(f, timeout=0.2, log_print=lambda *a: logs.append(" ".join(str(x) for x in a)))
        st = sim.state()
        s.ok(not ok and _sent_off_after_on(f.sent) and st[2] == 0, "ngoai le I/O khi doc buoc 3: FAIL, gui OFF, PA8 thap",
             "ok=%s err=%r; bo %s" % (ok, err, st))
        sim.close()
        # mat cong ngay sau LASER ON: khong gui duoc gi nua
        sim = SimSerial(exe, door=1, estop=0)
        f = _Fault(sim, dead_after="LASER ON")
        _seq_preset(None)
        logs = []
        ok, err = npg.run_p1_session(f, timeout=0.2, log_print=lambda *a: logs.append(" ".join(str(x) for x in a)))
        st1 = sim.state()
        sim.advance(3000)
        st2 = sim.state()
        s.ok(not ok and "PASS" not in (err or "") and any("[R03 NGUY HIEM]" in x for x in logs) and st1[2] == 1 and st2[2] == 0
             and st2[:2] == ("ERROR", "LINK_LOST"),
             "mat cong ngay sau ON: FAIL + canh bao 'R03 NGUY HIEM' (khong xac nhan duoc); bo tu ha PA8 sau 3 s (LINK_LOST)",
             "ok=%s; ngay sau %s; sau 3 s %s" % (ok, st1, st2))
        sim.close()
        # dung som: nguoi dung Ctrl+C luc dang doi phan hoi buoc 3 (sau LASER ON)
        sim = SimSerial(exe, door=1, estop=0)
        f = _Fault(sim, read_raise=("STATUS", KeyboardInterrupt()))
        _seq_preset(None)
        try:
            npg.run_p1_session(f, timeout=0.2, log_print=lambda *a: None)
            exc = None
        except KeyboardInterrupt:
            exc = "KeyboardInterrupt"
        st = sim.state()
        offs = _sent_off_after_on(f.sent)
        s.ok(bool(offs) and st[2] == 0,
             "dung som (Ctrl+C) sau LASER ON: van co gang gui LASER OFF/STOP truoc khi thoat (01_PLAN Vong 7 muc 3.3 'hoac dung som')",
             "ngoai le %s; OFF/STOP sau ON: %s; bo %s" % (exc, offs, st))
        sim.close()
    s.done()


def p1_seq(exe):
    s = Sc("P1-SEQ", "R03: lenh dung khan cua --p1 phai mang 'seq moi' (khac seq bo vua nhan) - neu trung, bo gui lai phan hoi cu va KHONG tat")
    with _SeqFileSandbox():
        for preset, step in ((None, 3), (50, 3), (2, 3), (1, 2)):
            sim = SimSerial(exe, door=1, estop=0)
            k = step
            if step == 2:
                mut = lambda ln, c: ln[:-1] + ("0" if ln[-1] != "0" else "1") if c == "LASER ON" else None
            else:
                mut = lambda ln, c, _k=k: ln[:-1] + ("0" if ln[-1] != "0" else "1") if c == "STATUS" and ln.startswith("%d " % _k) else None
            f = _Fault(sim, mutate=mut)
            _seq_preset(preset)
            logs = []
            ok, err = npg.run_p1_session(f, timeout=0.2, log_print=lambda *a: logs.append(" ".join(str(x) for x in a)))
            st = sim.state()
            offs = _sent_off_after_on(f.sent)
            s.ok(not ok and st[2] == 0,
                 "tep seq dang la %s, loi o buoc %d: LASER OFF cuu ho phai duoc bo thuc thi (PA8 thap)" % (preset, step),
                 "OFF seq %s (bo vua nhan seq %d); bo %s; %s" % (offs, step, st, [x for x in logs if "R03 AN TOAN" in x or "R03 NGUY HIEM" in x][:1]))
            sim.close()
    s.done()


def _mut_status_after_trip(kind):
    def m(ln, c):
        if c != "STATUS":
            return None
        sp = _split(ln)
        if not sp or not sp[1].startswith("DONE ERROR "):
            return None
        seq, body = sp
        tok = body.split(" ")
        if kind == "bad_chk":
            return ln[:-1] + ("0" if ln[-1] != "0" else "1")
        if kind == "bad_seq":
            return _frame(int(seq) + 100, body)
        if kind == "missing_tok":
            return _frame(seq, " ".join(tok[:-1]))
        if kind == "wrong_state":
            tok[1] = "IDLE"
            return _frame(seq, " ".join(tok))
        if kind == "laser1":
            tok[3] = "1"
            return _frame(seq, " ".join(tok))
        if kind == "wrong_err":
            tok[8] = "ESTOP"
            return _frame(seq, " ".join(tok))
        if kind == "rem_nonzero":
            tok[9] = "4000"
            return _frame(seq, " ".join(tok))
        if kind == "garbage":
            return "garbage DOOR_OPEN"
        return None
    return m


def p1_r04(exe):
    s = Sc("P1-R04", "R04 (01_PLAN Vong 7 muc 3.4, T3/T4): --test-door chi DAT khi STATUS dung seq/checksum/10 token/ERROR/laser=0/last_err DUNG va nguoi van hanh xac nhan VOM")
    with _SeqFileSandbox():
        for kind in ("bad_chk", "bad_seq", "missing_tok", "wrong_state", "laser1", "wrong_err", "rem_nonzero", "garbage"):
            sim = SimSerial(exe, door=1, estop=0)
            f = _Fault(sim, mutate=_mut_status_after_trip(kind))
            rc, out, st = interlock_run(sim, "door", 2000, vom="y", ser_obj=f)
            fin = sim.state()
            clear = [x for x in f.sent if _split(x) and _split(x)[1] == "CLEAR"]
            s.ok(rc != 0 and "PHEP THU DAT" not in out and fin[2] == 0 and not clear,
                 "STATUS sau trip bi lam hong (%s): KHONG in 'PHEP THU DAT', rc != 0, PA8 thap, khong tu CLEAR" % kind,
                 "rc %s; dong ket luan %s; bo %s" % (rc, [x for x in out.splitlines() if "KET LUAN" in x or "R04" in x][:2], fin))
            sim.close()
        for label, vom, extra, want in (("khong tuong tac, khong co co", None, (), 1), ("nguoi van hanh go 'n'", "n", (), 1),
                                        ("nguoi van hanh go 'y'", "y", (), 0), ("co --confirm-vom-0v", None, ("--confirm-vom-0v",), 0)):
            sim = SimSerial(exe, door=1, estop=0)
            rc, out, st = interlock_run(sim, "door", 2000, vom=vom, extra=extra)
            dat = "PHEP THU DAT" in out
            s.ok(rc == want and dat == (want == 0) and sim.state()[2] == 0,
                 "xac nhan VOM - %s: %s" % (label, "DAT, rc 0" if want == 0 else "KHONG DAT, rc != 0"),
                 "rc %s; %s" % (rc, [x for x in out.splitlines() if "VOM" in x or "KET LUAN" in x][-2:]))
            sim.close()
        # mat cong ngay sau LASER ON trong --test-door
        sim = SimSerial(exe, door=1, estop=0)
        f = _Fault(sim, dead_after="LASER ON")
        try:
            rc, out, st = interlock_run(sim, "door", 2000, vom="y", ser_obj=f)
            exc = None
        except Exception as e:  # noqa: BLE001
            rc, out, exc = None, "", type(e).__name__
        st1 = sim.state()
        sim.advance(3000)
        st2 = sim.state()
        s.ok("PHEP THU DAT" not in out and rc != 0 and st2[2] == 0,
             "--test-door mat cong ngay sau ON: khong bao DAT; bo tu ha PA8 sau 3 s",
             "rc %s, ngoai le %s; ngay sau %s; sau 3 s %s" % (rc, exc, st1, st2))
        sim.close()
    s.done()


def _first_on(kind):
    """Lam hong phan hoi cua lenh LASER ON DAU TIEN (bo da nhan va thuc thi lenh, PA8 cao).
    'late' = phan hoi ON den sau khi cong cu het cho: dong ON nam lai trong bo dem, moi phan hoi sau bi lui mot dong."""
    st = {"n": 0, "q": []}

    def m(ln, c):
        if st["q"]:
            st["q"].append(ln)
            return st["q"].pop(0)
        if c != "LASER ON":
            return None
        st["n"] += 1
        if st["n"] != 1:
            return None
        seq, body = _split(ln)
        if kind == "bad_chk":
            return ln[:-1] + ("0" if ln[-1] != "0" else "1")
        if kind == "missing":
            return ""
        if kind == "wrong_seq":
            return _frame(99 if seq != "99" else 98, body)
        if kind == "wrong_body":
            return _frame(seq, "DONE IDLE")
        if kind == "forged_refusal":
            return _frame(seq, "ERROR DOOR_OPEN")
        if kind == "late":
            st["q"].append(ln)
            return ""
        return None
    return m


ON_FAULTS = (("bad_chk", "phan hoi LASER ON sai checksum"), ("missing", "mat phan hoi LASER ON"),
             ("wrong_seq", "phan hoi LASER ON sai seq (checksum dung)"),
             ("wrong_body", "phan hoi LASER ON sai noi dung 'DONE IDLE' (checksum, seq dung)"))


def _off_fresh(sent):
    """LASER OFF/STOP dau tien sau ON phai mang seq KHAC lenh lien truoc no (bo vua nhan), neu trung bo nuot lenh."""
    prev = None
    on = False
    for x in sent:
        sp = _split(x)
        if not sp:
            continue
        if sp[1] == "LASER ON":
            on = True
        elif on and sp[1] in ("LASER OFF", "STOP"):
            return prev is not None and sp[0] != prev
        prev = sp[0]
    return False


def _fault_run(exe, argv, mutate=None, read_raise=None, door=1, estop=0, prep=None, interlock=None):
    """Chay main() that qua cong COM gia co tiem loi. interlock = 'door'/'estop' (cach A) hoac None (argv)."""
    sim = SimSerial(exe, door=door, estop=estop)
    if prep is not None:
        prep(sim)
    f = _Fault(sim, mutate=mutate, read_raise=read_raise)
    try:
        if interlock is not None:
            rc, out, _ = interlock_run(sim, interlock, None, vom="y", ser_obj=f)
        else:
            rc, out = run_main(sim, argv, ser_obj=f, vom="y")
        exc = None
    except KeyboardInterrupt:
        rc, out, exc = None, "", "KeyboardInterrupt"
    fin = sim.state()
    r = {"rc": rc, "out": out, "exc": exc, "fin": fin, "offs": _sent_off_after_on(f.sent), "fresh": _off_fresh(f.sent),
         "sent": list(f.sent), "sim": sim}
    return r


def _tool_off(r):
    """Laser da tat NGAY boi lenh cua cong cu (khong phai nho LINK_LOST/LASER_TIMEOUT cua firmware), khong vi pham PA8."""
    fin = r["fin"]
    return bool(r["offs"]) and r["fresh"] and fin[2] == 0 and fin[1] not in ("LINK_LOST", "LASER_TIMEOUT") and fin[3] == 0


def _brief(r):
    lines = [x for x in r["out"].splitlines() if "FAIL" in x or "R03" in x or "DAT" in x]
    return "rc %s, ngoai le %s; OFF/STOP sau ON %s (seq moi %s); bo %s; %s" % (
        r["rc"], r["exc"], r["offs"], r["fresh"], r["fin"], lines[:3])


def _to_error_state(sim):
    """Dua bo ve ERROR (DOOR_OPEN) roi dong cua lai, KHONG CLEAR: bo con o ERROR."""
    run_cmd(sim, "LASER ON")
    sim.set_inputs(0, 0)
    sim.advance(10)
    sim.set_inputs(1, 0)
    sim.advance(10)


def p1_r04b(exe):
    s = Sc("P1-R04B", "R04/R03 cho --test-door/--test-estop: phan hoi cua chinh LASER ON hong/mat/sai seq/sai noi dung/den muon, Ctrl+C luc doc ON va luc giam sat -> chu dong tat seq moi, khong DAT; tu choi hop le -> FAIL, PA8 thap")
    with _SeqFileSandbox():
        for which in ("door", "estop"):
            for kind, label in ON_FAULTS:
                if which == "estop" and kind not in ("bad_chk", "missing"):
                    continue
                r = _fault_run(exe, None, mutate=_first_on(kind), interlock=which)
                s.ok(r["rc"] not in (None, 0) and "PHEP THU DAT" not in r["out"] and _tool_off(r),
                     "--test-%s, %s (bo da thuc thi ON): FAIL va chu dong gui LASER OFF/STOP seq moi, PA8 thap ngay (01_PLAN Vong 7 muc 3.4)" % (which, label),
                     _brief(r))
                r["sim"].close()
        # phan hoi ON den muon (sau timeout cua cong cu)
        r = _fault_run(exe, None, mutate=_first_on("late"), interlock="door")
        s.ok(r["rc"] not in (None, 0) and "PHEP THU DAT" not in r["out"] and _tool_off(r),
             "--test-door, phan hoi LASER ON den muon (sau timeout): FAIL, van gui LASER OFF seq moi, PA8 thap",
             _brief(r))
        s.note("--test-door, phan hoi LASER ON den muon: cong cu doc lech mot dong nen bao '%s' (bo thuc te: %s)" % (
            "R03 AN TOAN" if "R03 AN TOAN" in r["out"] else ("R03 NGUY HIEM" if "R03 NGUY HIEM" in r["out"] else "?"), r["fin"]))
        r["sim"].close()
        # Ctrl+C dung luc doc phan hoi LASER ON (Vong 7: NOTE; Vong 8: sau khi Coder dua buoc ON vao khoi try -> kiem)
        r = _fault_run(exe, None, read_raise=("LASER ON", KeyboardInterrupt()), interlock="door")
        s.ok(r["rc"] == 1 and "PHEP THU DAT" not in r["out"] and _tool_off(r),
             "--test-door, Ctrl+C dung luc doc phan hoi LASER ON: gui LASER OFF seq moi, PA8 thap, rc 1", _brief(r))
        r["sim"].close()
        # Ctrl+C luc dang giam sat (doc phan hoi HEARTBEAT dau tien)
        for which in ("door", "estop"):
            r = _fault_run(exe, None, read_raise=("HEARTBEAT", KeyboardInterrupt()), interlock=which)
            s.ok(r["rc"] == 1 and "PHEP THU DAT" not in r["out"] and _tool_off(r),
                 "--test-%s, Ctrl+C luc giam sat lien dong: gui LASER OFF seq moi, PA8 thap, rc 1" % which, _brief(r))
            r["sim"].close()
        # bo tu choi LASER ON hop le: khong co luc nao PA8 cao
        for label, kw in (("cua mo tu dau (D8 o GND) -> 'ERROR DOOR_OPEN'", dict(interlock="door", door=0)),
                          ("estop nhan tu dau (D9 ho) -> 'ERROR ESTOP'", dict(interlock="estop", estop=1)),
                          ("bo dang ERROR chua CLEAR -> 'ERROR IN_ERROR'", dict(interlock="door", prep=_to_error_state))):
            r = _fault_run(exe, None, **kw)
            on_rep = [x for x in r["out"].splitlines() if x.strip().startswith("Nhan:")][:1]
            s.ok(r["rc"] not in (None, 0) and "PHEP THU DAT" not in r["out"] and r["fin"][2] == 0 and r["fin"][3] == 0,
                 "bo tu choi hop le, %s: FAIL, PA8 khong cao" % label,
                 "%s; phan hoi ON %s" % (_brief(r), on_rep))
            r["sim"].close()
        # phan hoi tu choi "hop le" gia (dung seq/checksum) trong khi bo da bat: cong cu tin phan hoi
        r = _fault_run(exe, None, mutate=_first_on("forged_refusal"), interlock="door")
        st0 = r["fin"]
        r["sim"].advance(3000)
        st3 = r["sim"].state()
        s.note("--test-door, phan hoi ON bi thay bang '<seq> ERROR DOOR_OPEN' dung seq/checksum trong khi bo da bat "
               "(khong the sinh ra do nhieu duong truyen): rc %s, OFF/STOP sau ON %s, bo ngay sau %s, sau 3 s %s - "
               "cong cu tin tu choi hop le, chi trong vao LINK_LOST cua firmware" % (r["rc"], r["offs"], st0, st3))
        r["sim"].close()
    s.done()


def p1_r04c(exe):
    s = Sc("P1-R04C", "R03 cho --test-laser-timeout (PT3 cach A): phan hoi LASER ON hong/mat/sai seq/sai noi dung/den muon, Ctrl+C luc doc ON va luc HEARTBEAT -> chu dong tat seq moi truoc han 5 s")
    with _SeqFileSandbox():
        for kind, label in ON_FAULTS + (("late", "phan hoi LASER ON den muon (sau timeout)"),):
            r = _fault_run(exe, ["--test-laser-timeout"], mutate=_first_on(kind))
            s.ok(r["rc"] == 1 and _tool_off(r),
                 "%s (bo da thuc thi ON): FAIL rc 1, gui LASER OFF seq moi, PA8 thap ngay (khong doi LASER_TIMEOUT 5 s)" % label,
                 _brief(r))
            r["sim"].close()
        for cmd, label in (("LASER ON", "Ctrl+C dung luc doc phan hoi LASER ON"), ("HEARTBEAT", "Ctrl+C luc doc HEARTBEAT dau tien")):
            r = _fault_run(exe, ["--test-laser-timeout"], read_raise=(cmd, KeyboardInterrupt()))
            s.ok(r["rc"] == 1 and _tool_off(r), "%s: gui LASER OFF seq moi, PA8 thap, rc 1" % label, _brief(r))
            r["sim"].close()
        r = _fault_run(exe, ["--test-laser-timeout"], door=0)
        s.ok(r["rc"] == 1 and r["fin"][2] == 0 and r["fin"][3] == 0,
             "cua mo tu dau -> bo tu choi 'ERROR DOOR_OPEN': FAIL rc 1, PA8 khong cao", _brief(r))
        r["sim"].close()
    s.done()


MODES = ("p1", "lt", "door", "estop")
MODE_NAME = {"p1": "--p1", "lt": "--test-laser-timeout", "door": "--test-door", "estop": "--test-estop"}
OK_MARK = {"p1": "DEU DAT", "lt": None, "door": "PHEP THU DAT", "estop": "PHEP THU DAT"}


def _run_mode(exe, mode, faults=(), mutate=None, dead_after=None, trip_ms=None, prep=None, restore_ms=None,
              alias=False, door=1, estop=0, vom="y"):
    """Chay main() that cua cong cu o mot che do, cong COM gia co tiem loi, bo gia chay ping_proto.c that."""
    sim = SimSerial(exe, door=door, estop=estop)
    if prep is not None:
        prep(sim)
    f = _Fault(sim, mutate=mutate, dead_after=dead_after, faults=faults)
    try:
        if mode in ("door", "estop"):
            rc, out, _ = interlock_run(sim, mode, trip_ms, vom=vom, ser_obj=f, alias=alias, restore_ms=restore_ms)
        else:
            rc, out = run_main(sim, ["--p1"] if mode == "p1" else ["--test-laser-timeout"], ser_obj=f, vom=vom)
        exc = None
    except BaseException as e:  # noqa: BLE001
        rc, out, exc = None, "", "%s(%s)" % (type(e).__name__, e)
    return {"rc": rc, "out": out, "exc": exc, "fin": sim.state(), "f": f, "sim": sim}


def _ev(r):
    """Phan tich thu tu su kien: lenh thu ghi SAU loi tiem, OFF/STOP truoc dong cong."""
    ev = r["f"].events
    fi = next((i for i, e in enumerate(ev) if e.startswith("FAULT") or e.startswith("MUT")), None)
    after = [(i, _split(e[2:])) for i, e in enumerate(ev) if fi is not None and i > fi and e.startswith("W ")]
    cmds = [(i, sp[0], sp[1]) for i, sp in after if sp]
    off_i = next((i for i, _, c in cmds if c in ("LASER OFF", "STOP")), None)
    close_i = next((i for i, e in enumerate(ev) if e == "CLOSE"), None)
    return {
        "fault_at": fi,
        "off_tried": off_i is not None,
        "off_before_close": off_i is not None and (close_i is None or off_i < close_i),
        "on_after": [s for _, s, c in cmds if c == "LASER ON"],
        "clear_any": [x for x in r["f"].attempts if _split(x) and _split(x)[1] == "CLEAR"],
        "cmds_after": ["%s %s" % (s, c) for _, s, c in cmds][:4],
    }


def _stopped_now(r):
    """PA8 thap NGAY sau xu ly, do lenh cua cong cu (khong phai LINK_LOST/LASER_TIMEOUT cua firmware), 0 vi pham PA8."""
    fin = r["fin"]
    return fin[2] == 0 and fin[1] not in ("LINK_LOST", "LASER_TIMEOUT") and fin[3] == 0


def _no_pass(mode, r):
    mark = OK_MARK[mode]
    return r["rc"] not in (None, 0) and (mark is None or mark not in r["out"])


def _desc(r):
    e = _ev(r)
    keys = ("FAIL", "R03", "R05", "R06", "Ngoai le", "Loi I/O", "Ctrl+C", "DAT", "KET LUAN")
    lines = [x.strip() for x in r["out"].splitlines() if any(k in x for k in keys)]
    return "rc %s, ngoai le %s; sau loi gui %s; OFF truoc dong cong %s; ON sau loi %s; CLEAR %s; OFF seq moi %s; bo %s; %s" % (
        r["rc"], r["exc"], e["cmds_after"], e["off_before_close"], e["on_after"], e["clear_any"],
        _off_fresh(r["f"].sent), r["fin"], lines[:3])


def p1_norm9(exe):
    s = Sc("P1-N9", "Vong 9 binh thuong (01_PLAN Vong 8 muc 4): alias --test-interlock door|estop; day cam lai ngay sau trip (bit ve muc binh thuong, last_err con giu) van DAT theo Q3")
    with _SeqFileSandbox():
        for which in ("door", "estop"):
            r = _run_mode(exe, which, trip_ms=2500, alias=True)
            s.ok(r["rc"] == 0 and "PHEP THU DAT" in r["out"] and r["fin"][2] == 0 and r["fin"][3] == 0,
                 "'--test-interlock %s', trip o 2.5 s, VOM 'y': DAT, rc 0, PA8 thap" % which, _desc(r))
            r["sim"].close()
        for which in ("door", "estop"):
            r = _run_mode(exe, which, trip_ms=2500, restore_ms=300)
            st_line = [x.strip() for x in r["out"].splitlines() if "DA PHAT HIEN" in x]
            s.ok(r["rc"] == 0 and "PHEP THU DAT" in r["out"] and r["fin"][2] == 0 and r["fin"][3] == 0,
                 "--test-%s: day cam lai 0.3 s sau trip, STATUS co bit %s ve muc binh thuong + last_err con giu -> DAT (N3/N8)" % (
                     which, "door=1" if which == "door" else "estop=0"), "%s; %s" % (_desc(r), st_line))
            r["sim"].close()
        # ghi nhan: last_err cu (LASER_TIMEOUT sau PT3, chua CLEAR) con giu khi CAPTURING
        def after_pt3(sim):
            run_main(sim, ["--test-laser-timeout"])
        r = _run_mode(exe, "door", trip_ms=None, prep=after_pt3)
        s.note("--test-door ngay sau PT3 (chua CLEAR), khong doi day: rc %s; dong ket luan %s - bo dang CAPTURING nhung last_err "
               "con LASER_TIMEOUT nen STATUS cuoi bi xep 'error_state' thay vi 'cho trip'; ket qua van FAIL nhu ca khong doi day" % (
                   r["rc"], [x.strip() for x in r["out"].splitlines() if "KET LUAN" in x][:1]))
        r["sim"].close()
        # ghi nhan: PT3 rc 0 khong doi chieu last_err=LASER_TIMEOUT
        def mut_lt(ln, c):
            sp = _split(ln)
            if c == "STATUS" and sp and sp[1].startswith("DONE IDLE ") and "LASER_TIMEOUT" in sp[1]:
                return _frame(sp[0], sp[1].replace("LASER_TIMEOUT", "NONE"))
            return None
        r = _run_mode(exe, "lt", mutate=mut_lt)
        s.note("--test-laser-timeout khi STATUS cuoi la 'DONE IDLE ... NONE 0' (khong phai LASER_TIMEOUT): rc %s - cong cu khong doi "
               "chieu last_err/thoi diem tat; ket luan PT3 van dua vao nguoi van hanh doc VOM va dong STATUS" % r["rc"])
        r["sim"].close()
    s.done()


def p1_r05(exe):
    s = Sc("P1-R05", "R05 (01_PLAN Vong 8 muc 4 'Bien R05'): loi I/O MOT LAN o write (sau/truoc khi byte toi bo), flush, read cua LASER ON; "
           "loi I/O luc giam sat/ON gia han; Ctrl+C - ca 4 che do: cong con dung duoc -> OFF/STOP seq moi truoc dong cong, PA8 thap ngay, FAIL, giu loi goc")
    mon = {"p1": ("HEARTBEAT", 1), "lt": ("HEARTBEAT", 2), "door": ("HEARTBEAT", 1), "estop": ("HEARTBEAT", 1)}
    with _SeqFileSandbox():
        for mode in MODES:
            cases = [("write_after", "LASER ON", 1, "write LASER ON nem loi SAU khi byte da toi bo"),
                     ("flush", "LASER ON", 1, "flush LASER ON loi (byte da toi bo)"),
                     ("read", "LASER ON", 1, "read phan hoi LASER ON loi"),
                     ("read", mon[mode][0], mon[mode][1], "read %s#%d luc giam sat loi" % mon[mode])]
            if mode in ("door", "estop"):
                cases += [("read", "LASER ON", 2, "read phan hoi ON gia han (giay 4) loi"),
                          ("flush", "LASER ON", 2, "flush ON gia han (giay 4) loi")]
            for stage, cmd, nth, label in cases:
                msg = "tiem loi R05 %s %s#%d" % (stage, cmd, nth)
                r = _run_mode(exe, mode, faults=[(stage, cmd, nth, OSError(msg))])
                e = _ev(r)
                s.ok(_no_pass(mode, r) and r["exc"] is None and e["off_before_close"] and _off_fresh(r["f"].sent) and _stopped_now(r)
                     and not e["on_after"] and not e["clear_any"] and msg in r["out"],
                     "%s, %s: FAIL rc!=0, OFF/STOP seq moi truoc dong cong, PA8 thap ngay, khong ON/CLEAR sau loi, in loi goc" % (MODE_NAME[mode], label),
                     _desc(r))
                r["sim"].close()
            # loi truoc khi byte toi bo: bo chua nhan ON
            msg = "tiem loi R05 write_before LASER ON#1"
            r = _run_mode(exe, mode, faults=[("write_before", "LASER ON", 1, OSError(msg))])
            e = _ev(r)
            s.ok(_no_pass(mode, r) and r["exc"] is None and r["fin"][2] == 0 and r["fin"][3] == 0 and not e["on_after"] and msg in r["out"],
                 "%s, write LASER ON loi TRUOC khi byte toi bo: FAIL rc!=0, PA8 khong len, khong gui lai ON, in loi goc" % MODE_NAME[mode],
                 "%s; co thu OFF %s" % (_desc(r), e["off_tried"]))
            r["sim"].close()
            # Ctrl+C
            for stage, cmd, nth, label in (("read", "LASER ON", 1, "Ctrl+C luc doc phan hoi LASER ON"),
                                           ("read", mon[mode][0], mon[mode][1], "Ctrl+C luc giam sat (%s#%d)" % mon[mode])):
                r = _run_mode(exe, mode, faults=[(stage, cmd, nth, KeyboardInterrupt())])
                e = _ev(r)
                s.ok(r["rc"] == 1 and r["exc"] is None and _no_pass(mode, r) and e["off_before_close"] and _off_fresh(r["f"].sent)
                     and _stopped_now(r) and not e["on_after"] and not e["clear_any"],
                     "%s, %s: rc 1, OFF/STOP seq moi truoc dong cong, PA8 thap ngay" % (MODE_NAME[mode], label), _desc(r))
                r["sim"].close()
    s.done()


def p1_r05d(exe):
    s = Sc("P1-R05D", "R05 thiet bi: cong mat han ngay sau khi LASER ON toi bo, ca 4 che do - da CO GANG gui OFF/STOP, canh bao chua xac nhan, FAIL; "
           "rieng MCU tu ha PA8 o LINK_LOST 3 s")
    with _SeqFileSandbox():
        for mode in MODES:
            r = _run_mode(exe, mode, dead_after="LASER ON")
            f = r["f"]
            idx_on = next(i for i, x in enumerate(f.attempts) if _split(x) and _split(x)[1] == "LASER ON")
            tried = [x for x in f.attempts[idx_on + 1:] if _split(x) and _split(x)[1] in ("LASER OFF", "STOP")]
            st0 = r["fin"]
            r["sim"].advance(3000)
            st3 = r["sim"].state()
            s.ok(_no_pass(mode, r) and r["exc"] is None and bool(tried) and "R03 NGUY HIEM" in r["out"] and st3[2] == 0
                 and st3[:2] == ("ERROR", "LINK_LOST") and st3[3] == 0,
                 "%s, cong mat han sau ON: FAIL rc!=0 (khong de ngoai le thoat), da thu gui %s, in 'R03 NGUY HIEM'; MCU ha PA8 sau 3 s (LINK_LOST)" % (
                     MODE_NAME[mode], "/".join(sorted({_split(x)[1] for x in tried})) or "OFF"),
                 "rc %s, ngoai le %s; lenh thu sau ON %s; bo ngay sau %s, sau 3 s %s" % (r["rc"], r["exc"], tried[:2], st0, st3))
            r["sim"].close()
    s.done()


def p1_r05s(exe):
    s = Sc("P1-R05S", "R05 bien seq/cuu ho: seq gan 65535, tep seq cu/khong co; loi sau STATUS long; loi trong chinh OFF/STATUS cuu ho - "
           "OFF khong bi cache nuot, khong treo, canh bao khi chua xac nhan, phan biet bo da tat voi cong cu chua xac nhan (N6)")
    with _SeqFileSandbox():
        for mode in ("door", "lt"):
            for preset, want_on, want_off in ((65534, 65535, 1), (65535, 1, 2), (None, 1, 2)):
                _seq_preset(preset)
                msg = "tiem loi R05S read LASER ON#1"
                r = _run_mode(exe, mode, faults=[("read", "LASER ON", 1, OSError(msg))])
                ons = [int(_split(x)[0]) for x in r["f"].sent if _split(x) and _split(x)[1] == "LASER ON"]
                offs = _sent_off_after_on(r["f"].sent)
                s.ok(_no_pass(mode, r) and ons[:1] == [want_on] and offs[:1] == [want_off] and _stopped_now(r),
                     "%s, tep seq %s: ON seq %d, loi doc -> OFF seq %d (qua 65535->1) duoc bo thuc thi, PA8 thap" % (
                         MODE_NAME[mode], preset, want_on, want_off), "ON %s, OFF %s; %s" % (ons, offs, _desc(r)))
                r["sim"].close()
        # tep seq cu: bo vua nhan seq 5 tu mot tien trinh khac, tep seq cong cu con 3
        def prep_stale(sim):
            run_cmd(sim, "5 STATUS")
            _seq_preset(3)
        r = _run_mode(exe, "door", faults=[("read", "LASER ON", 1, OSError("tiem loi R05S tep seq cu"))], prep=prep_stale)
        s.ok(_no_pass("door", r) and _off_fresh(r["f"].sent) and _stopped_now(r),
             "--test-door, tep seq cu (3) trong khi bo da nhan seq 5: ON/OFF van duoc thuc thi, PA8 thap ngay", _desc(r))
        r["sim"].close()
        _seq_preset(None)
        # loi I/O khi doc STATUS long (sau HEARTBEAT bao ERROR)
        for which in ("door", "estop"):
            msg = "tiem loi R05S read STATUS long"
            r = _run_mode(exe, which, trip_ms=2500, faults=[("read", "STATUS", 1, OSError(msg))])
            e = _ev(r)
            s.ok(_no_pass(which, r) and r["exc"] is None and e["off_before_close"] and r["fin"][2] == 0 and r["fin"][3] == 0
                 and not e["on_after"] and not e["clear_any"] and msg in r["out"],
                 "--test-%s, loi doc STATUS long sau trip: FAIL, khong DAT, van gui OFF truoc dong cong, khong ON/CLEAR, giu loi goc" % which,
                 _desc(r))
            r["sim"].close()
        # loi trong chinh lenh cuu ho
        for stage, cmd, label, want_board_off in (
                ("write_before", "LASER OFF", "OFF cuu ho khong toi duoc bo (ghi loi truoc khi byte toi)", False),
                ("read", "LASER OFF", "doc phan hoi OFF cuu ho loi (OFF da toi bo)", True),
                ("read", "STATUS", "doc STATUS xac nhan cuu ho loi (OFF da toi bo)", True)):
            msg0 = "tiem loi R05S goc read LASER ON#1"
            r = _run_mode(exe, "door", faults=[("read", "LASER ON", 1, OSError(msg0)), (stage, cmd, 1, OSError("tiem loi trong cuu ho"))])
            st0 = r["fin"]
            r["sim"].advance(3000)
            st3 = r["sim"].state()
            board_off_now = st0[2] == 0
            s.ok(_no_pass("door", r) and r["exc"] is None and msg0 in r["out"] and "R03 NGUY HIEM" in r["out"]
                 and board_off_now == want_board_off and st3[2] == 0,
                 "--test-door, %s: khong treo, FAIL, giu loi goc, in 'R03 NGUY HIEM' (chua xac nhan); bo %s; MCU ha PA8 trong 3 s" % (
                     label, "da tat that" if want_board_off else "con bat toi LINK_LOST"),
                 "%s; bo ngay sau %s, sau 3 s %s" % (_desc(r), st0, st3))
            r["sim"].close()
    s.done()


def _once(cmd, nth, fn):
    st = {"n": 0}

    def m(ln, c):
        if c != cmd:
            return None
        st["n"] += 1
        return fn(ln) if st["n"] == nth else None
    return m


def _once_status_after_trip(kind):
    st = {"done": False}
    base = _mut_status_after_trip(kind) if kind not in ("err_linklost", "err_other_door", "err_other_estop", "rem1") else None

    def m(ln, c):
        if st["done"] or c != "STATUS":
            return None
        sp = _split(ln)
        if not sp or not sp[1].startswith("DONE ERROR "):
            return None
        st["done"] = True
        seq, body = sp
        tok = body.split(" ")
        if kind == "err_linklost":
            tok[8] = "LINK_LOST"
        elif kind == "err_other_door":
            tok[8] = "ESTOP"
        elif kind == "err_other_estop":
            tok[8] = "DOOR_OPEN"
        elif kind == "rem1":
            tok[9] = "1"
        else:
            return base(ln, c)
        return _frame(seq, " ".join(tok))
    return m


def _flip(ln):
    return ln[:-1] + ("0" if ln[-1] != "0" else "1")


def p1_r06(exe):
    s = Sc("P1-R06", "R06 (01_PLAN Vong 8 muc 4 'Dau vao R06'): cua va estop - hong/mat DUNG MOT HEARTBEAT, ON gia han hoac STATUS sau trip roi moi phan hoi sau dung, "
           "VOM 'y' -> giu FAIL, rc!=0, khong 'PHEP THU DAT', khong ON gia han/CLEAR sau loi, co gang dung; gom 4 ca bang R06 Reviewer")
    one = {
        "missing": lambda ln: "",
        "wrong_seq": lambda ln: _frame(int(_split(ln)[0]) + 100, _split(ln)[1]),
        "bad_chk": _flip,
        "garbage": lambda ln: ln.split("*")[0] + " rac",
        "body_idle": lambda ln: _frame(_split(ln)[0], "DONE IDLE"),
    }
    with _SeqFileSandbox():
        for which in ("door", "estop"):
            cases = []
            for k in ("missing", "wrong_seq", "bad_chk", "garbage", "body_idle"):
                cases.append(("HEARTBEAT dau: %s" % k, _once("HEARTBEAT", 1, one[k]), 2500, True))
            for k in ("missing", "wrong_seq", "bad_chk"):
                cases.append(("ON gia han (giay 4): %s" % k, _once("LASER ON", 2, one[k]), 5500, True))
            for k in ("err_linklost", "err_other_%s" % which, "rem1", "laser1", "wrong_state", "missing_tok", "bad_chk", "bad_seq"):
                cases.append(("STATUS dau sau trip: %s" % k, _once_status_after_trip(k), 2500, False))
            for label, mut, trip, laser_maybe_on in cases:
                r = _run_mode(exe, which, trip_ms=trip, mutate=mut)
                e = _ev(r)
                ok = (_no_pass(which, r) and r["exc"] is None and e["fault_at"] is not None and not e["on_after"] and not e["clear_any"]
                      and e["off_before_close"] and r["fin"][2] == 0 and r["fin"][3] == 0)
                if laser_maybe_on:
                    ok = ok and _stopped_now(r)
                s.ok(ok, "--test-%s, %s; sau do moi phan hoi dung, VOM 'y': FAIL, khong DAT, khong ON/CLEAR sau loi, OFF truoc dong cong%s" % (
                    which, label, ", PA8 thap ngay" if laser_maybe_on else ""), _desc(r))
                r["sim"].close()
    s.done()


def _set_body(body):
    """Thay noi dung phan hoi, GIU seq va tinh lai checksum dung (loi noi dung, khong phai loi khung)."""
    return lambda ln: _frame(_split(ln)[0], body)


def _suffix(extra):
    return lambda ln: _frame(_split(ln)[0], _split(ln)[1] + extra)


def p1_r07(exe):
    s = Sc("P1-R07", "R07 (04_REVIEW Vong 4; 01_PLAN Vong 8 muc 3.3-3.4): phan hoi DUNG seq/checksum nhung SAI noi dung Q3 o HEARTBEAT, ON dau, ON gia han "
           "(cua, estop) va PT3 -> FAIL rc!=0, khong DAT, dung truoc dong cong, khong ON/CLEAR sau loi; gom 8 ca bang R07 Reviewer")
    with _SeqFileSandbox():
        for which in ("door", "estop"):
            code = "DOOR_OPEN" if which == "door" else "ESTOP"
            cases = [
                ("HEARTBEAT luc trip -> 'garbage ERROR'", _once("HEARTBEAT", 3, _set_body("garbage ERROR")), 2500, False),
                ("HEARTBEAT luc trip -> 'DONE ERROR EXTRA'", _once("HEARTBEAT", 3, _set_body("DONE ERROR EXTRA")), 2500, False),
                ("ON gia han -> 'DONE ON'", _once("LASER ON", 2, _set_body("DONE ON")), 5500, True),
                ("ON gia han -> 'DONE ON -1'", _once("LASER ON", 2, _set_body("DONE ON -1")), 5500, True),
                ("ON gia han -> 'DONE ON 5001'", _once("LASER ON", 2, _set_body("DONE ON 5001")), 5500, True),
                ("ON gia han -> 'DONE ON 5000 X'", _once("LASER ON", 2, _set_body("DONE ON 5000 X")), 5500, True),
                ("ON gia han -> 'DONE ON abc'", _once("LASER ON", 2, _set_body("DONE ON abc")), 5500, True),
                ("HEARTBEAT chua trip -> 'ERROR %s'" % code, _once("HEARTBEAT", 1, _set_body("ERROR " + code)), 2500, True),
                ("HEARTBEAT chua trip -> 'ERROR BADCHK'", _once("HEARTBEAT", 1, _set_body("ERROR BADCHK")), 2500, True),
                ("HEARTBEAT -> 'DONE FOO'", _once("HEARTBEAT", 1, _set_body("DONE FOO")), 2500, True),
                ("HEARTBEAT -> 'DONE CAPTURING X'", _once("HEARTBEAT", 1, _suffix(" X")), 2500, True),
            ]
            for label, mut, trip, laser_maybe_on in cases:
                r = _run_mode(exe, which, trip_ms=trip, mutate=mut)
                e = _ev(r)
                ok = (_no_pass(which, r) and r["exc"] is None and e["fault_at"] is not None and not e["on_after"] and not e["clear_any"]
                      and e["off_before_close"] and r["fin"][2] == 0 and r["fin"][3] == 0)
                if laser_maybe_on:
                    ok = ok and _stopped_now(r)
                s.ok(ok, "--test-%s, %s (dung seq/checksum), sau do moi phan hoi dung, VOM 'y': FAIL, khong DAT, OFF truoc dong cong%s" % (
                    which, label, ", PA8 thap ngay" if laser_maybe_on else ""), _desc(r))
                r["sim"].close()
        # ON dau tien sai noi dung (bo da thuc thi ON); cua/estop co trip o 2.5 s de ban 'bo qua roi DAT' lo ra
        for mode in ("door", "estop", "lt"):
            for body in ("DONE ON", "DONE ON -1", "DONE ON 5001", "DONE ON 5000 X", "ERROR FOO", "ERROR BUSY"):
                r = _run_mode(exe, mode, mutate=_once("LASER ON", 1, _set_body(body)), trip_ms=2500 if mode != "lt" else None)
                e = _ev(r)
                first = e["cmds_after"][0].split(" ", 1)[1] if e["cmds_after"] else None
                s.ok(_no_pass(mode, r) and r["exc"] is None and first in ("LASER OFF", "STOP") and e["off_before_close"]
                     and _off_fresh(r["f"].sent) and _stopped_now(r),
                     "%s, phan hoi LASER ON dau la '%s' (dung seq/checksum, bo da bat): FAIL, lenh KE TIEP la OFF seq moi (khong giam sat tiep), PA8 thap ngay" % (
                         MODE_NAME[mode], body), _desc(r))
                r["sim"].close()
        # PT3: HEARTBEAT giua chung sai noi dung
        for label, fn in (("'DONE CAPTURING X'", _suffix(" X")), ("'garbage ERROR'", _set_body("garbage ERROR")),
                          ("'DONE FOO'", _set_body("DONE FOO")), ("'ERROR DOOR_OPEN'", _set_body("ERROR DOOR_OPEN"))):
            r = _run_mode(exe, "lt", mutate=_once("HEARTBEAT", 2, fn))
            e = _ev(r)
            s.ok(_no_pass("lt", r) and r["exc"] is None and e["off_before_close"] and _stopped_now(r) and not e["on_after"],
                 "--test-laser-timeout, HEARTBEAT#2 la %s (dung seq/checksum): FAIL rc 1, OFF truoc dong cong, PA8 thap ngay" % label, _desc(r))
            r["sim"].close()
        # ghi nhan
        r = _run_mode(exe, "door", trip_ms=2500, mutate=_once("HEARTBEAT", 3, _set_body("ERROR DOOR_OPEN")))
        s.note("--test-door, HEARTBEAT luc bo DA trip bi thay bang 'ERROR DOOR_OPEN' (ma Q3 hop le nhung Q3 muc 2 cho HEARTBEAT tra 'DONE <state>'): rc %s, DAT %s - "
               "cong cu coi la goi y roi quyet bang STATUS hop le (04_REVIEW Vong 4 R07 cho phep 'phan hoi ERROR co ma Q3 hop le' dan toi hoi STATUS)" % (
                   r["rc"], "PHEP THU DAT" in r["out"]))
        r["sim"].close()
        r = _run_mode(exe, "door", trip_ms=2500, mutate=_once("LASER ON", 1, _set_body("DONE ON 0")))
        s.note("--test-door, phan hoi ON dau 'DONE ON 0' (bo da bat, han con 5000 ms): rc %s, DAT %s - parse_laser_on_reply nhan mien 0..5000; "
               "firmware C4 luon tra 'DONE ON 5000'" % (r["rc"], "PHEP THU DAT" in r["out"]))
        r["sim"].close()
    s.done()


def p1_r07p(exe):
    s = Sc("P1-R07P", "--p1 (01_PLAN Vong 7 muc 4 T3: phan hoi sau ON 'sai dinh dang/noi dung' -> --p1 FAIL va gui OFF/STOP seq moi): "
           "phan hoi DUNG seq/checksum nhung thua duoi/sai so - cung loai R07")
    with _SeqFileSandbox():
        for cmd, nth, label, fn, laser_maybe_on in (
                ("LASER ON", 1, "buoc 2 ON -> 'DONE ON 5000 X'", _suffix(" X"), True),
                ("LASER ON", 1, "buoc 2 ON -> 'DONE ON 50000'", _set_body("DONE ON 50000"), True),
                ("HEARTBEAT", 1, "buoc 4 HEARTBEAT -> 'DONE CAPTURING X'", _suffix(" X"), True),
                ("LASER OFF", 1, "buoc 6 OFF -> 'DONE OFF 0 X'", _suffix(" X"), True),
                ("STOP", 1, "buoc 8 STOP -> 'DONE PAUSED X'", _suffix(" X"), False),
                ("HOME", 1, "buoc 10 HOME -> 'ERROR NOTIMPLX'", _set_body("ERROR NOTIMPLX"), False),
                # Vong 11: them
                ("LASER ON", 1, "buoc 2 ON -> 'DONE ON 4999' (dung cu phap, sai gia tri)", _set_body("DONE ON 4999"), True),
                ("LASER OFF", 2, "buoc 6 OFF gui lap (seq 6) -> 'DONE OFF 0 X'", _suffix(" X"), True),
                ("CLEAR", 1, "buoc 9 CLEAR -> 'DONE IDLE X'", _suffix(" X"), False),
                ("MOVE_ABS 10", 1, "buoc 11 MOVE_ABS -> 'ERROR NOTIMPL X'", _suffix(" X"), False)):
            r = _run_mode(exe, "p1", mutate=_once(cmd, nth, fn))
            e = _ev(r)
            ok = _no_pass("p1", r) and r["exc"] is None
            if laser_maybe_on:
                ok = ok and e["off_before_close"] and _stopped_now(r)
            s.ok(ok, "--p1, %s (dung seq/checksum): FAIL rc!=0, khong 'DEU DAT'%s" % (
                label, ", OFF truoc dong cong, PA8 thap ngay" if laser_maybe_on else ""), _desc(r))
            r["sim"].close()
    s.done()


def _status_tok(idx, val):
    """Doi token thu idx cua body STATUS (8 = last_err, 9 = remaining_ms), giu seq, tinh lai checksum dung."""
    def f(ln):
        seq, body = _split(ln)
        tok = body.split(" ")
        tok[idx] = val
        return _frame(seq, " ".join(tok))
    return f


def p1_r09(exe):
    s = Sc("P1-R09", "R09 (04_REVIEW Vong 5): STATUS dung seq/checksum/10 token nhung SAI MIEN (remaining_ms > 5000, last_err khong thuoc Q3 muc 3) -> FAIL, "
           "dung truoc dong cong neu da ON; bien hop le (5000, LASER_TIMEOUT, WDG_RESET) van DAT; gom 3 ca bang R09 Reviewer")
    with _SeqFileSandbox():
        # --p1: STATUS thu n (1 = seq 1 truoc ON, 2 = seq 3, 3 = seq 5, 4 = seq 7 sau OFF)
        for n, label, fn, after_on in (
                (2, "seq 3 remaining_ms 5001", _status_tok(9, "5001"), True),
                (2, "seq 3 remaining_ms 999999", _status_tok(9, "999999"), True),
                (2, "seq 3 last_err NO_SUCH_ERROR", _status_tok(8, "NO_SUCH_ERROR"), True),
                (3, "seq 5 remaining_ms 5001", _status_tok(9, "5001"), True),
                (3, "seq 5 last_err 'none' (chu thuong)", _status_tok(8, "none"), True),
                (4, "seq 7 (sau OFF) last_err BOGUS", _status_tok(8, "BOGUS"), True),
                (1, "seq 1 (truoc ON) last_err BOGUS", _status_tok(8, "BOGUS"), False)):
            r = _run_mode(exe, "p1", mutate=_once("STATUS", n, fn))
            e = _ev(r)
            first = e["cmds_after"][0].split(" ", 1)[1] if e["cmds_after"] else None
            ok = _no_pass("p1", r) and r["exc"] is None and r["fin"][2] == 0 and r["fin"][3] == 0
            if after_on:
                ok = ok and first in ("LASER OFF", "STOP") and e["off_before_close"] and _stopped_now(r)
            else:
                ok = ok and not [x for x in r["f"].attempts if _split(x) and _split(x)[1] == "LASER ON"]
            s.ok(ok, "--p1, STATUS %s (dung seq/checksum): FAIL rc!=0, khong 'DEU DAT'%s" % (
                label, ", lenh ke tiep la OFF seq moi, PA8 thap ngay" if after_on else ", khong gui LASER ON"), _desc(r))
            r["sim"].close()
        # bien hop le: khong duoc tu choi sai
        for n, label, fn in ((2, "seq 3 remaining_ms 5000", _status_tok(9, "5000")),
                             (1, "seq 1 last_err LASER_TIMEOUT", _status_tok(8, "LASER_TIMEOUT")),
                             (1, "seq 1 last_err WDG_RESET", _status_tok(8, "WDG_RESET"))):
            r = _run_mode(exe, "p1", mutate=_once("STATUS", n, fn))
            s.ok(r["rc"] == 0 and "DEU DAT" in r["out"] and r["fin"][2] == 0,
                 "--p1, STATUS %s (gia tri hop le theo Q3): van DAT, rc 0" % label, _desc(r))
            r["sim"].close()
        r = _run_mode(exe, "p1", prep=lambda sim: run_main(sim, ["--test-laser-timeout"]))
        s.ok(r["rc"] == 0 and "DEU DAT" in r["out"] and "LASER_TIMEOUT" in r["out"],
             "--p1 ngay sau PT3 (firmware that giu last_err LASER_TIMEOUT, nhu D1 lan 1 tren bo Vong 11): van DAT, rc 0", _desc(r))
        r["sim"].close()
        # PT3: STATUS cuoi sai mien
        for label, fn in (("last_err BOGUS", _status_tok(8, "BOGUS")), ("remaining_ms 5001", _status_tok(9, "5001"))):
            r = _run_mode(exe, "lt", mutate=_once("STATUS", 1, fn))
            s.ok(_no_pass("lt", r) and r["exc"] is None and r["fin"][2] == 0 and r["fin"][3] == 0,
                 "--test-laser-timeout, STATUS cuoi %s (dung seq/checksum): FAIL rc 1" % label, _desc(r))
            r["sim"].close()
        # cua/estop: STATUS dau sau trip sai mien
        for which in ("door", "estop"):
            for label, fn in (("last_err NO_SUCH_ERROR", _status_tok(8, "NO_SUCH_ERROR")), ("remaining_ms 5001", _status_tok(9, "5001"))):
                r = _run_mode(exe, which, trip_ms=2500, mutate=_once_status_after_trip_fn(fn))
                e = _ev(r)
                s.ok(_no_pass(which, r) and r["exc"] is None and e["off_before_close"] and not e["on_after"] and not e["clear_any"]
                     and r["fin"][2] == 0 and r["fin"][3] == 0,
                     "--test-%s, STATUS dau sau trip %s, sau do moi phan hoi dung, VOM 'y': FAIL, khong DAT" % (which, label), _desc(r))
                r["sim"].close()
        # ghi nhan: STATUS xac nhan cuu ho sai mien
        r = _run_mode(exe, "door", faults=[("read", "LASER ON", 1, OSError("tiem loi R09 ghi nhan"))],
                      mutate=_once("STATUS", 1, _status_tok(8, "BOGUS")))
        s.note("--test-door, cuu ho sau loi doc ON ma STATUS xac nhan co last_err la: rc %s, canh bao %s, bo %s - parser chat lam cuu ho "
               "khong xac nhan duoc (huong an toan, nhu N6)" % (
                   r["rc"], "R03 NGUY HIEM" if "R03 NGUY HIEM" in r["out"] else ("R03 AN TOAN" if "R03 AN TOAN" in r["out"] else "?"), r["fin"]))
        r["sim"].close()
    s.done()


def _once_status_after_trip_fn(fn):
    st = {"done": False}

    def m(ln, c):
        if st["done"] or c != "STATUS":
            return None
        sp = _split(ln)
        if not sp or not sp[1].startswith("DONE ERROR "):
            return None
        st["done"] = True
        return fn(ln)
    return m


def legacy_e2e(exe):
    s = Sc("PING-E2E", "hoi quy: run_session 10 PING ke thua noi voi ping_proto.c that (quy trinh muc 3 C1)")
    ser = SimSerial(exe, door=1, estop=0)
    res, pairs = npg.run_session(ser, 10, 0.2, 0, log_print=lambda *a: None)
    ser.close()
    s.ok(res.get("id_line") == "ID NUCLEO-F446RE NucleoPing 0.2.0 hosttest", "ID? mang phien ban C4 0.2.0", res.get("id_line"))
    good = [p for p in pairs if p.get("ok") in (1, True, "1")]
    s.ok(len(pairs) == 10 and len(good) == 10, "10/10 PONG dung", "%d cap, %d dung" % (len(pairs), len(good)))
    s.done()


def selftest():
    s = Sc("SELF", "selftest cong cu: nucleo_ping.py --selftest")
    seqf = Path(REAL_TMPDIR) / "scanner3d_p1_seq.txt"

    def seq_state():
        return (seqf.read_bytes(), seqf.stat().st_mtime_ns) if seqf.exists() else None
    before = seq_state()
    r = subprocess.run([PY, str(REPO / "pc" / "nucleo_ping.py"), "--selftest"], cwd=REPO, capture_output=True, text=True,
                       errors="replace")
    after = seq_state()
    s.ok(r.returncode == 0 and "SELFTEST PASS" in r.stdout, "--selftest rc 0, SELFTEST PASS", "rc %s; %s" % (r.returncode, r.stdout.strip()[-60:]))
    s.ok(before == after, "--selftest khong doi tep seq that %TEMP%/scanner3d_p1_seq.txt (noi dung va thoi diem ghi)",
         "truoc %s | sau %s" % (before[0] if before else None, after[0] if after else None))
    s.note("FakeNucleo cua selftest khong co bo nho chong lap seq (Q3 1.1) nen khong bat duoc buoc 'duplicate seq 6' cua run_p1_session")
    s.done()


def abort_note(exe):
    s = Sc("P1-N", "ghi nhan: run_p1_session dung giua chung sau LASER ON thi co gui LASER OFF/STOP khong", note_only=True)
    ser = SimSerial(exe, door=1, estop=0)
    orig = npg.parse_p1_reply

    def broken(line):
        r = orig(line)
        if r and r[1].startswith("DONE CAPTURING"):
            return r[0], "DONE KHAC", r[2]   # gia lap mot phan hoi khong khop o buoc 3 (sau LASER ON)
        return r
    npg.parse_p1_reply = broken
    try:
        with _SeqFileSandbox():   # Vong 6: R03 cua cong cu ghi tep seq - khong de cham tep that cua may
            ok, err = npg.run_p1_session(ser, timeout=0.2, log_print=lambda *a: None)
    finally:
        npg.parse_p1_reply = orig
    st = ser.state()
    sent = [b.decode("ascii", "replace").strip() for b in ser.sent]
    ser.close()
    s.note("dung o buoc 3: ok=%s; lenh cuoi cong cu gui %r; trang thai bo %s (PA8=%d, chi ha khi het 3 s/5 s cua firmware)"
           % (ok, sent[-1] if sent else None, st, st[2]))
    s.done()


def main():
    print("Tester C4 - pc/nucleo_ping.py P1; thu muc tam:", TMP)
    # Vong 6: moi ham cua cong cu chay trong tien trinh nay ghi tep seq vao thu muc tam rieng, khong cham tep that
    (TMP / "seq_global").mkdir()
    tempfile.tempdir = str(TMP / "seq_global")
    t0 = time.time()
    exe, log = build_sim()
    sc = Sc("BUILD", "build bo gia tu ping_proto.c that (MinGW gcc)")
    sc.ok(exe is not None, "gcc build tester_c4_sim.exe", log[-200:] if log else "rc 0, khong canh bao")
    sc.done()
    fns = [p1_unit, selftest]
    if exe is not None:
        fns += [lambda: p1_e2e(exe), lambda: p1_bare(exe), lambda: legacy_e2e(exe), lambda: abort_note(exe),
                lambda: p1_proc(exe), lambda: p1_auto(exe), lambda: p1_interlock(exe),
                lambda: p1_r03(exe), lambda: p1_seq(exe), lambda: p1_r04(exe), lambda: p1_r04b(exe), lambda: p1_r04c(exe), lambda: p1_norm9(exe), lambda: p1_r05(exe), lambda: p1_r05d(exe),
                lambda: p1_r05s(exe), lambda: p1_r06(exe), lambda: p1_r07(exe), lambda: p1_r07p(exe), lambda: p1_r09(exe), lambda: p1_mix(exe), lambda: p1_encoding(exe)]
    for f in fns:
        try:
            f()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            SUMMARY.append((getattr(f, "__name__", "?").upper(), "FAIL", "ngoai le trong kich ban: %r" % e))
    print("\nMa        KQ    Kich ban")
    for sid, st, title in SUMMARY:
        print("%-9s %-5s %s" % (sid, st, title))
    nf = sum(1 for x in SUMMARY if x[1] == "FAIL")
    print("\nTONG: %d PASS, %d FAIL, %d NOTE, %d kich ban, %.0f s" % (
        sum(1 for x in SUMMARY if x[1] == "PASS"), nf, sum(1 for x in SUMMARY if x[1] == "NOTE"), len(SUMMARY), time.time() - t0))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
