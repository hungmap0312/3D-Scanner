#!/usr/bin/env python3
"""Tester C5a Vong 2 - kiem doc lap ho so Q3/Q4 `/capture_fresh` (handoff/2026-09-21_c5a-s3-fresh-capture).

Vong 2 chi la ho so thiet ke, khong co ma san pham. Test nay kiem phan MAY KIEM DUOC cua D1-D5
(01_PLAN.md Vong 2 muc 5); phan doc noi dung con lai la checklist thu cong trong 03_TEST.md.

- D1: ancestry, pham vi diff tu base, firmware/ va pc/ khong doi tai B.
- D2: bam lai thu vien/header driver dang cai; tu phan tich ma may `libespressif__esp32-camera.a`
      (xtensa readelf/objdump cua core 3.3.11) de biet ham nao gan timestamp va `esp_camera_fb_get()`
      chan toi da bao lau; doi chieu voi loi ho so ghi.
- D3: dinh dang header thoi gian cua firmware dang co va quy tac phan tich cua ho so.
- D5: quy tac tang Frame ID giua ho so Q3, D041 va 02_BUILD.
- D6 (Tester Vong 4, 01_PLAN Vong 3 muc 5): R01 chuoi nguon goc driver (index -> zip -> versions.txt ->
      manifest lib-builder -> revision esp32-camera) va dau van tay ma may; doi chieu trich dan nguon/ma may
      cua bang muc 2.2; cau dan xuat ve doi so 4000 tick; R02 cau C2; R03 so sach va tai hien so lieu test cu;
      R05 mo hinh buffer neo vao nguon (D6.17-D6.18); R06 dinh chinh duong dan header (D6.19).
      Can mang de clone nguon (hoac C5A_SRC tro toi thu muc co san esp32-camera/ va lib-builder/).

Khong mo COM/HTTP, khong nap bo, khong sua tep san pham.

Chay tu goc repo (Git Bash):
  .venv/Scripts/python.exe pc/test_c5a_contract.py
C5A_PHASE: q6 (mac dinh; ma Q6, 01_PLAN Vong 5, base e92867e) hoac q3 (ho so Q3/Q4 Vong 2-4, base 64d67a8).
Moc mac dinh q6 (Tester Vong 23): C5A_B cc16b13, C5A_B_PREV 502ea45 (B Coder vong truoc), C5A_H_PREV f1b7211
(H Tester Vong 22), C5A_P d3b2d20 (ke hoach Vong 7/8), C5A_BASE e92867e. Vong dau sau P (H truoc nam truoc P): luot Coder
la P..B; tu vong sua thu 2 (P nam truoc H truoc): luot Coder la H truoc..B. Ke hoach moi nhat tai P la Vong 6 thi
luot Coder (P..B hoac H truoc..B) kiem theo danh sach trang Vong 6 muc 3 (hep hon Vong 5); ke hoach Vong 7/8 theo
danh sach trang goi A Vong 7 muc 3. Moc q3: B 1a26df9, B_PREV 1b3b239, H_PREV 187cdf9, P 2ed9a75,
BASE 64d67a8. C5A_SRC (ban clone nguon co san; bo trong thi tu clone vao thu muc tam),
ARDUINO15 (mac dinh %LOCALAPPDATA%/Arduino15). Thoat 0 khi khong co kiem FAIL.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PHASE = os.environ.get("C5A_PHASE", "q6")
Q3 = PHASE == "q3"   # q3: chang ho so (firmware bat bien); q6: chang ma (01_PLAN Vong 5)
_DEF = {True: ("64d67a84572ffbfdf559d8dc5496b89106d99098", "1a26df9c4f896fad6e286f2e1c02b4c6485ee547",
               "1b3b239a22dba68ea0899d746be53d576365e788", "187cdf90ce2837a82e6d5accdf13dd863e7fd7f3",
               "2ed9a75cc5d8a93b0811fb04d01fe64d8d3cfa80"),
        False: ("e92867eecf5eaad308ab1a222069de07d964e6fb", "5092910b23dbffeb50eed751fca362f96efb2d9b",
                "6f6948f868c007915217bb26c06dfc63bea42c0f", "4f6123e6eaf1434adb22cbe57e3672e797208304",
                "7ce9475033130d8288b2e030e5e65bb844155f2d")}[Q3]
R03_SRC = "1a26df9c4f896fad6e286f2e1c02b4c6485ee547"   # Q6: vong 02_BUILD chua doi chieu R03 (B cuoi chang Q3)
BASE = os.environ.get("C5A_BASE", _DEF[0])
B = os.environ.get("C5A_B", _DEF[1])
# ban 02_BUILD.md cua lan ban giao Coder gan nhat (01_PLAN Vong 3 muc 5: kiem bao toan toan ban, khong chi Vong 1)
B_PREV = os.environ.get("C5A_B_PREV", _DEF[2])
A15 = Path(os.environ.get("ARDUINO15", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Arduino15")))
LIBS = A15 / "packages/esp32/tools/esp32s3-libs/3.3.11"
XT = A15 / "packages/esp32/tools/esp-x32/2601/bin"
CAM_A = LIBS / "lib/libespressif__esp32-camera.a"
CAM_H = LIBS / "include/espressif__esp32-camera/driver/include/esp_camera.h"
DOC = "docs/design/S3_FRESH_CAPTURE.md"
SKETCH = "firmware/esp32s3/CameraWebServerTest/"
# danh sach trang: Q3 (01_PLAN Vong 2-3) / Q6 (01_PLAN Vong 5 muc 3)
WHITELIST = ({"docs/design/S3_FRESH_CAPTURE.md", "docs/design/SCAN_SESSION.md", "DECISIONS.md"} if Q3 else
             {SKETCH + "app_httpd.cpp", SKETCH + "CameraWebServerTest.ino", SKETCH + "fresh_capture_core.h",
              "pc/fresh_capture_probe.py", "pc/mock_camera.py", "docs/design/S3_FRESH_CAPTURE.md",
              "docs/design/SCAN_SESSION.md", "firmware/esp32s3/README.md", "pc/README.md",
              "docs/procedures/quy-trinh-c5a-fresh-capture.md"})
RECORDS = {"STATUS.md", "docs/SESSION_LOG.md", "ENVIRONMENT.md"}
HANDOFF = "handoff/2026-09-21_c5a-s3-fresh-capture/"
TESTER_FILES = {"pc/test_c5a_contract.py", "pc/test_c5a_runtime.py", "pc/test_c5a_evidence.py"}   # evidence: Vong 24 (01_PLAN Vong 7 muc 3)
# log Tester + bang chung do bo do Tester khai va commit (03_TEST Vong 17: phien c5a_q6_*; Vong 18: nguon R09 c5a-r09-*)
TESTER_LOG_PREFIX = ("docs/logs/test-c5a-", "docs/logs/c5a_q6_", "docs/logs/c5a-r09-")
TESTER_DIRS = (SKETCH + "test/",)   # harness C++ cua Tester (01_PLAN Vong 5 muc 5)
H_PREV = os.environ.get("C5A_H_PREV", _DEF[3])  # H cua vong Tester truoc
SRC = os.environ.get("C5A_SRC", "")
CAM_GIT = "https://github.com/espressif/esp32-camera.git"
LB_GIT = "https://github.com/espressif/esp32-arduino-lib-builder.git"
INDEX = A15 / "package_esp32_index.json"
ZIP = A15 / "staging/packages/esp32s3-libs-3.3.11.zip"
REVIEW_SHA = "55ba2f6f2105e877cd9adc9fd2cba794746c82a96b08c5de9e4d1da42e2ed92a"  # 04_REVIEW.md, 01_PLAN Vong 3 muc 7
# ban 04_REVIEW.md lich su: (commit luu, SHA-256 dung luc luu) - Vong 1 (01_PLAN Vong 3 muc 7), Vong 2 (03_TEST Vong 7-9)
REVIEW_HIST = (("08564f1894d448a29ff46c442578e55448e2bafe", REVIEW_SHA),
               ("7487c18141acc56972dcf2ec8e8eb7ab371dc2ba", "4507b1f81bc51381718e51d92b86f18da4b28516d59417489b46a96b9dad5563"))
# P: commit chuan bi (luu bao cao Reviewer/ke hoach/nhat ky) truoc B moi - 01_PLAN Vong 4 muc 4 buoc 1
P = os.environ.get("C5A_P", _DEF[4])
# P..B: Vong 4 chi ban giao lai; Vong 5 = danh sach trang + ho so Coder (01_PLAN Vong 5 muc 3)
CODER_TURN = ({HANDOFF + "02_BUILD.md", "STATUS.md", "docs/SESSION_LOG.md"} if Q3 else
              WHITELIST | {HANDOFF + "02_BUILD.md", "STATUS.md", "docs/SESSION_LOG.md", "DECISIONS.md", "ENVIRONMENT.md"})
PREP_FILES = {HANDOFF + "04_REVIEW.md", HANDOFF + "01_PLAN.md", "STATUS.md", "docs/SESSION_LOG.md"}  # H truoc..P
# 01_PLAN Vong 6 muc 3: luot sua chi 4 tep san pham/thiet ke + ho so Coder (khong .ino, probe, mock, README)
CODER_TURN_V6 = {SKETCH + "app_httpd.cpp", "docs/design/S3_FRESH_CAPTURE.md", "docs/design/SCAN_SESSION.md",
                 "docs/procedures/quy-trinh-c5a-fresh-capture.md", HANDOFF + "02_BUILD.md", "STATUS.md",
                 "docs/SESSION_LOG.md", "DECISIONS.md", "ENVIRONMENT.md"}
# 01_PLAN Vong 7 muc 3 (giu o Vong 8): goi A chi probe (R12), Q3, quy trinh, pc/README + ho so Coder
# (Vong 23) + log tu kiem cua Coder docs/logs/coder-c5a-* (01_PLAN Vong 7 muc 3 "Co the them log tu kiem moi trong docs/logs/")
CODER_TURN_V7 = {"pc/fresh_capture_probe.py", "docs/design/S3_FRESH_CAPTURE.md", "docs/procedures/quy-trinh-c5a-fresh-capture.md",
                 "pc/README.md", HANDOFF + "02_BUILD.md", "STATUS.md", "docs/SESSION_LOG.md", "DECISIONS.md", "ENVIRONMENT.md"}
# 01_PLAN Vong 9 muc 3: luot sua R14/R15 chi probe + thiet ke S3 + ho so Coder (02_BUILD, STATUS, SESSION_LOG) + log tu kiem
CODER_TURN_V9 = {"pc/fresh_capture_probe.py", "docs/design/S3_FRESH_CAPTURE.md", HANDOFF + "02_BUILD.md", "STATUS.md",
                 "docs/SESSION_LOG.md"}

RESULTS = []


def is_tester(x):
    return x in TESTER_FILES or x.startswith(TESTER_LOG_PREFIX) or x.startswith(TESTER_DIRS)


def check(cid, ok, title, detail=""):
    tag = "PASS" if ok else "FAIL"
    RESULTS.append((cid, tag))
    print("  [%s] %s %s%s" % (tag, cid, title, ("  | " + detail) if detail else ""))
    return ok


def note(cid, title, detail=""):
    RESULTS.append((cid, "NOTE"))
    print("  [NOTE] %s %s%s" % (cid, title, ("  | " + detail) if detail else ""))


def git(*args):
    return subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True, text=True, encoding="utf-8")


def at_b(path):
    """Noi dung tep tai commit B (khong doc cay lam viec, de ket qua gan dung voi B)."""
    r = git("show", "%s:%s" % (B, path))
    return r.stdout if r.returncode == 0 else ""


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tool(name):
    exe = XT / (name + ".exe")
    return exe if exe.exists() else XT / name


def d1():
    print("---- D1 cong/pham vi (B = %s, base = %s)" % (B[:12], BASE[:12]))
    r = git("merge-base", "--is-ancestor", BASE, B)
    check("D1.1", r.returncode == 0, "base la to tien cua B")
    names = [x for x in git("diff", "--name-only", "%s..%s" % (BASE, B)).stdout.split() if x]
    # log tu kiem cua Coder docs/logs/coder-c5a-* duoc phep tu ke hoach Vong 7 muc 3
    extra = [x for x in names if x not in WHITELIST | RECORDS | {"DECISIONS.md"} and not is_tester(x) and not x.startswith(HANDOFF)
             and not (not Q3 and x.startswith("docs/logs/coder-c5a-"))]
    check("D1.2", not extra, "diff base..B chi gom danh sach trang %s + ho so duoc phep + handoff C5a + tep/log Tester da khai"
          % ("Vong 2" if Q3 else "Vong 5 (Q6)"),
          "%d tep; ngoai pham vi: %s" % (len(names), extra))
    fw = [x for x in git("diff", "--name-only", "%s..%s" % (BASE, B), "--", "firmware", "pc").stdout.split()
          if x and not is_tester(x) and (Q3 or x not in WHITELIST)]
    check("D1.3", not fw, "firmware/ va pc/ khong doi tu base toi B (tru tep test Tester da khai)" if Q3 else
          "firmware/ va pc/ chi doi trong danh sach trang Vong 5 (tru tep test Tester da khai)", str(fw))
    if git("merge-base", "--is-ancestor", H_PREV, B).returncode == 0:
        touched = [x for x in git("diff", "--name-only", "%s..%s" % (H_PREV, B)).stdout.split()
                   if is_tester(x) or x == HANDOFF + "03_TEST.md"]
        check("D1.8", not touched, "Coder khong sua tep test/log/03_TEST cua Tester tu H vong truoc toi B",
              "H truoc %s; tep Tester bi sua: %s" % (H_PREV, touched))
        old_log = git("show", "%s:docs/SESSION_LOG.md" % H_PREV).stdout.splitlines()
        new_log = at_b("docs/SESSION_LOG.md").splitlines()
        lost, j = [], 0      # ban cu phai la day con (theo thu tu) cua ban moi: chi chen them, khong xoa
        for ln in old_log:
            k = j
            while k < len(new_log) and new_log[k] != ln:
                k += 1
            if k < len(new_log):
                j = k + 1
            elif ln.strip():
                lost.append(ln)
        if lost:
            note("D1.9", "docs/SESSION_LOG.md tai B mat dong so voi H vong truoc (ho so dung chung chi duoc them)",
                 "%d dong mat: %s" % (len(lost), [x.strip()[:60] for x in lost[:3]]))
        else:
            check("D1.9", True, "docs/SESSION_LOG.md chi duoc them tu H vong truoc toi B", "")
    else:   # truoc day bo qua im lang D1.8-D1.10 -> nay la FAIL ro rang
        check("D1.8", False, "H truoc la commit co that va la to tien cua B (khong thi khong kiem duoc D1.8-D1.10)",
              "H truoc %s; git cat-file: %s" % (H_PREV, git("cat-file", "-t", H_PREV).stdout.strip() or "khong ton tai"))
    num = git("diff", "--numstat", "%s..%s" % (BASE, B), "--", "DECISIONS.md").stdout.split()
    check("D1.4", len(num) >= 2 and num[1] == "0", "DECISIONS.md chi them dong (khong xoa/sua dong cu)", " ".join(num[:2]))
    ws = git("diff", "--check", "%s..%s" % (BASE, B), "--", ".", ":!docs/logs/*").stdout.strip()
    claim = "git diff --check" in at_b(HANDOFF + "02_BUILD.md") and "sạch" in at_b(HANDOFF + "02_BUILD.md")
    if ws:
        note("D1.5", "git diff --check base..B KHONG sach (khoang trang cuoi dong) trong khi 02_BUILD ghi 'git diff --check sach'"
             if claim else "git diff --check base..B co canh bao", ws.splitlines()[0])
    else:
        check("D1.5", True, "git diff --check base..B sach")
    build = at_b(HANDOFF + "02_BUILD.md")
    named = re.findall(r"Commit B[^`\n]*`([0-9a-f]{7,40})`", build)
    if named:
        anc = [git("merge-base", "--is-ancestor", h, B).returncode == 0 for h in named]
        check("D1.6", all(anc), "commit B ghi trong 02_BUILD.md la to tien cua B dang kiem (D042: B phai la to tien H)",
              "02_BUILD ghi %s; la to tien: %s" % (named, anc))
    prev = git("show", "%s:%s" % (B_PREV, HANDOFF + "02_BUILD.md")).stdout
    if prev and B_PREV != B:
        gone = lost_lines(prev.splitlines(), build.splitlines())
        check("D1.7", not gone, "02_BUILD.md giu nguyen noi dung vong truoc (AGENTS: chang nhan lai them '## Vong k', khong xoa vong truoc)",
              "%d dong cua ban %s khong con (theo thu tu) trong B" % (len(gone), B_PREV[:7]))
    # pham vi luot sua: Q3 (01_PLAN Vong 3 muc 3) ngoai handoff/ho so chung chi Q3 muc 2 (+7/9) va Q4 muc 6;
    # Q6 (01_PLAN Vong 5 muc 3, luot Coder P..B) Q3 chi muc 1, 3-9 (giu muc 2), Q4 chi muc 6-7
    frm = H_PREV if (Q3 or later_round()) else P   # Q6 vong sua thu 2+: luot Coder la H truoc..B
    if git("merge-base", "--is-ancestor", frm, B).returncode == 0:
        turn = [x for x in git("diff", "--name-only", "%s..%s" % (frm, B)).stdout.split()
                if x and not x.startswith(HANDOFF) and x not in RECORDS and x not in ("DECISIONS.md",) and not is_tester(x)
                and not (not Q3 and x.startswith("docs/logs/coder-c5a-"))]   # log tu kiem Coder (01_PLAN Vong 7 muc 3)
        secs = {}
        for path in ("docs/design/S3_FRESH_CAPTURE.md", "docs/design/SCAN_SESSION.md"):
            old_t, new_t = git("show", "%s:%s" % (frm, path)).stdout, at_b(path)
            hunks = re.findall(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
                               git("diff", "-U0", "%s..%s" % (frm, B), "--", path).stdout, re.M)
            got = set()
            for a, na, c, nc in hunks:
                if na != "0":
                    got.add(section_of(old_t, int(a)))
                if nc != "0":
                    got.add(section_of(new_t, int(c)))
            secs[path] = sorted(got)
        if Q3:
            ok = (set(turn) <= {"docs/design/S3_FRESH_CAPTURE.md", "docs/design/SCAN_SESSION.md"}
                  and set(secs["docs/design/S3_FRESH_CAPTURE.md"]) <= {2, 7, 9}
                  and set(secs["docs/design/SCAN_SESSION.md"]) <= {6})
            title = "luot sua (H truoc..B), theo danh sach trang Vong 3, chi sua Q3 muc 2 (7/9) va Q4 muc 6, ngoai handoff/ho so chung"
        else:
            ok = (set(turn) <= WHITELIST and set(secs["docs/design/S3_FRESH_CAPTURE.md"]) <= {1, 3, 4, 5, 6, 7, 8, 9}
                  and set(secs["docs/design/SCAN_SESSION.md"]) <= {6, 7})
            title = "luot Coder P..B trong danh sach trang Vong 5; Q3 chi sua muc 1, 3-9 (giu muc 2), Q4 chi muc 6-7"
        check("D1.10", ok, title, "tep: %s; muc bi sua: %s" % (turn, {k.split("/")[-1]: v for k, v in secs.items()}))


def plan_round_at_p():
    """So vong moi nhat cua 01_PLAN.md tai P."""
    plan = git("show", "%s:%s" % (P, HANDOFF + "01_PLAN.md")).stdout
    nums = [int(x) for x in re.findall(r"(?m)^## Vòng (\d+)", plan)]
    return max(nums) if nums else 0


def coder_allowed():
    """Danh sach trang luot Coder theo vong ke hoach tai P (Q6)."""
    r = plan_round_at_p()
    return CODER_TURN_V9 if r >= 9 else CODER_TURN_V7 if r >= 7 else CODER_TURN_V6 if r >= 6 else CODER_TURN


def d1_gate():
    """01_PLAN Vong 9 V9-T1 (R14): cong Coder phai nam trong blob 02_BUILD tai B (khong phai cay lam viec);
    B->HEAD giu nguyen 02_BUILD; bao cao Reviewer luu tai P truoc B, dung SHA ke hoach ghi."""
    if Q3 or plan_round_at_p() < 9:
        return
    bb = gitb(REPO, "show", "%s:%s" % (B, HANDOFF + "02_BUILD.md"))
    bh = gitb(REPO, "show", "HEAD:%s" % (HANDOFF + "02_BUILD.md"))
    last = [ln.strip() for ln in bb.decode("utf-8").splitlines() if ln.strip()][-1:]
    anc = [git("merge-base", "--is-ancestor", a, b).returncode == 0 for a, b in ((P, B), (H_PREV, B), (B, "HEAD"))]
    check("D1.17", last == ["Trạng thái: SẴN SÀNG CHO TESTER"] and bb == bh and all(anc),
          "V9-T1/R14: dong trang thai cuoi cua 02_BUILD tai B la 'SAN SANG CHO TESTER'; 02_BUILD tai HEAD trung bytes B; P->B, H truoc->B, B->HEAD la to tien",
          "dong cuoi tai B: %r; B==HEAD: %s; to tien: %s" % (last, bb == bh, anc))
    plan = git("show", "%s:%s" % (P, HANDOFF + "01_PLAN.md")).stdout
    v9 = plan[plan.rfind("\n## Vòng 9"):]
    want = re.findall(r"`([0-9a-f]{64})`", v9[v9.find("### 4."):v9.find("### 5.")])
    rv = [hashlib.sha256(gitb(REPO, "show", "%s:%s" % (r, HANDOFF + "04_REVIEW.md"))).hexdigest() for r in (P, B, "HEAD")]
    check("D1.18", bool(want) and rv[0] == want[0] and len(set(rv)) == 1,
          "V9-T1: 04_REVIEW Vong 6 luu tai P dung SHA 01_PLAN Vong 9 muc 4 buoc 1, giu nguyen tai B va HEAD",
          "ke hoach: %s; P/B/HEAD: %s" % ([w[:16] for w in want], [x[:16] for x in rv]))


def later_round():
    """Q6 vong sua thu 2 tro di: P (ke hoach Vong 5) da nam truoc H Tester vong truoc."""
    return (not Q3) and bool(P) and git("merge-base", "--is-ancestor", P, H_PREV).returncode == 0


def d1_later():
    """Q6 vong sua thu 2+: luot Coder H truoc..B trong danh sach trang + ho so, chi them o 02_BUILD/SESSION_LOG,
    STATUS giu cau cu; khong chen ke hoach/bao cao Reviewer vao luot Coder (D042)."""
    anc = git("merge-base", "--is-ancestor", H_PREV, B).returncode == 0
    turn = [x for x in git("diff", "--name-only", "%s..%s" % (H_PREV, B)).stdout.split() if x]
    keep = [f for f in (HANDOFF + "02_BUILD.md", "docs/SESSION_LOG.md")
            if lost_lines(git("show", "%s:%s" % (H_PREV, f)).stdout.splitlines(), at_b(f).splitlines())]
    st_h = git("show", "%s:STATUS.md" % H_PREV).stdout.splitlines()
    st_lost = [ln for ln in st_h if ln.strip() and not any(ln.replace("Cập nhật: ", "", 1).strip() in x for x in at_b("STATUS.md").splitlines())]
    allowed = coder_allowed()
    if plan_round_at_p() >= 7:
        turn = [x for x in turn if not x.startswith("docs/logs/coder-c5a-")]
    check("D1.12", anc and set(turn) <= allowed and not keep and not st_lost,
          "luot Coder (H truoc..B) trong danh sach trang (01_PLAN Vong %d muc 3) + ho so; 02_BUILD va SESSION_LOG chi them; STATUS giu cau cu" % plan_round_at_p(),
          "H truoc->B to tien: %s; tep: %s; mat dong: %s; STATUS mat %d" % (anc, turn, keep, len(st_lost)))
    side = [x for x in turn if x in (HANDOFF + "01_PLAN.md", HANDOFF + "04_REVIEW.md")]
    check("D1.13", not side, "luot Coder khong kem thay doi ke hoach/bao cao Reviewer (D042)", "tep: %s" % side)
    d1_q6_records()


def d1_prep():
    """01_PLAN Vong 4 (V4-T1, V4-T2): tach H truoc..P (luu bao cao/ke hoach/nhat ky) khoi P..B (luot Coder)."""
    if not P:
        check("D1.12", False, "co moc P (C5A_P) de tach luot chuan bi khoi luot Coder", "")
        return
    if later_round():
        d1_later()
        return
    anc = (git("merge-base", "--is-ancestor", H_PREV, P).returncode == 0, git("merge-base", "--is-ancestor", P, B).returncode == 0)
    turn = [x for x in git("diff", "--name-only", "%s..%s" % (P, B)).stdout.split() if x]
    keep = [f for f in (HANDOFF + "02_BUILD.md", "docs/SESSION_LOG.md")
            if lost_lines(git("show", "%s:%s" % (P, f)).stdout.splitlines(), at_b(f).splitlines())]
    st_p = git("show", "%s:STATUS.md" % P).stdout.splitlines()
    st_lost = [ln for ln in st_p if ln.strip() and not any(ln.replace("Cập nhật: ", "", 1).strip() in x for x in at_b("STATUS.md").splitlines())]
    frozen = [x for x in git("diff", "--name-only", "%s..%s" % (B_PREV, B), "--", "docs/design", "firmware", "pc",
                             "DECISIONS.md", "ENVIRONMENT.md").stdout.split() if x and not is_tester(x)] if Q3 else []
    allowed = coder_allowed() if not Q3 else CODER_TURN
    if not Q3 and plan_round_at_p() >= 7:
        turn = [x for x in turn if not x.startswith("docs/logs/coder-c5a-")]
    check("D1.12", all(anc) and set(turn) <= allowed and not keep and not st_lost and not frozen,
          "luot Coder P..B chi them 02_BUILD/STATUS/SESSION_LOG; B cu..B moi giu nguyen thiet ke, firmware, ma PC, DECISIONS, ENVIRONMENT"
          if Q3 else "luot Coder P..B trong danh sach trang (01_PLAN Vong %d muc 3) + ho so; 02_BUILD va SESSION_LOG chi them (khong xoa dong cua chang khac); STATUS giu cau cu" % plan_round_at_p(),
          "H truoc->P->B to tien: %s; P..B: %s; mat dong (02_BUILD/SESSION_LOG): %s; STATUS mat %d; doi so voi B cu: %s" % (
              anc, turn, keep, len(st_lost), frozen))
    commits = git("log", "--format=%h %s", "%s..%s" % (H_PREV, P)).stdout.strip().splitlines()
    prep = [x for x in git("diff", "--name-only", "%s..%s" % (H_PREV, P)).stdout.split() if x]
    plan_lost = lost_lines(git("show", "%s:%s" % (H_PREV, HANDOFF + "01_PLAN.md")).stdout.splitlines(),
                           git("show", "%s:%s" % (P, HANDOFF + "01_PLAN.md")).stdout.splitlines())
    log_lost = lost_lines(git("show", "%s:docs/SESSION_LOG.md" % H_PREV).stdout.splitlines(),
                          git("show", "%s:docs/SESSION_LOG.md" % P).stdout.splitlines())
    rv_p, rv_b = gitb(REPO, "show", "%s:%s" % (P, HANDOFF + "04_REVIEW.md")), gitb(REPO, "show", "%s:%s" % (B, HANDOFF + "04_REVIEW.md"))
    check("D1.13", set(prep) <= PREP_FILES and not plan_lost and not log_lost and rv_p == rv_b and bool(rv_p),
          "chuan bi H truoc..P chi luu bao cao Reviewer/ke hoach/STATUS/nhat ky (chi them); 04_REVIEW tai B = tai P (Coder khong cham)",
          "commit: %s; tep: %s; 01_PLAN mat %d, SESSION_LOG mat %d; 04_REVIEW P==B: %s, SHA %s" % (
              commits, prep, len(plan_lost), len(log_lost), rv_p == rv_b, hashlib.sha256(rv_p).hexdigest()))
    if not Q3:
        d1_q6_records()
        return
    # SHA bao cao Reviewer ma ke hoach moi nhat ghi phai khop ban that tai P (ghi nhan, ho so cua Planner)
    plan = git("show", "%s:%s" % (P, HANDOFF + "01_PLAN.md")).stdout
    last = plan[plan.rfind("\n## Vòng "):]
    real = hashlib.sha256(rv_p).hexdigest()
    # chi SHA ghi tren cung dong voi 04_REVIEW (Vong 6 co SHA profile C2 khong lien quan)
    noted = [h for ln in last.splitlines() if "04_REVIEW" in ln for h in re.findall(r"`([0-9a-f]{60,70})`", ln) if h != real and h not in (
        "987505d39e652d35830676e97ad8be8d4e21eefe744e2d83a8029ded248bb226",)]
    if noted:
        note("D1.14", "SHA bao cao Reviewer ghi trong 01_PLAN vong moi nhat khong khop ban that tai P (ho so Planner)",
             "ghi %s (%d ky tu); that %s" % ([h for h in noted], len(noted[0]), real))
    else:
        check("D1.14", True, "SHA bao cao Reviewer ghi trong 01_PLAN vong moi nhat khop ban that tai P", real[:16])


def d1_q6_records():
    """Q6: D1.14 dinh chinh R08 (01_PLAN Vong 5 muc 2) dung blob Vong 3 tai P/B cu; D1.15 ENVIRONMENT khong mat bang chung."""
    plan = git("show", "%s:%s" % (P, HANDOFF + "01_PLAN.md")).stdout
    v5 = plan[plan.rfind("\n## Vòng 5"):]
    sec2 = v5[v5.find("### 2."):v5.find("### 3.")]
    shas = re.findall(r"`([0-9a-f]{64})`", sec2)
    blobs = [gitb(REPO, "show", "%s:%s" % (r, HANDOFF + "04_REVIEW.md"))
             for r in ("2ed9a75cc5d8a93b0811fb04d01fe64d8d3cfa80", "1a26df9c4f896fad6e286f2e1c02b4c6485ee547")]
    real = [hashlib.sha256(b).hexdigest() for b in blobs]
    check("D1.14", bool(shas) and all(h == real[0] for h in shas) and real[0] == real[1] and len(blobs[0]) == 28877,
          "dinh chinh R08 (01_PLAN Vong 5 muc 2): SHA 64 ky tu = blob 04_REVIEW Vong 3 tai P cu 2ed9a75 va B cu 1a26df9, 28877 byte",
          "ghi %s; that %s / %s; %d byte" % ([h[:16] for h in shas], real[0][:16], real[1][:16], len(blobs[0])))
    new = at_b("ENVIRONMENT.md").splitlines()
    lost = []   # so voi P (dau chang Q6) va voi H truoc: khong mat dong van ban nao
    for ref in dict.fromkeys((P, H_PREV)):   # dong van con nguyen chu (vd. viet noi them vao cuoi dong) thi khong tinh la mat
        lost += [ln for ln in git("show", "%s:ENVIRONMENT.md" % ref).stdout.splitlines()
                 if ln.strip() and ln not in new and ln not in lost and not any(ln.strip() in x for x in new)]
    prose = [ln for ln in lost if not ln.startswith("|")]
    rows = [ln for ln in lost if ln.startswith("|")]
    check("D1.15", not prose, "ENVIRONMENT.md: luot Coder khong xoa doan van ban ghi bang chung/lich su (chi them; dong bang cau hinh sua co ly do)",
          "doan van ban mat %d dong: %s" % (len(prose), [x.strip()[:70] for x in prose[:3]]))
    if rows:
        note("D1.16", "ENVIRONMENT.md: dong bang bi sua tai cho (doi chieu thu cong trong 03_TEST.md)",
             "; ".join(dict.fromkeys(r.split("|")[1].strip() for r in rows)))


def d1_hashes():
    """D1.11: ma bam 40 ky tu trong ho so Coder (02_BUILD moi vong, STATUS dong 3, muc Coder C5a cua SESSION_LOG)
    phai la commit co that cua repo, hoac revision repo ngoai ho so Q3 muc 2.1 khai, hoac da duoc dinh chinh
    (ma dung day du cung tien to 7 ky tu xuat hien sau lan nhac cuoi cua ma sai)."""
    doc = at_b(DOC)
    i = doc.find("### 2.1")
    ext = set(re.findall(r"\b[0-9a-f]{40}\b", doc[i:doc.find("### 2.2", i)] if i >= 0 else ""))
    slog = at_b("docs/SESSION_LOG.md")
    texts = [("02_BUILD.md", at_b(HANDOFF + "02_BUILD.md")),
             ("STATUS.md dong 3", (at_b("STATUS.md").splitlines() + ["", "", ""])[2])]
    for m in re.finditer(r"^## .*$", slog, re.M):
        if "C5a" in m.group(0) and "Coder" in m.group(0):
            texts.append(("SESSION_LOG " + m.group(0)[3:40], slog[m.start():slog.find("\n## ", m.end())]))
    bad = []
    for name, txt in texts:
        for h in sorted(set(re.findall(r"\b[0-9a-f]{40}\b", txt))):
            if h in ext or git("cat-file", "-e", h + "^{commit}").returncode == 0:
                continue
            real = git("rev-parse", "--verify", "--quiet", h[:7] + "^{commit}").stdout.strip()
            full = slog if name.startswith("SESSION_LOG") else txt   # dinh chinh nhat ky co the o muc sau
            if real and real in full[full.rfind(h):]:
                continue
            bad.append("%s: %s.. (that: %s)" % (name, h[:16], real[:16] or "?"))
    check("D1.11", not bad, "ma bam 40 ky tu trong ho so Coder la commit co that (hoac revision ngoai Q3 2.1, hoac da dinh chinh)",
          "ma khong ton tai chua dinh chinh: %s" % bad)


def lost_lines(old, new):
    """Dong khong rong cua `old` khong con trong `new` theo dung thu tu (old phai la day con cua new)."""
    lost, j = [], 0
    for ln in old:
        k = j
        while k < len(new) and new[k] != ln:
            k += 1
        if k < len(new):
            j = k + 1
        elif ln.strip():
            lost.append(ln)
    return lost


def section_of(text, lineno):
    """So muc cap '## n.' chua dong lineno (1-based) cua text."""
    cur = 0
    for i, ln in enumerate(text.splitlines()[:lineno], 1):
        m = re.match(r"## (\d+)\.", ln)
        if m:
            cur = int(m.group(1))
    return cur


def d2():
    print("---- D2 can cu driver (doc lap voi ho so)")
    doc = at_b(DOC)
    if not CAM_A.exists() or not CAM_H.exists() or not tool("xtensa-esp-elf-readelf").exists():
        check("D2.0", False, "tim thay thu vien/header driver va xtensa binutils cua core 3.3.11", str(LIBS))
        return
    ha, hh = sha256(CAM_A), sha256(CAM_H)
    check("D2.1", ha.upper() in doc and hh.upper() in doc, "SHA-256 thu vien va header dang cai khop gia tri ghi trong ho so",
          "a=%s.. h=%s.." % (ha[:16], hh[:16]))
    vt = (LIBS / "versions.txt").read_text(encoding="utf-8", errors="replace") if (LIBS / "versions.txt").exists() else ""
    m = re.search(r"^espressif__esp32-camera:\s*(.*)$", vt, re.M)
    note("D2.2", "versions.txt cua core khong ghi phien ban esp32-camera (khong truy duoc nguon dung goi build tu tep nay)",
         "dong: %r" % (m.group(0) if m else None))
    hz = None
    sdk = LIBS / "opi_opi/include/sdkconfig.h"
    if sdk.exists():
        mm = re.search(r"#define CONFIG_FREERTOS_HZ (\d+)", sdk.read_text(encoding="utf-8", errors="replace"))
        hz = int(mm.group(1)) if mm else None
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([str(tool("xtensa-esp-elf-ar")), "x", str(CAM_A), "cam_hal.c.obj", "ll_cam.c.obj", "esp_camera.c.obj"],
                       cwd=td, check=True)
        refs = {}
        for obj in ("cam_hal.c.obj", "ll_cam.c.obj", "esp_camera.c.obj"):
            out = subprocess.run([str(tool("xtensa-esp-elf-readelf")), "-rW", obj], cwd=td, capture_output=True, text=True).stdout
            sec = None
            for ln in out.splitlines():
                ms = re.match(r"Relocation section '([^']+)'", ln)
                if ms:
                    sec = ms.group(1)
                for sym in ("esp_timer_get_time", "gettimeofday"):
                    if ln.rstrip().endswith(sym) or (" " + sym + " ") in ln:
                        fn = re.sub(r"^\.rela\.(text|literal)\.", "", sec or "")
                        refs.setdefault(sym, set()).add("%s:%s" % (obj, fn))
        timer_fns = sorted(refs.get("esp_timer_get_time", set()))
        check("D2.3", timer_fns == ["cam_hal.c.obj:cam_start_frame"] and not refs.get("gettimeofday"),
              "(du kien) timestamp khung do esp_timer_get_time() gan, chi trong cam_start_frame; khong dung gettimeofday",
              "esp_timer_get_time: %s; gettimeofday: %s" % (timer_fns, sorted(refs.get("gettimeofday", set()))))
        claims_vsync = "ll_cam_do_vsync" in doc or "ISR" in doc
        names_start = "cam_start_frame" in doc
        check("D2.4", names_start and not claims_vsync,
              "ho so ghi dung ham/ngu canh gan timestamp (ma may: cam_start_frame trong cam_hal.c, khong co trong ll_cam/ISR)",
              "ho so nhac 'll_cam_do_vsync'/'ISR': %s; nhac 'cam_start_frame': %s" % (claims_vsync, names_start))
        dis = subprocess.run([str(tool("xtensa-esp-elf-objdump")), "-dr", "--section=.text.esp_camera_fb_get", "esp_camera.c.obj"],
                             cwd=td, capture_output=True, text=True).stdout
        mv = re.search(r"movi\s+a10, (-?\d+)", dis)
        ad = re.search(r"addmi\s+a10, a10, (0x[0-9a-f]+|-?\d+)", dis)
        ticks = (int(mv.group(1)) + int(ad.group(1), 0)) if (mv and ad) else None
        calls_take = "cam_take" in dis
        ms_bound = (ticks * 1000 // hz) if (ticks and hz) else None
        check("D2.5", calls_take and ticks == 4000 and hz == 1000,
              "(du kien) esp_camera_fb_get() goi cam_take voi doi so timeout 4000 tick, CONFIG_FREERTOS_HZ=1000 (~4000 ms; doi so, khong phai can cung)",
              "cam_take(%s tick), HZ=%s -> ~%s ms" % (ticks, hz, ms_bound))
        take = subprocess.run([str(tool("xtensa-esp-elf-objdump")), "-dr", "--section=.text.cam_take", "cam_hal.c.obj"],
                              cwd=td, capture_output=True, text=True).stdout
        inner = [s for s in ("xTaskGetTickCount", "xQueueReceive", "ll_cam_dma_reset", "vTaskDelay", "cam_verify_jpeg_eoi", "cam_give")
                 if s in take]
        note("D2.6", "cam_take co vong theo han tick: nhan hang doi, reset DMA + vTaskDelay khi loi, tu bo khung JPEG hong (cam_give)",
             "ham duoc goi: %s" % inner)
    bound_doc = bool(re.search(r"cam_take|4000\s*ms|4\s*s(?:\b|giây)|FB_GET_TIMEOUT|4 giây", doc))
    check("D2.7", bound_doc,
          "ho so neu can thoi gian chan cua esp_camera_fb_get() (01_PLAN Vong 2 buoc 2 va muc 4: vong ngoai kiem dong ho khong tao can cung)",
          "ho so co nhac cam_take/4000 ms/FB_GET_TIMEOUT: %s; han vong ngoai ho so dat: %s" % (
              bound_doc, re.findall(r"timeout_us = \d+LL", doc)))


def fmt_fw(sec, usec):
    """Dinh dang firmware dang co dung cho X-Timestamp (app_httpd.cpp): '%u.%06u'."""
    return "%u.%06u" % (sec, usec)


def parse_doc(s):
    """Quy tac PC trong ho so muc 3.3: t = sec*10^6 + usec (so nguyen)."""
    a, b = s.split(".")
    return int(a) * 1000000 + int(b)


def d3():
    print("---- D3 dinh dang header thoi gian")
    fw = (REPO / "firmware/esp32s3/CameraWebServerTest/app_httpd.cpp").read_text(encoding="utf-8", errors="replace")
    pad = re.findall(r'"X-Timestamp", \(const char \*\)ts\)', fw)
    fw_fmt = re.findall(r'snprintf\(ts, 32, "%" PRIu32 "\.%06" PRIu32', fw)
    check("D3.1", len(fw_fmt) >= 2 and len(pad) >= 2, "firmware dang co in X-Timestamp dang '<sec>.<usec 6 chu so>' (%06)",
          "%d cho snprintf %%06" % len(fw_fmt))
    cases = [(45, 123456), (45, 5), (45, 0), (4294967295, 999999)]
    ok = all(parse_doc(fmt_fw(s, u)) == s * 1000000 + u for s, u in cases)
    check("D3.2", ok, "quy tac phan tich so nguyen cua ho so dung voi dinh dang %06 cua firmware (ca usec nho, 0, sec max uint32)",
          ", ".join("%s->%d" % (fmt_fw(s, u), parse_doc(fmt_fw(s, u))) for s, u in cases))
    unpadded = "%u.%u" % (45, 5)
    as_float = round(float(unpadded) * 1000000)
    note("D3.3", "minh hoa ly do phai quy dinh %06: neu in khong dem 0, '45.5' bi phan tich sai lech",
         "sec=45 usec=5 -> '%s': theo ho so %d us, doc nhu so thap phan %d us" % (unpadded, parse_doc(unpadded), as_float))
    doc = at_b(DOC)
    spec_pad = bool(re.search(r"%06|06\s*l?u|6 chữ số|sáu chữ số|zero-pad|đệm 0", doc))
    check("D3.4", spec_pad, "ho so quy dinh phan micro giay du 6 chu so cho X-Timestamp/X-Request-Timestamp",
          "co quy dinh: %s" % spec_pad)
    # chi do trong phan noi ve Frame ID (muc 3.3 'Quy tac Frame ID' toi het muc 3, va buoc 4 FSM 'Cap phat Frame ID'),
    # tranh khop nham chu 'tran DMA (DMA overflow)' o muc 7
    i3 = doc.find("Quy tắc Frame ID")
    j3 = doc.find("## 4.", i3) if i3 >= 0 else -1
    i5 = doc.find("Cấp phát Frame ID")
    j5 = doc.find("5. Gửi Body", i5) if i5 >= 0 else -1
    fid = (doc[i3:j3] if i3 >= 0 and j3 > i3 else "") + (doc[i5:j5] if i5 >= 0 and j5 > i5 else "")
    ovf = bool(re.search(r"tràn|overflow|UINT64_MAX|UINT32_MAX|2\^64|2\^32|quay vòng|wrap", fid))
    ctype = bool(re.search(r"uint64_t|uint32_t|unsigned long long", fid))
    check("D3.5", bool(fid) and ovf and ctype,
          "ho so neu kieu/mien so va chinh sach tran cua bo dem Frame ID (01_PLAN Vong 2 muc 4: khong quay vong im lang)",
          "doan Frame ID %d ky tu; co kieu so: %s; co chinh sach tran: %s" % (len(fid), ctype, ovf))
    m_lim = re.search(r"discarded_count\s*(>=|>)\s*(\d+)", doc)
    m_dom = re.search(r"X-Discarded-Frames`?: Số nguyên không âm \$\\in \[(\d+), (\d+)\]", doc)
    if m_lim:
        op, n = m_lim.group(1), int(m_lim.group(2))
        max_ok = n - 1 if op == ">=" else n   # so lan loai lon nhat con co the tra 200
        dom = (int(m_dom.group(1)), int(m_dom.group(2))) if m_dom else None
        if dom is None:
            note("D3.6", "khong tim thay mien X-Discarded-Frames dang [a, b] trong ho so", "FSM: discarded_count %s %d" % (op, n))
        elif dom[1] == max_ok:
            check("D3.6", True, "mien X-Discarded-Frames khop gioi han loai khung cua FSM", "FSM %s %d -> 200 co toi da %d; mien %s" % (op, n, max_ok, dom))
        else:
            note("D3.6", "mien X-Discarded-Frames chua khop FSM (gia tri bien khong bao gio xuat hien o 200)",
                 "FSM: discarded_count %s %d -> 200 co toi da %d lan loai; ho so ghi mien %s" % (op, n, max_ok, dom))
        d3_model(doc, op, n)
    else:
        check("D3.6", False, "tim thay dieu kien dung loai khung trong FSM", "")


def fsm_fresh(t_req, frames, op, n, counter):
    """Mo hinh FSM muc 5.1 cua ho so: frames = timestamp (us) driver tra lan luot. Tra (status, id, t_f, discarded, counter)."""
    disc = 0
    for tf in frames:
        if tf > t_req:
            if counter >= (1 << 64) - 1:
                return 500, None, None, disc, counter
            counter += 1
            return 200, counter, tf, disc, counter
        disc += 1
        if (disc >= n) if op == ">=" else (disc > n):
            return 503, None, None, disc, counter
    return 503, None, None, disc, counter


def d3_model(doc, op, n):
    """D3: chuoi 20 request tuan tu theo quy tac ho so (queue 0/1/2 stale, khung bang moc request), bien ID va tran."""
    counter, rows, t = 0, [], 10_000_000
    patterns = [0, 1, 2, "eq", 0, 1, 0, 2, "eq", 1, 0, 0, 2, 1, "eq", 0, 1, 2, 0, 1]
    for k, pat in enumerate(patterns):
        t += 500_000
        t_req = t
        if pat == "eq":
            frames = [t_req, t_req + 33_000]
        else:
            frames = [t_req - 33_000 * (i + 1) for i in range(pat)][::-1] + [t_req + 30_000]
        st, fid, tf, disc, counter = fsm_fresh(t_req, frames, op, n, counter)
        rows.append((st, fid, tf, t_req, disc))
    ok = (all(r[0] == 200 for r in rows) and [r[1] for r in rows] == list(range(1, 21))
          and all(r[2] > r[3] for r in rows) and all(r[4] == (1 if p == "eq" else p) for r, p in zip(rows, patterns)))
    check("D3.7", ok, "mo hinh FSM cua ho so: 20 request tuan tu (stale 0/1/2, khung bang moc request) -> ID 1..20, t_f > t_r, so khung loai dung",
          "ID cuoi %s; discarded %s" % (rows[-1][1], [r[4] for r in rows]))
    st1 = fsm_fresh(1, [2], op, n, (1 << 64) - 2)
    st2 = fsm_fresh(1, [2], op, n, (1 << 64) - 1)
    check("D3.8", st1[0] == 200 and st1[1] == (1 << 64) - 1 and st2[0] == 500,
          "bien ID theo ho so: counter UINT64_MAX-1 -> ID UINT64_MAX; counter UINT64_MAX -> 500 FRAME_ID_OVERFLOW (khong quay vong)",
          "%s / %s" % (st1[:2], st2[:1]))
    ex = re.findall(r"X-Frame-Id: (\d+)\s+(?:X-Boot-Id: [0-9a-f]{32}\s+)?X-Timestamp: (\d+)\.(\d{6})\s+"
                    r"X-Request-Timestamp: (\d+)\.(\d{6})\s+X-Discarded-Frames: (\d+)", doc)
    ids = [int(e[0]) for e in ex]
    tfs = [int(e[1]) * 1000000 + int(e[2]) for e in ex]
    trs = [int(e[3]) * 1000000 + int(e[4]) for e in ex]
    okx = bool(ex) and ids == list(range(1, len(ex) + 1)) and all(a > b for a, b in zip(tfs, trs)) and all(x < y for x, y in zip(tfs, tfs[1:]))
    check("D3.9", okx, "chuoi vi du muc 3.4 cua ho so tu nhat quan (ID 1..n, t_f > t_r, timestamp tang)",
          "%d vi du; ID %s; t_f-t_r (us) %s" % (len(ex), ids, [a - b for a, b in zip(tfs, trs)]))


def d4():
    print("---- D4 mo hinh tranh chap va ma tran loi (kiem tu khoa la gan dung; checklist thu cong trong 03_TEST.md la chinh)")
    doc = at_b(DOC)
    lib = LIBS / "lib/libesp_http_server.a"
    if lib.exists():
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([str(tool("xtensa-esp-elf-ar")), "x", str(lib), "httpd_main.c.obj"], cwd=td, check=True)
            dis = subprocess.run([str(tool("xtensa-esp-elf-objdump")), "-dr", "--section=.text.httpd_start", "httpd_main.c.obj"],
                                 cwd=td, capture_output=True, text=True).stdout
        ntask = len(re.findall(r"R_XTENSA_ASM_EXPAND\s+xTaskCreate\w*", dis))
        check("D4.1", ntask == 1, "(du kien) httpd_start tao dung 1 task moi server -> cac handler cung cong 80 chay tuan tu",
              "so lenh tao task trong httpd_start: %d; SHA-256 lib %s.." % (ntask, sha256(lib)[:16]))
    i4 = doc.find("## 4.")
    j4 = doc.find("## 5.", i4)
    sec4 = doc[i4:j4] if i4 >= 0 and j4 > i4 else ""
    two_clients = "Hai client cùng lúc" in sec4
    serial = bool(re.search(r"một task|1 task|tuần tự|single task|httpd_thread", sec4))
    check("D4.2", not two_clients or serial,
          "ho so mo ta dung tranh chap cung cong 80 (server mot task -> hai /capture_fresh xep hang, khong phai 503 BUSY_CAPTURE)",
          "co 'Tinh huong C hai client cung luc': %s; co nhac server mot task/tuan tu: %s" % (two_clients, serial))
    # chi xet phan QUY TAC (muc 4.2); muc 4.1 chi liet ke endpoint cua cong 80, khong phai quy tac phoi hop
    i42 = sec4.find("### 4.2")
    rules = sec4[i42:] if i42 >= 0 else ""
    others = {k: (k in rules) for k in ("/capture`", "/bmp", "/control")}
    check("D4.3", bool(rules) and all(others.values()),
          "muc 4.2 (quy tac) co quy tac phoi hop cho /capture cu, /bmp va thao tac doi cau hinh /control (01_PLAN Vong 2 buoc 3)",
          "co nhac trong 4.2: %s" % others)
    client = bool(re.search(r"NaN|Inf|thiếu header|header sai|thiếu.*X-Frame-Id|cắt cụt|truncat", doc))
    check("D4.4", client,
          "ho so co quy tac phia client cho header thieu/sai/NaN/Inf/am/thua va JPEG hong/cat cut (01_PLAN Vong 2 muc 5 D4)",
          "co nhac: %s" % client)
    row = next((ln for ln in doc.splitlines() if "CAMERA_NO_BUFFER" in ln and ln.startswith("|")), "")
    names_timeout = bool(re.search(r"hết hạn|timeout|4000|4 s|4 giây|cam_take", row))
    check("D4.5", bool(row) and names_timeout,
          "bang loi: fb_get tra NULL (driver het han ~4 s HOAC loi khac) duoc goi dung, khong chi la 'het buffer' (01_PLAN muc 4: ma rieng cho 'het han', phan biet timeout driver)",
          "dong bang: %r" % row[:160])
    tcp = next((ln for ln in doc.splitlines() if "Mất kết nối TCP" in ln and ln.startswith("|")), "")
    conditional = "nếu đang bật laser" in tcp
    check("D4.6", bool(tcp) and not conditional,
          "mat ket noi TCP lam phien cu khong con hop le, khong co dieu kien (01_PLAN muc 4: 'Reset/mat ket noi/lui ID ... phai lam phien cu khong tiep tuc duoc coi hop le')",
          "dong ma tran client: %r" % tcp[:200])


def d5():
    print("---- D5 dong bo quy tac Frame ID")
    doc = at_b(DOC)
    build_all = at_b(HANDOFF + "02_BUILD.md")
    k = build_all.rfind("\n## Vòng ")
    build = build_all[k:] if k >= 0 else build_all   # chi vong moi nhat; vong cu la lich su
    dec = at_b("DECISIONS.md")
    i_inc = doc.find("Tăng Frame ID")
    i_send = doc.find("Gửi Body JPEG")
    before_send = 0 <= i_inc < i_send
    consumed = "Frame ID đã được tiêu thụ" in doc
    build_after = "chỉ tăng khi gửi thành công" in build or "tăng Frame ID sau khi gửi thành công" in build
    d041 = "tăng dần cho mỗi khung trả thành công" in dec
    check("D5.1", not (before_send and consumed and build_after),
          "thoi diem tang Frame ID nhat quan giua ho so Q3, 02_BUILD (vong moi nhat) va D041",
          "Q3: tang truoc khi gui=%s, tieu thu khi gui loi=%s; 02_BUILD: 'chi tang khi gui thanh cong'=%s; D041: 'moi khung tra thanh cong'=%s" % (
              before_send, consumed, build_after, d041))
    env = at_b("ENVIRONMENT.md")
    check("D5.2", "ll_cam_do_vsync" not in env,
          "ENVIRONMENT.md khong ghi sai ham gan timestamp (ma may: cam_start_frame)", "ENVIRONMENT nhac ll_cam_do_vsync: %s" % ("ll_cam_do_vsync" in env))


def gitc(repo, *args):
    r = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def gitb(repo, *args):
    r = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True)
    return r.stdout if r.returncode == 0 else b""


def zip_info():
    z = zipfile.ZipFile(ZIP)
    vt = z.read("esp32s3-libs/versions.txt")
    m = re.search(rb"^lib-builder: \S+ ([0-9a-f]{7,})", vt, re.M)
    return z, vt, (m.group(1).decode() if m else None)


def d6_local(doc):
    """V3-T1, phan cuc bo: package index -> zip staging -> tep dang cai; ho so ghi dung moc."""
    if not (INDEX.exists() and ZIP.exists()):
        check("D6.1", False, "tim thay package index va zip esp32s3-libs 3.3.11 trong staging", "%s; %s" % (INDEX, ZIP))
        return None
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    dep, sums = False, set()
    for p in idx.get("packages", []):
        for pl in p.get("platforms", []):
            if pl.get("architecture") == "esp32" and pl.get("version") == "3.3.11":
                dep = any(t.get("name") == "esp32s3-libs" and t.get("version") == "3.3.11" for t in pl.get("toolsDependencies", []))
        for t in p.get("tools", []):
            if t.get("name") == "esp32s3-libs" and t.get("version") == "3.3.11":
                sums |= {(s.get("url", ""), s.get("checksum", "").split(":")[-1].lower()) for s in t.get("systems", [])}
    zsha = sha256(ZIP)
    z, vt, lb_short = zip_info()
    za = hashlib.sha256(z.read("esp32s3-libs/lib/libespressif__esp32-camera.a")).hexdigest()
    zh = hashlib.sha256(z.read("esp32s3-libs/include/espressif__esp32-camera/driver/include/esp_camera.h")).hexdigest()
    url = next((u for u, c in sums if c == zsha), "")
    same_v = vt == (LIBS / "versions.txt").read_bytes()
    check("D6.1", dep and bool(url) and za == sha256(CAM_A) and zh == sha256(CAM_H) and same_v,
          "chuoi cuc bo: index esp32 3.3.11 -> esp32s3-libs 3.3.11, checksum index == SHA zip staging; lib/header/versions.txt trong zip == ban dang cai",
          "phu thuoc=%s; zip %s..; checksum khop=%s; lib=%s header=%s versions=%s" % (
              dep, zsha[:16], bool(url), za == sha256(CAM_A), zh == sha256(CAM_H), same_v))
    full_lb = re.search(r"\b(%s[0-9a-f]{%d})\b" % (lb_short, 40 - len(lb_short)), doc) if lb_short else None
    check("D6.2", zsha.upper() in doc and bool(url) and url in doc and bool(full_lb),
          "ho so Q3 ghi dung SHA/URL zip va commit lib-builder day du ung voi dong versions.txt",
          "versions.txt 'lib-builder: ... %s'; ho so ghi %s" % (lb_short, full_lb.group(1) if full_lb else None))
    return full_lb.group(1) if full_lb else None


def d6_sources(td):
    if SRC:
        cam, lb = Path(SRC) / "esp32-camera", Path(SRC) / "lib-builder"
    else:
        cam, lb = Path(td) / "esp32-camera", Path(td) / "lib-builder"
        subprocess.run(["git", "clone", "-q", CAM_GIT, str(cam)], capture_output=True)
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", LB_GIT, str(lb)], capture_output=True)
    ok = bool(gitc(cam, "rev-parse", "origin/master")) and bool(gitc(lb, "rev-parse", "HEAD"))
    check("D6.0", ok, "co nguon esp32-camera va esp32-arduino-lib-builder de kiem doc lap (thieu = provenance D2 CHUA DAT)",
          "esp32-camera origin/master %s" % gitc(cam, "rev-parse", "--short", "origin/master"))
    return (cam, lb) if ok else (None, None)


def d6_chain(doc, cam, lb, lb_full):
    """V3-T1, phan nguon: manifest lib-builder -> master esp32-camera trong cua so build -> dau van tay ma may."""
    i = doc.find("### 2.1")
    sec21 = doc[i:doc.find("### 2.2", i)] if i >= 0 else ""
    revs = sorted({h for h in re.findall(r"\b[0-9a-f]{40}\b", sec21) if gitc(cam, "cat-file", "-t", h) == "commit"})
    rev = revs[0] if len(revs) == 1 else None
    yml = gitc(lb, "show", "%s:main/idf_component.yml" % lb_full) if lb_full else ""
    blk = re.search(r"espressif/esp32-camera:\n((?:[ \t]+.*\n?)+)", yml)
    pin = bool(blk) and bool(re.search(r'version:\s*"?master"?', blk.group(1))) and "github.com/espressif/esp32-camera" in blk.group(1)
    check("D6.3", pin, "lib-builder@<commit trong versions.txt> ghim espressif/esp32-camera theo git, nhanh master (main/idf_component.yml)",
          "lib-builder %s; khoi camera: %r" % ((lb_full or "")[:12], " ".join(blk.group(1).split())[:110] if blk else None))
    z, _, _ = zip_info()
    t0 = int(gitc(lb, "log", "-1", "--format=%ct", lb_full) or 0) if lb_full else 0
    # tep trong zip ghi gio khong mui gio: cong 1 ngay cho can tren cua so build
    t1 = datetime(*z.getinfo("esp32s3-libs/versions.txt").date_time, tzinfo=timezone.utc).timestamp() + 86400
    fp = [ln.split() for ln in gitc(cam, "log", "--first-parent", "--format=%H %ct", "origin/master").splitlines()]
    at = lambda t: next((h for h, c in fp if int(c) <= t), None)  # noqa: E731  (fp moi nhat truoc)
    k = next((n for n, (h, _) in enumerate(fp) if h == at(t1)), None)
    nxt = fp[k - 1] if k else None
    still = bool(rev) and at(t0) == rev and at(t1) == rev and nxt is not None and int(nxt[1]) > t1
    check("D6.4", still,
          "trong cua so build [commit lib-builder, ngay tep zip + 1 ngay], master esp32-camera (first-parent) dung yen o revision ho so ghi",
          "ho so: %s; master luc dau/cuoi cua so: %s/%s; commit ke tiep %s luc %s" % (
              (rev or revs)[:12] if rev else revs, (at(t0) or "")[:7], (at(t1) or "")[:7], nxt[0][:7] if nxt else None,
              datetime.fromtimestamp(int(nxt[1]), timezone.utc).date() if nxt else None))
    if not rev:
        return None
    hcur = sha256(CAM_H)
    h_rev = hashlib.sha256(gitb(cam, "show", "%s:driver/include/esp_camera.h" % rev)).hexdigest()
    h_nxt = hashlib.sha256(gitb(cam, "show", "%s:driver/include/esp_camera.h" % nxt[0])).hexdigest() if nxt else None
    diff = gitc(cam, "show", "--format=", rev, "--", "driver")
    plus = set(re.findall(r'"([^"\\]{12,})"', "\n".join(l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))))
    minus = set(re.findall(r'"([^"\\]{12,})"', "\n".join(l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))))
    in_tree = lambda r, s: subprocess.run(["git", "-C", str(cam), "grep", "-q", "-F", "-e", s, r, "--", "driver"]).returncode == 0  # noqa: E731
    added = [s for s in plus - minus if not in_tree(rev + "^", s)]
    removed = [s for s in minus - plus if not in_tree(rev, s)]
    blob = CAM_A.read_bytes()
    add_in = [s for s in added if s.encode() in blob]
    rem_in = [s for s in removed if s.encode() in blob]
    check("D6.5", h_rev == hcur and h_nxt != hcur and bool(add_in) and not rem_in,
          "dau van tay: header@revision == header dang cai, header@commit ke tiep khac; chuoi chi co tu revision co trong .a, chuoi revision xoa khong con",
          "header@%s khop=%s; header@%s khac=%s; chuoi moi co trong .a: %s; chuoi bi xoa con trong .a: %s" % (
              rev[:7], h_rev == hcur, nxt[0][:7] if nxt else None, h_nxt != hcur, [s[:32] for s in add_in], [s[:32] for s in rem_in]))
    return rev


# trich dan nguon trong bang muc 2.2 -> doan ma phai co trong dung khoang dong tai revision
CITE_EXPECT = {
    ("cam_hal.c", 235, 248): ["esp_timer_get_time()", "tv_usec = us % 1000000UL"],
    ("cam_hal.c", 608, 612): ["CAMERA_GRAB_LATEST", "frame_cnt - 1", "xQueueCreate(frame_buffer_queue_len"],
    ("cam_hal.c", 404, 420): ["xQueueReceive(cam_obj->frame_buffer_queue, &fb2, 0)", "cam_give(fb2)"],
    ("esp_camera.c", 387, 394): ["(4000 / portTICK_PERIOD_MS)", "cam_take(FB_GET_TIMEOUT)"],
    ("cam_hal.c", 686, 772): ["for (;;)", "ll_cam_dma_reset", "vTaskDelay(1)", "cam_verify_jpeg_eoi", "cam_give(dma_buffer)"],
    ("esp_camera.c", 404, 410): ["esp_camera_fb_return", "cam_give(fb)"],
    ("cam_hal.c", 771, 771): ["cam_give(dma_buffer)"],
}


def last_def(lines, upto):
    """Ten ham C dinh nghia gan nhat truoc/tai dong upto (1-based)."""
    name = None
    for ln in lines[:upto]:
        m = re.match(r"^(?!typedef|struct|enum|union|if\b|for\b|while\b|return\b)[A-Za-z_][\w \t\*]*?\b(\w+)\s*\(", ln)
        if m and not ln.rstrip().endswith(";"):
            name = m.group(1)
    return name


def calls(td, obj, fn):
    """Ky hieu ngoai duoc tham chieu trong section .text.<fn>, theo thu tu dia chi."""
    dis = subprocess.run([str(tool("xtensa-esp-elf-objdump")), "-dr", "--section=.text." + fn, obj],
                         cwd=td, capture_output=True, text=True).stdout
    # ham static trong cung tep duoc tham chieu qua ten section '.text.<ham>' (khong co +offset)
    return re.findall(r"R_XTENSA_(?:ASM_EXPAND|SLOT0_OP)\s+(?:\.text\.)?([A-Za-z_]\w*)\s*$", dis, re.M), dis


def subseq(want, seq):
    it = iter(seq)
    return all(any(x == w for x in it) for w in want)


def d6_source_binary(doc, cam, rev, td):
    """V3-T2: trich dan nguon (dong/ham) va cot ma may cua bang muc 2.2 tai lap duoc."""
    i = doc.find("### 2.2")
    sec22 = doc[i:doc.find("### 2.3", i)] if i >= 0 else ""
    bad, seen = [], []
    for f, a, b_, fn in re.findall(r"`driver/(cam_hal\.c|esp_camera\.c):(\d+)(?:-(\d+))?`(?: \(`(\w+)`\))?", sec22):
        a, b_ = int(a), int(b_ or a)
        src = gitc(cam, "show", "%s:driver/%s" % (rev, f)).splitlines()
        seg = "\n".join(src[a - 1:b_])
        exp = CITE_EXPECT.get((f, a, b_))
        real = last_def(src, b_)
        seen.append("%s:%d-%d%s" % (f, a, b_, "(%s)" % fn if fn else ""))
        if exp is None:
            bad.append("%s:%d-%d chua co ky vong" % (f, a, b_))
        elif not all(t in seg for t in exp):
            bad.append("%s:%d-%d thieu %s" % (f, a, b_, [t for t in exp if t not in seg]))
        if fn and fn != real:
            bad.append("%s:%d-%d ghi ham `%s`, nguon la `%s`" % (f, a, b_, fn, real))
    check("D6.6", bool(seen) and not bad, "trich dan nguon cua bang 2.2 (dong + ten ham) dung tai revision",
          "%d trich dan; lech: %s" % (len(seen), bad))
    subprocess.run([str(tool("xtensa-esp-elf-ar")), "x", str(CAM_A), "cam_hal.c.obj", "esp_camera.c.obj"], cwd=td, check=True)
    st, _ = calls(td, "cam_hal.c.obj", "cam_start_frame")
    want_ts = ["ll_cam_start", "ll_cam_do_vsync", "esp_timer_get_time", "__udivdi3", "__umoddi3"]
    check("D6.7", subseq(want_ts, st), "ma may cam_start_frame goi theo thu tu nguon: ll_cam_start -> ll_cam_do_vsync -> esp_timer_get_time -> chia/du 10^6",
          "thu tu trong .text.cam_start_frame: %s" % st)
    row = next((ln for ln in sec22.splitlines() if ln.startswith("|") and "GRAB_LATEST" in ln and "xQueueCreate" in ln), "")
    claimed = re.findall(r"section `\.text\.(\w+)`", row)
    q_claim = claimed[0] if claimed else None
    secs = [m for m in re.findall(r"\.text\.(\w+)", subprocess.run(
        [str(tool("xtensa-esp-elf-objdump")), "-h", "cam_hal.c.obj"], cwd=td, capture_output=True, text=True).stdout)]
    # nguon: event_queue roi frame_buffer_queue tao lien nhau trong cung mot ham -> section co >= 2 xQueueGenericCreate
    real_q = [s for s in dict.fromkeys(secs) if calls(td, "cam_hal.c.obj", s)[0].count("xQueueGenericCreate") >= 2]
    claim_has = q_claim is not None and calls(td, "cam_hal.c.obj", q_claim)[0].count("xQueueGenericCreate") >= 1
    check("D6.8", claim_has and q_claim in real_q,
          "hang GRAB_LATEST: section ma may ho so ghi la noi tao frame_buffer_queue (xQueueGenericCreate)",
          "ho so ghi .text.%s (co xQueueGenericCreate: %s); thuc te hai hang doi tao trong %s" % (
              q_claim, claim_has, [".text." + s for s in real_q]))
    tk, _ = calls(td, "cam_hal.c.obj", "cam_task")
    tkb, _ = calls(td, "cam_hal.c.obj", "cam_take")
    fr, _ = calls(td, "esp_camera.c.obj", "esp_camera_fb_return")
    src_hal = gitc(cam, "show", "%s:driver/cam_hal.c" % rev)
    j = src_hal.find("camera_fb_t *cam_take(")
    body = src_hal[j:src_hal.find("\n}\n", j)] if j >= 0 else ""
    inner = ["xTaskGetTickCount", "xQueueReceive", "ll_cam_dma_reset", "vTaskDelay", "cam_verify_jpeg_eoi", "cam_give"]
    ok = (subseq(["xQueueGenericSend", "xQueueReceive", "xQueueGenericSend", "cam_give"], tk) and "cam_give" in fr
          and all(s in tkb for s in inner) and all(s + "(" in body for s in inner))
    check("D6.9", ok, "ma may khop nguon: cam_task day->rut->day->cam_give khi hang doi day; fb_return -> cam_give; cam_take goi du cac ham cua vong for(;;)",
          "cam_task co chuoi: %s; fb_return->cam_give: %s; cam_take ma may/nguon: %s/%s" % (
              subseq(["xQueueGenericSend", "xQueueReceive", "xQueueGenericSend", "cam_give"], tk), "cam_give" in fr,
              [s for s in inner if s in tkb], [s for s in inner if s + "(" in body]))


def d6_derived(doc):
    """V3-T2: khong dung doi so 4000 tick lam tran thoi gian chan o bat ky dau trong ho so (01_PLAN Vong 3 buoc 4)."""
    i = doc.find("## 2.")
    sec2 = doc[i:doc.find("## 3.", i)] if i >= 0 else ""
    hedge = bool(re.search(r"chưa[^|\n]{0,40}chứng minh[^|\n]{0,60}cận cứng", sec2, re.I))
    # moi lan 4000/4 s duoc goi la tran ('toi/toi da/khoang', 'can/tran [cung]') ma 60 ky tu truoc khong co 'chua ... chung minh'
    # (R04 Reviewer Vong 2: 'can 4 s cua driver' lot qua mau cu chi xet 'toi/toi da' theo dong)
    num = r"~?\s*(?:4000|4\.000|4 giây|4 s\b)"
    pats = [r"(?:tới|tối đa)\s*(?:khoảng\s*)?" + num, r"(?:cận|trần)(?:\s+cứng)?(?:\s+thời gian)?\s*" + num]
    bad = []
    for n, ln in enumerate(doc.splitlines(), 1):
        for p in pats:
            for m in re.finditer(p, ln, re.I):
                if not re.search(r"chưa[^|]{0,40}chứng minh", ln[max(0, m.start() - 60):m.start()], re.I):
                    bad.append("L%d: ...%s" % (n, ln[max(0, m.start() - 50):m.end() + 20].strip()))
    env = next((ln for ln in at_b("ENVIRONMENT.md").splitlines() if "esp32-camera" in ln and ln.startswith("|")), "")
    env_ok = bool(re.search(r"chưa[^|\n]{0,20}chứng minh[^|\n]{0,20}cận cứng", env))
    check("D6.10", hedge and env_ok and not bad,
          "4000 tick chi la doi so timeout: muc 2 va ENVIRONMENT ghi 'chua chung minh can cung', khong cau nao khac goi no la tran/can ('toi ~4000 ms', 'tre toi 4 giay', 'can 4 s')",
          "muc 2 ha nhan: %s; ENVIRONMENT: %s; cau con dung lam tran: %s" % (hedge, env_ok, bad))


class DrvModel:
    """Mo hinh toi gian cam_task/cam_take/cam_give theo nguon cam_hal.c (revision ho so ghi; diem neo kiem o D6.17).

    en[x] = 1: o x ranh (cam_get_next_frame chon duoc); en = 0 dat khi khung nhan xong (nhanh VSYNC, sau ll_cam_stop);
    khong con o ranh -> state IDLE, moi VSYNC sau chi thu lai (bo khung cam bien), khong tran/khong reset DMA.
    """

    def __init__(self, n, latest):
        self.n, self.en, self.pos, self.state = n, [1] * n, 0, "IDLE"
        self.qlen = n - 1 if (latest and n > 1) else n
        self.q, self.ts, self.skipped = [], [None] * n, 0

    def _next(self):
        if self.en[self.pos]:
            return True
        for x in range(self.n):
            if self.en[x]:
                self.pos = x
                return True
        return False

    def vsync(self, t):
        if self.state == "IDLE":
            if self._next():
                self.ts[self.pos], self.state = t, "READ"
            else:
                self.skipped += 1
            return
        self.en[self.pos] = 0                       # khung xong: ll_cam_stop, en = 0, day vao hang doi
        if len(self.q) < self.qlen:
            self.q.append(self.pos)
        else:                                       # GRAB_LATEST: rut khung cu, day khung moi, cam_give khung cu
            old = self.q.pop(0)
            self.q.append(self.pos)
            self.en[old] = 1
        if self._next():
            self.ts[self.pos] = t
        else:
            self.state = "IDLE"

    def take(self):
        return self.q.pop(0) if self.q else None    # cam_take: caller giu, en van 0

    def give(self, x):
        self.en[x] = 1                              # cam_give


def d6_buffers(doc, cam, rev):
    """R05 (Reviewer Vong 2): muc 7 ve 1/2 buffer phai khop luong nguon; ca 1 buffer co khung cho, 2 buffer cung bi giu."""
    src = gitc(cam, "show", "%s:driver/cam_hal.c" % rev)
    flat = " ".join(src.split())
    i_v = flat.find("} else if (cam_event == CAM_VSYNC_EVENT) {")
    vs = flat[i_v:flat.find("break;", flat.find("if(!cam_start_frame(&frame_pos)){", i_v))] if i_v >= 0 else ""
    j = src.find("camera_fb_t *cam_take(")
    take = src[j:src.find("\n}\n", j)] if j >= 0 else ""
    g = src.find("void cam_give(camera_fb_t *dma_buffer)")
    give = src[g:src.find("\n}\n", g)] if g >= 0 else ""
    sends = src.count("xQueueSend(cam_obj->frame_buffer_queue")
    anchors = {
        "queue_len = frame_cnt, -1 chi khi LATEST va > 1": all(s in flat for s in (
            "size_t frame_buffer_queue_len = cam_obj->frame_cnt;",
            "if (config->grab_mode == CAMERA_GRAB_LATEST && cam_obj->frame_cnt > 1) {",
            "frame_buffer_queue_len = cam_obj->frame_cnt - 1;")),
        "VSYNC: ll_cam_stop -> en = 0 -> xQueueSend -> khong o ranh thi IDLE": bool(vs) and 0 <= vs.find("ll_cam_stop(cam_obj);")
            < vs.find("cam_obj->frames[frame_pos].en = 0;") < vs.find("xQueueSend(") < vs.find(
                "if(!cam_start_frame(&frame_pos)){ cam_obj->state = CAM_STATE_IDLE;"),
        "IDLE: moi VSYNC thu cam_start_frame": "case CAM_STATE_IDLE: { if (cam_event == CAM_VSYNC_EVENT) { //DBG_PIN_SET(1); if(cam_start_frame(&frame_pos)){" in flat,
        "cam_give dat en = 1; cam_take khong tra o": ".en = 1;" in give and ".en = 1" not in take,
        "cam_task chi day &frame_buffer_event (khong NULL)": sends > 0 and sends == src.count(
            "xQueueSend(cam_obj->frame_buffer_queue, (void *)&frame_buffer_event"),
        "ll_cam_dma_reset trong cam_hal.c chi o cam_take": src.count("ll_cam_dma_reset(") == take.count("ll_cam_dma_reset("),
    }
    # ca 1: 1 buffer, khung xong truoc request nam cho trong hang doi; tra no ra thi khung sau moi > t_req
    m1 = DrvModel(1, True)
    for t in (0, 33):
        m1.vsync(t)
    t_req = 50
    a = m1.take()
    stale1 = a is not None and m1.ts[a] < t_req
    m1.give(a)
    for t in (66, 99):
        m1.vsync(t)
    b = m1.take()
    fresh1 = b is not None and m1.ts[b] > t_req
    # ca 2: 2 buffer GRAB_LATEST, HTTP giu mot o, hang doi giu o con lai -> khong o ranh, IDLE, bo khung
    m2 = DrvModel(2, True)
    for t in (0, 33, 66):
        m2.vsync(t)
    held = m2.take()
    m2.vsync(99)
    blocked = m2.state == "IDLE" and held is not None and len(m2.q) == 1 and not any(m2.en)
    m2.vsync(132)
    skip2 = m2.skipped == 1
    m2.give(held)
    m2.vsync(165)
    resumed = m2.state == "READ" and m2.ts[m2.pos] == 165
    if not Q3:
        d6_q6_buffers(doc, anchors, (stale1, fresh1, blocked, skip2, resumed))
        return
    i7 = doc.find("### 7.2")
    s72 = doc[i7:doc.find("### 7.3", i7)] if i7 >= 0 else ""
    old_claims = [p for p in ("Không có khung cũ nằm chờ", "luôn có 1 buffer dự phòng", "không bị mất đồng bộ DMA") if p in s72]
    says1 = bool(re.search(r"fb_count = 1", s72)) and bool(re.search(r"vẫn có thể nằm chờ|vẫn chứa", s72))
    says2 = bool(re.search(r"không đảm bảo[^.]{0,60}buffer rảnh", s72))
    ok = all(anchors.values()) and stale1 and fresh1 and blocked and skip2 and resumed and not old_claims and says1 and says2
    check("D6.17", ok, "R05: mo hinh buffer neo vao nguon - 1 buffer van co khung cu cho trong hang doi; 2 buffer co the khong con o ranh; muc 7.2 noi dung dieu do",
          "neo nguon sai: %s; ca1 khung cu cho=%s, sau tra co khung moi=%s; ca2 het o ranh=%s, bo khung=%s, chay lai sau cam_give=%s; "
          "7.2 con cau cu %s; noi ca1=%s ca2=%s" % ([k for k, v in anchors.items() if not v], stale1, fresh1, blocked, skip2, resumed,
                                                     old_claims, says1, says2))
    i7 = doc.find("## 7.")
    s7 = doc[i7:doc.find("## 8.", i7)] if i7 >= 0 else ""
    wrong = [m.group(0) for m in re.finditer(r"tràn DMA|DMA overflow|ll_cam_dma_reset|(?:đang nhận|đang ghi)[^.;]{0,30}không rảnh", s7)]
    # va phai noi dung co che (L12): en = 0 khi khung xong; het o ranh -> IDLE, bo khung; chay lai sau cam_give
    mech = {"en = 0 khi khung xong": bool(re.search(r"en = 0[^.]{0,80}(hoàn tất|xong)", s72)),
            "IDLE": "IDLE" in s72,
            "bo khung": bool(re.search(r"bỏ qua|bỏ khung|dropped", s72)),
            "chay lai sau cam_give": bool(re.search(r"sau khi[^.]{0,40}cam_give", s72))}
    check("D6.18", not wrong and all(mech.values()) and anchors["ll_cam_dma_reset trong cam_hal.c chi o cam_take"],
          "muc 7 mo ta dung co che het o ranh theo nguon (en = 0 khi khung xong; IDLE, bo khung toi khi cam_give), khong gan tran/reset DMA",
          "cum tu trai nguon trong muc 7: %s; 7.2 neu co che: %s" % (wrong, mech))


def sim_requests(n, period=40, interval=200, count=10, offset=7):
    """Mo hinh DrvModel (neo nguon): VSYNC moi `period` ms, request moi `interval` ms; fb_get chan toi khi co khung,
    tra ngay moi khung (cu hoac moi). Tra (tuoi khung dau lay duoc, do tre toi khung moi, so khung loai) moi request."""
    m = DrvModel(n, True)
    nv = [0]

    def until(tt):
        while nv[0] <= tt:
            m.vsync(nv[0])
            nv[0] += period
    ages, lats, discs = [], [], []
    for i in range(1, count + 1):
        t_req = i * interval + offset
        until(t_req)
        now, d, age = t_req, 0, None
        while True:
            while not m.q:
                now = nv[0]
                until(now)
            s = m.take()
            ts = m.ts[s]
            age = now - ts if age is None else age
            m.give(s)
            if ts > t_req:
                lats.append(now - t_req)
                break
            d += 1
        ages.append(age)
        discs.append(d)
    return ages, lats, discs


def d6_q6_buffers(doc, anchors, model_ok):
    """Q6 (01_PLAN Vong 5 muc 3: Q3 khong nang so do chua co thanh dat; R05 Reviewer Vong 2): muc 7 sau D043 khong
    khang dinh loi ich hieu nang/on dinh cua 1 buffer ma chua do; doi chieu voi mo hinh neo nguon."""
    check("D6.17", all(anchors.values()) and all(model_ok),
          "mo hinh buffer neo vao nguon cam_hal.c (6 diem neo; 1 buffer co khung cu cho; 2 buffer co the het o ranh; IDLE bo khung; chay lai sau cam_give)",
          "neo sai: %s; mo hinh: %s" % ([k for k, v in anchors.items() if not v], model_ok))
    a1, l1, d1 = sim_requests(1)
    a2, l2, d2 = sim_requests(2)
    detail = ("mo hinh (VSYNC 40 ms, request moi 200 ms): 1 buffer tuoi khung dau %d..%d ms, loai %s, tre %d..%d ms; "
              "2 buffer tuoi %d..%d ms, loai %s, tre %d..%d ms" % (min(a1), max(a1), sorted(set(d1)), min(l1), max(l1),
                                                                 min(a2), max(a2), sorted(set(d2)), min(l2), max(l2)))
    i7 = doc.find("## 7.")
    s7 = doc[i7:doc.find("## 8.", i7)] if i7 >= 0 else ""
    sents = [s.strip() for s in re.split(r"(?<=[.;])\s+|\n", s7) if s.strip()]
    claims = [s[:120] for s in sents if re.search(r"giảm tối đa|tối ưu|bảo đảm|đảm bảo", s, re.I)
              and not re.search(r"giả thuyết|cần đo|chưa đo|chưa kiểm|đo đạc|đo trên bo", s, re.I)]
    check("D6.20", not claims, "Q3 muc 7 (D043) khong khang dinh loi ich hieu nang/an toan cua 1 buffer ma chua do (R05: ha thanh gia thuyet)",
          "cau khang dinh chua do: %s; %s" % (claims, detail))
    i34 = doc.find("### 3.4")
    s34 = doc[i34:doc.find("## 4.", i34)] if i34 >= 0 else ""
    if re.search(r"hàng đợi rỗng", s34) and min(d1) >= 1:
        note("D6.21", "vi du 3.4 'khung dau sau boot, hang doi rong, discarded 0' khac mo hinh 1 buffer (hang doi giu khung cuoi -> request cach nhau loai >= 1)",
             detail)


def d6_r06():
    """R06 (Gop y Reviewer Vong 2): nhat ky co dong dinh chinh duong dan header that, sau dong sai; dong sai giu nguyen."""
    slog = at_b("docs/SESSION_LOG.md")
    wrong = slog.find("hardware/esp32/3.3.11/tools/esp32-arduino-libs")
    right = "packages/esp32/tools/esp32s3-libs/3.3.11/include/espressif__esp32-camera/driver/include/esp_camera.h"
    fixed = slog.find(right, wrong + 1) if wrong >= 0 else 0
    check("D6.19", (wrong < 0 or fixed > wrong) and CAM_H.exists(),
          "R06: SESSION_LOG co dong dinh chinh duong dan header that (ton tai tren may) dat sau dong ghi sai",
          "dong sai o ky tu %d; dinh chinh o %d; header that ton tai: %s" % (wrong, fixed, CAM_H.exists()))


def d6_r02():
    """V3-T3: doan C2 Vong 7 muc 6 SCAN_SESSION nguyen van nhu base, bullet C5a nam sau doan."""
    p = "docs/design/SCAN_SESSION.md"
    cut = lambda t: t[t.find("\n## 6."):t.find("\n## 7.")].splitlines()  # noqa: E731
    base6, b6 = cut(git("show", "%s:%s" % (BASE, p)).stdout), cut(at_b(p))
    lost = lost_lines(base6, b6)
    if not Q3:   # Q6 (01_PLAN Vong 5 muc 3): duoc sua bullet C5a cua chinh no; khong xoa doan C2
        lost = [ln for ln in lost if not ln.startswith("- C5a")]
    c2 = next((n for n, ln in enumerate(base6) if ln.startswith("  instrument firmware,")), None)
    k = b6.index(base6[c2]) if c2 is not None and base6[c2] in b6 else None
    after_ok = k is not None and k + 1 < len(b6) and b6[k + 1].startswith("- C5a")
    num = git("diff", "--numstat", "%s..%s" % (H_PREV, B), "--", p).stdout.split()
    # numstat rong = luot nay khong cham tep (khong xoa dong nao)
    if not Q3:   # Q6: bullet C5a va muc 7 muc 1 duoc sua (danh sach trang Vong 5); D1.10 gioi han muc 6-7
        num = []
    check("D6.11", not lost and after_ok and (not num or num[1] == "0"),
          "Q4 muc 6: moi dong cua base con nguyen theo thu tu (ca dong 'instrument firmware, ...'), bullet C5a ngay sau doan C2; luot nay chi them dong",
          "dong base mat: %d; dong C2: %r; dong sau la C5a: %s; numstat H truoc..B: %s" % (
              len(lost), base6[c2] if c2 is not None else None, after_ok, " ".join(num[:2])))


def run_old(rev, env_over):
    """Chay ban test tai commit rev (khong ghi ra dia) voi bien moi truong cho truoc; tra ((pass, fail, note), exit)."""
    src = git("show", "%s:pc/test_c5a_contract.py" % rev).stdout
    env = {k: v for k, v in os.environ.items() if not k.startswith("C5A_") or k == "C5A_SRC"}
    env.update(env_over)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Vong 22: lan chay long danh dau C5A_NESTED. Trong lan chay long, D6.16 khong duoc goi lai run_old (truoc day
    # STATUS/SESSION_LOG co so lieu test_c5a_contract -> D6.16 chay blob H truoc, blob do lai thay cung so lieu -> de quy
    # vo han). D6.13 (tai hien blob Q3 77bdbbc/d2aa737) van chay that. D6.16 cua lan long tinh PASS de tong khop lan thuong.
    env["C5A_NESTED"] = "1"
    # doc stdin dang byte UTF-8 (stdin mac dinh cua Windows la cp1252, lam hong chuoi tieng Viet trong test cu)
    code = """import sys, os
src = sys.stdin.buffer.read().decode('utf-8')
g = {'__name__': 'c5a_long', '__file__': sys.argv[1]}
exec(compile(src, sys.argv[1], 'exec'), g)
if 'main' not in g:
    g = {'__name__': '__main__', '__file__': sys.argv[1]}
    exec(compile(src, sys.argv[1], 'exec'), g)
else:
    if 'run_old' in g and 'check' in g:
        ro, ck = g['run_old'], g['check']
        g['run_old'] = lambda rev, e: ro(rev, e) if rev[:7] in ('77bdbbc', 'd2aa737') else ((0, 0, 0), 0)
        g['check'] = lambda cid, ok, title, detail='': ck(cid, True if cid == 'D6.16' else ok, title, detail)
    g['main']()
"""
    r = subprocess.run([sys.executable, "-c", code, str(REPO / "pc/test_c5a_contract.py")], input=src, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"TONG: (\d+) PASS, (\d+) FAIL, (\d+) NOTE", r.stdout)
    return (tuple(int(x) for x in m.groups()) if m else None), r.returncode


def d6_r03():
    """V3-T4: doi chieu muc dinh chinh 02_BUILD Vong 3 voi Git va tai hien hai ket qua test cu."""
    build_all = at_b(HANDOFF + "02_BUILD.md") if Q3 else git("show", "%s:%s" % (R03_SRC, HANDOFF + "02_BUILD.md")).stdout
    latest = build_all[build_all.rfind("\n## Vòng "):]
    bad = []
    for rng, scope in (("3467e3e..77bdbbc", None), ("3467e3e..d2aa737", None), ("b5f87b4..77bdbbc", ("firmware", "pc"))):
        actual = [x for x in git("diff", "--name-only", rng, *(("--",) + scope if scope else ())).stdout.split() if x]
        line = next((ln for ln in latest.splitlines() if ("`%s`" % rng) in ln and "Khoảng" in ln), "")
        listed = re.findall(r"`([\w./-]+\.(?:md|py|log))`", line.split("gồm", 1)[1]) if "gồm" in line else None
        if scope:
            if actual or "rỗng" not in line:
                bad.append("%s -- firmware pc: thuc te %s; dong: %r" % (rng, actual, line[:80]))
        elif listed is not None:
            if sorted(listed) != sorted(actual):
                bad.append("%s: ghi %s, thuc te %s" % (rng, sorted(set(listed) ^ set(actual)), len(actual)))
        elif not all(x.split("/")[-1] in line for x in actual if x.startswith("docs/logs/test-c5a-v3")):
            bad.append("%s: khong nhac log v3" % rng)
    nums = all(s in latest for s in ("28 PASS, 1 FAIL, 3 NOTE", "29 PASS, 0 FAIL, 4 NOTE")) and "exit code 1" in latest and "exit code 0" in latest
    check("D6.12", not bad and nums, "02_BUILD vong moi nhat, muc doi chieu lich su: danh sach tep 3 khoang Git khop output that; ghi tach 28/1/3 exit 1 va 29/0/4 exit 0",
          "lech: %s; co ca hai so lieu: %s" % (bad, nums))
    env = {"C5A_B": "77bdbbc5061497a5216ff618b253705506787065", "C5A_H_PREV": "b5f87b4"}
    old = run_old("77bdbbc", env)
    new = run_old("d2aa737", env)
    check("D6.13", old == ((28, 1, 3), 1) and new == ((29, 0, 4), 0),
          "tai hien: test tai 77bdbbc -> 28/1/3 exit 1; test Tester Vong 3 (d2aa737) -> 29/0/4 exit 0 (cung B=77bdbbc, H_PREV=b5f87b4)",
          "77bdbbc: %s exit %s; d2aa737: %s exit %s" % (old[0], old[1], new[0], new[1]))
    if not Q3:   # D6.14 xet vong moi nhat cua 02_BUILD tai B (D6.12 o tren xet vong R03 cua B cu)
        b_all = at_b(HANDOFF + "02_BUILD.md")
        latest = b_all[b_all.rfind(chr(10) + "## Vòng "):]
    sec1 = latest[latest.find("### 1."):latest.find("### 2.")]
    m = re.search(r"`git diff --name-only ([0-9a-f]{7,40})\.\.HEAD`", sec1)
    if m:
        listed = re.findall(r"^- `([\w./-]+)`", sec1, re.M)
        actual = [x for x in git("diff", "--name-only", "%s..%s" % (m.group(1), B)).stdout.split() if x]
        if sorted(listed) != sorted(actual):
            note("D6.14", "02_BUILD vong moi nhat muc 1 gan danh sach tep voi lenh '%s..HEAD' nhung output that khac" % m.group(1),
                 "ghi %d tep; thuc te %d, thieu %s" % (len(listed), len(actual), sorted(set(actual) - set(listed))))
        else:
            check("D6.14", True, "02_BUILD vong moi nhat muc 1 khop output lenh ghi kem")
    # so lieu test Coder tu bao (cau moi nhat cua STATUS, muc Coder moi nhat cua SESSION_LOG) phai tai hien duoc
    # bang test Tester tai H truoc voi moc ma 02_BUILD huong dan (01_PLAN Vong 3 R03 y 2: ghi so PASS/FAIL/NOTE, exit)
    head = at_b("STATUS.md").splitlines()[2].split("Trước đó:")[0] if len(at_b("STATUS.md").splitlines()) > 2 else ""
    slog = at_b("docs/SESSION_LOG.md")
    k = slog.rfind("Chặng: Coder")
    entry = slog[k:slog.find("\n## ", k)] if k >= 0 else ""
    # (a) cau khong ghi moc: tai hien bang test tai H truoc voi moc hien hanh
    # (b) cau ghi du 'blob test <rev> ... B=<b> ... H_PREV=<h> [B_PREV=<p>] ... <p>/<f>/<n> | <p> PASS, <f> FAIL, <n> NOTE ... exit <e>'
    claims = []   # ((rev, env), (pass, fail[, note]), exit hoac None, nguyen van)
    for p, f in re.findall(r"test_c5a_contract\.py`?[^;\n]{0,40}?(\d+) PASS, (\d+) FAIL", head + "\n" + entry):
        claims.append(((H_PREV, (("C5A_B", B), ("C5A_H_PREV", H_PREV), ("C5A_B_PREV", B_PREV), ("C5A_BASE", BASE))),
                       (int(p), int(f)), None, "%s PASS, %s FAIL" % (p, f)))
    for clause in re.split(r";|\n", head + "\n" + latest + "\n" + entry):
        c = clause.replace("`", "").replace("*", "")
        mb, mB = re.search(r"blob test ([0-9a-f]{7,40})", c), re.search(r"\bB=([0-9a-f]{7,40})", c)
        mH, mP = re.search(r"H_PREV=([0-9a-f]{7,40})", c), re.search(r"B_PREV=([0-9a-f]{7,40})", c)
        mr = re.search(r"(\d+) PASS, (\d+) FAIL, (\d+) NOTE", c) or re.search(r"\b(\d+)/(\d+)/(\d+) exit", c)
        me = re.search(r"exit(?: code)? (\d+)", c)
        if mb and mB and mH and mr and me:
            env = (("C5A_B", mB.group(1)), ("C5A_H_PREV", mH.group(1))) + ((("C5A_B_PREV", mP.group(1)),) if mP else ())
            claims.append(((mb.group(1), env), tuple(int(x) for x in mr.groups()), int(me.group(1)), " ".join(c.split())[:90]))
    if claims:
        cache, bad, shown = {}, [], []
        for key, nums, ex, txt in claims:
            if key not in cache:
                cache[key] = run_old(key[0], dict(key[1]))
            got = cache[key]
            ok1 = got[0] is not None and got[0][:len(nums)] == nums and (ex is None or got[1] == ex)
            shown.append("%r -> tai hien %s exit %s" % (txt, got[0], got[1]))
            if not ok1:
                bad.append(txt)
        check("D6.16", not bad, "so lieu test Coder tu bao (STATUS cau moi nhat, 02_BUILD vong moi nhat, SESSION_LOG muc Coder moi nhat) tai hien duoc",
              "; ".join(shown) + ("; LECH: %s" % bad if bad else ""))
    else:
        check("D6.16", True, "khong co so lieu test Coder tu bao can tai hien trong STATUS/02_BUILD/SESSION_LOG moi nhat")


def d6_preserve():
    """V3-T5: bao toan bao cao Reviewer, STATUS (them truoc cau cu), 02_BUILD tai H truoc."""
    # 01_PLAN Vong 4 muc 5: khong so ca bao cao hien hanh voi SHA Vong 1 (fail gia) ma kiem tung ban lich su
    # (Vong 1, Vong 2, dung SHA tai commit luu) con nguyen van trong ban tai B
    rv_b = at_b(HANDOFF + "04_REVIEW.md")
    hist = []
    for rev, want in REVIEW_HIST:
        raw = gitb(REPO, "show", "%s:%s" % (rev, HANDOFF + "04_REVIEW.md"))
        txt = raw.decode("utf-8", "replace").replace("\r\n", "\n").strip()
        hist.append((rev, hashlib.sha256(raw).hexdigest() == want, bool(txt) and txt in rv_b.replace("\r\n", "\n")))
    st_old = git("show", "%s:STATUS.md" % H_PREV).stdout.splitlines()
    st_new = at_b("STATUS.md").splitlines()
    st_lost = [ln for ln in st_old if ln.strip() and not any(ln.replace("Cập nhật: ", "", 1).strip() in x for x in st_new)]
    bd_lost = lost_lines(git("show", "%s:%s" % (H_PREV, HANDOFF + "02_BUILD.md")).stdout.splitlines(),
                         at_b(HANDOFF + "02_BUILD.md").splitlines())
    check("D6.15", all(a and b for _, a, b in hist) and not st_lost and not bd_lost,
          "04_REVIEW.md tai B giu nguyen van cac vong cu (dung SHA luc luu); STATUS.md va 02_BUILD.md tai H truoc con nguyen trong B",
          "04_REVIEW tai B %s..; vong cu (commit, SHA dung, con nguyen): %s; STATUS mat %d; 02_BUILD mat %d" % (
              hashlib.sha256(rv_b.encode("utf-8")).hexdigest()[:16], hist, len(st_lost), len(bd_lost)))


def d6():
    print("---- D6 (01_PLAN Vong 3 muc 5) R01 nguon goc + doi chieu nguon/ma may, R02, R03")
    doc = at_b(DOC)
    lb_full = d6_local(doc)
    td = tempfile.mkdtemp(prefix="c5a_src_")
    try:
        cam, lb = d6_sources(td)
        if cam:
            rev = d6_chain(doc, cam, lb, lb_full)
            if rev:
                d6_source_binary(doc, cam, rev, td)
                d6_buffers(doc, cam, rev)
    finally:
        shutil.rmtree(td, onerror=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
    d6_derived(doc)
    d6_r02()
    d6_r03()
    d6_preserve()
    d6_r06()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:  # noqa: BLE001
        pass
    print("Tester C5a Vong 10 - kiem may cua ho so /capture_fresh; B=%s" % B)
    for f in (d1, d1_prep, d1_gate, d1_hashes, d2, d3, d4, d5, d6):
        try:
            f()
        except Exception as e:  # noqa: BLE001
            check(f.__name__.upper() + ".X", False, "ngoai le khi kiem", repr(e))
    nf = sum(1 for _, t in RESULTS if t == "FAIL")
    print("\nTONG: %d PASS, %d FAIL, %d NOTE" % (sum(1 for _, t in RESULTS if t == "PASS"), nf, sum(1 for _, t in RESULTS if t == "NOTE")))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
