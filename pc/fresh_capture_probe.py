#!/usr/bin/env python3
"""
pc/fresh_capture_probe.py - Cong cu tham do doc lap endpoint /capture_fresh tren ESP32-S3

Dac ta theo docs/design/S3_FRESH_CAPTURE.md va Quyet dinh D043:
- Kiem tra 5 header bat buoc: X-Frame-Id, X-Boot-Id, X-Timestamp, X-Request-Timestamp, X-Discarded-Frames.
- Kiem tra dinh dang usec (%06d, dung 6 chu so) va so sanh so nguyen t_frame > t_req.
- Kiem tra boot_id (dung 32 ky tu hex thuong) va phat hien reboot bo.
- Kiem tra tinh don dieu cua Frame ID (don luong: last_frame_id + 1, gap phai dung).
- Kiem tra tinh toan ven JPEG (SOI 0xFFD8, EOI 0xFFD9).
- Timeout ket noi/socket: 5.0 giay. Hạn tong tung luot: 10.0 giay.
- Luu bang chung ra thu muc output (raw JPEG, headers, summary.json), tu choi ghi de.
- Tich hop --selftest tu khoi chay mock va kiem tra toan dien cac kich ban.
"""

import argparse
import http.client
from http.server import HTTPServer
import io
import json
import os
import re
import secrets
import socket
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

HEX_32_RE = re.compile(r"^[0-9a-f]{32}$")
TIMESTAMP_RE = re.compile(r"^([0-9]+)\.([0-9]{6})$")
DISCARDED_RE = re.compile(r"^[0-9]+$")
FRAME_ID_RE = re.compile(r"^[0-9]+$")

UINT32_MAX = 4294967295
UINT64_MAX = 18446744073709551615


def parse_timestamp_us(ts_str):
    """Phan tich timestamp chuoi <sec>.<usec> thanh so nguyen micro giay.
    Yeu cau usec phai co dung 6 chu so va sec khong vuot qua UINT32_MAX.
    Tra ve (int_us, sec, usec) hoac gay ValueError.
    """
    m = TIMESTAMP_RE.match(ts_str.strip())
    if not m:
        raise ValueError(f"Timestamp '{ts_str}' khong dung dinh dang <sec>.<usec> 6 chu so")
    sec = int(m.group(1))
    if sec > UINT32_MAX:
        raise ValueError(f"Timestamp sec '{sec}' vuot qua UINT32_MAX ({UINT32_MAX})")
    usec = int(m.group(2))
    return sec * 1_000_000 + usec, sec, usec


def validate_jpeg(data):
    """Kiem tra tinh toan ven co ban cua anh JPEG."""
    if len(data) < 4:
        return False, "Du lieu qua ngan (< 4 bytes)"
    if data[0] != 0xFF or data[1] != 0xD8:
        return False, f"Thieu SOI 0xFFD8 (dau byte: {data[:2].hex()})"
    if data[-2] != 0xFF or data[-1] != 0xD9:
        return False, f"Thieu EOI 0xFFD9 (duoi byte: {data[-2:].hex()})"
    if HAS_PIL:
        try:
            im = Image.open(io.BytesIO(data))
            im.verify()
        except Exception as e:
            return False, f"Pillow verify that bai: {e}"
    return True, "OK"


class TrackedHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        super().connect()
        self.active_sock = self.sock


class FreshCaptureClient:
    def __init__(self, host, port=80, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.first_boot_id = None
        self.last_frame_id = None
        self.last_frame_ts_us = None

    def capture_fresh(self, deadline=10.0):
        """Thuc hien 1 request GET /capture_fresh va kiem tra nghiem ngat.
        Co watchdog timer va cap nhat socket timeout dong theo deadline con lai de unblock ngay khi het han.
        """
        t_start = time.monotonic()
        t_start_perf = time.perf_counter()
        conn = None
        timed_out = [False]
        cleanup_time_ms = [0.0]
        t_abort_decide = [0.0]

        def abort_watchdog():
            timed_out[0] = True
            t_abort_decide[0] = time.monotonic()
            s = getattr(conn, "active_sock", None) or getattr(conn, "sock", None)
            if s:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    s.close()
                except Exception:
                    pass
            cleanup_time_ms[0] = (time.monotonic() - t_abort_decide[0]) * 1000.0

        timer = threading.Timer(deadline, abort_watchdog)
        timer.daemon = True
        timer.start()

        def remaining_sec():
            return deadline - (time.monotonic() - t_start)

        current_sock_to = [max(0.001, min(self.timeout, deadline))]

        def update_sock_timeout(connection):
            rem = remaining_sec()
            if timed_out[0] or rem <= 0:
                timed_out[0] = True
                raise TimeoutError(f"TIMEOUT_TOTAL_DEADLINE: Request vuot qua deadline tong {deadline:.1f}s (cleanup mat {cleanup_time_ms[0]:.1f}ms)")
            to_val = max(0.001, min(self.timeout, rem))
            current_sock_to[0] = to_val
            s = getattr(connection, "active_sock", None) or getattr(connection, "sock", None)
            if s:
                try:
                    s.settimeout(to_val)
                except Exception:
                    pass
            return to_val

        status = None
        reason = None
        raw_headers = []
        raw_headers_dict = {}
        http_status_line = None
        body = b""
        partial_body = b""
        body_chunks = []

        try:
            init_to = max(0.001, min(self.timeout, remaining_sec()))
            current_sock_to[0] = init_to
            conn = TrackedHTTPConnection(self.host, self.port, timeout=init_to)
            conn.request("GET", "/capture_fresh", headers={"Connection": "close"})

            update_sock_timeout(conn)
            resp = conn.getresponse()
            status = resp.status
            reason = resp.reason
            http_status_line = f"HTTP/{resp.version/10:.1f} {status} {reason}" if getattr(resp, "version", None) else f"HTTP/1.1 {status} {reason}"
            raw_headers = resp.getheaders()
            raw_headers_dict = dict(raw_headers)

            read_fn = getattr(resp, "read1", resp.read)
            while True:
                update_sock_timeout(conn)
                chunk = read_fn(4096)
                if not chunk:
                    break
                body_chunks.append(chunk)
            body = b"".join(body_chunks)

            rtt_ms = (time.monotonic() - t_start) * 1000.0

            res = {
                "status": status,
                "reason": reason,
                "rtt_ms": rtt_ms,
                "body": body,
                "body_len": len(body),
                "headers": raw_headers_dict,
                "raw_headers_list": raw_headers,
                "http_status_line": http_status_line,
                "error": None,
                "frame_id": None,
                "boot_id": None,
                "t_frame_us": None,
                "t_req_us": None,
                "discarded": None,
                "fresh": False,
                "jpeg_valid": False,
            }

            if timed_out[0] or (time.monotonic() - t_start) >= deadline:
                res["error"] = f"TIMEOUT_TOTAL_DEADLINE: Request vuot qua deadline tong {deadline:.1f}s (cleanup mat {cleanup_time_ms[0]:.1f}ms)"
                return res

            if status != 200:
                res["error"] = f"HTTP {status}: {body.decode('utf-8', errors='replace').strip()}"
                return res

            # Dem so lan xuat hien cua tung header (chong header lap)
            header_counts = {}
            for k, v in raw_headers:
                kl = k.lower()
                header_counts[kl] = header_counts.get(kl, 0) + 1

            required = ["x-frame-id", "x-boot-id", "x-timestamp", "x-request-timestamp", "x-discarded-frames"]
            for req_h in required:
                cnt = header_counts.get(req_h, 0)
                if cnt == 0:
                    res["error"] = f"Thieu header bat buoc: {req_h}"
                    return res
                elif cnt > 1:
                    res["error"] = f"Header bat buoc bi lap: {req_h} ({cnt} lan)"
                    return res

            headers_lower = {k.lower(): v for k, v in raw_headers}

            # 1. X-Boot-Id
            boot_id = headers_lower["x-boot-id"].strip()
            if not HEX_32_RE.match(boot_id):
                res["error"] = f"X-Boot-Id khong hop le (phai la 32 hex thuong): '{boot_id}'"
                return res
            res["boot_id"] = boot_id

            # Kiem tra reboot detection
            if self.first_boot_id is None:
                self.first_boot_id = boot_id
            elif boot_id != self.first_boot_id:
                res["error"] = f"CAMERA_REBOOT: Boot ID thay doi (cu: {self.first_boot_id}, moi: {boot_id})"
                return res

            # 2. X-Frame-Id
            fid_str = headers_lower["x-frame-id"].strip()
            if not FRAME_ID_RE.match(fid_str):
                res["error"] = f"X-Frame-Id khong phai so nguyen duong hop le: '{fid_str}'"
                return res
            frame_id = int(fid_str)
            if frame_id < 1 or frame_id > UINT64_MAX:
                res["error"] = f"X-Frame-Id ngoai mien [1, UINT64_MAX]: {frame_id}"
                return res
            res["frame_id"] = frame_id

            if self.last_frame_id is not None:
                if frame_id <= self.last_frame_id:
                    res["error"] = f"X-Frame-Id lui hoac trung trong cung Boot ID (truoc: {self.last_frame_id}, nay: {frame_id})"
                    return res
                if frame_id > self.last_frame_id + 1:
                    res["error"] = f"FRAME_ID_GAP: Frame ID bi nhay coc (truoc: {self.last_frame_id}, nay: {frame_id})"
                    return res

            # 3. Timestamps
            try:
                t_frame_us, _, _ = parse_timestamp_us(headers_lower["x-timestamp"])
                t_req_us, _, _ = parse_timestamp_us(headers_lower["x-request-timestamp"])
            except ValueError as e:
                res["error"] = f"Loi parse timestamp: {e}"
                return res
            res["t_frame_us"] = t_frame_us
            res["t_req_us"] = t_req_us

            if t_frame_us <= t_req_us:
                res["error"] = f"STALE_FRAME: t_frame ({t_frame_us} us) <= t_req ({t_req_us} us)"
                return res
            res["fresh"] = True

            if self.last_frame_ts_us is not None and t_frame_us <= self.last_frame_ts_us:
                res["error"] = f"X-Timestamp khong tang don dieu (truoc: {self.last_frame_ts_us}, nay: {t_frame_us})"
                return res

            # 4. X-Discarded-Frames
            disc_str = headers_lower["x-discarded-frames"].strip()
            if not DISCARDED_RE.match(disc_str):
                res["error"] = f"X-Discarded-Frames khong hop le: '{disc_str}'"
                return res
            discarded = int(disc_str)
            if discarded < 0 or discarded > 4:
                res["error"] = f"X-Discarded-Frames ngoai mien [0, 4]: {discarded}"
                return res
            res["discarded"] = discarded

            # 5. JPEG validation
            ok_jpg, msg_jpg = validate_jpeg(body)
            if not ok_jpg:
                res["error"] = f"JPEG khong hop le: {msg_jpg}"
                return res
            res["jpeg_valid"] = True

            # Cap nhat trang thai hop le
            self.last_frame_id = frame_id
            self.last_frame_ts_us = t_frame_us
            return res

        except Exception as e:
            t_now = time.monotonic()
            elapsed_perf = time.perf_counter() - t_start_perf
            elapsed_mono = t_now - t_start
            rtt_ms = elapsed_mono * 1000.0
            if getattr(e, "partial", None):
                body_chunks.append(e.partial)
            captured_body = b"".join(body_chunks) if body_chunks else (partial_body if partial_body else body)
            is_sock_timeout = isinstance(e, (socket.timeout, TimeoutError))
            is_shrunk_sock_to = is_sock_timeout and (current_sock_to[0] < self.timeout)
            if is_shrunk_sock_to and not timed_out[0] and (elapsed_mono < deadline and elapsed_perf < deadline):
                remain = deadline - elapsed_perf
                if 0 < remain <= 0.05:
                    t_target_perf = t_start_perf + deadline
                    for _ in range(10):
                        t_rem = t_target_perf - time.perf_counter()
                        if t_rem <= 0:
                            break
                        time.sleep(t_rem)
                    elapsed_mono = time.monotonic() - t_start
                    elapsed_perf = time.perf_counter() - t_start_perf
                    rtt_ms = elapsed_mono * 1000.0

            is_total_deadline = (
                timed_out[0]
                or elapsed_mono >= deadline
                or elapsed_perf >= deadline
            )
            if is_total_deadline:
                err_msg = f"TIMEOUT_TOTAL_DEADLINE: Request vuot qua deadline tong {deadline:.1f}s (cleanup mat {cleanup_time_ms[0]:.1f}ms)"
            elif is_sock_timeout:
                err_msg = f"TIMEOUT_SOCKET: Socket timeout ({self.timeout:.1f}s) truoc khi het deadline tong {deadline:.1f}s"
            else:
                err_msg = f"Socket/Network error: {e}"
            return {
                "status": status,
                "reason": reason,
                "rtt_ms": rtt_ms,
                "body": captured_body,
                "body_len": len(captured_body),
                "headers": raw_headers_dict,
                "raw_headers_list": raw_headers,
                "http_status_line": http_status_line,
                "error": err_msg,
                "frame_id": None,
                "boot_id": None,
                "t_frame_us": None,
                "t_req_us": None,
                "discarded": None,
                "fresh": False,
                "jpeg_valid": False,
            }
        finally:
            timer.cancel()
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


def run_probe(host, port, count, interval_sec, per_request_deadline_sec=10.0, output_dir=None, commit_sha=None, build_sha=None):
    """Chay chuoi probe, luu bang chung ra thu muc output va in ket qua."""
    print(f"=== FRESH CAPTURE PROBE ===")
    print(f"Target: http://{host}:{port}/capture_fresh | Count: {count} | Interval: {interval_sec}s | Deadline/request: {per_request_deadline_sec}s")

    out_path = None
    if output_dir:
        out_path = Path(output_dir)
        if out_path.exists():
            print(f"Loi: Thu muc output da ton tai, tu choi de tranh ghi de bang chung: {output_dir}")
            return 1
        out_path.mkdir(parents=True, exist_ok=False)
    else:
        # Neu khong truyen, luon tao thu muc luu bang chung theo timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        if Path("docs/logs").exists():
            candidate = Path("docs/logs") / f"probe_{timestamp_str}"
        else:
            candidate = Path(f"probe_{timestamp_str}")
        out_path = candidate
        out_path.mkdir(parents=True, exist_ok=False)

    if out_path:
        print(f"Luu bang chung vao: {out_path}")

    client = FreshCaptureClient(host, port, timeout=5.0)
    results = []
    failed = False
    start_time_iso = datetime.now().isoformat()

    for i in range(1, count + 1):
        res = client.capture_fresh(deadline=per_request_deadline_sec)
        results.append(res)

        status_str = f"HTTP {res['status']}" if res['status'] else "ERR"
        rtt_str = f"{res['rtt_ms']:.1f}ms"

        # Luu file bang chung tung luot neu co thu muc output
        if out_path:
            raw_ext = "jpg" if res.get("jpeg_valid") else "bin"
            raw_file_name = f"frame_{i:04d}.{raw_ext}"
            raw_file_path = out_path / raw_file_name
            with open(raw_file_path, "wb") as f:
                f.write(res.get("body", b""))

            headers_file_path = out_path / f"headers_{i:04d}.txt"
            with open(headers_file_path, "w", encoding="utf-8") as f:
                status_line = res.get("http_status_line")
                if status_line:
                    f.write(f"{status_line}\n")
                if res.get("raw_headers_list"):
                    for hk, hv in res["raw_headers_list"]:
                        f.write(f"{hk}: {hv}\n")
                else:
                    for hk, hv in res.get("headers", {}).items():
                        f.write(f"{hk}: {hv}\n")

        if res["error"]:
            print(f"[{i}/{count}] {status_str} RTT={rtt_str} -> FAIL: {res['error']}")
            failed = True
            break
        else:
            print(f"[{i}/{count}] {status_str} RTT={rtt_str} ID={res['frame_id']} Boot={res['boot_id'][:8]}... Stale={res['discarded']} Bytes={res['body_len']} -> OK")

        if i < count and interval_sec > 0:
            time.sleep(interval_sec)

    print("\n--- TONG KET ---")
    total_requests = len(results)
    success_requests = sum(1 for r in results if r["error"] is None)
    print(f"So request da gui: {total_requests}/{count}")
    print(f"Thanh cong: {success_requests}/{total_requests}")

    verdict = "PASS" if (not failed and success_requests == count) else "INVALID"
    if results:
        rtts = [r["rtt_ms"] for r in results if r["rtt_ms"] is not None]
        if rtts:
            print(f"RTT min/avg/max: {min(rtts):.1f} / {sum(rtts)/len(rtts):.1f} / {max(rtts):.1f} ms")
    print(f"Ket luan: {verdict}")

    if out_path:
        summary = {
            "verdict": verdict,
            "host": host,
            "port": port,
            "requested_count": count,
            "total_sent": total_requests,
            "success_count": success_requests,
            "interval_sec": interval_sec,
            "per_request_deadline_sec": per_request_deadline_sec,
            "start_time": start_time_iso,
            "end_time": datetime.now().isoformat(),
            "commit_sha": commit_sha,
            "build_sha": build_sha,
            "error": results[-1]["error"] if failed and results else None,
            "frames": [
                {
                    "index": idx + 1,
                    "status": r["status"],
                    "rtt_ms": r["rtt_ms"],
                    "frame_id": r["frame_id"],
                    "boot_id": r["boot_id"],
                    "t_frame_us": r["t_frame_us"],
                    "t_req_us": r["t_req_us"],
                    "discarded": r["discarded"],
                    "body_len": r["body_len"],
                    "error": r["error"],
                    "valid": r["error"] is None
                }
                for idx, r in enumerate(results)
            ]
        }
        with open(out_path / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Da ghi bao cao tom tat: {out_path / 'summary.json'}")

    return 0 if verdict == "PASS" else 1


def run_selftest():
    """Chay 10 kich ban selftest noi bo bang cach khoi chay FakeCameraServer."""
    import tempfile
    here = Path(__file__).resolve().parent
    root = here.parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from mock_camera import H, apply_options, STATE
    except ImportError:
        from pc.mock_camera import H, apply_options, STATE

    print("=== BAT DAU SELFTEST fresh_capture_probe.py ===")

    class MockOpts:
        def __init__(self, **kwargs):
            self.reset_at = 0
            self.fail_frames = ""
            self.drop_ts_frames = ""
            self.lowercase_headers = False
            self.status_mode = "ok"
            self.status_fail_after = 0
            self.ignore_controls = ""
            self.fail_controls = ""
            self.drift_registers = ""
            self.drift_after = 0
            self.status_drop_fields = ""
            self.control_drift_fields = ""
            self.control_drift_after = 0
            self.registers = ""
            self.status_fail_at_count = 0
            self.wb_registers_stuck = False
            self.fresh_stream_busy = False
            self.fresh_capture_busy = False
            self.fresh_no_buffer = False
            self.fresh_timeout_stale = False
            self.fresh_unsupported_format = False
            self.fresh_overflow = False
            self.fresh_discard_frames = 0
            self.fresh_reboot_at = 0
            self.fresh_corrupt_jpeg = False
            self.fresh_drop_headers = ""
            for k, v in kwargs.items():
                setattr(self, k, v)

    def start_mock(port, **kwargs):
        apply_options(MockOpts(**kwargs))
        srv = HTTPServer(("127.0.0.1", port), H)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        return srv

    with tempfile.TemporaryDirectory() as td:
        # Kich ban 1: 20 capture thanh cong lien tiep co luu bang chung
        print("\n--- Selftest Kich ban 1: 20 capture thanh cong lien tiep ---")
        port1 = 8991
        srv1 = start_mock(port1)
        out_k1 = Path(td) / "k1_out"
        ret1 = run_probe("127.0.0.1", port1, count=20, interval_sec=0.01, per_request_deadline_sec=5.0, output_dir=str(out_k1))
        srv1.shutdown()
        assert ret1 == 0, f"Kich ban 1 that bai, ret={ret1}"
        assert (out_k1 / "summary.json").exists(), "Thieu summary.json o Kich ban 1"
        assert (out_k1 / "frame_0020.jpg").exists(), "Thieu frame_0020.jpg o Kich ban 1"
        print("-> PASS Kich ban 1")

        # Kich ban 2: Stale frame handling (discarded = 2)
        print("\n--- Selftest Kich ban 2: Stale frame handling (discarded = 2) ---")
        port2 = 8992
        srv2 = start_mock(port2, fresh_discard_frames=2)
        client2 = FreshCaptureClient("127.0.0.1", port2)
        r2 = client2.capture_fresh()
        srv2.shutdown()
        assert r2["error"] is None, f"Kich ban 2 that bai: {r2['error']}"
        assert r2["discarded"] == 2, f"Kich ban 2 sai discarded: {r2['discarded']}"
        assert r2["fresh"] is True, "Kich ban 2 khong fresh"
        print("-> PASS Kich ban 2")

        # Kich ban 3: Reboot detection (doi Boot ID)
        print("\n--- Selftest Kich ban 3: Reboot detection (doi Boot ID) ---")
        port3 = 8993
        srv3 = start_mock(port3, fresh_reboot_at=2)
        client3 = FreshCaptureClient("127.0.0.1", port3)
        r3_1 = client3.capture_fresh()
        assert r3_1["error"] is None, f"Kich ban 3 luot 1 that bai: {r3_1}"
        r3_2 = client3.capture_fresh()
        srv3.shutdown()
        assert r3_2["error"] is not None and "CAMERA_REBOOT" in r3_2["error"], f"Kich ban 3 luot 2 that bai: {r3_2}"
        print(f"-> PASS Kich ban 3 (Bat duoc {r3_2['error']})")

        # Kich ban 4: Thieu header bat buoc
        print("\n--- Selftest Kich ban 4: Thieu header bat buoc ---")
        port4 = 8994
        srv4 = start_mock(port4, fresh_drop_headers="X-Boot-Id")
        client4 = FreshCaptureClient("127.0.0.1", port4)
        r4 = client4.capture_fresh()
        srv4.shutdown()
        assert r4["error"] is not None and "Thieu header bat buoc" in r4["error"], f"Kich ban 4 that bai: {r4}"
        print(f"-> PASS Kich ban 4 (Bat duoc {r4['error']})")

        # Kich ban 5: 503 ERROR CAMERA_BUSY_STREAM
        print("\n--- Selftest Kich ban 5: 503 ERROR CAMERA_BUSY_STREAM ---")
        port5 = 8995
        srv5 = start_mock(port5, fresh_stream_busy=True)
        client5 = FreshCaptureClient("127.0.0.1", port5)
        r5 = client5.capture_fresh()
        srv5.shutdown()
        assert r5["status"] == 503 and "CAMERA_BUSY_STREAM" in r5["error"], f"Kich ban 5 that bai: {r5}"
        print(f"-> PASS Kich ban 5 (Bat duoc {r5['error']})")

        # Kich ban 6: 503 ERROR CAMERA_BUSY_CAPTURE
        print("\n--- Selftest Kich ban 6: 503 ERROR CAMERA_BUSY_CAPTURE ---")
        port6 = 8996
        srv6 = start_mock(port6, fresh_capture_busy=True)
        client6 = FreshCaptureClient("127.0.0.1", port6)
        r6 = client6.capture_fresh()
        srv6.shutdown()
        assert r6["status"] == 503 and "CAMERA_BUSY_CAPTURE" in r6["error"], f"Kich ban 6 that bai: {r6}"
        print(f"-> PASS Kich ban 6 (Bat duoc {r6['error']})")

        # Kich ban 7: 503 ERROR CAMERA_NO_BUFFER
        print("\n--- Selftest Kich ban 7: 503 ERROR CAMERA_NO_BUFFER ---")
        port7 = 8997
        srv7 = start_mock(port7, fresh_no_buffer=True)
        client7 = FreshCaptureClient("127.0.0.1", port7)
        r7 = client7.capture_fresh()
        srv7.shutdown()
        assert r7["status"] == 503 and "CAMERA_NO_BUFFER" in r7["error"], f"Kich ban 7 that bai: {r7}"
        print(f"-> PASS Kich ban 7 (Bat duoc {r7['error']})")

        # Kich ban 8: 503 ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME
        print("\n--- Selftest Kich ban 8: 503 ERROR CAMERA_TIMEOUT_NO_FRESH_FRAME ---")
        port8 = 8998
        srv8 = start_mock(port8, fresh_timeout_stale=True)
        client8 = FreshCaptureClient("127.0.0.1", port8)
        r8 = client8.capture_fresh()
        srv8.shutdown()
        assert r8["status"] == 503 and "CAMERA_TIMEOUT_NO_FRESH_FRAME" in r8["error"], f"Kich ban 8 that bai: {r8}"
        print(f"-> PASS Kich ban 8 (Bat duoc {r8['error']})")

        # Kich ban 9: 500 ERROR FRAME_ID_OVERFLOW
        print("\n--- Selftest Kich ban 9: 500 ERROR FRAME_ID_OVERFLOW ---")
        port9 = 8999
        srv9 = start_mock(port9, fresh_overflow=True)
        client9 = FreshCaptureClient("127.0.0.1", port9)
        r9 = client9.capture_fresh()
        srv9.shutdown()
        assert r9["status"] == 500 and "FRAME_ID_OVERFLOW" in r9["error"], f"Kich ban 9 that bai: {r9}"
        print(f"-> PASS Kich ban 9 (Bat duoc {r9['error']})")

        # Kich ban 10: Corrupt truncated JPEG
        print("\n--- Selftest Kich ban 10: Corrupt truncated JPEG ---")
        port10 = 9000
        srv10 = start_mock(port10, fresh_corrupt_jpeg=True)
        client10 = FreshCaptureClient("127.0.0.1", port10)
        r10 = client10.capture_fresh()
        srv10.shutdown()
        assert r10["error"] is not None and "JPEG khong hop le" in r10["error"], f"Kich ban 10 that bai: {r10}"
        print(f"-> PASS Kich ban 10 (Bat duoc {r10['error']})")

    print("\n=== TOAN BO 10 KICH BAN SELFTEST DA PASS THANH CONG ===")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Probe kiem tra /capture_fresh tren ESP32-S3 hoac Mock")
    ap.add_argument("--host", default="127.0.0.1", help="Dia chi IP bo ESP32-S3 hoac mock")
    ap.add_argument("--port", type=int, default=80, help="Cong HTTP (mac dinh 80 cho ESP32-S3, 8081 cho mock)")
    ap.add_argument("--count", type=int, default=10, help="So luong capture can thu (mac dinh 10)")
    ap.add_argument("--interval", type=float, default=0.2, help="Khoang nghi giua cac request (giay)")
    ap.add_argument("--deadline", type=float, default=10.0, help="Han tong tung luot request (giay, mac dinh 10.0s)")
    ap.add_argument("--output", "--out", "--out-dir", dest="output_dir", default=None,
                    help="Thu muc luu bang chung doc quyen (tu choi neu da ton tai)")
    ap.add_argument("--commit", default=None, help="Git commit SHA nguoi chay khai bao")
    ap.add_argument("--build-sha", default=None, help="Binary build SHA nguoi chay khai bao")
    ap.add_argument("--selftest", action="store_true", help="Chay selftest noi bo khong can thiet bi")

    args = ap.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    ret = run_probe(
        args.host,
        args.port,
        args.count,
        args.interval,
        per_request_deadline_sec=args.deadline,
        output_dir=args.output_dir,
        commit_sha=args.commit,
        build_sha=args.build_sha
    )
    sys.exit(ret)


if __name__ == "__main__":
    main()
