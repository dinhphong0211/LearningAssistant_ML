"""Tab Quiz: tạo câu hỏi trắc nghiệm từ bài học, làm bài, chấm điểm, ôn lại câu sai.

Nguồn câu hỏi: văn bản gốc nếu bài có lưu (full_text), nếu không thì bản tóm tắt/toàn văn đã lưu.
Tóm tắt càng ngắn thì càng ít câu hỏi chất lượng; bài Study Notes hoặc Đọc toàn bộ cho đề tốt hơn.
"""
import streamlit as st

from quiz import generator, storage

LETTERS = "ABCD"
MODE_AI = "Gemini (có kiểm chứng với tài liệu)"
MODE_LOCAL = "Offline: điền khuyết (không tốn lượt gọi)"


def _show(text):
    # "_____" trong markdown dễ bị hiểu thành định dạng; hiển thị bằng ký hiệu khác
    return text.replace("_____", "**[ ……… ]**")


def _state(lesson_id, result):
    key = f"quiz-{lesson_id}"
    if key not in st.session_state:
        st.session_state[key] = {"quiz": result.get("quiz"), "attempt": 0, "graded": None, "subset": None}
    return st.session_state[key]


def _generate_panel(owner, lesson_id, result, get_summarizer, state):
    text = result.get("full_text") or result.get("summary") or ""
    src_name = "văn bản gốc đã lưu" if result.get("full_text") else "bản tóm tắt/toàn văn đã lưu"
    n = st.slider("Số câu hỏi", 4, 15, 8, key=f"quiz-n-{lesson_id}")
    mode = st.radio("Cách tạo", (MODE_AI, MODE_LOCAL), key=f"quiz-mode-{lesson_id}")
    st.caption(
        f"Câu hỏi được tạo từ {src_name} ({len(text.split())} từ). "
        "Bản tóm tắt ngắn cho ít ý để hỏi; muốn đề tốt hơn hãy tạo bài ở chế độ Chi tiết hoặc Đọc toàn bộ."
    )
    if st.button("🧠 Tạo bộ câu hỏi", type="primary", key=f"quiz-gen-{lesson_id}"):
        use_ai = mode == MODE_AI
        summarizer = get_summarizer() if use_ai else None
        with st.spinner("Đang tạo và kiểm chứng câu hỏi..."):
            questions, report = generator.generate_quiz(
                summarizer, text, result.get("terms"), result.get("abbreviations"), n=n, use_ai=use_ai,
                seed=len(st.session_state.get(f"quiz-count-{lesson_id}", [])),
            )
        if not questions:
            st.error("Chưa tạo được câu hỏi nào (văn bản quá ngắn hoặc thiếu thuật ngữ). Thử bài dài hơn.")
            return
        storage.save_quiz(owner, lesson_id, questions, report)
        saved = storage.load_quiz(owner, lesson_id)
        st.session_state[f"quiz-{lesson_id}"] = {"quiz": saved, "attempt": 0, "graded": None, "subset": None}
        st.rerun()


def _report_caption(report):
    if not report:
        return
    parts = [f"Gemini: {report.get('gemini', 0)} câu", f"điền khuyết: {report.get('offline', 0)} câu"]
    if report.get("gemini_dropped"):
        parts.append(f"đã loại {report['gemini_dropped']} câu Gemini không qua kiểm chứng "
                     f"({', '.join(report.get('dropped_reasons', []))})")
    if report.get("error"):
        parts.append(f"Gemini lỗi: {report['error'][:120]} → dùng điền khuyết thay thế")
    st.caption(" · ".join(parts))


def _grade(owner, lesson_id, qs, indices, answers, state):
    results = [(i, answers.get(i), qs[i]["answer"]) for i in indices]
    score = sum(1 for _, chosen, correct in results if chosen == correct)
    wrong = [i for i, chosen, correct in results if chosen != correct]
    storage.add_attempt(owner, lesson_id, score, len(indices), wrong)
    state["graded"] = {"results": results, "score": score, "total": len(indices), "wrong": wrong}
    st.rerun()


def _graded_view(qs, state):
    g = state["graded"]
    pct = g["score"] / g["total"] if g["total"] else 0
    (st.success if pct >= 0.7 else st.warning)(f"Kết quả: {g['score']}/{g['total']} câu đúng ({pct:.0%})")
    for pos, (i, chosen, correct) in enumerate(g["results"], 1):
        q = qs[i]
        mark = "✅" if chosen == correct else "❌"
        st.markdown(f"{mark} **Câu {pos}.** {_show(q['q'])}")
        mine = f"{LETTERS[chosen]}. {q['options'][chosen]}" if chosen is not None else "(chưa chọn)"
        st.markdown(f"- Bạn chọn: {mine}\n- Đáp án đúng: **{LETTERS[correct]}. {q['options'][correct]}**")
        with st.expander("Giải thích và căn cứ trong tài liệu"):
            st.write(q.get("explain", ""))
            if q.get("evidence"):
                st.caption("Căn cứ: " + q["evidence"])
    c1, c2 = st.columns(2)
    if c1.button("🔁 Làm lại tất cả", key="quiz-redo-all"):
        state.update(attempt=state["attempt"] + 1, graded=None, subset=None)
        st.rerun()
    if g["wrong"] and c2.button("🎯 Chỉ làm lại câu sai", key="quiz-redo-wrong"):
        state.update(attempt=state["attempt"] + 1, graded=None, subset=g["wrong"])
        st.rerun()


def render(owner, lesson_id, result, get_summarizer):
    """get_summarizer: hàm không đối số trả về summarizer (hoặc None nếu chưa có model)."""
    state = _state(lesson_id, result)
    quiz = state["quiz"]

    with st.expander("⚙️ Tạo bộ câu hỏi mới" if quiz else "⚙️ Tạo bộ câu hỏi", expanded=not quiz):
        _generate_panel(owner, lesson_id, result, get_summarizer, state)
    if not quiz:
        st.info("Chưa có bộ câu hỏi cho bài này. Bấm **Tạo bộ câu hỏi** ở trên.")
        return

    qs = quiz["questions"]
    _report_caption(quiz.get("report"))
    history = quiz.get("history") or []
    if history:
        last = history[-1]
        best = max(h["score"] / h["total"] for h in history if h["total"])
        st.caption(f"Đã làm {len(history)} lượt · lần gần nhất {last['score']}/{last['total']} · tốt nhất {best:.0%}")

    if state["graded"]:
        _graded_view(qs, state)
        return

    indices = state["subset"] if state["subset"] else list(range(len(qs)))
    att = state["attempt"]
    if state["subset"]:
        st.info(f"Đang ôn lại {len(indices)} câu làm sai.")
    with st.form(f"quiz-form-{lesson_id}-{att}"):
        answers = {}
        for pos, i in enumerate(indices, 1):
            q = qs[i]
            answers[i] = st.radio(
                f"**Câu {pos}.** {_show(q['q'])}", options=[0, 1, 2, 3],
                format_func=lambda k, opts=q["options"]: f"{LETTERS[k]}. {opts[k]}",
                index=None, key=f"quiz-ans-{lesson_id}-{att}-{i}",
            )
        submitted = st.form_submit_button("📨 Nộp bài", type="primary")
    if submitted:
        _grade(owner, lesson_id, qs, indices, answers, state)
