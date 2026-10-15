"""Tải bài Wikipedia tiếng Việt về data/domain/<nhãn>/wiki_<tên>.txt để mở rộng tập huấn luyện phân loại lĩnh vực.

Chạy:   python scripts/fetch_wikipedia_data.py
        python scripts/fetch_wikipedia_data.py --only networks databases     (chỉ vài nhãn)
        python scripts/fetch_wikipedia_data.py --dry-run                     (chỉ liệt kê tiêu đề)
Rồi:    python scripts/train_domain_classifier.py --data data/domain --loo
        python scripts/evaluate_reliability.py --data data/domain

Chỉ dùng thư viện chuẩn, cần có mạng. Nguồn: MediaWiki API của vi.wikipedia.org.
Giấy phép: văn bản Wikipedia là CC BY-SA 4.0, BẮT BUỘC ghi nguồn. Script ghi danh sách bài đã tải
(tiêu đề, đường dẫn, ngày tải) vào data/domain/ATTRIBUTION_wikipedia.md; hãy nhắc tới file đó trong data/README.md.

VÌ SAO có cả 4 nhãn cũ (ML, DL, NLP, Toán): tập hiện tại lấy các nhãn đó từ sách D2L. Nếu nhãn mới chỉ
lấy từ Wikipedia thì bộ phân loại có thể học phong cách nguồn (sách dịch hay bách khoa) thay vì chủ đề, làm
độ chính xác của nhãn mới cao giả tạo. Cho mọi nhãn cùng có tài liệu Wikipedia để cân bằng nguồn.

CẢNH BÁO: danh sách tiêu đề bên dưới tôi chưa kiểm chứng trên trang thật (môi trường soạn không có mạng).
Tiêu đề không tồn tại sẽ bị báo "THIẾU" và bỏ qua; bài quá ngắn (< --min-words) cũng bị bỏ. Cuối lượt chạy
script báo nhãn nào còn dưới 7 tài liệu: hãy thêm tiêu đề đúng vào TITLES rồi chạy lại (file đã có được bỏ qua).
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date

API = "https://vi.wikipedia.org/w/api.php"
UA = "TroLyHocTap-student-project/1.0 (do an mon Hoc may; lien he qua trang GitHub cua du an)"
CUT_SECTIONS = {"tham khảo", "liên kết ngoài", "xem thêm", "chú thích", "ghi chú", "đọc thêm", "thư mục"}
TARGET_DOCS = 7

TITLES = {
    "machine_learning": [
        "Học máy", "Học có giám sát", "Học không giám sát", "Hồi quy tuyến tính", "Hồi quy logistic",
        "Cây quyết định", "Rừng ngẫu nhiên", "Máy vectơ hỗ trợ", "K-means", "Phân tích thành phần chính",
        "Học tăng cường", "Học bán giám sát", "Quá khớp", "Thuật toán k-láng giềng gần nhất",
    ],
    "deep_learning": [
        "Học sâu", "Mạng nơ-ron nhân tạo", "Mạng nơ-ron tích chập", "Mạng nơ-ron hồi quy",
        "Bộ nhớ dài-ngắn hạn", "Lan truyền ngược", "Hàm kích hoạt", "Autoencoder", "Perceptron",
        "Mạng đối nghịch tạo sinh", "Perceptron đa lớp", "Transformer (mô hình học máy)",
        "Học chuyển giao", "Nơ-ron nhân tạo",
    ],
    "nlp": [
        "Xử lý ngôn ngữ tự nhiên", "Phân tích cảm xúc", "Nhúng từ", "Mô hình ngôn ngữ", "Dịch máy",
        "Nhận dạng thực thể có tên", "Kho ngữ liệu", "Tóm tắt tự động", "Gắn thẻ từ loại",
        "Mô hình ngôn ngữ lớn", "Nhận dạng giọng nói", "Tách từ", "Tổng hợp tiếng nói", "ChatGPT",
    ],
    "math": [
        "Giải tích", "Đạo hàm", "Tích phân", "Đại số tuyến tính", "Ma trận (toán học)", "Xác suất",
        "Thống kê", "Định lý Bayes", "Phân phối chuẩn", "Biến ngẫu nhiên", "Kỳ vọng toán học",
        "Phương sai", "Giá trị riêng và vectơ riêng", "Lý thuyết thông tin",
    ],
    "software": [
        "Kỹ thuật phần mềm", "Scrum", "Phát triển phần mềm linh hoạt", "UML", "Kiểm thử phần mềm",
        "Git", "Docker (phần mềm)", "Lập trình hướng đối tượng", "PHP", "JavaScript", "HTML", "CSS",
        "Laravel", "Giao diện lập trình ứng dụng", "DevOps", "Python (ngôn ngữ lập trình)",
    ],
    "networks": [
        "Mạng máy tính", "Mô hình OSI", "Bộ giao thức Internet", "Giao thức điều khiển truyền vận",
        "User Datagram Protocol", "Hệ thống tên miền", "Địa chỉ IP", "Ethernet", "Định tuyến",
        "Bộ định tuyến", "HTTP", "Wi-Fi", "Chuyển mạch gói", "Băng thông", "Mạng cục bộ",
    ],
    "databases": [
        "Cơ sở dữ liệu", "Cơ sở dữ liệu quan hệ", "SQL", "Hệ quản trị cơ sở dữ liệu", "NoSQL", "MySQL",
        "PostgreSQL", "MongoDB", "ACID", "Chuẩn hóa cơ sở dữ liệu", "Khóa chính", "Khóa ngoại",
        "Mô hình thực thể - liên kết", "Giao dịch cơ sở dữ liệu", "Chỉ mục cơ sở dữ liệu",
    ],
    "os": [
        "Hệ điều hành", "Nhân hệ điều hành", "Tiến trình", "Luồng (khoa học máy tính)", "Bộ nhớ ảo",
        "Phân trang bộ nhớ", "Bế tắc (khoa học máy tính)", "Linux", "Unix", "Hệ thống tập tin",
        "Semaphore", "Lập lịch (khoa học máy tính)", "Hệ điều hành thời gian thực", "Ngắt (tin học)",
    ],
    "algorithms": [
        "Thuật toán", "Cấu trúc dữ liệu", "Độ phức tạp tính toán", "Thuật toán sắp xếp", "Sắp xếp nhanh",
        "Sắp xếp trộn", "Tìm kiếm nhị phân", "Danh sách liên kết", "Ngăn xếp", "Hàng đợi",
        "Cây nhị phân", "Bảng băm", "Đệ quy", "Quy hoạch động", "Thuật toán Dijkstra",
        "Tìm kiếm theo chiều rộng", "Tìm kiếm theo chiều sâu",
    ],
    "security": [
        "An toàn thông tin", "Mật mã học", "RSA", "Advanced Encryption Standard", "Hàm băm mật mã",
        "Chữ ký số", "Tường lửa", "Mạng riêng ảo", "Phần mềm độc hại", "Tấn công từ chối dịch vụ",
        "Lừa đảo trực tuyến", "Chứng chỉ khóa công khai", "Xác thực", "Mã hóa", "Bảo mật tầng giao vận",
    ],
}


def fetch_extract(title):
    """Trả về (tiêu đề thật, văn bản) hoặc (None, None) nếu bài không tồn tại."""
    params = {
        "action": "query", "prop": "extracts", "explaintext": 1, "exsectionformat": "wiki",
        "redirects": 1, "format": "json", "formatversion": 2, "titles": title,
    }
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    pages = (data.get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing") or not pages[0].get("extract"):
        return None, None
    return pages[0]["title"], pages[0]["extract"]


_HEADING = re.compile(r"^\s*=+\s*(.*?)\s*=+\s*$")


def clean_extract(text):
    """Cắt từ mục 'Tham khảo...' trở đi, đổi dòng tiêu đề '== X ==' thành dòng 'X', gọn dòng trống."""
    out = []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            if m.group(1).lower() in CUT_SECTIONS:
                break
            out.append("")
            out.append(m.group(1))
            out.append("")
        else:
            out.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def slugify(title):
    s = unicodedata.normalize("NFKD", title.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60] or "bai"


def write_attribution(root, manifest):
    lines = [
        "# Nguồn: Wikipedia tiếng Việt", "",
        "Các file `wiki_*.txt` trong thư mục con của `data/domain/` là văn bản bài viết trên vi.wikipedia.org, "
        "lấy qua MediaWiki API, giấy phép **Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)**. "
        "Có cắt các mục 'Tham khảo', 'Liên kết ngoài'; không chỉnh sửa nội dung khác. "
        "Tác giả: những người đóng góp cho từng bài (xem lịch sử trang).", "",
        "| File | Bài Wikipedia | Ngày tải |", "|---|---|---|",
    ]
    for rel, m in sorted(manifest.items()):
        url = "https://vi.wikipedia.org/wiki/" + urllib.parse.quote(m["title"].replace(" ", "_"))
        lines.append(f"| `{rel}` | [{m['title']}]({url}) | {m['date']} |")
    with open(os.path.join(root, "ATTRIBUTION_wikipedia.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "domain"))
    ap.add_argument("--only", nargs="+", choices=sorted(TITLES), help="chỉ tải các nhãn này")
    ap.add_argument("--min-words", type=int, default=300, help="bỏ bài ngắn hơn số từ này")
    ap.add_argument("--delay", type=float, default=0.7, help="giây nghỉ giữa các lần gọi")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    labels = args.only or list(TITLES)
    if args.dry_run:
        for lab in labels:
            print(f"{lab}: {len(TITLES[lab])} tiêu đề -> " + "; ".join(TITLES[lab]))
        return

    os.makedirs(args.root, exist_ok=True)
    mpath = os.path.join(args.root, "wikipedia_manifest.json")
    manifest = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}
    summary = {}
    for lab in labels:
        os.makedirs(os.path.join(args.root, lab), exist_ok=True)
        for title in TITLES[lab]:
            rel = f"{lab}/wiki_{slugify(title)}.txt"
            path = os.path.join(args.root, rel)
            if os.path.exists(path):
                print(f"[CÓ SẴN] {rel}")
                continue
            try:
                real, extract = fetch_extract(title)
            except Exception as e:  # noqa: BLE001
                print(f"[LỖI]   {title}: {e}")
                time.sleep(args.delay)
                continue
            time.sleep(args.delay)
            if not real:
                print(f"[THIẾU] {title}: không có bài này trên vi.wikipedia")
                continue
            body = clean_extract(extract)
            n = len(body.split())
            if n < args.min_words:
                print(f"[NGẮN]  {title} -> '{real}': {n} từ (< {args.min_words}), bỏ qua")
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{real} — Wikipedia tiếng Việt (CC BY-SA 4.0)\n\n{body}\n")
            manifest[rel] = {"title": real, "date": date.today().isoformat(), "words": n}
            print(f"[OK]    {rel}  ({n} từ)" + ("" if real == title else f"  (chuyển hướng từ '{title}')"))

    for lab in TITLES:
        d = os.path.join(args.root, lab)
        summary[lab] = len([x for x in os.listdir(d) if x.lower().endswith(".txt")]) if os.path.isdir(d) else 0
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    write_attribution(args.root, manifest)

    print("\nSố tài liệu mỗi nhãn (gồm cả file D2L đã có):")
    low = []
    for lab, n in summary.items():
        flag = "" if n >= TARGET_DOCS else f"  <-- dưới {TARGET_DOCS}, thêm tiêu đề vào TITLES"
        print(f"  {lab:18s} {n:3d}{flag}")
        if n < TARGET_DOCS:
            low.append(lab)
    print("\nĐã ghi data/domain/ATTRIBUTION_wikipedia.md. Hãy nhắc tới file này trong data/README.md (CC BY-SA 4.0).")
    print("Tiếp theo: python scripts/train_domain_classifier.py --loo  rồi  python scripts/evaluate_reliability.py")
    sys.exit(1 if low else 0)


if __name__ == "__main__":
    main()
