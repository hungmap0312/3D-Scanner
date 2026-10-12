"""
nucleo_ping.py - Kiem tra giao tiep PC <-> Nucleo-F446RE qua COM ao ST-LINK.

Phuc vu chi tieu B "Giao tiep Nucleo" tuan 1 cua roadmap:
  100 yeu cau PING co 100 phan hoi dung thu tu; nap va chay lai duoc sau
  khi rut cam nguon.

Firmware doi dien: firmware/stm32/NucleoPing (giao thuc trong
Core/Inc/ping_proto.h). Moi lenh mot dong ASCII ket thuc LF:
  PING <n>  ->  PONG <n> <uptime_ms>
  ID?       ->  ID NUCLEO-F446RE NucleoPing <FW_VERSION> <git>

Script gui ID? mot lan, roi gui PING 1..N tuan tu; moi PING cho dung mot
dong tra loi trong --timeout giay. Phien PASS chi khi N/N dong tra loi la
PONG voi cung so thu tu, khong sai, khong timeout. Sai o dau dung o do,
khong gui lai ngam. uptime_ms trong PONG duoc ghi lai: sau khi rut cam
nguon va chay lan hai, gia tri nay phai nho lai; do la bang chung bo da
chay lai chu khong phai van chay tu lan truoc.

Moi lan chay la mot phien co ID rieng (ping_YYYYMMDD_HHMMSS), khong ghi de.
Ho so ghi thang vao docs/logs/<id>/ vi khong co anh, chi vai KB:
  session.json  - commit repo, cong, tham so, dong ID?, ket qua
  pairs.csv     - tung cap: seq, gui luc, nhan luc, tre ms, dong tra loi, uptime
  summary.txt   - khoi tong ket de gui lai

Ho so duoc tao TRUOC khi mo cong va pairs.csv ghi dan tung cap (sua 20/09,
review R06): rut cap, loi I/O hay Ctrl+C giua phien thi cac PONG da nhan
van con tren dia, session.json ghi FAIL kem diem mat lien lac. Loi mo cong
(rc 3) va mat ket noi sau khi da bat dau (rc 1) duoc ghi rieng.

Khong suy cong COM tu S3 (COM9). Cong cua Nucleo phai lay tu buoc nhan
dien trong STATUS.md.

Ma nguon co y KHONG chua dau gach cheo nguoc nao.
"""

import argparse
import csv
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from capture_session import git_info, now_iso

REPO_ROOT = Path(__file__).resolve().parent.parent
LF = chr(10)
CR = chr(13)

_cmd_auto_seq = 0


def record_p1_seq(seq):
    """Ghi nhan seq vua dung (du tu sinh hay do nguoi dung chi dinh) vao bien module va tep tam."""
    global _cmd_auto_seq
    _cmd_auto_seq = seq
    try:
        (Path(tempfile.gettempdir()) / "scanner3d_p1_seq.txt").write_text(str(seq))
    except Exception:
        pass


def get_next_p1_seq():
    """Lay sequence number tiep theo cho lenh P1 (1..65535), tranh trung lap giua cac lenh."""
    global _cmd_auto_seq
    seq = _cmd_auto_seq
    seq_file = Path(tempfile.gettempdir()) / "scanner3d_p1_seq.txt"
    if seq_file.exists():
        try:
            seq_val = int(seq_file.read_text().strip())
            if seq_val > seq:
                seq = seq_val
        except Exception:
            pass
    seq = (seq % 65535) + 1
    record_p1_seq(seq)
    return seq


def open_serial(port, baud, timeout):
    import serial
    ser = serial.Serial(port=port, baudrate=baud, bytesize=8, parity="N",
                        stopbits=1, timeout=timeout, write_timeout=timeout)
    return ser


def read_line(ser, timeout):
    """Doc mot dong ket thuc LF, bo CR. Tra ve chuoi hoac None neu het gio.

    KHONG gan ser.timeout trong ham nay. Tren Windows moi lan gan timeout
    pyserial goi SetCommState, va driver VCP cua ST-LINK xoa bo dem nhan
    khi dang co byte toi: ban dau tien (16/09) gan timeout sau moi byte
    nen chuoi ID ve thanh 'ID NUCLEO-F4P3eccab9', PING 1 mat LF roi timeout.
    ser.timeout duoc run_session dat MOT LAN o dau phien, luc cong ranh;
    read_until tu tinh het gio theo gia tri do. Tham so timeout chi de
    ghi loi, khong dung de cau hinh cong."""
    del timeout
    data = ser.read_until(LF.encode())
    if not data.endswith(LF.encode()):
        return None
    return data.decode("ascii", errors="replace").replace(CR, "").replace(LF, "")


def send_line(ser, text):
    ser.write((text + LF).encode("ascii"))
    ser.flush()


def drain(ser, seconds):
    """Doc bo moi dong dang cho (vi du dong BOOT). Moi lan doc cho toi
    ser.timeout; dung khi het dong hoac qua `seconds` giay."""
    got = []
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        line = read_line(ser, None)
        if line is None:
            break
        got.append(line)
    return got


def parse_pong(line):
    """'PONG 7 12345' -> (7, 12345); sai dinh dang -> None."""
    parts = line.split(" ")
    if len(parts) != 3 or parts[0] != "PONG":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def calc_p1_checksum(body):
    """Tinh XOR checksum hai ky tu hex viet hoa cua chuoi body."""
    chk = 0
    for b in body.encode("ascii"):
        chk ^= b
    return "%02X" % chk


def format_p1_cmd(seq, cmd_str):
    """Tao khung lenh P1: <seq> <CMD> [args...]*<HH>"""
    body = "%d %s" % (seq, cmd_str)
    return "%s*%s" % (body, calc_p1_checksum(body))


def parse_p1_reply(line):
    """Phan tich phan hoi P1: <seq> <BODY>*<HH>
    Tra ve (seq, body, ok_checksum) hoac None neu sai dinh dang.
    """
    if not line or "*" not in line:
        return None
    p_star = line.rfind("*")
    body = line[:p_star]
    chk_hex = line[p_star + 1:]
    if len(chk_hex) != 2:
        return None
    try:
        expected = calc_p1_checksum(body)
        ok_chk = (expected.upper() == chk_hex.upper())
    except Exception:
        return None
    parts = body.split(" ", 1)
    try:
        seq = int(parts[0])
    except ValueError:
        return None
    resp_body = parts[1] if len(parts) > 1 else ""
    return seq, resp_body, ok_chk


STATUS_VALID_STATES = {
    "IDLE", "HOMING", "MOVING", "SETTLING", "CAPTURING", "PAUSED", "COMPLETED", "ERROR"
}

VALID_ERROR_CODES = {
    "TOOLONG", "BADFRAME", "BADCHK", "UNKNOWN", "BADARG", "NOTIMPL", "OVERRUN",
    "BUSY", "NOT_HOMED", "RANGE", "LASER_ON", "IN_ERROR", "DOOR_OPEN", "ESTOP",
    "HOME_TIMEOUT", "HOME_STEPS", "LINK_LOST", "LASER_TIMEOUT", "WDG_RESET",
}

VALID_LAST_ERR_CODES = {"NONE"} | VALID_ERROR_CODES


def parse_status_tokens(body):
    """Phan tich body phan hoi STATUS (khong kem seq va checksum).
    Theo Q3 / D039 gom dung 10 token phan tach bang dau cach:
      DONE <state> <step_count> <laser> <door> <estop> <homed> <uptime_ms> <last_err> <remaining_ms>
    Tra ve dict neu hop le hoac None neu sai dinh dang/sai mien gia tri.
    R09: remaining_ms bat buoc trong mien 0..5000; last_err bat buoc thuoc VALID_LAST_ERR_CODES (NONE hoac ma Q3).
    """
    if not body:
        return None
    parts = body.strip().split(" ")
    if len(parts) != 10:
        return None
    if parts[0] != "DONE":
        return None
    state = parts[1]
    if state not in STATUS_VALID_STATES:
        return None
    try:
        step_count = int(parts[2])
        laser = int(parts[3])
        door = int(parts[4])
        estop = int(parts[5])
        homed = int(parts[6])
        uptime_ms = int(parts[7])
        last_err = parts[8]
        remaining_ms = int(parts[9])
    except ValueError:
        return None

    if step_count < 0 or uptime_ms < 0 or not (0 <= remaining_ms <= 5000):
        return None
    if laser not in (0, 1) or door not in (0, 1) or estop not in (0, 1) or homed not in (0, 1):
        return None
    if last_err not in VALID_LAST_ERR_CODES:
        return None

    return {
        "state": state,
        "step_count": step_count,
        "laser": laser,
        "door": door,
        "estop": estop,
        "homed": homed,
        "uptime_ms": uptime_ms,
        "last_err": last_err,
        "remaining_ms": remaining_ms,
    }


def parse_laser_on_reply(body):
    """Phan tich phan hoi cua lenh LASER ON theo Q3 / D039.
    Tra ve (status, detail) trong do:
    - 'ok': dung schema 'DONE ON <remaining_ms>' voi remaining_ms la so tu 0 den 5000. Detail la int(remaining_ms).
    - 'refused': dung schema 'ERROR <err_code>' voi err_code thuoc VALID_ERROR_CODES. Detail la err_code.
    - 'invalid': bat ky phan hoi nao khac (thieu/thua token, remaining_ms am hoac khong phai so, loi la...). Detail la body.
    """
    if not body:
        return "invalid", ""
    toks = body.strip().split(" ")
    if len(toks) == 3 and toks[0] == "DONE" and toks[1] == "ON":
        if toks[2].isdigit() and 0 <= int(toks[2]) <= 5000:
            return "ok", int(toks[2])
        return "invalid", body
    if len(toks) == 2 and toks[0] == "ERROR" and toks[1] in VALID_ERROR_CODES:
        return "refused", toks[1]
    return "invalid", body


def parse_heartbeat_reply(body):
    """Phan tich phan hoi cua lenh HEARTBEAT theo Q3.
    Tra ve (status, detail) trong do:
    - 'done': dung schema 'DONE <state>' voi state thuoc STATUS_VALID_STATES. Detail la state.
    - 'error': dung schema 'ERROR <err_code>' voi err_code thuoc VALID_ERROR_CODES. Detail la err_code.
    - 'invalid': bat ky phan hoi nao khac (thieu/thua token, state la, chuoi rac...). Detail la body.
    """
    if not body:
        return "invalid", ""
    toks = body.strip().split(" ")
    if len(toks) == 2:
        if toks[0] == "DONE" and toks[1] in STATUS_VALID_STATES:
            return "done", toks[1]
        if toks[0] == "ERROR" and toks[1] in VALID_ERROR_CODES:
            return "error", toks[1]
    return "invalid", body


def abort_emergency(ser, timeout=1.0, log_print=print, last_seq=None):
    """[R03] Chu dong gui LASER OFF bang seq moi khi gap loi sau khi da bat laser;
    doc STATUS de kiem tra PA8; neu khong xac nhan duoc thi in canh bao nguy hiem.
    """
    log_print("[R03 CANH BAO] Phat hien loi sau LASER ON! Kich hoat co che dung khan cap...")
    if last_seq is not None:
        try:
            record_p1_seq(max(_cmd_auto_seq, int(last_seq)))
        except Exception:
            pass
    seq_off = get_next_p1_seq()
    while last_seq is not None and seq_off == last_seq:
        seq_off = get_next_p1_seq()
    cmd_off = format_p1_cmd(seq_off, "LASER OFF")
    log_print("   Gui lenh tat: %s" % cmd_off)
    try:
        send_line(ser, cmd_off)
        rep_off = read_line(ser, timeout)
        log_print("   Nhan: %s" % rep_off)
    except (Exception, KeyboardInterrupt) as ex:
        log_print("   Loi khi gui/nhan LASER OFF: %s" % ex)

    seq_st = get_next_p1_seq()
    while seq_st == seq_off or (last_seq is not None and seq_st == last_seq):
        seq_st = get_next_p1_seq()
    cmd_st = format_p1_cmd(seq_st, "STATUS")
    log_print("   Gui kiem tra: %s" % cmd_st)
    confirmed_off = False
    try:
        send_line(ser, cmd_st)
        rep_st = read_line(ser, timeout)
        log_print("   Nhan: %s" % rep_st)
        parsed_st = parse_p1_reply(rep_st)
        if parsed_st and parsed_st[2] and parsed_st[0] == seq_st:
            st_dict = parse_status_tokens(parsed_st[1])
            if st_dict and st_dict["laser"] == 0:
                confirmed_off = True
    except (Exception, KeyboardInterrupt) as ex:
        log_print("   Loi khi gui/nhan STATUS: %s" % ex)

    if confirmed_off:
        log_print("[R03 AN TOAN] Da gui LASER OFF va xac nhan PA8 thap qua STATUS (laser=0).")
    else:
        log_print("[R03 NGUY HIEM] KHONG THE XAC NHAN LASER DA TAT QUA GIAO THUC! "
                  "Yeu cau nguoi van hanh quan sat VOM phai ve 0.00V va cho timeout 5000 ms tren bo.")
    return confirmed_off


def run_p1_session(ser, timeout=1.0, log_print=print):
    """Chay chuoi kiem tra giao thuc P1 tren bo Nucleo khong tai.
    Bao dam co che an toan R03: chu dong tat laser khi co bat ky loi phan hoi nao sau LASER ON.
    """
    ser.timeout = timeout
    drain(ser, 0.3)

    log_print("=== KIEM TRA GIAO THUC P1 TREN BO NUCLEO KHONG TAI ===")
    send_line(ser, "ID?")
    id_line = read_line(ser, timeout)
    log_print("1. ID? ->", id_line)
    if not id_line or not id_line.startswith("ID "):
        return False, "Khong nhan duoc ID hop le"

    tests = [
        (1, "STATUS", "DONE IDLE", "Trang thai khoi dau IDLE"),
        (2, "LASER ON", "DONE ON 5000", "Bat laser (5000 ms)"),
        (3, "STATUS", "DONE CAPTURING", "Kiem tra trang thai CAPTURING"),
        (4, "HEARTBEAT", "DONE CAPTURING", "Gui Heartbeat 1 giay"),
        (5, "STATUS", "DONE CAPTURING", "Kiem tra duy tri CAPTURING"),
        (6, "LASER OFF", "DONE OFF 0", "Tat laser"),
        (6, "LASER OFF", "DONE OFF 0", "Kiem tra duplicate seq 6"),
        (7, "STATUS", "DONE IDLE", "Kiem tra tro ve IDLE"),
        (8, "STOP", "DONE PAUSED", "Lenh STOP chuyen sang PAUSED"),
        (9, "CLEAR", "DONE IDLE", "Lenh CLEAR tro ve IDLE"),
        (10, "HOME", "ERROR NOTIMPL", "Lenh HOME tra ERROR NOTIMPL"),
        (11, "MOVE_ABS 10", "ERROR NOTIMPL", "Lenh MOVE_ABS tra ERROR NOTIMPL"),
    ]

    laser_might_be_on = False
    last_sent_seq = None

    try:
        for seq, cmd_text, expect_start, desc in tests:
            full_cmd = format_p1_cmd(seq, cmd_text)
            log_print("Gui: %s (%s)" % (full_cmd, desc))
            last_sent_seq = seq
            record_p1_seq(seq)
            if cmd_text == "LASER ON":
                laser_might_be_on = True
            send_line(ser, full_cmd)

            reply = read_line(ser, timeout)
            log_print("Nhan:", reply)
            parsed = parse_p1_reply(reply)
            if not parsed:
                log_print("FAIL: Phan hoi khong dung dinh dang P1")
                if laser_might_be_on:
                    abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return False, "Khung loi o seq %d: %r" % (seq, reply)

            r_seq, r_body, r_ok_chk = parsed
            if not r_ok_chk:
                log_print("FAIL: Sai checksum o phan hoi")
                if laser_might_be_on:
                    abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return False, "Sai checksum o seq %d: %r" % (seq, reply)

            if r_seq != seq and seq != 0:
                log_print("FAIL: Sai seq")
                if laser_might_be_on:
                    abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return False, "Sai seq (cho %d, nhan %d)" % (seq, r_seq)

            # Kiem tra noi dung phan hoi theo dung giao thuc Q3 va lenh
            if cmd_text == "STATUS":
                st_dict = parse_status_tokens(r_body)
                if not st_dict:
                    log_print("FAIL: Phan hoi STATUS khong dung schema 10 token Q3: %r" % r_body)
                    if laser_might_be_on:
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return False, "Phan hoi STATUS khong dung schema 10 token Q3 o seq %d" % seq

                expected_state = expect_start.split()[1] if " " in expect_start else expect_start
                if st_dict["state"] != expected_state:
                    log_print("FAIL: Trang thai STATUS khong khop (cho %r, nhan %r)" % (expected_state, st_dict["state"]))
                    if laser_might_be_on:
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return False, "Trang thai STATUS khong khop o seq %d" % seq

                if seq == 1 and (st_dict["state"] != "IDLE" or st_dict["laser"] != 0 or st_dict["remaining_ms"] != 0):
                    log_print("FAIL: STATUS khoi dau khong phai IDLE hoac laser/remaining_ms != 0")
                    return False, "STATUS khoi dau khong hop le o seq %d" % seq
                elif seq in (3, 5) and (st_dict["state"] != "CAPTURING" or st_dict["laser"] != 1 or not (0 < st_dict["remaining_ms"] <= 5000)):
                    log_print("FAIL: STATUS khong o CAPTURING hoac laser=0/remaining_ms ngoai mien 1..5000")
                    if laser_might_be_on:
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return False, "STATUS CAPTURING khong hop le o seq %d" % seq
                elif seq == 7:
                    if st_dict["state"] != "IDLE" or st_dict["laser"] != 0 or st_dict["remaining_ms"] != 0:
                        log_print("FAIL: STATUS sau LASER OFF khong tro ve IDLE hoac laser != 0")
                        if laser_might_be_on:
                            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                        return False, "STATUS sau LASER OFF khong hop le o seq %d" % seq
                    laser_might_be_on = False

            elif cmd_text == "LASER ON":
                on_kind, on_val = parse_laser_on_reply(r_body)
                if on_kind != "ok" or r_body != expect_start:
                    log_print("FAIL: Noi dung phan hoi LASER ON khong khop Q3 (cho %r, nhan %r)" % (expect_start, r_body))
                    if laser_might_be_on:
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return False, "Noi dung khong khop o seq %d: %r" % (seq, r_body)

            elif cmd_text == "HEARTBEAT":
                hb_kind, hb_state = parse_heartbeat_reply(r_body)
                if hb_kind != "done" or r_body != expect_start:
                    log_print("FAIL: Noi dung phan hoi HEARTBEAT khong khop Q3 (cho %r, nhan %r)" % (expect_start, r_body))
                    if laser_might_be_on:
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return False, "Noi dung khong khop o seq %d: %r" % (seq, r_body)

            else:
                # Cac lenh con lai (LASER OFF, STOP, CLEAR, HOME, MOVE_ABS...): so khop nguyen van
                if r_body != expect_start:
                    log_print("FAIL: Noi dung khong khop (cho %r, nhan %r)" % (expect_start, r_body))
                    if laser_might_be_on:
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return False, "Noi dung khong khop o seq %d: %r" % (seq, r_body)

            log_print("PASS: %s" % desc)

    except (Exception, KeyboardInterrupt) as e:
        log_print("FAIL: Ngoai le trong phien P1: %s" % e)
        if laser_might_be_on:
            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
        if isinstance(e, KeyboardInterrupt):
            raise
        return False, "Ngoai le trong phien P1: %s" % e

    log_print("=== TAT CA CAC PHEP THU P1 DEU DAT ===")
    return True, None



def run_session(ser, count, timeout, interval, log_print=print, on_pair=None):
    """Chay N PING. Tra ve dict ket qua va danh sach cap.

    on_pair(row): goi ngay sau moi cap de ghi dan ra dia. Loi I/O cua cong
    (OSError, gom SerialException) va KeyboardInterrupt duoc bat o day va
    bien thanh first_error + aborted, KHONG de thoat mat ket qua (R06).
    """
    result = {
        "count_requested": count,
        "count_sent": 0,
        "count_ok": 0,
        "first_error": None,
        "aborted": None,
        "timeouts": 0,
        "wrong_seq": 0,
        "bad_reply": 0,
        "uptime_first_ms": None,
        "uptime_last_ms": None,
        "latency_ms_min": None,
        "latency_ms_max": None,
        "latency_ms_mean": None,
        "boot_lines": [],
        "id_line": None,
    }
    pairs = []
    latencies = []

    def keep(row):
        pairs.append(row)
        if on_pair is not None:
            on_pair(row)

    try:
        _run_loop(ser, count, timeout, interval, log_print, result, keep, latencies)
    except KeyboardInterrupt:
        result["aborted"] = "user_interrupt"
        result["first_error"] = "nguoi dung ngat (Ctrl+C) sau PING %d, %d PONG dung" % (
            result["count_sent"], result["count_ok"])
        log_print(result["first_error"])
    except OSError as e:
        # pyserial SerialException ke thua OSError: rut cap, cong bien mat, loi doc/ghi
        result["aborted"] = "io_error"
        result["first_error"] = "mat ket noi / loi I-O sau PING %d (%d PONG dung): %s: %s" % (
            result["count_sent"], result["count_ok"], type(e).__name__, e)
        log_print(result["first_error"])

    if latencies:
        result["latency_ms_min"] = round(min(latencies), 3)
        result["latency_ms_max"] = round(max(latencies), 3)
        result["latency_ms_mean"] = round(sum(latencies) / len(latencies), 3)
    return result, pairs


def _run_loop(ser, count, timeout, interval, log_print, result, keep, latencies):
    # Dat timeout dung mot lan, khi chua gui gi va bo dang im.
    ser.timeout = timeout
    result["boot_lines"] = drain(ser, 0.3)

    send_line(ser, "ID?")
    result["id_line"] = read_line(ser, timeout)
    log_print("ID? ->", result["id_line"])
    if result["id_line"] is None or not result["id_line"].startswith("ID "):
        result["first_error"] = "khong nhan duoc dong ID hop le; kiem tra cong COM, firmware da nap, baud 115200"
        return

    for seq in range(1, count + 1):
        t_send = time.perf_counter()
        send_line(ser, "PING %d" % seq)
        result["count_sent"] += 1
        line = read_line(ser, timeout)
        t_recv = time.perf_counter()
        latency_ms = (t_recv - t_send) * 1000.0
        row = {"seq": seq, "sent_at": now_iso(), "latency_ms": round(latency_ms, 3),
               "reply": line if line is not None else "", "uptime_ms": "", "ok": 0}
        if line is None:
            result["timeouts"] += 1
            result["first_error"] = "timeout o PING %d sau %.1f s" % (seq, timeout)
            keep(row)
            log_print("PING %d -> TIMEOUT" % seq)
            break
        pong = parse_pong(line)
        if pong is None:
            result["bad_reply"] += 1
            result["first_error"] = "PING %d nhan dong khong phai PONG: %r" % (seq, line)
            keep(row)
            log_print("PING %d -> BAD %r" % (seq, line))
            break
        if pong[0] != seq:
            result["wrong_seq"] += 1
            result["first_error"] = "PING %d nhan PONG %d, sai thu tu" % (seq, pong[0])
            row["uptime_ms"] = pong[1]
            keep(row)
            log_print("PING %d -> PONG %d SAI THU TU" % (seq, pong[0]))
            break
        row["uptime_ms"] = pong[1]
        row["ok"] = 1
        keep(row)
        result["count_ok"] += 1
        latencies.append(latency_ms)
        if result["uptime_first_ms"] is None:
            result["uptime_first_ms"] = pong[1]
        result["uptime_last_ms"] = pong[1]
        if seq % 10 == 0 or seq == count:
            log_print("PING %d -> PONG %d uptime %d ms, tre %.1f ms" % (seq, pong[0], pong[1], latency_ms))
        if interval > 0:
            time.sleep(interval)


PAIR_FIELDS = ["seq", "sent_at", "latency_ms", "reply", "uptime_ms", "ok"]


def open_session_dir(out_dir, meta):
    """Tao thu muc phien va session.json truoc khi giao tiep; tu choi neu da co."""
    if out_dir.exists():
        return False
    out_dir.mkdir(parents=True, exist_ok=False)
    meta["result"] = {"verdict": "DANG CHAY", "note": "session.json ghi truoc khi mo cong"}
    (out_dir / "session.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out_dir / "pairs.csv").open("w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=PAIR_FIELDS).writeheader()
    return True


def append_pair(out_dir, row):
    """Ghi dan mot cap vao pairs.csv (R06: mat ket noi khong mat du lieu da nhan)."""
    with (out_dir / "pairs.csv").open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=PAIR_FIELDS).writerow(row)


def write_session(out_dir, meta, pairs, result):
    out_dir.mkdir(parents=True, exist_ok=True)  # da tao boi open_session_dir; ghi de tep cua CHINH phien nay
    with (out_dir / "pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PAIR_FIELDS)
        w.writeheader()
        for row in pairs:
            w.writerow(row)
    meta["result"] = result
    (out_dir / "session.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    text = summary_text(meta, result)
    (out_dir / "summary.txt").write_text(text + LF, encoding="utf-8")
    return text


def summary_text(meta, result):
    passed = result["count_ok"] == result["count_requested"] and result["first_error"] is None
    lines = [
        "Phien %s (%s) tren cong %s" % (meta["session_id"], meta.get("label") or "khong nhan", meta["port"]),
        "Firmware tra loi ID?: %s" % (result["id_line"] or "KHONG"),
        "PING gui / PONG dung: %d / %d (yeu cau %d)" % (result["count_sent"], result["count_ok"], result["count_requested"]),
        "Timeout: %d, sai thu tu: %d, dong la: %d" % (result["timeouts"], result["wrong_seq"], result["bad_reply"]),
        "Uptime bo dau/cuoi (ms): %s / %s" % (result["uptime_first_ms"], result["uptime_last_ms"]),
        "Tre PC->bo->PC (ms) min/mean/max: %s / %s / %s" % (result["latency_ms_min"], result["latency_ms_mean"], result["latency_ms_max"]),
        "Commit repo: %s (%s)" % (meta["git"].get("commit", "?")[:7], "BAN" if meta["git"].get("dirty") else "sach"),
        "Ket qua: %s" % ("PASS" if passed else "FAIL - " + str(result["first_error"])),
    ]
    return LF.join(lines)


def run_test_interlock(ser, which, timeout=1.0, max_seconds=12, interval_s=1.0, log_print=print, confirm_vom=False):
    """Chay phep thu ngat lien dong (PT5: cua an toan D8 hoac PT6: estop D9).
    R04: Kiem tra chat che phan hoi STATUS (seq moi, checksum dung, schema 10 token Q3,
    state=ERROR, laser=0, last_err dung ma loi cua/estop, dung bit ngoai vi) va xac nhan VOM 0.00V.
    Tu dong bat laser va gui HEARTBEAT deu dan moi 1.0 s de duy tri lien lac (khong bi LINK_LOST).
    Gia han LASER ON o giay thu 4 neu chua ngat de nguoi dung co du thoi gian thao tac tay (10-15s).
    """
    time.sleep(0.05)
    ser.reset_input_buffer()
    is_door = (which.lower() == "door")
    expected_code = "DOOR_OPEN" if is_door else "ESTOP"
    title = "PHEP THU 5: NGAT LIEN DONG CUA AN TOAN (D8 / PA9)" if is_door else "PHEP THU 6: NGAT LIEN DONG ESTOP (D9 / PC7)"
    prep_msg = (
        "Truoc khi chay: day D8 phai noi 3V3 (cua dong). Ban co %d giay de rut D8 cam xuong GND." % max_seconds
        if is_door else
        "Truoc khi chay: day D9 phai noi GND (estop nha). Ban co %d giay de rut D9 khoi GND." % max_seconds
    )
    log_print("=== %s ===" % title)
    log_print(prep_msg)

    # 1. Bat laser
    seq = get_next_p1_seq()
    cmd_on = format_p1_cmd(seq, "LASER ON")
    log_print("1. Gui: %s" % cmd_on)

    laser_might_be_on = True
    last_sent_seq = seq
    record_p1_seq(seq)

    try:
        send_line(ser, cmd_on)
        rep = read_line(ser, timeout)
        log_print("   Nhan: %s" % rep)
        parsed = parse_p1_reply(rep)
        if not parsed or not parsed[2] or parsed[0] != seq:
            log_print("FAIL: Khong bat duoc laser (khung phan hoi loi hoac sai seq/checksum). Dung phep thu.")
            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
            return 1

        on_status, on_detail = parse_laser_on_reply(parsed[1])
        if on_status != "ok":
            refused_safely = (on_status == "refused" and on_detail in ("DOOR_OPEN", "ESTOP", "IN_ERROR"))
            log_print("FAIL: Khong bat duoc laser (phan hoi sai schema hoac bi tu choi: %s). Dung phep thu." % on_detail)
            if not refused_safely:
                abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
            else:
                laser_might_be_on = False
            return 1
        log_print("   -> [ON OK] Bo xac nhan bat laser: VOM phai len ~3.3V")

        log_print("2. Bat dau giam sat lien dong (gui HEARTBEAT moi %.1f s de giu lien lac)..." % interval_s)
        log_print("   Hay thao tac rut/doi day NGAY BAY GIO!")
        t0 = time.time()
        interlock_tripped = False
        last_on_sec = 0

        def check_status_interlock():
            """Gui STATUS va phan tich nghiem ngat 10 token theo R04/R06/N3/N8."""
            nonlocal last_sent_seq
            seq_chk = get_next_p1_seq()
            last_sent_seq = seq_chk
            record_p1_seq(seq_chk)
            cmd_chk = format_p1_cmd(seq_chk, "STATUS")
            send_line(ser, cmd_chk)
            rep_chk = read_line(ser, timeout)
            parsed_chk = parse_p1_reply(rep_chk)
            if not parsed_chk or not parsed_chk[2] or parsed_chk[0] != seq_chk:
                log_print("   -> [R04/R06 FAIL] Phan hoi STATUS kiem tra lien dong loi/sai chk/sai seq: %r" % rep_chk)
                return False, "bad_reply", rep_chk
            st_info = parse_status_tokens(parsed_chk[1])
            if not st_info:
                log_print("   -> [R04/R06 FAIL] STATUS khong dung schema 10 token Q3: %r" % parsed_chk[1])
                return False, "bad_schema", rep_chk
            if st_info["state"] == "ERROR" and st_info["last_err"] == expected_code:
                if st_info["laser"] != 0:
                    log_print("   -> [R04 NGUY HIEM] STATUS o ERROR nhung laser van bat (laser=1)!")
                    return False, "laser_not_zero", rep_chk
                if st_info["remaining_ms"] != 0:
                    log_print("   -> [R04/R06 FAIL] STATUS o ERROR nhung remaining_ms != 0 (%d)!" % st_info["remaining_ms"])
                    return False, "remaining_ms_not_zero", rep_chk
                # N3/N8: bit door/estop mo ta muc hien tai, khong bat buoc con dang mo/nhan
                return True, "ok", rep_chk
            if st_info["state"] == "CAPTURING" and st_info["laser"] == 1 and st_info["last_err"] == "NONE":
                return False, "waiting", rep_chk
            log_print("   -> [R06 FAIL] STATUS o trang thai khong hop le: state=%s, last_err=%s, laser=%d, remaining_ms=%d"
                      % (st_info["state"], st_info["last_err"], st_info["laser"], st_info["remaining_ms"]))
            return False, "error_state", rep_chk

        for i in range(1, max_seconds + 1):
            time.sleep(interval_s)
            t_now = time.time() - t0
            if (i - last_on_sec >= 4) and not interlock_tripped:
                seq = get_next_p1_seq()
                cmd = format_p1_cmd(seq, "LASER ON")
                cmd_type = "ON"
                last_on_sec = i
            else:
                seq = get_next_p1_seq()
                cmd = format_p1_cmd(seq, "HEARTBEAT")
                cmd_type = "HB"

            last_sent_seq = seq
            record_p1_seq(seq)
            log_print("   [Giay %2d] Gui: %s" % (i, cmd))
            send_line(ser, cmd)
            rep = read_line(ser, timeout)
            log_print("        Nhan: %s" % rep)
            parsed = parse_p1_reply(rep)
            if not parsed or not parsed[2]:
                log_print("   -> [R06 FAIL] Phan hoi %s loi dinh dang hoac sai checksum: %r" % (cmd_type, rep))
                abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return 1

            r_seq, r_body, r_ok_chk = parsed
            if r_seq != seq:
                log_print("   -> [R06 FAIL] Phan hoi %s sai seq (cho %d, nhan %d)" % (cmd_type, seq, r_seq))
                abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return 1

            if cmd_type == "HB":
                hb_status, hb_detail = parse_heartbeat_reply(r_body)
                if hb_status == "done":
                    if hb_detail == "CAPTURING":
                        pass
                    elif hb_detail == "ERROR":
                        trip_ok, reason, rep_status = check_status_interlock()
                        if trip_ok:
                            log_print("   -> [OK] DA PHAT HIEN NGAT LIEN DONG %s! STATUS: %s" % (expected_code, rep_status))
                            interlock_tripped = True
                            break
                        else:
                            log_print("   -> [R06/R07 FAIL] Bo bao DONE ERROR nhung STATUS khong phai trip hop le (ly do: %s)" % reason)
                            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                            return 1
                    else:
                        log_print("   -> [R06/R07 FAIL] Phan hoi HEARTBEAT state bat thuong: %s" % hb_detail)
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                        return 1
                elif hb_status == "error":
                    if hb_detail == expected_code or hb_detail in ("DOOR_OPEN", "ESTOP", "IN_ERROR"):
                        trip_ok, reason, rep_status = check_status_interlock()
                        if trip_ok:
                            log_print("   -> [OK] DA PHAT HIEN NGAT LIEN DONG %s! STATUS: %s" % (expected_code, rep_status))
                            interlock_tripped = True
                            break
                        else:
                            log_print("   -> [R06/R07 FAIL] Bo bao ERROR %s nhung STATUS khong phai trip hop le (ly do: %s)" % (hb_detail, reason))
                            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                            return 1
                    else:
                        log_print("   -> [R06/R07 FAIL] Bo bao loi HEARTBEAT khong khop muc tieu: %s" % hb_detail)
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                        return 1
                else:
                    log_print("   -> [R06/R07 FAIL] Phan hoi HEARTBEAT khong hop le theo Q3: %r" % r_body)
                    abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return 1

            elif cmd_type == "ON":
                on_status, on_detail = parse_laser_on_reply(r_body)
                if on_status == "ok":
                    pass
                elif on_status == "refused":
                    if on_detail == expected_code or on_detail in ("DOOR_OPEN", "ESTOP", "IN_ERROR"):
                        trip_ok, reason, rep_status = check_status_interlock()
                        if trip_ok:
                            log_print("   -> [OK] DA PHAT HIEN NGAT LIEN DONG %s! STATUS: %s" % (expected_code, rep_status))
                            interlock_tripped = True
                            break
                        else:
                            log_print("   -> [R06/R07 FAIL] Bo tu choi ON nhung STATUS khong phai trip hop le (ly do: %s)" % reason)
                            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                            return 1
                    else:
                        log_print("   -> [R06/R07 FAIL] Bo tu choi ON voi ma loi khong khop muc tieu: %s" % on_detail)
                        abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                        return 1
                else:
                    log_print("   -> [R06/R07 FAIL] Phan hoi LASER ON gia han khong hop le theo Q3: %r" % r_body)
                    abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                    return 1

        # 3. Kiem tra STATUS lan cuoi neu chua phat hien
        if not interlock_tripped:
            log_print("3. Kiem tra STATUS lan cuoi...")
            trip_ok, reason, rep_status = check_status_interlock()
            if trip_ok:
                log_print("   -> [OK] DA PHAT HIEN NGAT LIEN DONG %s! STATUS: %s" % (expected_code, rep_status))
                interlock_tripped = True
            elif reason == "waiting":
                log_print("=== KET LUAN: KHONG PHAT HIEN NGAT LIEN DONG TRONG THOI GIAN CHO ===")
                abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return 1
            else:
                log_print("=== KET LUAN: PHAT HIEN LOI KHI KIEM TRA STATUS (ly do: %s) ===" % reason)
                abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
                return 1
    except (Exception, KeyboardInterrupt) as ex:
        if isinstance(ex, KeyboardInterrupt):
            log_print("[R03 CANH BAO] Nguoi dung ngat (Ctrl+C) trong phep thu lien dong!")
        else:
            log_print("[R05 LOI I/O] Ngoai le I/O trong phep thu lien dong: %s" % ex)
        if laser_might_be_on:
            abort_emergency(ser, timeout, log_print, last_seq=last_sent_seq)
        if isinstance(ex, KeyboardInterrupt):
            raise
        return 1

    # 4. [R04] Xac nhan VOM 0.00V
    is_sim = (
        getattr(ser, "port", "") in ("SIM", "FAKE")
        or (isinstance(ser, FakeNucleo) and getattr(ser, "port", "FAKE") in ("SIM", "FAKE"))
    )
    vom_confirmed = False
    if is_sim or confirm_vom:
        vom_confirmed = True
        log_print("   [XAC NHAN VOM] Da xac nhan VOM 0.00V (%s)." % ("gia lap" if is_sim else "co co --confirm-vom-0v"))
    elif sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        try:
            ans = input("Vui long nhin VOM do tai PA8/D7: Dien ap da ve 0.00V chua? (y/N): ").strip().lower()
            if ans in ("y", "yes"):
                vom_confirmed = True
                log_print("   [XAC NHAN VOM] Nguoi van hanh xac nhan VOM da ve 0.00V.")
            else:
                log_print("   [TU CHOI] Nguoi van hanh khong xac nhan VOM ve 0.00V.")
        except (Exception, KeyboardInterrupt) as ex:
            log_print("   [LOI] Khong the doc tu ban phim: %s" % ex)
    else:
        log_print("   [CANH BAO] Moi truong khong tuong tac (non-tty) va khong co co --confirm-vom-0v.")

    if vom_confirmed:
        log_print("=== KET LUAN: PHEP THU DAT! Lien dong %s ngat laser an toan ===" % expected_code)
        port_arg = getattr(ser, "port", "COM3") or "COM3"
        if is_door:
            log_print("Huong dan: Cam lai day D8 len 3V3, sau do chay: .venv/Scripts/python.exe pc/nucleo_ping.py --port %s --cmd \"CLEAR\" de dua bo ve IDLE." % port_arg)
        else:
            log_print("Huong dan: Cam lai day D9 xuong GND, sau do chay: .venv/Scripts/python.exe pc/nucleo_ping.py --port %s --cmd \"CLEAR\" de dua bo ve IDLE." % port_arg)
        return 0
    else:
        log_print("=== KET LUAN: PHEP THU CHUA DAT! Chua xac nhan duoc VOM ve 0.00V tren phan cung ===")
        return 1


# ---------------------------------------------------------------------------
# Selftest: bo gia lap, khong can pyserial mo cong that
# ---------------------------------------------------------------------------

class FakeNucleo:
    """Gia lap cong serial noi voi firmware NucleoPing.
    mode: 'ok' | 'wrong_seq_at' | 'silent_at' | 'garbage_at' | 'no_id'
          | 'io_error_at' (OSError khi ghi PING n, nhu rut cap)
          | 'interrupt_at' (KeyboardInterrupt khi ghi PING n)."""

    def __init__(self, mode="ok", at=0, crlf=False, uptime0=1500):
        self.mode = mode
        self.at = at
        self.crlf = crlf
        self.uptime = uptime0
        self.state = "IDLE"
        self.laser = 0
        self.last_seq = None
        self.last_resp = None
        self.received_cmds = []
        self.inbuf = bytearray()
        self.outbuf = bytearray()
        self.timeout = 1.0
        self.outbuf += self._enc("BOOT NucleoPing 0.2.0 selftest P1")

    def _enc(self, s):
        return (s + (CR + LF if self.crlf else LF)).encode("ascii")

    def reset_input_buffer(self):
        self.inbuf.clear()
        self.outbuf.clear()

    def flush(self):
        if self.mode == "flush_io_error_on" and self.laser == 1:
            self.mode = "ok"
            raise OSError("tiem loi: flush error sau write ON")

    def write(self, data):
        self.inbuf += data
        while LF.encode() in self.inbuf:
            idx = self.inbuf.index(LF.encode())
            line = self.inbuf[:idx].decode("ascii").replace(CR, "")
            del self.inbuf[:idx + 1]
            self._handle(line)
        return len(data)

    def _handle(self, line):
        self.uptime += 7
        if line == "ID?":
            if self.mode != "no_id":
                self.outbuf += self._enc("ID NUCLEO-F446RE NucleoPing 0.2.0 selftest")
            return
        if "*" in line:
            p_star = line.rfind("*")
            body = line[:p_star]
            chk = line[p_star + 1:]
            if chk.upper() != calc_p1_checksum(body).upper():
                self.outbuf += self._enc("0 ERROR BADCHK*%s" % calc_p1_checksum("0 ERROR BADCHK"))
                return
            parts = body.split(" ", 1)
            seq = int(parts[0])
            cmd_body = parts[1] if len(parts) > 1 else ""
            self.received_cmds.append(cmd_body)

            if self.last_seq is not None and seq == self.last_seq and self.last_resp is not None:
                self.outbuf += self._enc(self.last_resp)
                return

            if self.mode == "error_after_on" and self.laser == 1 and cmd_body == "STATUS":
                # Mo phong loi sau LASER ON de kiem tra R03
                self.outbuf += self._enc("%d ERROR BADCHK*00" % seq)
                return

            if self.mode == "r06_bad_hb_once" and cmd_body == "HEARTBEAT":
                self.mode = "interlock_door"
                return

            if self.mode == "r06_bad_seq_hb" and cmd_body == "HEARTBEAT":
                self.mode = "interlock_door"
                ans = "99 DONE CAPTURING"
                full_resp = "%s*%s" % (ans, calc_p1_checksum(ans))
                self.last_seq = 99
                self.last_resp = full_resp
                self.outbuf += self._enc(full_resp)
                return

            if cmd_body == "STATUS":
                err_code = "NONE"
                door_val = 1
                estop_val = 0
                if self.state == "ERROR":
                    if self.mode in ("interlock_door", "bad_status_chk", "bad_status_schema", "r06_rem_nonzero",
                                     "interlock_door_closed_again", "r07_hb_garbage", "r07_hb_extra"):
                        err_code = "DOOR_OPEN"
                        door_val = 0 if self.mode != "interlock_door_closed_again" else 1
                        estop_val = 0
                    elif self.mode == "interlock_estop":
                        err_code = "ESTOP"
                        door_val = 1
                        estop_val = 1
                    elif self.mode == "r06_wrong_err":
                        err_code = "LINK_LOST"
                        door_val = 0
                        estop_val = 0
                    else:
                        err_code = "NONE"
                rem_ms = 5000 if self.laser == 1 and self.state == "CAPTURING" else (1 if self.mode == "r06_rem_nonzero" and self.state == "ERROR" else 0)
                if self.mode == "r09_status_rem_5001" and seq == 3:
                    rem_ms = 5001
                elif self.mode == "r09_status_rem_999999" and seq == 3:
                    rem_ms = 999999
                elif self.mode == "r09_status_bad_lasterr" and seq == 3:
                    err_code = "NO_SUCH_ERROR"

                if self.mode == "bad_status_chk":
                    ans = "%d DONE %s 0 %d %d %d 0 %d %s %d" % (seq, self.state, self.laser, door_val, estop_val, self.uptime, err_code, rem_ms)
                    chk_real = calc_p1_checksum(ans)
                    bad_chk = "FF" if chk_real != "FF" else "00"
                    full_resp = "%s*%s" % (ans, bad_chk)  # Luon luon sai checksum
                    self.outbuf += self._enc(full_resp)
                    return
                elif self.mode == "bad_status_schema":
                    ans = "%d DONE %s 0 %d %d" % (seq, self.state, self.laser, door_val)  # Thieu token
                else:
                    ans = "%d DONE %s 0 %d %d %d 0 %d %s %d" % (seq, self.state, self.laser, door_val, estop_val, self.uptime, err_code, rem_ms)
            elif cmd_body == "LASER ON":
                if self.mode == "r07_on_missing_rem":
                    ans = "%d DONE ON" % seq
                elif self.mode == "r07_on_negative_rem":
                    ans = "%d DONE ON -1" % seq
                elif self.mode == "l19_on_extra":
                    self.laser = 1
                    self.state = "CAPTURING"
                    ans = "%d DONE ON 5000 X" % seq
                else:
                    self.laser = 1
                    self.state = "CAPTURING"
                    ans = "%d DONE ON 5000" % seq
            elif cmd_body == "LASER OFF":
                self.laser = 0
                self.state = "IDLE"
                if self.mode == "l19_off_extra":
                    ans = "%d DONE OFF 0 X" % seq
                else:
                    ans = "%d DONE OFF 0" % seq
            elif cmd_body == "HEARTBEAT":
                if self.mode == "r07_hb_garbage":
                    self.state = "ERROR"
                    self.laser = 0
                    ans = "%d garbage ERROR" % seq
                elif self.mode == "r07_hb_extra":
                    self.state = "ERROR"
                    self.laser = 0
                    ans = "%d DONE ERROR EXTRA" % seq
                elif self.mode == "l19_hb_extra":
                    ans = "%d DONE CAPTURING X" % seq
                elif self.mode in ("interlock_door", "interlock_estop", "bad_status_chk", "bad_status_schema",
                                   "r06_rem_nonzero", "r06_wrong_err", "interlock_door_closed_again"):
                    self.at -= 1
                    if self.at <= 0:
                        self.state = "ERROR"
                        self.laser = 0
                        ans = "%d DONE ERROR" % seq
                    else:
                        ans = "%d DONE %s" % (seq, self.state)
                else:
                    ans = "%d DONE %s" % (seq, self.state)
            elif cmd_body == "STOP":
                self.laser = 0
                self.state = "PAUSED"
                if self.mode == "l19_stop_extra":
                    ans = "%d DONE PAUSED X" % seq
                else:
                    ans = "%d DONE PAUSED" % seq
            elif cmd_body == "CLEAR":
                self.state = "IDLE"
                ans = "%d DONE IDLE" % seq
            elif cmd_body in ("HOME", "MOVE_ABS 10"):
                if self.mode == "l19_home_extra":
                    ans = "%d ERROR NOTIMPLX" % seq
                else:
                    ans = "%d ERROR NOTIMPL" % seq
            else:
                ans = "%d ERROR UNKNOWN" % seq

            full_resp = "%s*%s" % (ans, calc_p1_checksum(ans))
            self.last_seq = seq
            self.last_resp = full_resp
            self.outbuf += self._enc(full_resp)
            return
        if line.startswith("PING "):
            n = int(line[5:])
            if self.mode == "io_error_at" and n == self.at:
                raise OSError("gia lap: cong bien mat (rut cap)")
            if self.mode == "interrupt_at" and n == self.at:
                raise KeyboardInterrupt()
            if self.mode == "silent_at" and n == self.at:
                return
            if self.mode == "garbage_at" and n == self.at:
                self.outbuf += self._enc("ERR unknown")
                return
            if self.mode == "wrong_seq_at" and n == self.at:
                n = n + 1
            self.outbuf += self._enc("PONG %d %d" % (n, self.uptime))
            return
        self.outbuf += self._enc("ERR unknown")

    def read_until(self, expected):
        if expected not in self.outbuf:
            return b""          # bo im lang: het gio, tra ve phan khong co LF
        idx = self.outbuf.index(expected) + len(expected)
        b = bytes(self.outbuf[:idx])
        del self.outbuf[:idx]
        return b

    def close(self):
        pass


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    r, p = run_session(FakeNucleo("ok"), 100, 0.2, 0, log_print=lambda *a: None)
    check("100 PING dung thu tu -> count_ok 100, khong loi", r["count_ok"] == 100 and r["first_error"] is None)
    check("ghi nhan dong ID", r["id_line"] is not None and r["id_line"].startswith("ID NUCLEO-F446RE"))
    check("dong BOOT truoc phien duoc rut ra", r["boot_lines"] == ["BOOT NucleoPing 0.2.0 selftest P1"])
    check("uptime dau < uptime cuoi", r["uptime_first_ms"] < r["uptime_last_ms"])
    check("100 dong pairs, tat ca ok", len(p) == 100 and all(x["ok"] == 1 for x in p))

    r, p = run_session(FakeNucleo("ok", crlf=True), 5, 0.2, 0, log_print=lambda *a: None)
    check("bo CR khi bo tra CRLF", r["count_ok"] == 5)

    r, p = run_session(FakeNucleo("wrong_seq_at", at=37), 100, 0.2, 0, log_print=lambda *a: None)
    check("sai thu tu o 37 -> dung tai 37, count_ok 36", r["count_ok"] == 36 and r["wrong_seq"] == 1 and "PING 37" in r["first_error"])

    r, p = run_session(FakeNucleo("silent_at", at=3), 10, 0.05, 0, log_print=lambda *a: None)
    check("khong tra loi o 3 -> timeout, count_ok 2", r["count_ok"] == 2 and r["timeouts"] == 1)

    r, p = run_session(FakeNucleo("garbage_at", at=5), 10, 0.2, 0, log_print=lambda *a: None)
    check("dong la o 5 -> bad_reply, count_ok 4", r["count_ok"] == 4 and r["bad_reply"] == 1)

    r, p = run_session(FakeNucleo("no_id"), 10, 0.05, 0, log_print=lambda *a: None)
    check("khong co ID -> dung truoc khi PING", r["count_sent"] == 0 and r["first_error"] is not None)

    # R06: loi I/O giua phien -> giu ket qua da co, khong thoat
    r, p = run_session(FakeNucleo("io_error_at", at=3), 10, 0.2, 0, log_print=lambda *a: None)
    check("OSError o PING 3 -> aborted io_error, giu 2 PONG", r["aborted"] == "io_error" and r["count_ok"] == 2
          and len(p) == 2 and "mat ket noi" in r["first_error"])
    r, p = run_session(FakeNucleo("interrupt_at", at=4), 10, 0.2, 0, log_print=lambda *a: None)
    check("Ctrl+C o PING 4 -> aborted user_interrupt, giu 3 PONG", r["aborted"] == "user_interrupt" and r["count_ok"] == 3)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "ping_x"
        m = {"session_id": "ping_x", "label": "t", "port": "FAKE", "git": {"commit": "0000000", "dirty": False}}
        check("open_session_dir tao thu muc + session.json truoc khi giao tiep",
              open_session_dir(d, m) and (d / "session.json").exists() and (d / "pairs.csv").exists())
        check("open_session_dir tu choi thu muc da co", open_session_dir(d, m) is False)
        r, p = run_session(FakeNucleo("io_error_at", at=3), 10, 0.2, 0, log_print=lambda *a: None,
                           on_pair=lambda row: append_pair(d, row))
        rows = (d / "pairs.csv").read_text(encoding="utf-8").strip().splitlines()
        check("pairs.csv ghi dan: 2 cap con tren dia sau loi I/O", len(rows) == 3 and rows[1].startswith("1,") and rows[2].startswith("2,"))
        text = write_session(d, m, p, r)
        check("summary sau loi I/O la FAIL kem diem mat lien lac", "Ket qua: FAIL - mat ket noi" in text)

    check("parse_pong hop le", parse_pong("PONG 12 3456") == (12, 3456))
    check("parse_pong tu choi thieu truong", parse_pong("PONG 12") is None)
    check("parse_pong tu choi chu", parse_pong("PONG x 1") is None)

    # R02: parse_status_tokens 10 token theo Q3
    check("parse_status_tokens chuoi 10 token hop le",
          parse_status_tokens("DONE IDLE 0 0 1 0 0 1500 NONE 0") == {
              "state": "IDLE", "step_count": 0, "laser": 0, "door": 1, "estop": 0, "homed": 0,
              "uptime_ms": 1500, "last_err": "NONE", "remaining_ms": 0
          })
    check("parse_status_tokens tu choi thieu token (9 token)",
          parse_status_tokens("DONE IDLE 0 0 1 0 0 1500 NONE") is None)
    check("parse_status_tokens tu choi thua token (11 token)",
          parse_status_tokens("DONE IDLE 0 0 1 0 0 1500 NONE 0 EXTRA") is None)
    check("parse_status_tokens tu choi state la",
          parse_status_tokens("DONE INVALID 0 0 1 0 0 1500 NONE 0") is None)
    check("parse_status_tokens tu choi bit laser sai (2)",
          parse_status_tokens("DONE IDLE 0 2 1 0 0 1500 NONE 0") is None)
    # R09: kiem tra mien gia tri remaining_ms 0..5000 va last_err thuoc VALID_LAST_ERR_CODES
    check("R09: parse_status_tokens chap nhan remaining_ms = 5000",
          parse_status_tokens("DONE CAPTURING 0 1 1 0 0 1500 NONE 5000") is not None)
    check("R09: parse_status_tokens chap nhan last_err = LASER_TIMEOUT",
          parse_status_tokens("DONE IDLE 0 0 1 0 0 1500 LASER_TIMEOUT 0") is not None)
    check("R09: parse_status_tokens chap nhan last_err = WDG_RESET",
          parse_status_tokens("DONE IDLE 0 0 1 0 0 1500 WDG_RESET 0") is not None)
    check("R09: parse_status_tokens tu choi remaining_ms > 5000 (5001)",
          parse_status_tokens("DONE CAPTURING 0 1 1 0 0 1500 NONE 5001") is None)
    check("R09: parse_status_tokens tu choi remaining_ms > 5000 (999999)",
          parse_status_tokens("DONE CAPTURING 0 1 1 0 0 1500 NONE 999999") is None)
    check("R09: parse_status_tokens tu choi last_err khong hop le (NO_SUCH_ERROR)",
          parse_status_tokens("DONE CAPTURING 0 1 1 0 0 1500 NO_SUCH_ERROR 4995") is None)

    # R07: parse_laser_on_reply theo Q3
    check("parse_laser_on_reply hop le", parse_laser_on_reply("DONE ON 5000") == ("ok", 5000))
    check("parse_laser_on_reply chap nhan 0 ms", parse_laser_on_reply("DONE ON 0") == ("ok", 0))
    check("parse_laser_on_reply tu choi thieu rem", parse_laser_on_reply("DONE ON") == ("invalid", "DONE ON"))
    check("parse_laser_on_reply tu choi rem am", parse_laser_on_reply("DONE ON -1") == ("invalid", "DONE ON -1"))
    check("parse_laser_on_reply tu choi rem > 5000", parse_laser_on_reply("DONE ON 5001") == ("invalid", "DONE ON 5001"))
    check("parse_laser_on_reply chap nhan tu choi hop le", parse_laser_on_reply("ERROR DOOR_OPEN") == ("refused", "DOOR_OPEN"))
    check("parse_laser_on_reply tu choi ma loi la", parse_laser_on_reply("ERROR UNKNOWN_CODE") == ("invalid", "ERROR UNKNOWN_CODE"))
    check("parse_laser_on_reply tu choi chuoi rac", parse_laser_on_reply("garbage ERROR") == ("invalid", "garbage ERROR"))

    # R07: parse_heartbeat_reply theo Q3
    check("parse_heartbeat_reply hop le", parse_heartbeat_reply("DONE CAPTURING") == ("done", "CAPTURING"))
    check("parse_heartbeat_reply hop le ERROR", parse_heartbeat_reply("DONE ERROR") == ("done", "ERROR"))
    check("parse_heartbeat_reply tu choi thua token", parse_heartbeat_reply("DONE ERROR EXTRA") == ("invalid", "DONE ERROR EXTRA"))
    check("parse_heartbeat_reply tu choi chuoi rac", parse_heartbeat_reply("garbage ERROR") == ("invalid", "garbage ERROR"))
    check("parse_heartbeat_reply chap nhan loi hop le", parse_heartbeat_reply("ERROR DOOR_OPEN") == ("error", "DOOR_OPEN"))

    # P1 selftest (cach ly thu muc tam de khong cham vao tep seq that cua may)
    with tempfile.TemporaryDirectory() as td_seq:
        old_temp = tempfile.tempdir
        tempfile.tempdir = td_seq
        try:
            check("calc_p1_checksum dung", calc_p1_checksum("1 STATUS") == "05")
            check("format_p1_cmd dung", format_p1_cmd(1, "STATUS") == "1 STATUS*05")
            check("parse_p1_reply dung", parse_p1_reply("1 DONE IDLE*35") == (1, "DONE IDLE", True))
            check("parse_p1_reply phat hien sai checksum", parse_p1_reply("1 DONE IDLE*00") == (1, "DONE IDLE", False))

            p1_ok, p1_err = run_p1_session(FakeNucleo("p1"), timeout=0.2, log_print=lambda *a: None)
            check("run_p1_session tren FakeNucleo dat PASS", p1_ok and p1_err is None)

            # R03: test co che tat khan cap abort_emergency khi phat hien loi sau LASER ON
            fake_r03 = FakeNucleo("error_after_on")
            p1_ok_r03, p1_err_r03 = run_p1_session(fake_r03, timeout=0.1, log_print=lambda *a: None)
            check("R03: run_p1_session bao FAIL khi phat hien loi sau LASER ON", not p1_ok_r03)
            check("R03: FakeNucleo nhan duoc LASER OFF cuu ho va da tat laser",
                  "LASER OFF" in fake_r03.received_cmds and fake_r03.laser == 0)

            # R04: kiem tra lien dong voi FakeNucleo
            rc_door = run_test_interlock(FakeNucleo("interlock_door", at=2), "door", timeout=0.1, max_seconds=3, interval_s=0.01, log_print=lambda *a: None)
            check("run_test_interlock door tren FakeNucleo dat PASS", rc_door == 0)
            rc_estop = run_test_interlock(FakeNucleo("interlock_estop", at=2), "estop", timeout=0.1, max_seconds=3, interval_s=0.01, log_print=lambda *a: None)
            check("run_test_interlock estop tren FakeNucleo dat PASS", rc_estop == 0)

            # R04: tu choi khi STATUS sai checksum
            rc_bad_chk = run_test_interlock(FakeNucleo("bad_status_chk", at=1), "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R04: run_test_interlock tu choi khi STATUS sai checksum", rc_bad_chk != 0)

            # R04: tu choi khi STATUS thieu token
            rc_bad_schema = run_test_interlock(FakeNucleo("bad_status_schema", at=1), "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R04: run_test_interlock tu choi khi STATUS thieu token", rc_bad_schema != 0)

            # R04: tu choi khi chua xac nhan VOM 0V tren cong COM gia dinh (khong phai sim, non-tty)
            fake_vom = FakeNucleo("interlock_door", at=1)
            fake_vom.port = "COM99"
            rc_no_vom = run_test_interlock(fake_vom, "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None, confirm_vom=False)
            check("R04: run_test_interlock tu choi khi chua xac nhan VOM 0V (non-sim/non-tty)", rc_no_vom != 0)

            # R04: pass khi co co confirm_vom tren cong COM do
            rc_vom_ok = run_test_interlock(fake_vom, "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None, confirm_vom=True)
            check("R04: run_test_interlock pass khi co co --confirm-vom-0v", rc_vom_ok == 0)

            # R05: flush loi sau khi gui LASER ON trong --p1 -> van goi abort_emergency cuu ho
            fake_r05 = FakeNucleo("flush_io_error_on")
            p1_ok_r05, _ = run_p1_session(fake_r05, timeout=0.1, log_print=lambda *a: None)
            check("R05: run_p1_session bao FAIL khi flush loi sau ON", not p1_ok_r05)
            check("R05: FakeNucleo nhan duoc LASER OFF cuu ho va da tat laser",
                  "LASER OFF" in fake_r05.received_cmds and fake_r05.laser == 0)

            # R06: mat HEARTBEAT dau tien -> khong bo qua roi PASS o luot sau ma phai FAIL ngay
            fake_r06_hb = FakeNucleo("r06_bad_hb_once", at=2)
            rc_r06_hb = run_test_interlock(fake_r06_hb, "door", timeout=0.1, max_seconds=3, interval_s=0.01, log_print=lambda *a: None)
            check("R06: run_test_interlock tu choi khi mat HEARTBEAT dau", rc_r06_hb != 0)

            # R06: HEARTBEAT dau sai seq -> FAIL ngay
            fake_r06_seq = FakeNucleo("r06_bad_seq_hb", at=2)
            rc_r06_seq = run_test_interlock(fake_r06_seq, "door", timeout=0.1, max_seconds=3, interval_s=0.01, log_print=lambda *a: None)
            check("R06: run_test_interlock tu choi khi HEARTBEAT sai seq", rc_r06_seq != 0)

            # R06: STATUS sau trip co remaining_ms != 0 -> FAIL ngay
            rc_r06_rem = run_test_interlock(FakeNucleo("r06_rem_nonzero", at=1), "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R06: run_test_interlock tu choi khi STATUS remaining_ms != 0", rc_r06_rem != 0)

            # R06: STATUS sau trip co last_err != DOOR_OPEN (LINK_LOST) -> FAIL ngay
            rc_r06_err = run_test_interlock(FakeNucleo("r06_wrong_err", at=1), "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R06: run_test_interlock tu choi khi STATUS last_err khac muc tieu", rc_r06_err != 0)

            # N3/N8: trip hop le khi bit door da dong lai (door=1) nhung last_err=DOOR_OPEN
            rc_n3 = run_test_interlock(FakeNucleo("interlock_door_closed_again", at=1), "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("N3/N8: run_test_interlock pass khi day da cam lai sau trip", rc_n3 == 0)

            # R07: HEARTBEAT rac chua chu ERROR nhung khong dung Q3 -> FAIL ngay
            fake_r07_hb_g = FakeNucleo("r07_hb_garbage", at=1)
            rc_r07_hb_g = run_test_interlock(fake_r07_hb_g, "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R07: run_test_interlock tu choi khi HEARTBEAT rac chua ERROR", rc_r07_hb_g != 0)

            # R07: HEARTBEAT thua token (DONE ERROR EXTRA) -> FAIL ngay
            fake_r07_hb_e = FakeNucleo("r07_hb_extra", at=1)
            rc_r07_hb_e = run_test_interlock(fake_r07_hb_e, "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R07: run_test_interlock tu choi khi HEARTBEAT thua token", rc_r07_hb_e != 0)

            # R07: ON thieu remaining_ms -> FAIL ngay
            fake_r07_on_m = FakeNucleo("r07_on_missing_rem")
            rc_r07_on_m = run_test_interlock(fake_r07_on_m, "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R07: run_test_interlock tu choi khi ON thieu remaining_ms", rc_r07_on_m != 0)

            # R07: ON co remaining_ms am -> FAIL ngay
            fake_r07_on_n = FakeNucleo("r07_on_negative_rem")
            rc_r07_on_n = run_test_interlock(fake_r07_on_n, "door", timeout=0.1, max_seconds=2, interval_s=0.01, log_print=lambda *a: None)
            check("R07: run_test_interlock tu choi khi ON co remaining_ms am", rc_r07_on_n != 0)

            # L19: run_p1_session tu choi phan hoi sai dinh dang Q3 / thua token o cac buoc
            fake_l19_on = FakeNucleo("l19_on_extra")
            p1_ok_l19_on, _ = run_p1_session(fake_l19_on, timeout=0.1, log_print=lambda *a: None)
            check("L19: run_p1_session tu choi khi LASER ON thua token ('DONE ON 5000 X')", not p1_ok_l19_on)
            check("L19: FakeNucleo tat laser cuu ho khi LASER ON thua token", "LASER OFF" in fake_l19_on.received_cmds and fake_l19_on.laser == 0)

            fake_l19_hb = FakeNucleo("l19_hb_extra")
            p1_ok_l19_hb, _ = run_p1_session(fake_l19_hb, timeout=0.1, log_print=lambda *a: None)
            check("L19: run_p1_session tu choi khi HEARTBEAT thua token ('DONE CAPTURING X')", not p1_ok_l19_hb)
            check("L19: FakeNucleo tat laser cuu ho khi HEARTBEAT thua token", "LASER OFF" in fake_l19_hb.received_cmds and fake_l19_hb.laser == 0)

            fake_l19_off = FakeNucleo("l19_off_extra")
            p1_ok_l19_off, _ = run_p1_session(fake_l19_off, timeout=0.1, log_print=lambda *a: None)
            check("L19: run_p1_session tu choi khi LASER OFF thua token ('DONE OFF 0 X')", not p1_ok_l19_off)
            check("L19: FakeNucleo tat laser cuu ho khi LASER OFF thua token", "LASER OFF" in fake_l19_off.received_cmds and fake_l19_off.laser == 0)

            fake_l19_stop = FakeNucleo("l19_stop_extra")
            p1_ok_l19_stop, _ = run_p1_session(fake_l19_stop, timeout=0.1, log_print=lambda *a: None)
            check("L19: run_p1_session tu choi khi STOP thua token ('DONE PAUSED X')", not p1_ok_l19_stop)

            fake_l19_home = FakeNucleo("l19_home_extra")
            p1_ok_l19_home, _ = run_p1_session(fake_l19_home, timeout=0.1, log_print=lambda *a: None)
            check("L19: run_p1_session tu choi khi HOME dinh ky tu la ('ERROR NOTIMPLX')", not p1_ok_l19_home)

            # R09: run_p1_session tu choi STATUS co remaining_ms > 5000 hoac last_err khong hop le theo Q3
            fake_r09_1 = FakeNucleo("r09_status_rem_5001")
            p1_ok_r09_1, _ = run_p1_session(fake_r09_1, timeout=0.1, log_print=lambda *a: None)
            check("R09: run_p1_session tu choi khi STATUS remaining_ms = 5001", not p1_ok_r09_1)
            check("R09: FakeNucleo tat laser cuu ho khi STATUS remaining_ms = 5001", "LASER OFF" in fake_r09_1.received_cmds and fake_r09_1.laser == 0)

            fake_r09_2 = FakeNucleo("r09_status_rem_999999")
            p1_ok_r09_2, _ = run_p1_session(fake_r09_2, timeout=0.1, log_print=lambda *a: None)
            check("R09: run_p1_session tu choi khi STATUS remaining_ms = 999999", not p1_ok_r09_2)
            check("R09: FakeNucleo tat laser cuu ho khi STATUS remaining_ms = 999999", "LASER OFF" in fake_r09_2.received_cmds and fake_r09_2.laser == 0)

            fake_r09_3 = FakeNucleo("r09_status_bad_lasterr")
            p1_ok_r09_3, _ = run_p1_session(fake_r09_3, timeout=0.1, log_print=lambda *a: None)
            check("R09: run_p1_session tu choi khi STATUS last_err la ('NO_SUCH_ERROR')", not p1_ok_r09_3)
            check("R09: FakeNucleo tat laser cuu ho khi STATUS last_err la", "LASER OFF" in fake_r09_3.received_cmds and fake_r09_3.laser == 0)
        finally:
            tempfile.tempdir = old_temp

    meta = {"session_id": "ping_selftest", "label": "selftest", "port": "FAKE", "git": {"commit": "0000000", "dirty": False}}
    r, p = run_session(FakeNucleo("ok"), 3, 0.2, 0, log_print=lambda *a: None)
    text = summary_text(meta, r)
    check("summary co PASS", "Ket qua: PASS" in text)
    r, p = run_session(FakeNucleo("silent_at", at=2), 3, 0.05, 0, log_print=lambda *a: None)
    check("summary co FAIL kem ly do", "Ket qua: FAIL - timeout o PING 2" in summary_text(meta, r))

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Gui N PING toi Nucleo-F446RE qua COM ao, kiem phan hoi dung thu tu.")
    ap.add_argument("--port", help="cong COM cua Nucleo, vi du COM5; lay tu buoc nhan dien, KHONG dung COM9 cua S3")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--count", type=int, default=100, help="so PING (mac dinh 100)")
    ap.add_argument("--timeout", type=float, default=1.0, help="giay cho moi PONG (mac dinh 1.0)")
    ap.add_argument("--interval", type=float, default=0.05, help="giay nghi giua hai PING (mac dinh 0.05)")
    ap.add_argument("--label", help="nhan phien, vi du run1 hoac run2-sau-rut-nguon")
    ap.add_argument("--out", default="docs/logs", help="thu muc goc cho ho so phien (mac dinh docs/logs)")
    ap.add_argument("--session-id", help="ID phien; mac dinh ping_YYYYMMDD_HHMMSS")
    ap.add_argument("--note", help="ghi chu tu do vao session.json")
    ap.add_argument("--selftest", action="store_true", help="chay kiem tra noi bo voi bo gia lap, khong can cong COM")
    ap.add_argument("--p1", action="store_true", help="chay chuoi kiem tra giao thuc P1 tren bo Nucleo khong tai")
    ap.add_argument("--cmd", help="gui mot lenh P1 duy nhat (hoac PING/ID? ke thua) toi bo roi in phan hoi; vi du: --cmd 'LASER ON'")
    ap.add_argument("--test-laser-timeout", action="store_true",
                    help="chay phep thu 3: bat laser va tu dong gui HEARTBEAT moi 1 s trong 6 s de quan sat laser tat dung tai 5.0 s")
    ap.add_argument("--test-door", action="store_true",
                    help="chay phep thu 5: bat laser va tu dong gui HEARTBEAT giu lien lac, doi ngat cua an toan D8")
    ap.add_argument("--test-estop", action="store_true",
                    help="chay phep thu 6: bat laser va tu dong gui HEARTBEAT giu lien lac, doi ngat dung khan cap D9")
    ap.add_argument("--test-interlock", choices=["door", "estop"],
                    help="chay phep thu ngat lien dong: door (PT5 D8) hoac estop (PT6 D9)")
    ap.add_argument("--confirm-vom-0v", action="store_true",
                    help="xac nhan VOM da do 0.00V tai PA8/D7 sau khi ngat lien dong (dung cho script tu dong)")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.port:
        ap.error("can --port (hoac --selftest)")

    if args.cmd:
        try:
            ser = open_serial(args.port, args.baud, args.timeout)
        except Exception as e:
            print("KHONG MO DUOC CONG", args.port, "-", e)
            return 3
        try:
            time.sleep(0.05)
            ser.reset_input_buffer()
            c_text = args.cmd.strip()
            if c_text == "ID?" or c_text.startswith("PING"):
                out_line = c_text
            elif "*" in c_text:
                out_line = c_text
            else:
                parts = c_text.split(" ", 1)
                if parts[0].isdigit() and 1 <= int(parts[0]) <= 65535:
                    seq = int(parts[0])
                    body = parts[1] if len(parts) > 1 else ""
                    record_p1_seq(seq)
                else:
                    seq = get_next_p1_seq()
                    body = c_text
                out_line = format_p1_cmd(seq, body)

            print("Gui:", out_line)
            send_line(ser, out_line)
            rep = read_line(ser, args.timeout)
            print("Nhan:", rep)
            return 0 if rep else 1
        finally:
            try:
                ser.close()
            except Exception:
                pass

    if args.test_laser_timeout:
        try:
            ser = open_serial(args.port, args.baud, args.timeout)
        except Exception as e:
            print("KHONG MO DUOC CONG", args.port, "-", e)
            return 3
        laser_might_be_on = False
        last_sent_seq = None
        try:
            time.sleep(0.05)
            ser.reset_input_buffer()
            print("=== PHEP THU 3: KIEM TRA HET HAN LASER 5000 MS CO HEARTBEAT ===")
            seq = get_next_p1_seq()
            cmd_on = format_p1_cmd(seq, "LASER ON")
            print("1. Gui:", cmd_on)
            laser_might_be_on = True
            last_sent_seq = seq
            record_p1_seq(seq)
            send_line(ser, cmd_on)
            rep = read_line(ser, args.timeout)
            print("   Nhan:", rep)
            parsed_on = parse_p1_reply(rep)
            if not parsed_on or not parsed_on[2] or parsed_on[0] != seq:
                print("FAIL: Khong bat duoc laser o phep thu 3 (sai seq/checksum).")
                abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
                return 1
            on_status, on_detail = parse_laser_on_reply(parsed_on[1])
            if on_status != "ok":
                print("FAIL: Phan hoi LASER ON khong hop le o phep thu 3: %r" % parsed_on[1])
                abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
                return 1
            print("   -> [ON OK] Bo xac nhan bat laser: VOM phai len ~3.3V")
            t0 = time.time()
            for i in range(1, 7):
                time.sleep(1.0)
                t_now = time.time() - t0
                seq = get_next_p1_seq()
                last_sent_seq = seq
                record_p1_seq(seq)
                cmd_hb = format_p1_cmd(seq, "HEARTBEAT")
                print("2.%d. [Giay %.1f] Gui: %s" % (i, t_now, cmd_hb))
                send_line(ser, cmd_hb)
                rep = read_line(ser, args.timeout)
                print("     Nhan: %s %s" % (rep, "-> VOM van ~3.3V" if i < 5 else "-> VOM PHAI TUT VE 0.00V"))
                parsed_hb = parse_p1_reply(rep)
                if not parsed_hb or not parsed_hb[2] or parsed_hb[0] != seq:
                    print("FAIL: Phan hoi HEARTBEAT thu %d loi hoac sai seq/checksum: %r" % (i, rep))
                    abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
                    return 1
                hb_status, hb_detail = parse_heartbeat_reply(parsed_hb[1])
                if hb_status != "done":
                    print("FAIL: Phan hoi HEARTBEAT thu %d khong hop le theo Q3: %r" % (i, parsed_hb[1]))
                    abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
                    return 1
            seq = get_next_p1_seq()
            last_sent_seq = seq
            record_p1_seq(seq)
            cmd_st = format_p1_cmd(seq, "STATUS")
            print("3. Kiem tra STATUS:", cmd_st)
            send_line(ser, cmd_st)
            rep = read_line(ser, args.timeout)
            print("   Nhan:", rep)
            parsed_st = parse_p1_reply(rep)
            if not parsed_st or not parsed_st[2] or parsed_st[0] != seq:
                print("FAIL: Phan hoi STATUS kiem tra het han loi hoac sai seq/checksum: %r" % rep)
                abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
                return 1
            st_dict = parse_status_tokens(parsed_st[1])
            if not st_dict or st_dict["state"] != "IDLE" or st_dict["laser"] != 0 or st_dict["remaining_ms"] != 0:
                print("FAIL: STATUS sau 5000 ms chua ve IDLE hoac laser != 0: %r" % (parsed_st[1] if parsed_st else rep))
                abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
                return 1
            return 0
        except (Exception, KeyboardInterrupt) as ex:
            if isinstance(ex, KeyboardInterrupt):
                print("\nNguoi dung ngat (Ctrl+C). Gui lenh tat khan cap...")
            else:
                print("\nLoi I/O trong phep thu laser timeout:", ex)
            if laser_might_be_on:
                abort_emergency(ser, args.timeout, last_seq=last_sent_seq)
            return 1
        finally:
            try:
                ser.close()
            except Exception:
                pass

    which_interlock = None
    if args.test_door:
        which_interlock = "door"
    elif args.test_estop:
        which_interlock = "estop"
    elif args.test_interlock:
        which_interlock = args.test_interlock

    if which_interlock:
        try:
            ser = open_serial(args.port, args.baud, args.timeout)
        except Exception as e:
            print("KHONG MO DUOC CONG", args.port, "-", e)
            return 3
        try:
            return run_test_interlock(ser, which_interlock, args.timeout, confirm_vom=args.confirm_vom_0v)
        except KeyboardInterrupt:
            print("\nNguoi dung ngat (Ctrl+C).")
            return 1
        except Exception as e:
            print("\nNgoai le trong phep thu lien dong:", e)
            return 1
        finally:
            try:
                ser.close()
            except Exception:
                pass


    if args.p1:
        try:
            ser = open_serial(args.port, args.baud, args.timeout)
        except Exception as e:
            print("KHONG MO DUOC CONG", args.port, "-", e)
            return 3
        try:
            time.sleep(0.5)
            ser.reset_input_buffer()
            ok_p1, err_p1 = run_p1_session(ser, args.timeout)
            return 0 if ok_p1 else 1
        except KeyboardInterrupt:
            print("\nNguoi dung ngat (Ctrl+C) trong khi chay --p1.")
            return 1
        except Exception as e:
            print("\nNgoai le trong khi chay --p1:", e)
            return 1
        finally:
            try:
                ser.close()
            except Exception:
                pass

    if args.count < 1:
        print("--count phai >= 1 (nhan duoc %s); PASS 0/0 khong co y nghia" % args.count)
        return 2

    session_id = args.session_id or datetime.now().strftime("ping_%Y%m%d_%H%M%S")
    out_dir = (REPO_ROOT / args.out / session_id).resolve()

    meta = {
        "session_id": session_id,
        "label": args.label,
        "note": args.note,
        "started_at": now_iso(),
        "port": args.port,
        "baud": args.baud,
        "count": args.count,
        "timeout_s": args.timeout,
        "interval_s": args.interval,
        "git": git_info(),
        "script": "pc/nucleo_ping.py",
        "firmware_dir": "firmware/stm32/NucleoPing",
    }

    print("Phien:", session_id, "cong:", args.port)
    # R06: ho so co truoc khi cham cong; tu choi neu thu muc da ton tai
    if not open_session_dir(out_dir, meta):
        print("Thu muc phien da ton tai, khong ghi de:", out_dir)
        return 2
    try:
        ser = open_serial(args.port, args.baud, args.timeout)
    except Exception as e:
        print("KHONG MO DUOC CONG", args.port, "-", e)
        print("Kiem tra: dung cong chua; Serial Monitor / CubeIDE / PuTTY co dang giu cong khong.")
        meta["finished_at"] = now_iso()
        meta["result"] = {"verdict": "FAIL", "reason": "khong mo duoc cong %s: %s: %s" % (args.port, type(e).__name__, e)}
        (out_dir / "session.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Ho so:", out_dir)
        return 3
    try:
        time.sleep(0.5)
        ser.reset_input_buffer()
        result, pairs = run_session(ser, args.count, args.timeout, args.interval,
                                    on_pair=lambda row: append_pair(out_dir, row))
    finally:
        try:
            ser.close()
        except Exception as e:  # cong da bien mat: dong loi cung khong duoc lam mat ho so
            print("Dong cong bao loi (bo qua):", e)
    meta["finished_at"] = now_iso()
    text = write_session(out_dir, meta, pairs, result)
    print()
    print("=== TONG KET (gui lai khoi nay) ===")
    print(text)
    print("Ho so:", out_dir)
    passed = result["count_ok"] == args.count and result["first_error"] is None
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
