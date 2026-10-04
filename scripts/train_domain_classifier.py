"""Huấn luyện + đánh giá bộ phân loại lĩnh vực, so với baseline đếm từ khóa.

Chạy:  python scripts/train_domain_classifier.py --data data/domain --words 150 --folds 5

Quy trình đánh giá:
  1. Đọc data/domain/<nhãn>/*.txt, cắt mỗi tài liệu thành đoạn ~N từ.
  2. StratifiedGroupKFold theo TÀI LIỆU: mọi đoạn của một tài liệu nằm cùng một fold.
  3. Mỗi fold: huấn luyện trên các fold còn lại, dự đoán fold giữ lại. Gộp dự đoán mọi fold.
  4. Baseline từ khóa (detector.detect_domain) chạy trên đúng các đoạn đó (không cần huấn luyện).
  5. Báo cáo accuracy, macro-F1, ma trận nhầm lẫn; thêm độ chính xác mức TÀI LIỆU (bỏ phiếu theo đoạn).
  6. Huấn luyện lại trên TOÀN BỘ dữ liệu và lưu models/domain_clf.joblib (dùng cho app, KHÔNG dùng để báo cáo số).
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "app"))

from domain.detector import detect_domain  # noqa: E402
from domain.ml_classifier import build_model, load_dataset, save_model  # noqa: E402


def _metrics(y_true, y_pred, labels):
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support

    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4),
        "per_class": {
            l: {"precision": round(float(p[i]), 3), "recall": round(float(r[i]), 3), "f1": round(float(f[i]), 3), "support": int(s[i])}
            for i, l in enumerate(labels)
        },
        "confusion": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def _doc_accuracy(groups, y_true, y_pred):
    votes, truth = defaultdict(list), {}
    for g, t, p in zip(groups, y_true, y_pred):
        votes[g].append(p)
        truth[g] = t
    ok = sum(Counter(v).most_common(1)[0][0] == truth[g] for g, v in votes.items())
    return round(ok / len(votes), 4), len(votes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "domain"))
    ap.add_argument("--words", type=int, default=150)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--loo", action="store_true",
                    help="Leave-one-document-out: mỗi fold giữ lại đúng 1 tài liệu (hợp khi mỗi lớp chỉ có vài tài liệu)")
    ap.add_argument("--out-model", default=os.path.join(ROOT, "models", "domain_clf.joblib"))
    ap.add_argument("--results", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()

    from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold

    texts, labels, groups = load_dataset(args.data, words=args.words)
    classes = sorted(set(labels))
    docs_per_class = {c: len({g for g, l in zip(groups, labels) if l == c}) for c in classes}
    chunks_per_class = Counter(labels)
    print("Lớp / số tài liệu / số đoạn:")
    for c in classes:
        print(f"  {c:32s} {docs_per_class[c]:3d} tài liệu, {chunks_per_class[c]:4d} đoạn")
    if len(classes) < 2:
        sys.exit("Cần ít nhất 2 lớp.")
    if min(docs_per_class.values()) < 2:
        sys.exit("Mỗi lớp cần ít nhất 2 tài liệu để chia theo tài liệu. Thêm tài liệu vào data/domain/.")
    if args.loo:
        n_splits = len(set(groups))
        cv = LeaveOneGroupOut()
        print(f"Leave-one-document-out: {n_splits} fold, mỗi fold giữ lại 1 tài liệu.\n")
    else:
        n_splits = min(args.folds, min(docs_per_class.values()))
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=args.seed)
        print(f"Chia {n_splits} fold theo tài liệu.\n")
    preds = {"logreg": [None] * len(texts), "nb": [None] * len(texts)}
    for tr, te in cv.split(texts, labels, groups):
        for kind in preds:
            m = build_model(kind).fit([texts[i] for i in tr], [labels[i] for i in tr])
            for i, p in zip(te, m.predict([texts[i] for i in te])):
                preds[kind][i] = p
    preds["keyword"] = [detect_domain(t)[0] for t in texts]

    names = {"keyword": "Baseline: đếm từ khóa", "nb": "TF-IDF + Complement NB", "logreg": "TF-IDF + Logistic Regression"}
    report = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "words_per_chunk": args.words,
        "n_chunks": len(texts),
        "n_docs": len(set(groups)),
        "protocol": "leave-one-document-out" if args.loo else "StratifiedGroupKFold",
        "folds": n_splits,
        "seed": args.seed,
        "docs_per_class": docs_per_class,
        "methods": {},
    }
    # Baseline có thể trả "General/Unknown" (ngoài danh sách lớp) -> tính là sai, thêm cột riêng cho ma trận.
    eval_labels = classes + (["General/Unknown"] if "General/Unknown" in set(preds["keyword"]) else [])
    for k in ("keyword", "nb", "logreg"):
        m = _metrics(labels, preds[k], eval_labels)
        m["doc_accuracy"], m["n_docs"] = _doc_accuracy(groups, labels, preds[k])
        report["methods"][names[k]] = m
        print(f"{names[k]:32s} acc={m['accuracy']:.3f}  macro-F1={m['macro_f1']:.3f}  acc theo tài liệu={m['doc_accuracy']:.3f} (n={m['n_docs']})")

    # Bảng theo tài liệu (bỏ phiếu theo đoạn) để làm phân tích lỗi
    truth, votes = {}, {k: defaultdict(list) for k in ("keyword", "logreg")}
    for g, t, i in zip(groups, labels, range(len(labels))):
        truth[g] = t
        for k in votes:
            votes[k][g].append(preds[k][i])
    doc_rows = []
    print("\nTheo tài liệu (nhãn thật | Logistic Regression | từ khóa):")
    for g in sorted(truth):
        row = {"doc": g, "true": truth[g]}
        for k in votes:
            c = Counter(votes[k][g])
            row[k] = c.most_common(1)[0][0]
            row[k + "_share"] = round(c.most_common(1)[0][1] / len(votes[k][g]), 2)
        doc_rows.append(row)
        ok = lambda k: "OK " if row[k] == row["true"] else "SAI"  # noqa: E731
        print(f"  {g:48s} {row['true'][:16]:16s} | {ok('logreg')} {row['logreg'][:16]:16s} | {ok('keyword')} {row['keyword'][:16]}")
    report["per_document"] = doc_rows

    os.makedirs(args.results, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jpath = os.path.join(args.results, f"domain_clf_{stamp}.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    cpath = os.path.join(args.results, f"domain_clf_{stamp}_confusion_logreg.csv")
    with open(cpath, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["thực tế \\ dự đoán"] + eval_labels)
        for l, row in zip(eval_labels, report["methods"][names["logreg"]]["confusion"]):
            w.writerow([l] + row)

    final = build_model("logreg").fit(texts, labels)
    save_model(final, args.out_model)
    print(f"\nĐã lưu kết quả: {jpath}\nMa trận nhầm lẫn: {cpath}\nMô hình (huấn luyện trên toàn bộ dữ liệu, chỉ để dùng trong app): {args.out_model}")


if __name__ == "__main__":
    main()