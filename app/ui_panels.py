"""Các khối giao diện cho phân tích chuyên ngành, kiểm chứng và đánh giá (tách khỏi main.py)."""
import streamlit as st

import ui_theme
from evaluation.metrics import rouge_all
from evaluation.report import evaluate_summaries

_LIMIT_NOTE = (
    "Các độ đo TPR, NPR, UPR, FPR và tỉ lệ nén do đồ án tự định nghĩa, không phải benchmark chuẩn. "
    "Kết quả chỉ là dấu hiệu nghi ngờ, cần đối chiếu với tài liệu gốc."
)


def _pct(d, with_counts=False):
    if not d:
        return "—"
    s = f"{d['rate']:.0%}"
    if with_counts and "kept" in d:
        s += f" ({d['kept']}/{d['total']})"
    return s


def profile_panel(result):
    """Hồ sơ chuyên ngành: lĩnh vực, ngôn ngữ, khái niệm chính, viết tắt, công thức, đơn vị."""
    p = result.get("profile")
    if not p:
        st.caption("Bài này được tạo bằng phiên bản cũ nên chưa có hồ sơ chuyên ngành.")
        return
    ui_theme.stat_grid([
        ("Lĩnh vực", p["domain"]),
        ("Chuyên ngành", p["subdomain"]),
        ("Ngôn ngữ", p["language"]),
        ("Độ phủ từ khóa", f"{p['confidence']}%"),
    ])
    if p.get("alternatives"):
        st.caption("Lĩnh vực gần nhất khác: " + ", ".join(p["alternatives"]))
    if p.get("important_concepts"):
        st.markdown("**Khái niệm chính** (thuật ngữ xuất hiện nhiều nhất)")
        ui_theme.chips(p["important_concepts"])
    if p.get("abbreviations"):
        st.markdown("**Từ viết tắt do tài liệu định nghĩa**")
        st.table([{"Viết tắt": a, "Dạng đầy đủ": f} for a, f in p["abbreviations"].items()])
    if p.get("undefined_abbreviations"):
        st.caption("Viết tắt xuất hiện nhiều lần nhưng tài liệu không định nghĩa (app không tự đoán): "
                   + ", ".join(p["undefined_abbreviations"]))
    if p.get("formulas"):
        st.markdown(f"**Công thức phát hiện được ({len(p['formulas'])})**")
        for f in p["formulas"][:15]:
            st.code(f, language=None)
    if p.get("units"):
        st.markdown("**Số liệu kèm đơn vị**")
        ui_theme.chips(p["units"])
    st.caption(
        "Nhận diện lĩnh vực bằng đếm từ khóa; viết tắt, công thức, đơn vị bằng luật. Công thức dạng ảnh hoặc "
        "nằm giữa câu văn có thể bị bỏ sót."
    )


def validation_banner(validation):
    """Cảnh báo ngắn ở tab Tóm tắt khi kiểm chứng thấy dấu hiệu bất thường."""
    if validation and validation.get("needs_review"):
        st.warning("🔎 Có dấu hiệu cần đối chiếu với tài liệu gốc: " + "; ".join(validation["issues"][:2])
                   + (" … (xem tab Đánh giá)" if len(validation["issues"]) > 2 else ""))


def validation_panel(validation):
    st.subheader("Kiểm chứng nội dung")
    if not validation:
        st.caption("Bài này chưa có kết quả kiểm chứng.")
        return
    if validation["needs_review"]:
        for issue in validation["issues"]:
            st.warning(issue)
    else:
        st.success("Không phát hiện dấu hiệu bất thường theo các kiểm tra tự động.")
    if validation.get("ungrounded_sentences"):
        with st.expander("Các câu ít bám vào nội dung gốc"):
            for item in validation["ungrounded_sentences"]:
                st.markdown(f"- {item['sentence']}  \n  _(điểm bám gốc {item['score']})_")
    mean = validation.get("grounding_mean")
    st.caption(
        f"Điểm bám gốc trung bình: {mean if mean is not None else '—'} (ngưỡng báo {validation['threshold']}). "
        "Kiểm tra dựa trên trùng từ vựng nên không hiểu ngữ nghĩa: diễn đạt lại có thể bị báo nhầm, "
        "câu sai nhưng dùng đúng từ của gốc có thể lọt qua. Ngưỡng chưa được hiệu chỉnh trên dữ liệu thật."
    )


def evaluation_panel(result):
    """So sánh TextRank, TextRank + thuật ngữ và Gemini, kèm kiểm chứng và ROUGE."""
    methods = {"TextRank": result.get("baseline", "")}
    if result.get("baseline_domain"):
        methods["TextRank + thuật ngữ"] = result["baseline_domain"]
    methods["Gemini"] = result["summary"]

    st.subheader("So sánh các phương pháp")
    notes = {
        "TextRank": "Trích xuất câu quan trọng bằng đồ thị TF-IDF/cosine, không học máy sinh văn bản.",
        "TextRank + thuật ngữ": "TextRank có tăng điểm câu chứa thuật ngữ chuyên ngành (biến thể do đồ án đề xuất).",
        "Gemini": "Sinh văn bản bằng mô hình pretrained, chỉ inference (không huấn luyện lại).",
    }
    for name, text in methods.items():
        with st.expander(name):
            st.caption(notes[name])
            st.write(text)

    evaluation = result.get("evaluation")
    if not evaluation and result.get("full_text"):
        evaluation = evaluate_summaries(methods, result["full_text"], result.get("terms"), result.get("formulas"))
    st.subheader("Độ đo không cần bản tham chiếu")
    if evaluation:
        rows = []
        for name, m in evaluation.items():
            npr = m.get("npr")
            rows.append({
                "Phương pháp": name,
                "TPR (giữ thuật ngữ)": _pct(m.get("tpr"), True),
                "NPR (số có trong gốc)": _pct(npr) if npr else "không có số",
                "UPR (đơn vị)": _pct(m.get("upr")) if m.get("upr") else "không có",
                "FPR (công thức)": _pct(m.get("fpr"), True) if m.get("fpr") else "không có",
                "Tỉ lệ nén": f"{m['compression']:.1%}" if m.get("compression") else "—",
                "Từ/câu": f"{m['avg_sentence_words']:.1f}" if m.get("avg_sentence_words") else "—",
            })
        st.table(rows)
        st.caption(_LIMIT_NOTE)
    else:
        st.info("Không còn văn bản gốc nên không tính lại được; bài này tạo trước khi app lưu sẵn kết quả đánh giá.")

    validation_panel(result.get("validation"))

    st.subheader("ROUGE (cần bản tóm tắt tham chiếu)")
    reference = st.text_area(
        "Dán bản tóm tắt tham chiếu do người viết (không phải do AI tạo) để tính ROUGE:",
        height=150,
    )
    if reference.strip():
        rouge_rows = []
        for name, text in methods.items():
            r = rouge_all(text, reference)
            rouge_rows.append({"Phương pháp": name, **{k: f"{v['f1']:.3f}" for k, v in r.items()}})
        st.table(rouge_rows)
        st.caption(
            "Điểm F1, ROUGE cài đặt thủ công trong đồ án nên có thể lệch nhẹ so với thư viện chuẩn. "
            "ROUGE đo trùng từ nên thường thấp với tóm tắt sinh văn bản dù nội dung đúng. "
            "Một cặp tài liệu chưa đủ để kết luận."
        )
