# Nguồn và mức tin cậy

Ngày tổng hợp nguồn ban đầu: 15/09/2026; cập nhật hiệu lực 08/10/2026 (D048).

**Người dùng đã duyệt kế hoạch rút gọn theo nhánh G/A/B/C/D/E/H1–H4/V/R/F.**
SPEC và ROADMAP Markdown cùng hai DOCX nguồn được đồng bộ theo quyết định
này. Yêu cầu mới thay phần phạm vi/kế hoạch từ sau tuần 2 của bản 15/09;
không thay lịch sử phép thử, tuần 2, an toàn hay thông số phần cứng.
Các nhãn tuần còn trong hồ sơ phần cứng đối chiếu ROADMAP §8.

Bản cũ của tài liệu được Git giữ. Báo cáo tiến độ có ngày, handoff và kho
review là lịch sử, không sửa kết quả cũ thành yêu cầu/kết quả mới. Báo cáo
trình bày kế hoạch cần theo D048; script dựng cũ là mã nguồn, được giữ
nguyên theo chỉ định người dùng và có thể sinh lại phạm vi cũ nếu chạy.


| Nguồn | Nội dung sử dụng | Cách hiểu |
| --- | --- | --- |
| `Mo_ta_chi_tiet_may_quet_3D_laser_STM32_ESP32S3.docx`, cập nhật 15/09/2026 | Toàn bộ 17 mục, đã trích toàn văn 19/09 vào `docs/SPEC.md` | Bản hiện hành cập nhật phần phạm vi/kế hoạch D048; yêu cầu không đồng nghĩa đã triển khai |
| `Roadmap_14_tuan_may_quet_3D_STM32_ESP32S3.docx`, cơ sở 15/09/2026 | Toàn bộ 14 tuần, quy cách đo, bảng nghiệm thu, biểu mẫu tuần; trích toàn văn 19/09 vào `docs/SPEC.md` | Tên tệp lịch sử được giữ; nội dung sau tuần 2 đổi sang nhánh/hội tụ D048; tuần 1–2 giữ nguyên |
| `BOM_may_quet_3D_ESP32_CAM_ESP32_S3.xlsx`, bản lưu 14/09/2026 | Nhận diện cấu hình camera/kiến trúc cũ | Chưa cập nhật theo mô tả 15/09; không làm nguồn cấu hình hiện tại |
| `docs/SPEC.md`, tổng hợp 19/09/2026 | Bản đối chiếu yêu cầu và chỉ tiêu gom từ ba tệp trên, có số mục bản gốc | Đặc tả hiện hành theo D048; phải thống nhất với ROADMAP và DOCX cập nhật, không dùng bản 15/09 để phủ định D048 |
| `quy-trinh-rd-phan-cung-phan-mem-2021.png`, ảnh sơ đồ © 2021 Nguyễn Đức Minh, Viện ĐTVT ĐHBKHN, người dùng dán 20/09/2026 | Quy trình thiết kế chín bước; văn bản hoá tại `docs/PROCESS.md` | Luật về thứ tự làm việc và sản phẩm mỗi bước (D017); không phải nguồn yêu cầu kỹ thuật, không thay SPEC hay roadmap |
| Trao đổi test camera ngày 14/09/2026 | ESP32-CAM đã lên hình; S3 log Flash 16 MB, PSRAM 0 KB, PID 0x3660 | Kết quả người dùng báo, chưa phải phép thử trực tiếp của trợ lý |

Các tài liệu nguồn hiện nằm trong `docs/reference/`. Giữ tên tệp để không làm hỏng liên kết; ngày và hiệu lực cập nhật ghi trong tài liệu. BOM cũ là nguồn lịch sử phần cứng, không tự ghi đè quyết định mới.

Nguồn chính thức dùng cho cách tổ chức môi trường:

- [OpenAI: Projects and chats](https://learn.chatgpt.com/docs/projects)
- [OpenAI: Memories](https://learn.chatgpt.com/docs/customization/memories)
- [OpenAI: AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [OpenAI: Codex IDE extension](https://learn.chatgpt.com/docs/codex/ide)
- [VS Code: Getting started](https://code.visualstudio.com/docs/getstarted/overview)
- [Git: First-time setup](https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup)
- [Python: venv](https://docs.python.org/3/library/venv.html)
