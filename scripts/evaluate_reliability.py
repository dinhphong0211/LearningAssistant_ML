"""Đánh giá ĐỘ TIN CẬY của bộ phân loại lĩnh vực (bổ sung cho train_domain_classifier.py).

Chạy:  python scripts/evaluate_reliability.py --data data/domain

Làm gì (mọi phép đo đều chia theo TÀI LIỆU bằng leave-one-document-out):
  1. So sánh 4 phương pháp: đoán ngẫu nhiên đều, đếm từ khóa, Naive Bayes, Logistic Regression.
  2. Khoảng tin cậy 95%: Wilson cho độ chính xác theo tài liệu; bootstrap theo TÀI LIỆU cho
     accuracy / macro-F1 mức đoạn (đoạn cùng tài liệu không độc lập nên không bootstrap theo đoạn).
  3. Kiểm định cặp (McNemar chính xác) Logistic Regression so với từ khóa, mức tài liệu.
  4. Độ nhạy theo cỡ đoạn (số từ mỗi đoạn).
  5. Độ ổn định theo seed chia fold (StratifiedGroupKFold).
  6. Hiệu chỉnh xác suất (ECE) và đánh đổi độ phủ / độ chính xác khi đặt ngưỡng "không chắc".
  7. Đường cong học: độ chính xác theo số tài liệu huấn luyện mỗi lớp (thêm dữ liệu có giúp không).
  8. Phân tích lỗi: tài liệu bị đoán sai, nhãn đoán, tỉ lệ phiếu.

Ghi ra results/reliability_<thời gian>.json và .md.
Giới hạn: nhãn là nhãn do người làm đồ án gán (thư mục); số tài liệu ít nên khoảng tin cậy rộng.
"""
import argparse
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "app"))

from domain.detector import detect_domain  # noqa: E402
from domain.ml_classifier import build_model, load_dataset  # noqa: E402

METHODS = [("random", "Đoán ngẫu nhiên đều"), ("keyword", "Đếm từ khóa"),
           ("nb", "TF-IDF + Complement NB"), ("logreg", "TF-IDF + Logistic Regression")]


def loo_predict(texts, labels, groups, kind):
    """Dự đoán từng đoạn khi giữ lại 1 tài liệu. Trả (pred, conf); conf=None nếu không có xác suất."""
    from sklearn.model_selection import LeaveOneGroupOut

    n = len(texts)
    if kind == "keyword":
        return [detect_domain(t)[0] for t in texts], None
    pred, conf = [None] * n, [0.0] * n
    rng = random.Random(0)
    for tr, te in LeaveOneGroupOut().split(texts, labels, groups):
        if kind == "random":
            for i in te:
                pred[i] = rng.choice(sorted(set(labels)))
            continue
        m = build_model(kind).fit([texts[i] for i in tr], [labels[i] for i in tr])
        P = m.predict_proba([texts[i] for i in te])
        for j, i in enumerate(te):
            k = int(P[j].argmax())
            pred[i], conf[i] = str(m.classes_[k]), float(P[j, k])
    return pred, (conf if kind != "random" else None)


def doc_votes(groups, labels, pred):
    votes, truth = defaultdict(list), {}
    for g, t, p in zip(groups, labels, pred):
        votes[g].append(p)
        truth[g] = t
    out = {}
    for g, v in votes.items():
        top, cnt = Counter(v).most_common(1)[0]
        out[g] = {"true": truth[g], "pred": top, "share": cnt / len(v), "ok": top == truth[g]}
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 3), round(min(1.0, c + h), 3))


def mcnemar_exact(ok_a, ok_b):
    """p hai phía của kiểm định dấu chính xác trên các tài liệu A và B khác kết quả."""
    b = sum(1 for x, y in zip(ok_a, ok_b) if x and not y)
    c = sum(1 for x, y in zip(ok_a, ok_b) if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / 2 ** n
    return b, c, round(min(1.0, 2 * tail), 4)


def bootstrap(labels, groups, pred, classes, B, seed):
    from sklearn.metrics import accuracy_score, f1_score

    idx_by_doc = defaultdict(list)
    for i, g in enumerate(groups):
        idx_by_doc[g].append(i)
    docs = sorted(idx_by_doc)
    rng = random.Random(seed)
    acc, f1 = [], []
    for _ in range(B):
        idx = [i for g in (rng.choice(docs) for _ in docs) for i in idx_by_doc[g]]
        yt, yp = [labels[i] for i in idx], [pred[i] for i in idx]
        acc.append(accuracy_score(yt, yp))
        f1.append(f1_score(yt, yp, labels=classes, average="macro", zero_division=0))

    def ci(v):
        v = sorted(v)
        return [round(v[int(0.025 * len(v))], 3), round(v[min(len(v) - 1, int(0.975 * len(v)))], 3)]
    return {"chunk_acc_ci95": ci(acc), "macro_f1_ci95": ci(f1)}


def learning_curve(texts, labels, groups, classes, reps, seed=0):
    """Huấn luyện chỉ với k tài liệu mỗi lớp (chọn ngẫu nhiên), kiểm tra trên 1 tài liệu giữ lại."""
    docs_by_class = defaultdict(list)
    for g, l in {(g, l) for g, l in zip(groups, labels)}:
        docs_by_class[l].append(g)
    for l in docs_by_class:
        docs_by_class[l].sort()
    idx_by_doc = defaultdict(list)
    for i, g in enumerate(groups):
        idx_by_doc[g].append(i)
    kmax = min(len(v) for v in docs_by_class.values()) - 1
    rng = random.Random(seed)
    rows = []
    for k in range(1, kmax + 1):
        correct, total = 0, 0
        for _ in range(reps):
            for test_doc in sorted(idx_by_doc):
                tr_docs = []
                for l in classes:
                    pool = [d for d in docs_by_class[l] if d != test_doc]
                    tr_docs += rng.sample(pool, k)
                tr = [i for d in tr_docs for i in idx_by_doc[d]]
                m = build_model("logreg").fit([texts[i] for i in tr], [labels[i] for i in tr])
                pv = Counter(m.predict([texts[i] for i in idx_by_doc[test_doc]])).most_common(1)[0][0]
                truth = labels[idx_by_doc[test_doc][0]]
                correct += pv == truth
                total += 1
        rows.append({"docs_per_class_train": k, "doc_acc": round(correct / total, 3), "n_tests": total})
    return rows


def calibration(labels, pred, conf, bins=5):
    n = len(labels)
    ece, rows = 0.0, []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        sel = [i for i in range(n) if lo <= conf[i] < hi or (b == bins - 1 and conf[i] == 1.0)]
        if not sel:
            continue
        a = sum(pred[i] == labels[i] for i in sel) / len(sel)
        c = sum(conf[i] for i in sel) / len(sel)
        ece += len(sel) / n * abs(a - c)
        rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(sel), "acc": round(a, 3), "mean_conf": round(c, 3)})
    return round(ece, 3), rows


def coverage_table(labels, pred, conf, thresholds):
    out = []
    for t in thresholds:
        sel = [i for i in range(len(labels)) if conf[i] >= t]
        out.append({"threshold": t, "coverage": round(len(sel) / len(labels), 3),
                    "accuracy_covered": round(sum(pred[i] == labels[i] for i in sel) / len(sel), 3) if sel else None})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "domain"))
    ap.add_argument("--words", type=int, default=150)
    ap.add_argument("--sens-words", type=int, nargs="+", default=[100, 150, 250, 400])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--curve-reps", type=int, default=3, help="số lần lặp cho đường cong học")
    ap.add_argument("--results", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()

    from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
    from sklearn.model_selection import StratifiedGroupKFold

    texts, labels, groups = load_dataset(args.data, words=args.words)
    classes = sorted(set(labels))
    docs = sorted(set(groups))
    dpc = {c: len({g for g, l in zip(groups, labels) if l == c}) for c in classes}
    if min(dpc.values()) < 2:
        sys.exit("Mỗi lớp cần ít nhất 2 tài liệu.")
    print(f"{len(docs)} tài liệu, {len(texts)} đoạn, tài liệu/lớp: {dpc}\n")
    rep = {"time": datetime.now().isoformat(timespec="seconds"), "words": args.words, "n_docs": len(docs),
           "n_chunks": len(texts), "docs_per_class": dpc, "protocol": "leave-one-document-out", "methods": {}}

    preds, confs, votes = {}, {}, {}
    for k, name in METHODS:
        preds[k], confs[k] = loo_predict(texts, labels, groups, k)
        votes[k] = doc_votes(groups, labels, preds[k])
        ok_docs = sum(v["ok"] for v in votes[k].values())
        m = {"chunk_acc": round(accuracy_score(labels, preds[k]), 3),
             "macro_f1": round(f1_score(labels, preds[k], labels=classes, average="macro", zero_division=0), 3),
             "doc_acc": round(ok_docs / len(docs), 3), "doc_correct": ok_docs,
             "doc_acc_ci95_wilson": wilson(ok_docs, len(docs))}
        m.update(bootstrap(labels, groups, preds[k], classes, args.boot, seed=1))
        rep["methods"][name] = m
        print(f"{name:32s} acc đoạn={m['chunk_acc']:.3f} {m['chunk_acc_ci95']}  macro-F1={m['macro_f1']:.3f} {m['macro_f1_ci95']}  "
              f"acc tài liệu={ok_docs}/{len(docs)}={m['doc_acc']:.3f} {m['doc_acc_ci95_wilson']}")

    ok = {k: [votes[k][d]["ok"] for d in docs] for k, _ in METHODS}
    rep["paired_tests_doc_level"] = {}
    print("\nKiểm định cặp mức tài liệu (McNemar chính xác), Logistic Regression so với:")
    for k in ("keyword", "nb", "random"):
        b, c, p = mcnemar_exact(ok["logreg"], ok[k])
        rep["paired_tests_doc_level"][k] = {"logreg_only_correct": b, "other_only_correct": c, "p_value": p}
        print(f"  {k:9s} LR đúng-mà-nó-sai={b}, nó đúng-mà-LR-sai={c}, p={p}")

    p_, r_, f_, s_ = precision_recall_fscore_support(labels, preds["logreg"], labels=classes, zero_division=0)
    rep["per_class_logreg_chunk"] = {l: {"precision": round(float(p_[i]), 3), "recall": round(float(r_[i]), 3),
                                         "f1": round(float(f_[i]), 3), "support": int(s_[i])} for i, l in enumerate(classes)}

    print("\nĐộ nhạy theo cỡ đoạn (Logistic Regression, leave-one-document-out):")
    rep["sensitivity_words"] = []
    for w in args.sens_words:
        t2, l2, g2 = load_dataset(args.data, words=w)
        p2, _ = loo_predict(t2, l2, g2, "logreg")
        v2 = doc_votes(g2, l2, p2)
        row = {"words": w, "n_chunks": len(t2), "chunk_acc": round(accuracy_score(l2, p2), 3),
               "macro_f1": round(f1_score(l2, p2, labels=classes, average="macro", zero_division=0), 3),
               "doc_acc": round(sum(v["ok"] for v in v2.values()) / len(v2), 3)}
        rep["sensitivity_words"].append(row)
        print(f"  {w:4d} từ/đoạn: {row['n_chunks']:4d} đoạn, acc đoạn={row['chunk_acc']:.3f}, macro-F1={row['macro_f1']:.3f}, acc tài liệu={row['doc_acc']:.3f}")

    print("\nĐộ ổn định theo seed chia fold (StratifiedGroupKFold, Logistic Regression):")
    n_splits = min(5, min(dpc.values()))
    accs = []
    for s in range(args.seeds):
        pred = [None] * len(texts)
        for tr, te in StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=s).split(texts, labels, groups):
            m = build_model("logreg").fit([texts[i] for i in tr], [labels[i] for i in tr])
            for i, p in zip(te, m.predict([texts[i] for i in te])):
                pred[i] = p
        v = doc_votes(groups, labels, pred)
        accs.append(round(sum(x["ok"] for x in v.values()) / len(v), 3))
    mean = sum(accs) / len(accs)
    sd = math.sqrt(sum((a - mean) ** 2 for a in accs) / max(1, len(accs) - 1))
    rep["seed_stability_doc_acc"] = {"folds": n_splits, "values": accs, "mean": round(mean, 3), "sd": round(sd, 3),
                                     "min": min(accs), "max": max(accs)}
    print(f"  {args.seeds} seed, {n_splits} fold: acc tài liệu {min(accs)}–{max(accs)} (TB {mean:.3f}, sd {sd:.3f})")

    print("\nĐường cong học (Logistic Regression): độ chính xác theo số tài liệu huấn luyện mỗi lớp")
    rep["learning_curve"] = learning_curve(texts, labels, groups, classes, args.curve_reps)
    for r in rep["learning_curve"]:
        print(f"  {r['docs_per_class_train']} tài liệu/lớp: acc tài liệu={r['doc_acc']:.3f} ({r['n_tests']} lượt thử)")

    ece, bins = calibration(labels, preds["logreg"], confs["logreg"])
    rep["calibration_logreg"] = {"ece": ece, "bins": bins}
    rep["abstain_logreg"] = coverage_table(labels, preds["logreg"], confs["logreg"], [0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    print(f"\nHiệu chỉnh xác suất Logistic Regression: ECE={ece}")
    print("Ngưỡng 'không chắc' (mức đoạn): ngưỡng / độ phủ / acc trên phần được trả lời")
    for r in rep["abstain_logreg"]:
        print(f"  >= {r['threshold']}: phủ {r['coverage']:.2f}, acc {r['accuracy_covered']}")

    rep["errors_logreg_doc"] = [{"doc": d, "true": votes["logreg"][d]["true"], "pred": votes["logreg"][d]["pred"],
                                 "vote_share": round(votes["logreg"][d]["share"], 2),
                                 "keyword_pred": votes["keyword"][d]["pred"]}
                                for d in docs if not votes["logreg"][d]["ok"]]
    print(f"\nTài liệu Logistic Regression đoán sai: {len(rep['errors_logreg_doc'])}")
    for e in rep["errors_logreg_doc"]:
        print(f"  {e['doc']:48s} thật={e['true']} | LR={e['pred']} ({e['vote_share']}) | từ khóa={e['keyword_pred']}")

    os.makedirs(args.results, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(os.path.join(args.results, f"reliability_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    lines = [f"# Độ tin cậy bộ phân loại lĩnh vực ({rep['time']})", "",
             f"{rep['n_docs']} tài liệu, {rep['n_chunks']} đoạn ~{args.words} từ, leave-one-document-out.", "",
             "| Phương pháp | Acc đoạn (CI95) | Macro-F1 (CI95) | Acc tài liệu (Wilson CI95) |", "|---|---|---|---|"]
    for name, m in rep["methods"].items():
        lines.append(f"| {name} | {m['chunk_acc']} {m['chunk_acc_ci95']} | {m['macro_f1']} {m['macro_f1_ci95']} | "
                     f"{m['doc_correct']}/{rep['n_docs']} = {m['doc_acc']} {list(m['doc_acc_ci95_wilson'])} |")
    with open(os.path.join(args.results, f"reliability_{stamp}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nĐã lưu results/reliability_{stamp}.json và .md")


if __name__ == "__main__":
    main()