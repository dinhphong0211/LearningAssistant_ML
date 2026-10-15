from domain.detector import detect_domain, build_domain_profile, score_domains, DOMAIN_PROFILES, PARENT_DOMAIN
from domain.ml_classifier import label_from_folder


def test_every_domain_has_parent_and_keywords():
    for d, kws in DOMAIN_PROFILES.items():
        assert d in PARENT_DOMAIN and len(kws) >= 10
        assert all(k == k.lower() for k in kws)


def test_new_domains_are_detected():
    cases = {
        "Computer Networks": "Giao thức TCP chia dữ liệu thành gói tin, router thực hiện định tuyến dựa trên địa chỉ IP.",
        "Databases": "Cơ sở dữ liệu quan hệ dùng khóa chính và khóa ngoại, truy vấn bằng SQL, giao dịch tuân theo ACID.",
        "Operating Systems": "Hệ điều hành lập lịch tiến trình, tránh deadlock bằng semaphore, quản lý bộ nhớ ảo và phân trang.",
        "Algorithms & Data Structures": "Thuật toán sắp xếp có độ phức tạp O(n log n); ngăn xếp, hàng đợi và bảng băm là cấu trúc dữ liệu cơ bản.",
        "Information Security": "Mã hóa khóa công khai RSA, chữ ký số và tường lửa giúp chống tấn công, mã độc, lỗ hổng bảo mật.",
    }
    for expected, text in cases.items():
        assert detect_domain(text)[0] == expected, (expected, score_domains(text))


def test_old_behaviour_preserved():
    ml = ("Học máy dùng gradient descent để giảm hàm mất mát. Overfitting xảy ra khi huấn luyện quá lâu, "
          "cần cross-validation và đo accuracy, precision, recall.")
    name, conf = detect_domain(ml)
    assert name == "Machine Learning" and conf > 50
    assert detect_domain("Mạng neural network dùng convolution, relu và backpropagation trên gpu.")[0] == "Deep Learning"
    assert detect_domain("The capital shows rapid growth.") == ("General/Unknown", 0.0)
    assert detect_domain("") == ("Unknown", 0.0)
    p = build_domain_profile("Học máy và overfitting. Overfitting là vấn đề. Mô hình học máy cần dữ liệu.", ["Overfitting"])
    assert p["domain"] == "Computer Science / AI"


def test_ambiguous_keywords_removed():
    for bad in ("feature", "training", "f1", "git"):
        assert not any(bad in kws for kws in DOMAIN_PROFILES.values())


def test_folder_labels():
    assert label_from_folder("networks") == "Computer Networks"
    assert label_from_folder("os") == "Operating Systems"
    assert label_from_folder("security") == "Information Security"
    assert label_from_folder("khac") == "khac"
