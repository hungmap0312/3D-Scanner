#!/usr/bin/env python3
"""Tester C6 Vong 4 chang A (01_PLAN Vong 4 muc 5: V4-T1..V4-T8; Vong 5 muc 5: V5-T1..V5-T8) va kich ban TX4-*.

Chi doc Git va tep trong repo; khong mo COM/HTTP toi bo, khong cap nguon.
Hoi quy Q5 goi lai cac ca noi dung cua pc/test_c6_q5_docs.py (khong sua tep do).
Chay tu goc repo:  .venv/Scripts/python.exe -B pc/test_c6_v4_docs.py
Bien moi truong: C6V4_B (B Coder), C6V4_PREV_H (HEAD Tester truoc luot sua). Thoat 0 khi khong co FAIL.
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)
sys.path.insert(0, str(REPO / "pc"))
import test_c6_q5_docs as q5  # noqa: E402  (chi dung ham noi dung)

BASE = "9592f3adc494f8f84b18b68ca78aa67df1eadfd8"
P = "6e44ff1b180d0e092eca175e874abb472ae6ad81"          # P Vong 4 (P cu)
B4 = "b7b3c7f192c70da9b984ce72aeafb1d510fb3b9b"         # B Vong 4 (B cu)
P5 = "1be4978bd4475087ffa8ccd2a588a7d35ff681d3"         # P Vong 5 (P moi)
B = os.environ.get("C6V4_B", "f3d0e816f41a24c0387433ad377482bd6bbdf567")
B5D = "5f6c14353ab95a06bc237e4204c1e59244efb892"         # B Vong 5 lan 4
H_P6 = "136926964d2770e59415c4bb6b906afcca1e3438"        # HEAD Tester ngay truoc P6
B5C = "d0140edf49e1cde5e1bddcd65463d6134b9f3f59"         # B Vong 5 lan 3
P6 = "fe6157c20b54f4c3676c048ab14b02e629d76c3b"          # P luu REVIEW Vong 3 + SESSION_LOG Planner
H_R3 = "52ee53fbf2fe056a2ed0903595baa2ced737573d"        # H ma REVIEW Vong 3 soi
REVIEW3_SHA = "15ba3d42524cb3b2a809551462caf247451069e873ca76d95f83e46877c510dc"
B5B = "5be2a86b0d4fadd99e8c05e755683e8a0a9a4fb5"         # B Vong 5 lan 2 (REVIEW Vong 3 soi H 52ee53f)
B5A = "c2e3063ce2bf27a7dd64a7f6a0a24ef2da7356ec"         # B Vong 5 lan 1
PREV_H = os.environ.get("C6V4_PREV_H", "29ea5b8b90f2f0e943f88fb38f62a772bca5cb2c")
H_V5 = "c611ebff6786dfb8c3269427baf9e77ff1fe520f"          # HEAD Tester truoc P5 (Vong 4 + bo sung)
PNG = {"docs/logs/c6-v4-ao3400-adapter-can-2026-10-07.png": "cc0ce92a30f9023c94b2892d68e7c1110833e872f8af1e0d774ca9e31bf55140",
       "docs/logs/c6-v4-ao3400-adapter-day-2026-10-07.png": "b93c397bfe6c1173c5d7aa98ffda2c14d51121cac88e583965288ea370ba09bc"}
HO = "handoff/2026-09-21_c6-laser-bringup/"
LC, PREP, HW = "docs/design/LASER_CIRCUIT.md", "docs/HARDWARE_PREP.md", "docs/HARDWARE.md"
PROC = "docs/procedures/quy-trinh-c6-chuan-bi-mach-laser.md"
WHITELIST = {LC, PREP, HW, PROC}
ALLOWED = {"STATUS.md", "DECISIONS.md", "docs/SESSION_LOG.md", HO + "01_PLAN.md", HO + "02_BUILD.md"}
TESTER = {"pc/test_c6_v4_docs.py", HO + "03_TEST.md", "docs/SESSION_LOG.md"}


def tester_file(n):
    return n in TESTER or n.startswith("docs/logs/test-c6-v") or n.startswith("docs/logs/c6-v4-")
FROZEN = sorted(WHITELIST | {"STATUS.md", "DECISIONS.md", "ENVIRONMENT.md", HO + "01_PLAN.md",
                             HO + "02_BUILD.md", HO + "04_REVIEW.md"})
# Trich tu AOS AO3400 datasheet Rev 8 (Dec 2011), https://www.aosmd.com/pdfs/datasheet/AO3400.pdf,
# ban tai 07/10 sha256 78d25ce9d2a776f837b3db4f180c31ebbfaa0aa47c9ac296e2b54c63aeda7d24 (log trich rieng)
DS = {"VDS": "30", "ID_25C": "5,8", "RDS_10": "28", "RDS_4V5": "33", "RDS_2V5": "52"}
RES = []


def check(cid, ok, title, detail=""):
    RES.append("PASS" if ok else "FAIL")
    print(("  [%s] %s %s  | %s" % ("PASS" if ok else "FAIL", cid, title, detail)).rstrip())


def note(cid, title, detail=""):
    RES.append("NOTE")
    print(("  [NOTE] %s %s  | %s" % (cid, title, detail)).rstrip())


git, rd, row, section = q5.git, q5.rd, q5.row, q5.section


def anc(a, b):
    return subprocess.run(["git", "merge-base", "--is-ancestor", a, b]).returncode == 0


def added_removed(path):
    d = git("diff", "-U0", BASE + ".." + B, "--", path)
    add = [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
    rem = [l[1:] for l in d.splitlines() if l.startswith("-") and not l.startswith("---")]
    return add, rem


def t7_scope():
    print("V4-T7 pham vi / D045")
    names = set(git("diff", "--name-only", BASE + ".." + B).split())
    extra = sorted(n for n in names if n not in WHITELIST | ALLOWED | {HO + "03_TEST.md", HO + "04_REVIEW.md"} and not tester_file(n))
    check("V4-T7.1", not extra, "base..B ten tep trong whitelist + ho so duoc phep + tep Tester da khai", "%d tep; thua=%s" % (len(names), extra))
    prod = git("diff", "--name-only", BASE + ".." + B, "--", "firmware", "pc", "docs/SPEC.md",
               "docs/design/NUCLEO_PROTOCOL.md", "docs/reviews", "ENVIRONMENT.md", "docs/logs",
               ":(exclude)pc/test_c6_v4_docs.py", ":(exclude)docs/logs/test-c6-v*", ":(exclude)docs/logs/c6-v4-*").split()
    check("V4-T7.2", not prod, "khong cham firmware/pc/SPEC/Q3/reviews/ENVIRONMENT/log cu", str(prod))
    add, rem = added_removed(HW)
    check("V4-T7.3", not rem, "HARDWARE.md 'chi them' so voi base: 0 dong base bi sua/xoa (L10)",
          "%d dong cu bi doi: %s" % (len(rem), [r[:48] for r in rem]))
    add, rem = added_removed(PREP)
    ok_rows = {"B2", "B2b", "B5", "B7", "B9", "B10", "B13", "B14", "B15"}
    safety = section(rd(PREP), r"^## An toàn laser")
    diagram = section(rd(PREP), r"^### Sơ đồ mạch laser đề xuất cho tuần 2", r"^### Bổ sung nhóm B ngày 17/09")
    out = []
    for l in add:
        m = re.match(r"\| (B\d+b?) \|", l)
        if m:
            if m.group(1) not in ok_rows:
                out.append("dong %s" % m.group(1))
        elif l.strip() and l not in safety and l not in diagram:
            out.append(l.strip()[:45])
    check("V4-T7.4", not out, "HARDWARE_PREP: moi dong doi thuoc B2/B2b/B5/B7/B9/B10/B13-15, muc an toan, muc so do (Vong 5); B1 mua va nhom D khop base",
          "ngoai pham vi=%s" % out)
    pb = git("diff", "--name-only", P6 + ".." + B, "--", HO + "01_PLAN.md", HO + "04_REVIEW.md").split()
    pb += git("diff", "--name-only", P5 + ".." + B, "--", HO + "01_PLAN.md").split()
    chain = [anc(BASE, P), anc(P, B4), anc(B4, H_V5), anc(H_V5, P5), anc(P5, H_P6), anc(H_P6, P6), anc(P6, PREV_H), anc(PREV_H, B)]
    check("V4-T7.5", all(chain) and not pb and "## Vòng 5" in git("show", "%s:%s01_PLAN.md" % (P5, HO)),
          "base -> P4 -> B4 -> H_V5 -> P5 (PLAN Vong 5) -> H_P6 -> P6 (REVIEW Vong 3) -> H truoc -> B; PLAN khong doi P5..B, REVIEW khong doi P6..B", "chain=%s; doi=%s" % (chain, pb))
    coder = set(git("diff", "--name-only", PREV_H + ".." + B).split())
    touched = sorted(n for n in coder if tester_file(n) and n != "docs/SESSION_LOG.md")
    pngs = {f: q5.sha(f) == h for f, h in PNG.items()}
    check("V4-T7.5b", not touched and all(pngs.values()), "luot Coder (H truoc..B) khong cham test/log/anh Tester; 2 PNG giu hash",
          "cham=%s; png=%s" % (touched, pngs))
    head = git("rev-parse", "HEAD").strip()
    bh = set(git("diff", "--name-only", B + "..HEAD").split())
    bad = sorted(n for n in bh if not tester_file(n))
    check("V4-T7.6", anc(B, "HEAD") and not bad, "B to tien HEAD; B..HEAD chi tep Tester", "HEAD=%s; thua=%s" % (head[:7], bad))
    mism = []
    for p in FROZEN:
        a, h, w = (git("rev-parse", "%s:%s" % (B, p)).strip(), git("rev-parse", "HEAD:%s" % p).strip(),
                   git("hash-object", p).strip())
        print("      blob %s B=%s HEAD=%s WT=%s sha256(WT)=%s" % (p, a[:10], h[:10], w[:10], q5.sha(p)[:16]))
        if not (a == h == w):
            mism.append(p)
    check("V4-T7.7", not mism, "san pham/PLAN/BUILD/REVIEW/STATUS/DECISIONS/ENV bat bien B..H", str(mism))
    dec = git("diff", BASE + ".." + B, "--", "DECISIONS.md")
    adds = [l for l in dec.splitlines() if l.startswith("+| D")]
    dels = [l for l in dec.splitlines() if l.startswith("-") and not l.startswith("---")]
    check("V4-T7.8", [a[:8] for a in adds] == ["+| D046 ", "+| D047 "] and not dels, "DECISIONS chi them D046, D047 (D046 giu nguyen)",
          str([a[:8] for a in adds]))
    for p in ("STATUS.md", "docs/SESSION_LOG.md"):
        d = git("diff", BASE + ".." + B, "--", p)
        dl = [l for l in d.splitlines() if l.startswith("-") and not l.startswith("---")]
        check("V4-T7.9", not dl, "%s base..B chi them" % p, "%d dong xoa" % len(dl))
    chk = git("diff", "--check", BASE + ".." + B, "--", ".", ":(exclude)docs/logs/test-c6-v*", ":(exclude)docs/logs/c6-v4-*").strip()
    check("V4-T7.10", chk == "", "git diff --check base..B sach", chk[:100])
    build = git("show", "%s:%s02_BUILD.md" % (B, HO))
    v5 = build[build.find("## Vòng 5"):]
    full = sorted(set(re.findall(r"\b[0-9a-f]{40}\b", v5)))
    need = {"P cu": P, "B cu": B4, "P moi": P5}
    old_wrong = "6e44ff18a1a364be16a542b4777efec92728d1ae"
    unknown = [h for h in full if h != old_wrong and git("cat-file", "-t", h).strip() != "commit"]
    missing = [k for k, h in need.items() if h not in v5]
    check("V4-T7.11", not unknown and not missing,
          "L12: moi hash 40 ky tu trong BUILD Vong 5 la commit that; co P cu, B cu, P moi dung Git", "sai=%s; thieu=%s" % (unknown, missing))
    sl_b = git("show", "%s:docs/SESSION_LOG.md" % B)
    i5 = sl_b.find("Chặng: Coder (Antigravity) — C6 Vòng 5 ")
    sl_v5 = sl_b[i5:sl_b.find("\n## ", i5)]
    check("V4-T7.11b", old_wrong in build and old_wrong in v5 and P in v5 and P in sl_v5,
          "L12: hash sai cu giu o lich su, co dinh chinh trong BUILD Vong 5 va SESSION_LOG Coder", "")
    check("V4-T7.12", build.rstrip().endswith("Trạng thái: SẴN SÀNG CHO TESTER"), "cong BUILD SAN SANG CHO TESTER", "")


def t1_q1():
    print("V4-T1 chot Q1 AO3400")
    d046 = row(rd("DECISIONS.md"), "D046")
    check("V4-T1.1", "AO3400" in d046 and "A09T" in d046 and "IRFZ44N" in d046 and "người dùng cung cấp" in d046,
          "D046 ghi AO3400 thay IRFZ44N, A09T mang nhan nguoi dung", "")
    texts = {p: rd(p) for p in (LC, PREP, HW, PROC)}
    d047 = row(rd("DECISIONS.md"), "D047")
    check("V4-T1.1b", "5,8 A" in d047 and "AO3400A" in d047 and "D046" in d047, "D047 dinh chinh D046 (5,8 A, BOM A06 = AO3400A)", "")
    texts["DECISIONS.md#D047"] = d047
    texts[HO + "02_BUILD.md#V5"] = rd(HO + "02_BUILD.md")[rd(HO + "02_BUILD.md").find("## Vòng 5"):]
    bad_rds = [p for p, t in texts.items() for m in re.finditer(r"AO3400(?!A)[^|\n]{0,200}?(\d+) mΩ tại Vgs = 2,5 V", t)
               if m.group(1) != DS["RDS_2V5"]]
    check("V4-T1.2", not bad_rds and "52 mΩ tại Vgs = 2,5 V" in texts[LC],
          "Rds(on) AO3400 @2,5 V = 52 mOhm (AOS Rev 8); khong lan AO3400A 48", str(bad_rds))
    four = [p for p, t in texts.items() if re.search(r"33 mΩ tại Vgs = 4,5 V", t)]
    four_bad = [p for p, t in texts.items() if re.search(r"(?<!\d)(?!33)\d\d mΩ tại Vgs = 4,5 V", t)]
    check("V4-T1.3", not four_bad, "Rds(on) @4,5 V neu co ghi = 33 mOhm (AOS Rev 8)", "co ghi o %s" % four)
    id_hits = {p: re.findall(r"I[dD][^|\n]{0,25}?(\d+,\d) A", t) for p, t in texts.items()}
    id_bad = {p: v for p, v in id_hits.items() if any(x != DS["ID_25C"] for x in v)}
    check("V4-T1.4", not id_bad, "Id lien tuc AO3400 ghi theo AOS Rev 8 phai la 5,8 A (TA=25C, VGS=10V)",
          "ghi sai=%s" % id_bad)
    a06 = [p for p, t in texts.items() if re.search(r"AO3400(?!A)\*{0,2} \(BOM A06", t)]
    hist = git("show", "%s:%s" % (BASE, PREP))
    check("V4-T1.5", not a06 or "AO3400 trong BOM A06" in hist,
          "khong gan AO3400 vao BOM A06 khi ho so cu ghi A06 la AO3400A",
          "ho so cu: 'AO3400A trong BOM A06'=%s; nay gan AO3400=%s" % ("AO3400A trong BOM A06" in hist, a06))
    check("V4-T1.6", "## 0c." in texts[LC] and "IRFZ44N 258X 77 WS" in texts[LC] and "IRFZ44N 258X 77 WS" in texts[HW],
          "lich su IRFZ44N con nguyen (LASER_CIRCUIT 0c, HARDWARE.md)", "")
    vds = re.search(r"Vds tối đa (\d+) V", texts[LC])
    check("V4-T1.7", vds and vds.group(1) == DS["VDS"], "VDS max 30 V khop AOS Rev 8", vds.group(0) if vds else "")


def t2_pins():
    print("V4-T2 chan SOT-23 / adapter")
    pins = {p: bool(re.search(r"Pin 1 = Gate[^\n]{0,20}Pin 2 = Source[^\n]{0,20}Pin 3 = Drain", rd(p)))
            for p in (LC, PREP, HW)}
    proc = rd(PROC)
    pins[PROC] = bool(re.search(r"Pin 1[^\n]*Gate \(G\)\s*\n\s*- Pin 2[^\n]*Source \(S\)\s*\n\s*- Pin 3[^\n]*Drain \(D\)", proc))
    check("V4-T2.1", all(pins.values()), "4 tep ghi SOT-23 Pin1=G, Pin2=S, Pin3=D (khop Top View AOS: D tren, G S duoi)", str(pins))
    lc = rd(LC)
    sch = section(lc, r"^## 1\.", r"^## ")
    check("V4-T2.2", "Q1.D (Pin 3)" in sch and "Q1.G (Pin 1)" in sch and "Q1.S (Pin 2)" in sch
          and not re.search(r"Pin 2\)?[^\n]{0,5}Drain|Drain \(Pin 2", lc + rd(PREP)),
          "so do muc 1 dung chan SOT-23, khong chep TO-220 (2=D)", "")
    i16 = row(proc, "I16")
    hw_ad = row(rd(HW), "Adapter AO3400 tự làm")
    check("V4-T2.3", "CHƯA KIỂM CHỨNG" in i16 and "**DỪNG**" in i16 and "Bước 2a" in i16 and "Bước 2a" in hw_ad,
          "adapter tu lam: chua kiem nhan -> DUNG cam breadboard cho toi Buoc 2a", i16[:70])


def t3_load():
    print("V4-T3 tai gia")
    i, p = 5.25 / 114, 5.25 ** 2 / 114
    pr1 = 5.25 ** 2 / 100
    lc = rd(LC)
    check("V4-T3.1", abs(i * 1000 - 46.05) < 0.01 and abs(p - 0.242) < 0.001 and "46,05 mA" in lc and "0,242 W" in lc,
          "tinh doc lap: 5,25/114 = %.2f mA, 5,25^2/114 = %.4f W khop van ban" % (i * 1000, p), "")
    check("V4-T3.2", "0,276 W" in lc and abs(pr1 - 0.2756) < 0.001 and "không dùng điện trở R1 100 Ω 1/4 W" in lc,
          "R1 100 Ohm 1/4 W khong lam tai: 5,25^2/100 = %.3f W > 0,25 W" % pr1, "")
    rows = {"HW": row(rd(HW), "Tải giả C6 (Rtest)"), "PREP": row(rd(PREP), "B15"), "PROC": row(rd(PROC), "I17")}
    check("V4-T3.3", all("CHƯA CÓ" in r for r in rows.values()) and all("1 W" in r for r in rows.values()),
          "Rtest >= 1 W chi la DE XUAT, CHUA CO o 3 tep; khong coi tinh toan la so do", "")
    st2 = section(lc, r"2\. \*\*Giai đoạn 2", r"^3\. ")
    check("V4-T3.4", "laser tháo" in st2 and not re.search(r"song song[^\n]{0,30}laser", st2),
          "tai gia thay tai J1, laser thao, khong mac song song laser", "")


def t4_seq():
    print("V4-T4 trinh tu TX11 / nguon")
    lc = rd(LC)
    s5 = section(lc, r"^## 5\.", r"^## 6\.")
    pos = [s5.find("Giai đoạn %d" % k) for k in (1, 2, 3, 4)]
    check("V4-T4.1", all(x >= 0 for x in pos) and pos == sorted(pos), "4 giai doan theo thu tu tien kiem -> tai gia -> laser -> nghiem thu", str(pos))
    g1 = section(s5, r"Giai đoạn 1", r"^2\. ")
    check("V4-T4.2", "không cấp điện" in g1 and not re.search(r"4,75|Vds ≤|đo L[13]", g1),
          "giai doan 1 khong doi so do co tai (phu thuoc vong da bo)", re.sub(r"\s+", " ", g1)[:90])
    s4 = section(lc, r"^## 4\.", r"^## 5\.")
    check("V4-T4.3", "300 mA khi JP1 = OFF" in s4 and "100 mA khi JP1 = ON" in s4 and "không phải là 300 mA trọn vẹn" in s4
          and "backfeed" in s4, "UM1724: 300/100 mA la tong bo+tai; canh bao backfeed", "")
    l1, l3 = row(lc, "L1"), row(lc, "L3")
    check("V4-T4.4", "4,75–5,25 V" in l1 and "≤ 0,2 V" in l3, "khong ha nguong L1/L3", "")
    i14 = row(rd(PROC), "I14")
    check("V4-T4.5", "**DỪNG**" in i14 and "tiền kiểm" in i14 and "4,75" not in i14,
          "I14 khong con doi so do co tai truoc chinh phep thu (TX11)", i14[:90])
    g3 = section(s5, r"3\. \*\*Giai đoạn 3", r"^4\. ")
    if not re.search(r"driver|hạn dòng", g3):
        note("TX4-1", "LASER_CIRCUIT giai doan 3 (lan dau cap nguon laser) khong neu cong driver han dong; cong nay co o quy trinh Cong 3/I13 va LASER_CIRCUIT 0b")


def t5_sw():
    print("V4-T5 SW1/SW2 / an toan")
    files = {p: rd(p) for p in (LC, PREP, HW, PROC)}
    sw = {p: ("CHƯA CÓ" in t and "chưa có cả 2" in t) for p, t in files.items()}
    check("V4-T5.1", all(sw.values()), "SW1/SW2 ghi CHUA CO (nguoi dung 07/10) o 4 tep", str(sw))
    byp = [p for p, t in files.items() for m in re.finditer(r"[^\n.]*jumper[^\n.]*", t)
           if re.search(r"bypass|thay (cho )?(SW|công tắc)", m.group(0)) and not re.search(r"không|tuyệt đối", m.group(0))]
    check("V4-T5.2", not byp, "khong cho bypass SW1/SW2 bang jumper", str(byp))
    wrong = []
    for p, t in files.items():
        # tach menh de; menh de khang dinh "de can ... COM-NC kin" la sai voi SPDT (de can -> COM-NC ho)
        for cl in re.split(r"[;.\n|]", t):
            if re.search(r"đè cần[^;.]*COM–NC kín", cl) and not re.match(r"\s*không mặc định", cl, re.I):
                wrong.append((p, re.sub(r"\s+", " ", cl.strip())[:90]))
    check("V4-T5.3", not wrong,
          "khong khang dinh 'cua dong de can -> COM-NC kin' (SPDT: de can thi COM-NC HO, COM-NO kin; PLAN Vong 4 cam mac dinh)",
          str(wrong))
    gates = []
    for p in (LC, PREP, PROC):
        for m in re.finditer(r"(Chỉ bật laser khi:|Không bật laser trước khi:)(.*?)(?:\n- |\n\n|\Z)", files[p], re.S):
            body = m.group(2)
            if not (re.search(r"cửa|SW1", body) and re.search(r"dừng|estop|SW2", body)):
                gates.append((p, m.group(1), re.sub(r"\s+", " ", body)[:80]))
    check("V4-T5.4", not gates, "moi danh sach dieu kien bat laser deu co SW1 cua va SW2 nut dung", str(gates))
    alt = [(p, m.group(0).strip()[:70]) for p, t in files.items()
           for m in re.finditer(r"[^.;\n]*driver[^.;\n]*hoặc (xác nhận )?an toàn L2[^.;\n]*", t)]
    check("V5-T2.1", not alt, "cong driver truoc khi cap nguon laser khong co phuong an 'hoac an toan L2' chua dinh nghia "
          "(quy trinh Cong 3/I13 doi driver bat buoc; PLAN V4 muc 4.6: quyet dinh khac phai do Planner/nguoi dung chot)", str(alt))
    kw = [p for p, t in files.items() if "KW11" in t]
    kw_bad = [p for p in kw if not re.search(r"không coi KW11 là SW1 chính thức|thử gá[^\n|]{0,20}không (cấp )?điện", files[p])]
    check("V4-T5.5", kw and not kw_bad, "KW11 chi la tam/thu ga khong dien, khong la SW1 chinh thuc", "co KW11=%s; thieu gioi han=%s" % (kw, kw_bad))
    c3 = section(files[PROC], r"\*\*Cổng 3", r"\n- \*\*Thấy")
    check("V4-T5.6", re.search(r"driver", c3) and "dòng danh định" in c3 and "B5" in c3 and "B10" in c3,
          "quy trinh Cong 3 (laser that) giu driver, L2, hop, kinh", "")


def t6_regress():
    print("V4-T6 hoi quy Q5 (goi ca noi dung cua pc/test_c6_q5_docs.py)")
    superseded = {"V2-T3.3": "xung dot IRFZ44N da giai quyet bang D046 (PLAN Vong 4) -> V4-T1",
                  "V2-T4.7": "I12 Q1 nay DA CHOT (D046) -> V4-T5.1/V4-T2.3 kiem I10/I11/I16 DUNG",
                  "V2-T5.1": "PLAN Vong 5 them Buoc 2a (7 buoc) -> V5-T6.0 kiem moi buoc du 4 y"}
    orig_check = q5.check

    def relay(cid, ok, title, detail=""):
        if cid in superseded and not ok:
            note("Q5/" + cid, "thay the theo PLAN Vong 4: " + superseded[cid], title)
        else:
            check("Q5/" + cid, ok, title, detail)
    q5.check = relay
    try:
        for f in (q5.t2_timeouts, q5.t3_inputs, q5.t4_evidence, q5.t5_procedure):
            f()
    finally:
        q5.check = orig_check
    proc = rd(PROC)
    check("V4-T6.1", "**DỪNG**" in row(proc, "I10") and "**DỪNG**" in row(proc, "I11"), "I10/I11 SW1/SW2 van DUNG", "")
    s3 = section(proc, r"^### Bước 3", r"^### ")
    lines = re.findall(r"- (R\d(?:, R\d)?): (\d+ k?Ω) \((.+)\)", s3)
    n, bad = 0, []
    for name, nom_txt, body in lines:
        nom = int(re.match(r"\d+", nom_txt).group()) * (1000 if "k" in nom_txt else 1)
        for nb, seq, tol in re.findall(r"(\d) vạch: ([^;]+?) là ±(\d)%", body):
            n += 1
            v, t = q5.decode(seq.split("-"))
            if v != nom or t != int(tol):
                bad.append(seq)
    check("V4-T6.2", n == 6 and not bad and "10,2 kΩ lệch 2% là ngoài dung sai" in s3
          and "nhũ vàng (gold)" in s3 and "xanh lá (green)" in s3 and "nâu (brown)" in s3,
          "buoc 3 (R03/L06) giu: 6 chuoi mau dung, 10,2 kOhm ngoai dung sai, chu thich mau", "%d chuoi; sai=%s" % (n, bad))
    s4 = section(proc, r"^### Bước 4", r"^### ")
    check("V4-T6.3", "GIẢ THUYẾT" in s4 and "Tuyệt đối không đo điện" in s4, "buoc 4 (R02/L04) giu nhan gia thuyet, cam do dien len laser", "")
    st_old = [l for l in git("show", "%s:STATUS.md" % BASE).splitlines() if l.strip()]
    st_new = git("show", "%s:STATUS.md" % B).splitlines()
    miss = [l[:50] for l in st_old if l not in st_new]
    check("V4-T6.4", not miss, "STATUS: moi dong o base con nguyen (R04)", str(miss)[:100])
    prep = rd(PREP)
    check("V4-T6.5", prep.count("kế hoạch C6 Vòng 1 mục 6") >= 3 and "chỉ xác nhận sở hữu" in row(prep, "B3"),
          "nguon kinh (TX12) va nhan so huu B3 (R01) giu nguyen", "")


def t8_handoff():
    print("V4-T8 ban giao")
    build = rd(HO + "02_BUILD.md")
    v4 = build[build.find("## Vòng 4"):]
    claim = re.findall(r"[^\n]*(C6 phần cứng (đã )?đạt|L1–L8 (đã )?ĐẠT|nghiệm thu (đã )?đạt)[^\n]*", v4)
    claim = [c for c in claim if not re.search(r"không|CHƯA", c[0] if isinstance(c, tuple) else c)]
    check("V4-T8.1", not claim and "CHƯA THỰC HIỆN" in v4 and "không nhận phần cứng C6 đạt" in v4,
          "BUILD chi nhan xong thiet ke Q5, khong nhan C6 phan cung dat", str(claim)[:80])
    c2 = section(rd(PROC), r"\*\*Cổng 2", r"\+ \*\*Cổng 3")
    check("V4-T8.2", "kế hoạch Q8" in c2 and "SW1/SW2" in c2 and "120 Ω" in c2 and "laser tháo" in c2,
          "Cong 2 (Q8 tai gia) chi mo khi co ke hoach Q8 rieng + SW1/SW2 + adapter + Rtest, laser thao", "")


def t_r05_r06():
    print("R05/R06 (04_REVIEW Vong 3) va ho so luot sua")
    lc = rd(LC)
    s4 = section(lc, r"^## 4\.", r"^## 5\.")
    refuse = [l for l in s4.splitlines() if re.search(r"từ chối|không chấp thuận|chưa/không enumeration", l)]
    bad = [l[:90] for l in refuse if "100 mA" in l.split("không suy")[0] or "dừng phép thử" not in l]
    check("R05.1", refuse and not bad,
          "UM1724: host tu choi/khong enumeration -> MCU/tai khong co nguon, dung phep thu; khong suy 100 mA",
          "dong=%d; sai=%s" % (len(refuse), bad))
    on = [l for l in s4.splitlines() if "JP1 = ON" in l]
    check("R05.2", on and all("100 mA" in l and "không chấp thuận" not in l for l in on),
          "nhanh JP1 = ON tach rieng, 100 mA cho bo+tai", "")
    others = [f for f in (PREP, HW, PROC) if re.search(r"100 mA[^\n|]{0,40}(từ chối|không chấp thuận)", rd(f))]
    check("R05.3", not others, "khong tai lap 'host tu choi -> 100 mA' o tep khac", str(others))
    s2a = section(rd(PROC), r"^### Bước 2a", r"^### ")
    hdr = next((l for l in s2a.splitlines() if l.startswith("| Cặp đo")), "")
    rows = [l for l in s2a.splitlines() if l.startswith("| ") and not l.startswith("| Cặp đo") and not l.startswith("| ---")]
    undecl = [r.split("|")[3].strip() for r in rows if "dự kiến" not in r.split("|")[3]]
    check("R06.1", "dự kiến" in hdr and "cần đối chiếu" in s2a and not undecl,
          "R06: cot va moi o dao dong ghi 'du kien', loi dan yeu cau doi chieu hien vat", "o thieu=%s" % undecl)
    hw = rd(HW)
    check("VOM.1", "Đồng hồ vạn năng — cập nhật 08/10" in hw and "08/10" in row(rd(PREP), "B9") and "08/10" in row(rd(PROC), "I7"),
          "dau vao 08/10: VOM muon nhan 10/10 ghi them o HARDWARE/B9/I7, giu lich su 07/10", "")
    build = git("show", "%s:%s02_BUILD.md" % (B, HO))
    last = build[build.rfind("\n## Vòng"):]
    decl = re.findall(r"^- Phạm vi tệp:.*$", last, re.M)
    sect = decl[-1] if decl else ""
    claimed = set(re.findall(r"`((?:docs|handoff)/[^`]+\.md|STATUS\.md|DECISIONS\.md)`", sect))
    actual = set(git("diff", "--name-only", PREV_H + ".." + B).split())
    check("BUILD.1", claimed and claimed == actual,
          "BUILD vong moi nhat: 'Pham vi tep' khop dung cac tep cua luot Coder (H truoc..B)",
          "khai=%s; thuc=%s" % (sorted(claimed), sorted(actual)))
    old_build = git("show", "%s:%s02_BUILD.md" % (B5C, HO))
    keep = old_build.rstrip("\n")
    check("BUILD.2", build.startswith(keep),
          "vong BUILD cu giu nguyen, chi them vong moi (PLAN Vong 5 muc 3: khong sua/xoa BUILD cu; AGENTS: them Vong k, khong xoa vong truoc)",
          "BUILD tai B bat dau bang nguyen BUILD tai %s = %s" % (B5C[:7], build.startswith(keep)))
    prev4 = git("show", "%s:%s02_BUILD.md" % (B5D, HO)).split("\n")
    orig = old_build.split("\n")
    fixed = [orig[i] if i < len(orig) and prev4[i] != orig[i] and i == 371 else prev4[i] for i in range(len(prev4))]
    diff_lines = [i + 1 for i in range(min(len(prev4), len(orig))) if prev4[i] != orig[i]]
    check("BUILD.3", build.startswith("\n".join(fixed).rstrip("\n")) and diff_lines == [372],
          "L17: BUILD tai B = BUILD tai 5f6c143 (giu Vong 5 lan 4) voi dong 372 tra nguyen van d0140ed, roi them vong moi",
          "dong lan 4 khac d0140ed=%s" % diff_lines)
    p6_files = sorted(git("diff", "--name-only", H_P6 + ".." + P6).split())
    p6_dels = [l for l in git("diff", H_P6 + ".." + P6).splitlines() if l.startswith("-") and not l.startswith("---")]
    check("P6.1", p6_files == ["docs/SESSION_LOG.md", HO + "04_REVIEW.md"] and not p6_dels,
          "moc P6 chi them 04_REVIEW Vong 3 va muc Planner SESSION_LOG, 0 dong xoa", "%s; xoa=%d" % (p6_files, len(p6_dels)))
    rv_b = subprocess.run(["git", "show", "%s:%s04_REVIEW.md" % (B, HO)], capture_output=True).stdout
    rv_p6 = subprocess.run(["git", "show", "%s:%s04_REVIEW.md" % (P6, HO)], capture_output=True).stdout
    check("REVIEW.0", hashlib.sha256(rv_p6).hexdigest() == REVIEW3_SHA == hashlib.sha256(rv_b).hexdigest(),
          "REVIEW tai P6 = tai B = ban cay lam viec Tester ghi luot truoc (sha256 15ba3d42...)", hashlib.sha256(rv_p6).hexdigest()[:16])
    rv_wt = Path(HO + "04_REVIEW.md").read_bytes()
    soi = "Commit đang soi (H): " + H_R3
    check("REVIEW.1", rv_b == rv_wt and soi in rv_b.decode("utf-8", "replace"),
          "04_REVIEW Vong 3 (phan quyet dan luot sua nay) da luu trong Git truoc/tai B, cay lam viec trung B (D045; PLAN V3/V5: luu REVIEW truoc B)",
          "REVIEW tai B co phan quyet soi H %s=%s; cay lam viec co=%s; cay lam viec trung B=%s"
          % (H_R3[:7], soi in rv_b.decode("utf-8", "replace"), soi in rv_wt.decode("utf-8", "replace"), rv_b == rv_wt))


def t_v5():
    print("V5 L08-L12 va buoc 2a (01_PLAN Vong 5 muc 5)")
    prods = {f: rd(f) for f in (LC, PREP, HW, PROC)}
    nham = [f for f, t in prods.items() if "nhận nhầm" in t]
    check("V5-T1.1", not nham, "khong con 'nhan nham' trong 4 san pham (TX4-3)", str(nham))
    bh = [f for f, t in prods.items() if re.search(r"bảo đảm dẫn bão hoà hoàn toàn|giải quyết triệt để", t)]
    check("V5-T1.2", not bh, "khong khang dinh 'bao dam dan bao hoa hoan toan/giai quyet triet de' cho A09T chua do (TX4-2)", str(bh))
    check("V5-T3.1", "**Mượn** cuối tuần" in row(prods[PREP], "B9") and row(git("show", "%s:%s" % (BASE, PREP)), "B1")
          in prods[PREP].splitlines(), "B9 giu lich su muon (TX4-4); dong B1 bang mua khop base", "")
    check("V5-T3.2", "chân 5V trên CN7, đối chiếu" in prods[PREP], "so do: chan 5V CN7 co ghi doi chieu nhan bo/UM1724 (TX4-5)", "")
    dip = [f for f, t in prods.items() if re.search(r"bước 2,54|header DIP liền|ra DIP 3 chân", t)]
    check("V5-T5.1", not dip, "khong con bat buoc header/bo chuyen DIP 2,54 mm", str(dip))
    ad = [f for f, t in prods.items() if not all(x in t for x in PNG)]
    check("V5-T5.2", not ad, "4 san pham ghi adapter tu lam kem 2 anh", "thieu anh o %s" % ad)
    proc = prods[PROC]
    steps = re.split(r"^### ", proc, flags=re.M)[1:]
    miss = [(st.splitlines()[0][:20], f) for st in steps
            for f in ("**Ở đâu:**", "**Làm gì:**", "**Thấy gì là đúng:**", "**Nếu sai:**") if f not in st]
    check("V5-T6.0", len(steps) == 7 and not miss, "quy trinh 7 buoc (them 2a), moi buoc du 4 y", "%d buoc; thieu=%s" % (len(steps), miss))
    s2a = section(proc, r"^### Bước 2a", r"^### ")
    check("V5-T6.1", bool(s2a) and all(k in s2a for k in ("**Ở đâu:**", "**Làm gì:**", "**Thấy gì là đúng:**", "**Nếu sai:**")),
          "co Buoc 2a du 4 y", "")
    check("V5-T6.2", "không nối Nucleo" in s2a and "không nối USB" in s2a and "module laser" in s2a,
          "Buoc 2a co lap adapter (khong Nucleo/USB/tai/laser)", "")
    hdr = next((l for l in s2a.splitlines() if l.startswith("| Cặp đo")), "")
    cols = [c.strip() for c in hdr.strip("|").split("|")]
    has_color = any("màu" in c.lower() for c in cols)
    has_island = any("đảo" in c.lower() for c in cols)
    check("V5-T6.3", has_color and has_island,
          "bang Buoc 2a co cot dao dong va mau day (PLAN V5 muc 4: pin <-> dao <-> mau day <-> dau cam <-> thang/chieu que <-> ket qua)",
          "cot=%s" % cols)
    rows = [l for l in s2a.splitlines() if l.startswith("| ") and not l.startswith("| Cặp đo") and not l.startswith("| ---")]
    filled = [r[:40] for r in rows if "(để trống)" not in r or "Chưa đo" not in r]
    check("V5-T6.4", rows and not filled, "bang chua dien so do/PASS gia", "%d dong; da dien=%s" % (len(rows), filled))
    thr = re.findall(r"0,5\s*V?\s*[–-]\s*0,9\s*V|0,5\s*[–-]\s*2\s*mA", s2a)
    check("V5-T7.1", not thr,
          "khong tu dat nguong diode/dong thu VOM khong co nguon (PLAN V5: chua co co so so do thi chi sang loc, khong che nguong V/Ohm moi)",
          "nguong tu dat=%s" % thr)
    vom = re.search(r"[^.]*chưa rõ model VOM[^.]*", s2a)
    check("V5-T7.2", not vom or "dừng" in vom.group(0).lower(),
          "thieu thong so VOM -> ghi thieu dau vao va DUNG phep do tuong ung (khong chi 'can trong')",
          re.sub(r"\s+", " ", vom.group(0))[:110] if vom else "")
    check("V5-T7.3", "xả điện tích Gate" in s2a and "KHÔNG yêu cầu cả hai chiều D–S đều là OL" in s2a and "beep" in s2a
          and re.search(r"I_S = 1|1 A", s2a), "Buoc 2a xet xa gate, khong doi OL ca hai chieu D-S, canh bao beep, VSD @1 A khong lam nguong", "")


def tx_extra():
    print("TX4 kich ban Tester them")
    print("  (TX4-2..TX4-5 da chuyen thanh ca V5-T1.1, V5-T1.2, V5-T3.1, V5-T3.2)")


def main():
    print("Tester C6 Vong 4 - base %s P %s B %s HEAD %s" % (BASE[:7], P[:7], B[:7], git("rev-parse", "HEAD").strip()[:7]))
    print("sha256 cong cu: %s" % q5.sha(__file__))
    for f in (t7_scope, t1_q1, t2_pins, t3_load, t4_seq, t5_sw, t6_regress, t8_handoff, t_v5, t_r05_r06, tx_extra):
        f()
    p, fl, n = RES.count("PASS"), RES.count("FAIL"), RES.count("NOTE")
    print("TONG: %d PASS, %d FAIL, %d NOTE" % (p, fl, n))
    return 1 if fl else 0


if __name__ == "__main__":
    sys.exit(main())
