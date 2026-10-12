#!/usr/bin/env python3
"""Tester C6 goi ho so Q5 (01_PLAN Vong 2 muc 5: V2-T1..V2-T6; Vong 3 muc 5: V3-T1..V3-T8) va kich ban Tester TX.

Chi doc Git va tep trong repo; khong mo COM/HTTP toi bo, khong cap nguon laser.
Chay tu goc repo:  .venv/Scripts/python.exe pc/test_c6_q5_docs.py
Bien moi truong: C6_B (B Coder), C6_PREV_H (H Tester truoc), C6_P (moc P Vong 3). Thoat 0 khi khong co FAIL.
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)

BASE = "4f6f9f92173ce2f7e745ef3215daae088a85f3d6"
B = os.environ.get("C6_B", "dbbdcfba4694496ee19036b3e9062cec293c1b5b")
# H cua vong Tester truoc; Coder khong duoc cham tep Tester sau moc nay
PREV_H = os.environ.get("C6_PREV_H", "d0cf7ce2eff2977e06b8dc427366ffe824e98b72")
# H Tester Vong 2 lan 2 (moc REVIEW soi); chuoi H_V2 -> P -> B va moc BOM tinh tu day
H_V2 = "e3e9cc07a10035092f73c4699a0fa36fae7447de"
# Moc P Vong 3: luu 01_PLAN Vong 3 + 04_REVIEW truoc B
P = os.environ.get("C6_P", "c5fca15b40fa1b6a928fb68dd581c7e3a93acb9f")
REVIEW_SHA = "2ac068dc79b38be5ebd98941e000f3a7014552c9140161e33e21366132b8f088"
HO = "handoff/2026-09-21_c6-laser-bringup/"
PROC = "docs/procedures/quy-trinh-c6-chuan-bi-mach-laser.md"
LC = "docs/design/LASER_CIRCUIT.md"
PREP = "docs/HARDWARE_PREP.md"
HW = "docs/HARDWARE.md"
WHITELIST = {PREP, LC, HW, PROC}
ALLOWED_DOCS = {"STATUS.md", "DECISIONS.md", "docs/SESSION_LOG.md"}
# San pham Coder + ho so phai bat bien B..H (D045)
FROZEN = sorted(WHITELIST | {"STATUS.md", "DECISIONS.md", "ENVIRONMENT.md",
                             HO + "01_PLAN.md", HO + "02_BUILD.md", HO + "04_REVIEW.md"})
TESTER_FILES = {"pc/test_c6_q5_docs.py", HO + "03_TEST.md", "docs/SESSION_LOG.md"}
RES = []


def check(cid, ok, title, detail=""):
    RES.append("PASS" if ok else "FAIL")
    print(("  [%s] %s %s  | %s" % ("PASS" if ok else "FAIL", cid, title, detail)).rstrip())


def note(cid, title, detail=""):
    RES.append("NOTE")
    print(("  [NOTE] %s %s  | %s" % (cid, title, detail)).rstrip())


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8").stdout


def rd(p):
    return Path(p).read_text(encoding="utf-8-sig")


def row(text, key):
    """Dong bang Markdown bat dau bang '| key |'."""
    for ln in text.splitlines():
        if ln.startswith("| %s |" % key):
            return ln
    return ""


def section(text, start, stop=r"^## "):
    m = re.search(start, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(stop, rest, re.M)
    return rest[: n.start()] if n else rest


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def t6_scope():
    print("V2-T6 pham vi / B..H")
    head = git("rev-parse", "HEAD").strip()
    names = set(git("diff", "--name-only", BASE + ".." + B).split())
    tester_ok = lambda n: n in TESTER_FILES or n.startswith("docs/logs/test-c6")
    extra = sorted(n for n in names if n not in WHITELIST | ALLOWED_DOCS and not n.startswith(HO) and not tester_ok(n))
    check("V2-T6.1", not extra, "base..B nam trong whitelist + ho so duoc phep + handoff + tep Tester da khai",
          "%d tep; thua=%s" % (len(names), extra))
    prod = git("diff", "--name-only", BASE + ".." + B, "--", "firmware", "pc", "docs/SPEC.md",
               "docs/design/NUCLEO_PROTOCOL.md", "docs/reviews", "ENVIRONMENT.md",
               ":(exclude)pc/test_c6_q5_docs.py").split()
    check("V2-T6.2", not prod, "khong cham firmware/pc (tru test Tester)/SPEC/Q3/reviews/ENVIRONMENT", str(prod))
    ho = [n for n in names if n.startswith(HO)]
    check("V2-T6.3", set(ho) <= {HO + "01_PLAN.md", HO + "02_BUILD.md", HO + "03_TEST.md", HO + "04_REVIEW.md"},
          "handoff chi 01_PLAN + 02_BUILD (+ 03_TEST cua Tester, 04_REVIEW luu o P)", str(sorted(ho)))
    num = git("diff", "--numstat", BASE + ".." + B, "--", HW).split()
    check("V2-T6.4", len(num) >= 2 and num[1] == "0", "HARDWARE.md base..B chi them (0 dong xoa)", " ".join(num[:2]))
    coder = set(git("diff", "--name-only", PREV_H + ".." + B).split())
    touched = sorted(n for n in coder if tester_ok(n) and n != "docs/SESSION_LOG.md")
    check("V2-T6.4b", not touched, "vong sua cua Coder (%s..B) khong cham test/log/03_TEST cua Tester" % PREV_H,
          "%s; cham=%s" % (sorted(coder), touched))
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", B, "HEAD"]).returncode == 0
    check("V2-T6.5", anc, "B la to tien HEAD", "B=%s HEAD=%s" % (B[:7], head[:7]))
    bh = set(git("diff", "--name-only", B + "..HEAD").split())
    bad = sorted(n for n in bh if not tester_ok(n))
    check("V2-T6.6", not bad, "B..HEAD chi tep Tester (test/log/03_TEST/SESSION_LOG)", "%s; thua=%s" % (sorted(bh), bad))
    diff_sl = git("diff", B + "..HEAD", "--", "docs/SESSION_LOG.md")
    dels = [l for l in diff_sl.splitlines() if l.startswith("-") and not l.startswith("---")]
    check("V2-T6.7", not dels, "SESSION_LOG B..HEAD chi them", "%d dong xoa" % len(dels))
    mism, bom_only = [], []
    for p in FROZEN:
        at_b = git("rev-parse", "%s:%s" % (B, p)).strip()
        at_h = git("rev-parse", "HEAD:%s" % p).strip()
        wt = git("hash-object", p).strip()
        if at_b != at_h:
            mism.append(p)
        elif wt != at_b:
            blob = subprocess.run(["git", "cat-file", "blob", at_b], capture_output=True).stdout
            if blob.startswith(b"\xef\xbb\xbf") and blob[3:] == Path(p).read_bytes():
                bom_only.append(p)
            else:
                mism.append(p)
        print("      blob %s B=%s HEAD=%s WT=%s sha256(WT)=%s" % (p, at_b[:10], at_h[:10], wt[:10], sha(p)[:16]))
    check("V2-T6.8", not mism, "san pham Coder/PLAN/BUILD/STATUS/DECISIONS/ENV bat bien B..H (cay lam viec chi khac BOM neu co)", str(mism))
    if bom_only:
        note("V2-T6.n1", "cay lam viec khac B chi o BOM UTF-8 dau tep (chua commit, khong phai cua Tester)", str(bom_only))
    b_build = rd(HO + "02_BUILD.md")
    check("V2-T6.9", b_build.rstrip().endswith("Trạng thái: SẴN SÀNG CHO TESTER"),
          "cong 02_BUILD: SAN SANG CHO TESTER", "")


def t1_deps():
    print("V2-T1 phu thuoc C2/C3/C4/C5a")
    for name, merge in (("c2-camera-profile", "3ec6dfa"), ("c3-line-extract", "b5c34db"),
                        ("c4-nucleo-laser-control", "8e5f1f7"), ("c5a-s3-fresh-capture", "bb8ac71")):
        anc = subprocess.run(["git", "merge-base", "--is-ancestor", merge, BASE]).returncode == 0
        parents = git("log", "-1", "--format=%P", merge).split()
        verdicts = re.findall(r"^Phán quyết: (\S+)", rd("handoff/2026-09-21_%s/04_REVIEW.md" % name), re.M)
        ok = anc and len(parents) == 2 and verdicts and verdicts[-1] == "GỘP"
        check("V2-T1." + name.split("-")[0], ok, "%s merge %s la to tien base, phan quyet cuoi GOP" % (name, merge),
              "anc=%s parents=%d verdict=%s" % (anc, len(parents), verdicts[-1:] ))
    c6 = sorted(p.name for p in Path(HO).iterdir())
    rv = re.findall(r"^Phán quyết: (.+)$", rd(HO + "04_REVIEW.md"), re.M) if "04_REVIEW.md" in c6 else []
    merged = subprocess.run(["git", "merge-base", "--is-ancestor", B, "main"]).returncode == 0
    check("V2-T1.c6", bool(rv) and rv[-1].startswith("CHẶN") and not merged,
          "C6 da co REVIEW phan quyet CHAN, chua gop main, chua nghiem thu", "verdict=%s merged=%s" % (rv[-1:], merged))
    hits = [p for p in (PREP, LC, HW, PROC) if re.search(r"chờ D027|chờ C2|D027 chưa", rd(p))]
    check("V2-T1.gia", not hits, "khong con cau hien hanh 'cho D027/C2' lam cong gia", str(hits))
    t = rd(HW) + rd(PROC)
    check("V2-T1.c4", "không tải" in row(rd(HW), "Nucleo PA8/D7 (LASER_CTRL)") and "Chưa nối tải thật" in t,
          "C4 chi ghi la khong tai", "")


def t2_timeouts():
    print("V2-T2 hai timeout / reset")
    lc = rd(LC)
    l8, l6 = row(lc, "L8"), row(lc, "L6")
    q3 = rd("docs/design/NUCLEO_PROTOCOL.md")
    check("V2-T2.q3", "T_hb = 3000 ms" in q3 and "T_laser_max = 5000 ms" in q3 and "1000 ms" in q3,
          "Q3 goc van T_hb 3000 / T_laser_max 5000 / HB 1000", "")
    check("V2-T2.1", "3000 ms" in l8 and "LINK_LOST" in l8 and "ERROR" in l8,
          "L8 mat lien lac >3000 ms -> ERROR/LINK_LOST", l8[:90])
    check("V2-T2.2", "5000 ms" in l8 and "LASER_TIMEOUT" in l8 and "IDLE" in l8 and "HEARTBEAT" in l8,
          "L8 heartbeat deu, het 5000 ms -> IDLE/LASER_TIMEOUT", "")
    check("V2-T2.3", not re.search(r"im lặng 5 s", lc), "khong con 'im lang 5 s'", "")
    check("V2-T2.4", "B2/RESET" in l6 and "B1/RESET" not in lc, "L6 dung B2/RESET, khong ghi B1 la RESET", l6[:80])
    hwb1 = row(rd(HW), "Nucleo-F446RE").find("PC13")
    check("V2-T2.5", "B1 nút USER" in rd(HW), "HARDWARE.md B1 = USER/PC13 (doi chieu)", "")
    check("V2-T2.6", not re.search(r"±|dung sai", l8 + l6), "khong tu them dung sai thoi gian o L6/L8", "")
    d038 = row(rd("DECISIONS.md"), "D038")
    check("V2-T2.7", "LINK_LOST" in d038 and "LASER_TIMEOUT" in d038 and "KHÔNG gia hạn" in d038,
          "L8 khop D038 (HB khong gia han laser)", "")
    _ = hwb1


def t3_inputs():
    print("V2-T3 dong <40 mA, Q1 IRFZ44N, driver/nguon")
    lc = rd(LC)
    l2 = row(lc, "L2")
    check("V2-T3.1", "CHƯA CÓ trị danh định" in l2 and "chưa áp dụng ±20%" in l2,
          "L2 khong tao danh dinh / mien ±20% gia", l2[:110])
    allt = lc + rd(PREP) + rd(HW) + rd(PROC)
    check("V2-T3.2", not re.search(r"32\s*[–-]\s*48\s*mA|danh định\s*(=|là)?\s*40\s*mA", allt),
          "khong co mien 32-48 mA hay 40 mA danh dinh", "")
    check("V2-T3.3", "Xung đột SPEC/Q5" in lc and "không tự động miễn" in lc,
          "ghi xung dot SPEC logic-level vs IRFZ44N, Vds khong mien SPEC", "")
    accept = [ln for ln in (rd(HW) + rd(PROC)).splitlines()
              if re.search(r"IRFZ44N[^|\n]{0,40}(ĐẠT|dùng được)", ln)
              and not re.search(r"(không|chưa)[^|\n]{0,30}IRFZ44N[^|\n]{0,40}(ĐẠT|dùng được)", ln)]
    check("V2-T3.4", not accept, "khong chap nhan Q1 IRFZ44N tu ten/Vds (bo qua cau phu dinh)", str(accept)[:120])
    check("V2-T3.5", "Driver hạn dòng CHƯA XÁC NHẬN" in row(rd(HW), "Laser SYD1230 ×2"),
          "HARDWARE.md giu driver han dong CHUA XAC NHAN", "")
    proc = rd(PROC)
    table = section(proc, r"^## Bảng đầu vào", r"^## ")
    has_drv = re.search(r"driver|hạn dòng", table, re.I)
    has_src = re.search(r"nguồn (5 V|laser)|backfeed|đủ tải", table, re.I)
    check("V2-T3.6", bool(has_drv and has_src),
          "bang dau vao I1-I12 cua quy trinh (cong Q8/Q9) giu driver han dong va nguon laser la CHUA DU",
          "driver=%s nguon=%s" % (bool(has_drv), bool(has_src)))


def t4_evidence():
    print("V2-T4 thieu vat tu / bang chung C4")
    hw = rd(HW)
    pa9 = row(hw, "Nucleo PA9/D8 (SENSE_PWR)")
    c4 = rd("handoff/2026-09-21_c4-nucleo-laser-control/03_TEST.md")
    c4_nopull = "NOPULL" in c4 or "không pull" in c4
    claims_pull = bool(re.search(r"pull-up/pull-down|pull-up|pull-down", pa9))
    check("V2-T4.1", not (c4_nopull and claims_pull),
          "PA9/D8: bang C6 khong nang bang chung qua C4 (C4 ghi PA9 NOPULL, ho de tha noi)",
          "C4 NOPULL=%s; dong C6: %s" % (c4_nopull, pa9[:100]))
    main_c = rd("firmware/stm32/NucleoPing/Core/Src/main.c")
    m = re.search(r"SENSE_ESTOP_Pin;\s*\n[^\n]*\n\s*GPIO_InitStruct\.Pull = (\w+)", main_c)
    pc7 = row(hw, "Nucleo PC7/D9 (SENSE_ESTOP)")
    check("V2-T4.2", m and m.group(1) == "GPIO_PULLUP" and "pull-up" in pc7,
          "PC7/D9 pull-up noi khop main.c", m.group(1) if m else "khong tim thay")
    prep = rd(PREP)
    safety = section(prep, r"^## An toàn laser")
    cond = re.search(r"Chỉ bật laser khi:(.*?)(?:\n- |\Z)", safety, re.S)
    cond = cond.group(1) if cond else ""
    check("V2-T4.3", bool(re.search(r"cửa|SW1", cond)) and bool(re.search(r"dừng|estop|SW2", cond)),
          "HARDWARE_PREP muc an toan: dieu kien bat laser co cua NC va nut dung (SPEC 9.3/9.4)",
          re.sub(r"\s+", " ", cond)[:160])
    b10 = row(prep, "B10")
    status_col = b10.rstrip(" |").split("|")[-1].strip()
    check("V2-T4.4", "khuyến nghị" not in status_col,
          "B10 cot trang thai khong con 'khuyen nghi' hien hanh", "cot cuoi: %s" % status_col)
    l6 = row(rd(LC), "L6")
    check("V2-T4.5", "không loại trừ xung ngắn" in l6 and "R08" in l6,
          "khong ket luan khong co xung ngan tu VOM/LED; R08 con mo", "")
    closed = re.search(r"(R01|R10|R08)[^|\n]{0,30}(ĐÃ ĐÓNG|đã đóng)", rd(HW) + rd(LC) + rd(PREP) + rd(PROC))
    check("V2-T4.6", not closed, "R01/R08/R10 khong bi tuyen bo dong", closed.group(0) if closed else "")
    proc = rd(PROC)
    check("V2-T4.7", "**DỪNG**" in row(proc, "I10") and "**DỪNG**" in row(proc, "I11")
          and "**DỪNG**" in row(proc, "I12"), "quy trinh dung khi thieu SW1/SW2/Q1", "")
    check("V2-T4.8", "Sở hữu ≠ đạt cổng" in row(proc, "I8") and "Sở hữu ≠ đạt cổng" in row(proc, "I9"),
          "hop/kinh: so huu khong thay dat cong", "")
    i1 = row(proc, "I1")
    check("V2-T4.9", "C4" in i1 and not re.search(r"L[1-8]|C6 đạt", i1), "I1 C4 khong thay C6", i1[:80])


def t5_procedure():
    print("V2-T5 quy trinh: duong dan, bon y, khong cap nguon laser")
    proc = rd(PROC)
    steps = re.split(r"^### ", proc, flags=re.M)[1:]
    miss = []
    for s in steps:
        for f in ("**Ở đâu:**", "**Làm gì:**", "**Thấy gì là đúng:**", "**Nếu sai:**"):
            if f not in s:
                miss.append((s.splitlines()[0], f))
    check("V2-T5.1", len(steps) == 6 and not miss, "6 buoc, moi buoc du 4 y", "%d buoc; thieu=%s" % (len(steps), miss))
    texts = {p: rd(p) for p in (PROC, HW, LC, PREP)}
    paths = set()
    for p, t in texts.items():
        if p == PROC:
            src = t
        else:
            src = "\n".join(l[1:] for l in git("diff", BASE + ".." + B, "--", p).splitlines()
                             if l.startswith("+") and not l.startswith("+++"))
        paths |= set(re.findall(r"`((?:docs|handoff|firmware|pc)/[^`<>* ]+?)`", src))
    paths = {q.rstrip("/") for q in paths}
    bad = sorted(q for q in paths if not Path(q).exists())
    check("V2-T5.2", not bad, "moi duong dan trong quy trinh va dong them deu ton tai", "%d duong dan; sai=%s" % (len(paths), bad))
    st = rd("STATUS.md")
    check("V2-T5.3", "](%s)" % PROC in section(st, r"^## Quy trình thao tác"),
          "STATUS muc Quy trinh thao tac co dong tro", "")
    check("V2-T5.4", not re.search(r"LASER ON|cấp nguồn 5 V cho laser|nối 5 ?V vào laser", proc),
          "khong co lenh bat laser", "")
    s4 = next((s for s in steps if s.startswith("Bước 4")), "")
    meter_on_laser = re.search(r"thông mạch giữa hai\s+dây|chế độ diode|Thông mạch thuận chiều", s4)
    check("V2-T5.5", not meter_on_laser,
          "buoc 4 'KHONG CAP NGUON' khong dat dong do cua dong ho len module laser (thong mach/diode)",
          re.sub(r"\s+", " ", meter_on_laser.group(0)) if meter_on_laser else "")
    spec9 = section(rd("docs/SPEC.md"), r"^## 9\.")
    cites = [p for p in (PREP,) if re.search(r"SPEC\.md` mục 9[^\]\n]{0,20}(yêu cầu kính|kính)|Kính B10 bắt buộc theo `docs/SPEC\.md` mục 9", rd(p))]
    check("V2-T5.6", "kính" in spec9 or not cites,
          "nhan nguon 'SPEC muc 9 yeu cau kinh' co that trong SPEC muc 9",
          "SPEC 9 co 'kinh'=%s; tep trich=%s" % ("kính" in spec9, cites))
    new_src = re.search(r"quy-trinh-tiep-nhan-laser-syd1230\.md` điều kiện 5", rd(PREP))
    r5 = row(rd("docs/procedures/quy-trinh-tiep-nhan-laser-syd1230.md"), "5")
    check("V2-T5.7", not new_src or "Kính" in r5,
          "nguon moi cho kinh (quy trinh tiep nhan dieu kien 5) that su noi kinh", r5[:70])
    if "mục 17" in rd(HW) and not re.search(r"^#+ .*17", rd(HW), re.M):
        note("V2-T5.n1", "HARDWARE.md tro 'docs/HARDWARE.md muc 17' nhung tep khong co muc 17 (la dong 17 cua bang)")


def tx_extra():
    print("TX kich ban Tester")
    proc = rd(PROC)
    i14 = row(proc, "I14")
    if "4,75" in i14 and "khi laser bật" in rd(LC):
        note("TX11", "I14 doi 5V_NUCLEO khong sut < 4,75 V truoc Q8/Q9, nhung LASER_CIRCUIT muc 4 chi do duoc khi laser bat "
             "(vong phu thuoc nhu mau thuan 6 ke hoach) - nghiem ngat hon, khong noi; Planner chot trinh tu o Q8/Q9")
    lcd = git("diff", "-U0", BASE + ".." + B, "--", LC)
    check("TX5", "@@" in lcd and "## 1." not in lcd, "LASER_CIRCUIT giu topology muc 1 (khong sua so do)", "")
    chk = git("diff", "--check", BASE + ".." + B, "--", ".", ":(exclude)docs/logs/test-c6*", ":(exclude)pc/test_c6_q5_docs.py", ":(exclude)" + HO + "03_TEST.md").strip()
    check("TX6", chk == "", "git diff --check base..B sach (tep Coder; log Tester cu khong sua)", chk[:120])
    dec = git("diff", BASE + ".." + B, "--", "DECISIONS.md")
    adds = [l for l in dec.splitlines() if l.startswith("+| D")]
    dels = [l for l in dec.splitlines() if l.startswith("-") and not l.startswith("---")]
    check("TX7", len(adds) == 1 and adds[0].startswith("+| D045 |") and not dels and "ok tôi duyệt" in adds[0],
          "DECISIONS chi them D045 co trich duyet nguoi dung", "")


COLOR = {"đen": 0, "nâu": 1, "đỏ": 2, "cam": 3, "vàng": 4, "xanh lá": 5, "xanh dương": 6,
         "tím": 7, "xám": 8, "trắng": 9}
TOL = {"nâu": 1, "nhũ vàng": 5}


def decode(bands):
    """Giai ma 4/5 vach (ten mau tieng Viet) -> (ohm, dung sai %)."""
    *digits, mult, tol = bands
    v = int("".join(str(COLOR[d]) for d in digits)) * 10 ** COLOR[mult]
    return v, TOL[tol]


def classify(nominal, tol_pct, measured):
    """Quy tac buoc 3 (Vong 3): trong [nom*(1-t), nom*(1+t)] la dung, ngoai la CHUA XAC NHAN/ngoai dung sai."""
    lo, hi = nominal * (100 - tol_pct) / 100, nominal * (100 + tol_pct) / 100
    return "trong" if lo <= measured <= hi else "ngoai"


def t_v3():
    print("V3 xu ly R01-R04 (01_PLAN Vong 3 muc 5)")
    prep, proc, plan = rd(PREP), rd(PROC), rd(HO + "01_PLAN.md")
    build_b = git("show", "%s:%s" % (B, HO + "02_BUILD.md"))
    # V3-T1 / R01 (TX4): moi dong doi trong HARDWARE_PREP base..B thuoc pham vi Vong 2 + Vong 3
    d = git("diff", "-U0", BASE + ".." + B, "--", PREP)
    added = [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in d.splitlines() if l.startswith("-") and not l.startswith("---")]
    safety = section(prep, r"^## An toàn laser")
    def allowed(l):
        m = re.match(r"\| (B\d+) \|", l)
        if m:
            return m.group(1) in ("B2", "B3", "B5", "B7", "B9", "B10")
        return l.startswith("Mượn cuối tuần") or (l.strip() and l in safety) or l.strip() == ""
    out = [l[:50] for l in added if not allowed(l)]
    rows = sorted(set(re.findall(r"^\| (B\d+) \|", "\n".join(added), re.M)))
    v3wl = section(plan, r"^## Vòng 3", r"^## ")
    check("V3-T1.1", not out and {"B3", "B9"} <= set(rows) and "B3/B9" in v3wl,
          "HARDWARE_PREP base..B: B3/B9 nay co trong whitelist Vong 3; moi dong doi thuoc pham vi",
          "dong B doi=%s; ngoai pham vi=%s" % (rows, out))
    c2 = [l for l in removed + added if l.startswith("| C2 |")]
    check("V3-T1.2", not c2, "khong cham dong thuoc cap C2 lan can", str(c2)[:80])
    sl_b = git("show", "%s:docs/SESSION_LOG.md" % B)
    sl_v3 = sl_b[sl_b.find("Chặng: Coder (Antigravity) — C6 Vòng 3"):]
    check("V3-T1.3", "vượt phạm vi whitelist Vòng 2" in build_b and "vượt phạm vi whitelist Vòng 2" in sl_v3,
          "BUILD va SESSION_LOG Vong 3 dinh chinh: luot cu vuot pham vi Vong 2", "")
    old_build = git("show", "%s:%s" % (PREV_H, HO + "02_BUILD.md"))
    check("V3-T1.4", build_b.startswith(old_build.lstrip("\ufeff").rstrip("\n")[:2000]) or old_build.lstrip("\ufeff")[:3000] in build_b,
          "BUILD giu nguyen cac vong cu (khong xoa ket luan lich su)", "")
    b3, b9 = row(prep, "B3"), row(prep, "B9")
    check("V3-T1.5", "chỉ xác nhận sở hữu" in b3 and "chưa đối chiếu" in b3 and "NGƯỜI DÙNG XÁC NHẬN 07/10" in b9,
          "B3/B9 chi nhan so huu, cong suat/dung sai chua doi chieu", "")
    # V3-T2 / R02 (TX14)
    s4 = section(proc, r"^### Bước 4", r"^### ")
    m = re.search(r"vành khía(.{0,160})", s4, re.S)
    ctx = re.sub(r"\s+", " ", m.group(1)) if m else ""
    xoay = [x for x in re.findall(r"[^.;(]*xoay[^.;)]*", s4) if not re.search(r"chưa|không", x)]
    check("V3-T2", m and "GIẢ THUYẾT" in ctx and "CHƯA KIỂM CHỨNG" in ctx and "chỉnh tiêu cự" in ctx
          and not re.search(r"vành khía chỉnh\s+tiêu cự", s4) and not xoay,
          "buoc 4: vanh khia la ngoai quan; chinh tieu cu la GIA THUYET; khong lenh xoay/bat",
          ctx[:110] + (" | lenh xoay=%s" % xoay if xoay else ""))
    # V3-T3 / R03 (TX10): quy tac so
    s3 = section(proc, r"^### Bước 3", r"^### ")
    cases = [(1, 10000, "trong"), (1, 9900, "trong"), (1, 10100, "trong"), (1, 9899, "ngoai"),
             (1, 10101, "ngoai"), (1, 10200, "ngoai"), (5, 9500, "trong"), (5, 10500, "trong"),
             (5, 9499, "ngoai"), (5, 10501, "ngoai")]
    bad = [(t, v) for t, v, exp in cases if classify(10000, t, v) != exp]
    stated = {"9900–10100": (1, 10000), "99–101": (1, 100), "14850–15150": (1, 15000),
              "9500–10500": (5, 10000), "95–105": (5, 100), "14250–15750": (5, 15000)}
    wrong = []
    for txt, (t, nom) in stated.items():
        lo, hi = (int(x) for x in txt.split("–"))
        if txt not in s3 or (lo, hi) != (nom * (100 - t) // 100, nom * (100 + t) // 100):
            wrong.append(txt)
    sai = section(s3, r"\*\*Nếu sai:\*\*", r"^### ")
    check("V3-T3.1", not bad and not wrong, "khoang ±1%/±5% ghi trong buoc 3 dung so hoc; 10 ca bien phan loai dung",
          "ca sai=%s; khoang sai/thieu=%s" % (bad, wrong))
    check("V3-T3.2", "10,2 kΩ lệch 2% là ngoài dung sai" in sai and "9899" in sai and "10101" in sai
          and "9499" in sai and "10501" in sai,
          "nhanh 'Neu sai' xu ly 10,2 kOhm ±1% (lech 2%) va cac ca ngoai bien", "")
    general = [x for x in re.findall(r"[^.]*> ±5%[^.]*", s3) if "không dùng ngưỡng chung" not in x]
    check("V3-T3.3", not general, "khong con nguong chung > ±5% (tru cau cam)", str(general)[:100])
    # V3-T4 / R03 thieu dau vao
    check("V3-T4", "không đọc được vạch màu/dung sai" in sai and "CHƯA XÁC NHẬN" in sai
          and "dừng kết luận đạt" in sai and "không mặc định ±5%" in sai,
          "khong doc duoc dung sai/thieu dau vao -> CHUA XAC NHAN, dung ket luan, khong mac dinh ±5%", "")
    # V3-T5 / R03 ma mau (TX9)
    lines = re.findall(r"- (R\d(?:, R\d)?): (\d+ k?Ω) \((.+)\)", s3)
    dec_bad, n = [], 0
    for name, nom_txt, body in lines:
        nom = int(re.match(r"\d+", nom_txt).group()) * (1000 if "k" in nom_txt else 1)
        for nb, seq, tol in re.findall(r"(\d) vạch: ([^;]+?) là ±(\d)%", body):
            bands = seq.split("-")
            n += 1
            try:
                v, t = decode(bands)
                if len(bands) != int(nb) or v != nom or t != int(tol):
                    dec_bad.append((name, seq, v, t))
            except KeyError as e:
                dec_bad.append((name, seq, "mau la %s" % e))
    plain_yellow = re.findall(r"(?<!nhũ )vàng(?! \(gold\))", re.sub(r"nhũ vàng", "", s3))
    check("V3-T5.1", n == 6 and not dec_bad, "6 chuoi ma mau giai ma dung tri danh dinh va dung sai",
          "%d chuoi; sai=%s" % (n, dec_bad))
    check("V3-T5.2", "vạch dung sai nhũ vàng" in s3 and not plain_yellow and "xanh lá" in s3
          and not re.search(r"xanh-(?!lá)", s3) and "vạch dung sai nâu" in s3,
          "vach ±5% la nhu vang; so 5 la xanh la; vach ±1% nau; khong con 'vang'/'xanh' tran",
          "vang tran=%d" % len(plain_yellow))
    # loi khai BUILD/SESSION_LOG Vong 3 ve chu da ghi phai co that trong quy trinh
    quoted = set(re.findall(r'"((?:nhũ vàng|xanh lá|nâu) \((?:gold|green|brown)\))"',
                            build_b[build_b.find("## Vòng 3"):] + sl_v3))
    missing_q = sorted(q for q in quoted if q not in s3)
    check("V3-T5.3", not missing_q, "cum tu BUILD/SESSION_LOG Vong 3 noi 'ghi ro' co that trong buoc 3",
          "khai=%s; khong co trong quy trinh=%s" % (sorted(quoted), missing_q))
    # V3-T6 / R04 (TX13): lich su STATUS
    st_c091 = git("show", "c091e1e:STATUS.md").lstrip("\ufeff")
    first = next(l for l in st_c091.splitlines() if l.startswith("Cập nhật 2026-10-07 — Chặng Coder (Antigravity), nhánh `docs/c6-laser-bringup`"))
    st_b = git("show", "%s:STATUS.md" % B).lstrip("\ufeff").splitlines()
    i_first = st_b.index(first) if first in st_b else -1
    i_l2 = next((i for i, l in enumerate(st_b) if "C6 Vòng 2 (lần 2)" in l and l.startswith("Cập nhật")), -1)
    i_l3 = next((i for i, l in enumerate(st_b) if "C6 Vòng 3" in l and l.startswith("Cập nhật")), -1)
    check("V3-T6.1", i_first > i_l2 > i_l3 >= 0, "dong Coder luot dau khop nguyen van c091e1e, nam duoi luot 2; luot 3 o tren",
          "vi tri luot3=%d luot2=%d luot1=%d" % (i_l3, i_l2, i_first))
    for frm in (PREV_H, P):
        dd = git("diff", frm + ".." + B, "--", "STATUS.md")
        dels = [l for l in dd.splitlines() if l.startswith("-") and not l.startswith("---")]
        check("V3-T6.2", not dels, "STATUS %s..B chi them" % frm[:7], "%d dong xoa" % len(dels))
    old = [l for l in git("show", "%s:STATUS.md" % PREV_H).lstrip("\ufeff").splitlines() if l.strip()]
    missing = [l[:60] for l in old if l not in st_b]
    check("V3-T6.3", not missing, "moi dong STATUS tai H cu con nguyen o B", str(missing)[:120])
    # V3-T7 TX12 + hoi quy L01-L05 (cac ca V2 o tren cung chay)
    check("V3-T7.1", "kế hoạch C6 mục 6" not in prep and prep.count("kế hoạch C6 Vòng 1 mục 6") >= 3
          and "kính" in section(plan, r"^## 6\. An toàn", r"^## "),
          "nguon kinh ghi ro Vong 1 muc 6 (B10, muc an toan, danh sach mua) va Vong 1 muc 6 that su noi kinh", "")
    check("V3-T7.2", "CHƯA XÁC NHẬN" in row(proc, "I14") and "**DỪNG**" in row(proc, "I14"),
          "TX11 khong bi bien thanh da dat: I14 van CHUA XAC NHAN/DUNG", "")
    # V3-T8 D045 voi P
    anc = lambda a, b: subprocess.run(["git", "merge-base", "--is-ancestor", a, b]).returncode == 0
    rv_p = subprocess.run(["git", "show", "%s:%s04_REVIEW.md" % (P, HO)], capture_output=True).stdout
    check("V3-T8.1", anc(H_V2, P) and anc(P, B) and hashlib.sha256(rv_p).hexdigest() == REVIEW_SHA,
          "H cu -> P -> B; REVIEW tai P dung SHA dau vong 3", hashlib.sha256(rv_p).hexdigest()[:16])
    pl_p = git("show", "%s:%s01_PLAN.md" % (P, HO))
    check("V3-T8.2", "## Vòng 3" in pl_p and pl_p.rstrip().endswith("Trạng thái: SẴN SÀNG"),
          "P chua PLAN Vong 3 SAN SANG truoc B", "")
    pb = git("diff", "--name-only", P + ".." + B, "--", HO + "01_PLAN.md", HO + "04_REVIEW.md").split()
    check("V3-T8.3", not pb, "PLAN/REVIEW khong doi P..B (khong chen PLAN/REVIEW sau P)", str(pb))
    check("V3-T8.4", build_b.rstrip().endswith("Trạng thái: SẴN SÀNG CHO TESTER") and "## Vòng 3" in build_b,
          "B chua BUILD Vong 3 SAN SANG CHO TESTER", "")
    # TX15: PLAN Vong 3 muc 7 - Coder ghi ro xu ly BOM san co truoc B moi
    bom_files = [f for f in (PROC, HO + "02_BUILD.md", "docs/SESSION_LOG.md")
                 if git("show", "%s:%s" % (H_V2, f)).startswith("\ufeff")
                 and not git("show", "%s:%s" % (B, f)).startswith("\ufeff")]
    v3_txt = build_b[build_b.find("## Vòng 3"):] + sl_b[sl_b.find("Chặng: Coder (Antigravity) — C6 Vòng 3"):]
    recs = [ln for ln in v3_txt.splitlines() if "BOM" in ln]
    named = [f for f in bom_files if any(f.split("/")[-1] in ln for ln in recs)]
    rec = bool(recs) and named == bom_files
    check("TX15", not bom_files or rec,
          "PLAN Vong 3 muc 7: Coder ghi ro xu ly BOM co san truoc B moi (BUILD/SESSION_LOG Vong 3)",
          "tep bo BOM trong %s..B=%s; dong ghi BOM=%d; tep duoc neu=%s" % (H_V2[:7], bom_files, len(recs), named))


def main():
    print("Tester C6 Q5 docs - base %s B %s HEAD %s" % (BASE[:7], B[:7], git("rev-parse", "HEAD").strip()[:7]))
    print("sha256 cong cu: %s" % sha(__file__))
    for f in (t6_scope, t1_deps, t2_timeouts, t3_inputs, t4_evidence, t5_procedure, tx_extra, t_v3):
        f()
    p, fl, n = RES.count("PASS"), RES.count("FAIL"), RES.count("NOTE")
    print("TONG: %d PASS, %d FAIL, %d NOTE" % (p, fl, n))
    return 1 if fl else 0


if __name__ == "__main__":
    sys.exit(main())
