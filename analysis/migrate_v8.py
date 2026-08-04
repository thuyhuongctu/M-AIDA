"""
migrate_v8.py — Bước 2: di trú lược đồ và sinh thế hệ khóa v8.0.0 (bản nháp).

Nguyên tắc thế hệ khóa (xem README.md):
  - KHÔNG đụng vào tệp v7.1.1. Script chỉ ĐỌC nó.
  - Sinh một tập v8.0.0-draft độc lập; mỗi bản ghi mang `derived_from`
    trỏ về effect_id gốc của v7.1.1.
  - Tập v7.1.1 chỉ lưu r cuối cùng, nên:
      * 239 bản ghi r trực tiếp (is_estimated = 0): tính lại đầy đủ ngay
        bằng analysis/effect_size.py — A1/A2 không chạm tới chúng, chỉ
        bổ sung phương sai, Fisher z và metric_type (A3/A4).
      * 47 bản ghi suy từ thống kê khác (is_estimated = 1): KHÔNG thể
        tính lại từ CSV — thống kê nguồn (t hay β, giá trị, df, số biến
        giải thích) phải thu hồi từ hồ sơ mã hóa gốc. Script sinh bảng
        thu hồi riêng; điền xong chạy lại script với --recovered để hoàn
        tất các bản ghi này.

Dùng:
    python3 migrate_v8.py <p6_study_database.csv> <thư_mục_ra>
    python3 migrate_v8.py <p6_study_database.csv> <thư_mục_ra> \
            --recovered <bảng_thu_hồi_đã_điền.csv>

Sinh ra trong <thư_mục_ra>:
    p6_study_database_v8_draft.csv   — 286 bản ghi, lược đồ mở rộng
    thu_hoi_thong_ke_nguon_47.csv    — bảng thu hồi (chỉ khi chưa --recovered)
    bao_cao_di_tru.txt               — tóm tắt: đã tính / chờ thu hồi / chênh lệch
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

from effect_size import ConversionError, convert, legacy_r

LOCK_GENERATION = "v8.0.0-draft"

# Lược đồ v8: cột gốc v7.1.1 giữ nguyên tên, cột mới thêm sau.
V8_FIELDS = [
    # định danh và phả hệ khóa
    "study_id", "effect_id", "derived_from", "lock_generation",
    # thư mục học gốc
    "author", "year", "country", "sample_start", "sample_end",
    # biến điều tiết đã có ở v7.1.1 (đổi tên theo lược đồ mới)
    "icrv", "cdai", "dpl", "intl_measure", "perf_measure", "include_flag",
    # thống kê
    "n", "stat_type", "source_value", "r_v711", "r_v8", "delta_r",
    "metric_type", "estimand_source", "source_controls", "r_source", "n_source",
    "variance", "variance_formula", "fisher_z", "var_z",
    "df", "df_source", "n_predictors", "lambda_applied", "beta_in_range",
    "confidence", "flagged",
    # trường mã hóa mới — PI điền, script không đoán
    "selection_rule", "sample_id", "sample_id_suggested",
    "coder_1", "coder_2", "model_version", "prompt_hash", "intl_level",
    "notes",
]

RECOVERY_FIELDS = [
    "study_id", "effect_id", "author", "year", "country", "n_v711",
    "r_v711", "notes_v711",
    # người thu hồi điền từ hồ sơ mã hóa gốc hoặc bài gốc:
    "stat_type",        # t | beta | r
    "source_value",     # giá trị t hoặc beta như bài báo cáo
    "n_reported",       # CỠ MẪU THẬT từ bài — BẮT BUỘC. n của v7.1.1 trong
                        # nhóm này 91% chia hết cho 10, tức là điền ước lượng;
                        # n bịa là TRỌNG SỐ bịa. Không hồi được thì ghi
                        # KHONG_HOI_DUOC -> bản ghi bị loại, không điền ước lượng
    "df_reported",      # df nếu bài in ra; để trống nếu không
    "n_predictors",     # số biến giải thích của mô hình (không kể hệ số chặn)
    "recovery_source",  # bảng nào / trang nào trong bài
    "recovered_by",     # ai thu hồi
    "recovery_date",
]

# r_source theo loại thống kê nguồn: reported (nguyên văn) / derived (tính
# chính xác từ t, df) / imputed (P&B từ beta — chỉ độ nhạy)
R_SOURCE_BY_STAT = {"r": "reported", "t": "derived", "beta": "imputed"}


def _base_row(src: dict) -> dict:
    """Các cột chép nguyên hoặc ánh xạ 1-1 từ v7.1.1."""
    return {
        "study_id": src["study_id"],
        "effect_id": src["effect_id"],
        "derived_from": f"v7.1.1:{src['effect_id']}",
        "lock_generation": LOCK_GENERATION,
        "author": src["author"],
        "year": src["year"],
        "country": src["country"],
        "sample_start": src["sample_start"],
        "sample_end": src["sample_end"],
        "icrv": src["icrv"],
        "cdai": src["cdai"],
        "dpl": src["dpl"],
        # doi_type / fp_type của v7.1.1 chính là intl_measure / perf_measure
        "intl_measure": src["doi_type"],
        "perf_measure": src["fp_type"],
        "include_flag": src["include_flag"],
        "n": src["n"],
        "r_v711": src["r"],
        # gợi ý cụm mẫu để dò mẫu dùng chung (B4) — PI xác nhận vào sample_id
        "sample_id_suggested": f"{src['country']}_{src['sample_start']}_{src['sample_end']}",
        "notes": src["notes"],
    }


def _fill_from_conversion(row: dict, stat_type: str, value: float,
                          n: int, n_predictors=None, df_reported=None) -> None:
    rec = convert(stat_type, value, n, n_predictors, df_reported)
    old = legacy_r(stat_type, value, n)
    row.update({
        "stat_type": stat_type,
        "source_value": value,
        "r_v8": rec.r,
        "delta_r": None if old is None else rec.r - old,
        "metric_type": rec.metric_type,
        "estimand_source": rec.estimand_source,
        "source_controls": rec.source_controls,
        "variance": rec.variance,
        "variance_formula": rec.variance_formula,
        "fisher_z": rec.fisher_z,
        "var_z": rec.var_z,
        "df": rec.df,
        "df_source": rec.df_source,
        "n_predictors": rec.n_predictors,
        "lambda_applied": rec.lambda_applied,
        "beta_in_range": rec.beta_in_range,
        "confidence": rec.confidence,
        "flagged": rec.flagged,
    })


def _pool_dl(rows: list[dict]) -> dict | None:
    """Gộp nhanh DerSimonian–Laird hai cấp trên thang Fisher z.

    Chỉ để ĐỊNH HƯỚNG phần thảo luận ngay khi mã lại xong; con số chính
    thức lấy từ metafor ba cấp (bước 5). Giả định độc lập giữa các hiệu
    ứng — với 1,21 hiệu ứng/nghiên cứu, sai số của giả định này nhỏ.
    """
    import math
    pts = [(float(r["fisher_z"]), float(r["var_z"]), r["study_id"])
           for r in rows if r.get("fisher_z") not in ("", None)
           and r.get("var_z") not in ("", None)]
    if len(pts) < 2:
        return None
    w = [1.0 / v for _, v, _ in pts]
    ybar_fe = sum(wi * y for wi, (y, _, _) in zip(w, pts)) / sum(w)
    q = sum(wi * (y - ybar_fe) ** 2 for wi, (y, _, _) in zip(w, pts))
    c = sum(w) - sum(wi * wi for wi in w) / sum(w)
    tau2 = max(0.0, (q - (len(pts) - 1)) / c) if c > 0 else 0.0
    ws = [1.0 / (v + tau2) for _, v, _ in pts]
    ybar = sum(wi * y for wi, (y, _, _) in zip(ws, pts)) / sum(ws)
    se = (1.0 / sum(ws)) ** 0.5
    return {
        "r": math.tanh(ybar),
        "ci_lo": math.tanh(ybar - 1.96 * se),
        "ci_hi": math.tanh(ybar + 1.96 * se),
        "k_studies": len({sid for _, _, sid in pts}),
        "K_effects": len(pts),
    }


def migrate(path_v711: str, out_dir: str, path_recovered: str | None) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    recovered: dict[str, dict] = {}
    if path_recovered:
        with open(path_recovered, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get("stat_type") or "").strip():
                    recovered[r["effect_id"]] = r

    rows, pending, excluded = [], [], []
    with open(path_v711, newline="", encoding="utf-8") as f:
        for src in csv.DictReader(f):
            row = {k: "" for k in V8_FIELDS}
            row.update(_base_row(src))
            estimated = src["is_estimated"].strip() == "1"

            if not estimated:
                # r trực tiếp: A1/A2 không chạm tới, chỉ bổ sung A3/A4.
                # n của nhóm này coi là báo cáo thật (chữ số cuối phân bố
                # đều); xác nhận chéo qua bảng đối chiếu ngược E2.
                _fill_from_conversion(row, "r", float(src["r"]), int(src["n"]))
                row["r_source"] = "reported"
                row["n_source"] = "reported"
                rows.append(row)
                continue

            rec = recovered.get(src["effect_id"])
            if rec is None:
                row["stat_type"] = ""
                row["notes"] = (row["notes"] + "; " if row["notes"] else "") + \
                    "CHỜ THU HỒI THỐNG KÊ NGUỒN VÀ n THẬT (is_estimated=1; " \
                    "n của v7.1.1 trong nhóm này là điền ước lượng)"
                rows.append(row)
                pending.append(src)
                continue

            n_rep_raw = (rec.get("n_reported") or "").strip()
            if not n_rep_raw.isdigit():
                # Không hồi được n thật thì LOẠI: một n điền tay là một trọng
                # số đặt ngầm không ai kiểm được.
                why = ("không hồi được n thật (n v7.1.1 = %s là ước lượng) — "
                       "loại, không điền ước lượng" % src["n"])
                row["stat_type"] = rec.get("stat_type", "")
                row["source_value"] = rec.get("source_value", "")
                row["flagged"] = True
                row["n_source"] = "imputed"
                row["notes"] = (row["notes"] + "; " if row["notes"] else "") + \
                    f"LOẠI TRỪ KHỎI GỘP: {why}"
                rows.append(row)
                excluded.append((src["effect_id"], why))
                continue

            n_true = int(n_rep_raw)
            try:
                _fill_from_conversion(
                    row,
                    rec["stat_type"].strip().lower(),
                    float(rec["source_value"]),
                    n_true,
                    int(rec["n_predictors"]) if rec.get("n_predictors", "").strip() else None,
                    int(rec["df_reported"]) if rec.get("df_reported", "").strip() else None,
                )
                row["n"] = n_true
                row["r_source"] = R_SOURCE_BY_STAT.get(
                    rec["stat_type"].strip().lower(), ""
                )
                row["n_source"] = "reported"
                if n_true != int(src["n"]):
                    row["notes"] = (row["notes"] + "; " if row["notes"] else "") + \
                        f"n v7.1.1 = {src['n']} là ước lượng; n thật = {n_true}"
                rows.append(row)
            except ConversionError as e:
                row["stat_type"] = rec["stat_type"]
                row["source_value"] = rec["source_value"]
                row["n"] = n_true
                row["flagged"] = True
                row["notes"] = (row["notes"] + "; " if row["notes"] else "") + \
                    f"LOẠI TRỪ KHỎI GỘP: {e}"
                rows.append(row)
                excluded.append((src["effect_id"], str(e)))

    out_csv = os.path.join(out_dir, "p6_study_database_v8_draft.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=V8_FIELDS)
        w.writeheader()
        w.writerows(rows)

    if pending and not path_recovered:
        out_form = os.path.join(out_dir, "thu_hoi_thong_ke_nguon_47.csv")
        with open(out_form, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=RECOVERY_FIELDS)
            w.writeheader()
            for src in pending:
                w.writerow({
                    "study_id": src["study_id"], "effect_id": src["effect_id"],
                    "author": src["author"], "year": src["year"],
                    "country": src["country"], "n_v711": src["n"],
                    "r_v711": src["r"], "notes_v711": src["notes"],
                })

    computed = [r for r in rows if r["r_v8"] != ""]
    deltas = [float(r["delta_r"]) for r in computed if r["delta_r"] not in ("", None)]
    report = {
        "total": len(rows),
        "computed": len(computed),
        "pending_recovery": len(pending),
        "excluded": len(excluded),
        "delta_nonzero": sum(1 for d in deltas if abs(d) > 1e-12),
        "excluded_detail": excluded,
    }
    main_rows = [r for r in rows if r.get("estimand_source") == "observed"]
    sens_rows = [r for r in rows if r.get("estimand_source")
                 in ("observed", "imputed_pb2005")]
    pool_main = _pool_dl(main_rows)
    pool_sens = _pool_dl(sens_rows)
    report["pool_main"] = pool_main
    report["pool_sens"] = pool_sens

    def _fmt(p):
        if p is None:
            return "chưa tính được"
        return (f"{p['r']:+.4f}  95% CI [{p['ci_lo']:+.4f}, {p['ci_hi']:+.4f}]  "
                f"(k = {p['k_studies']} nghiên cứu, K = {p['K_effects']} hiệu ứng)")

    with open(os.path.join(out_dir, "bao_cao_di_tru.txt"), "w", encoding="utf-8") as f:
        f.write(
            f"Di trú v7.1.1 -> {LOCK_GENERATION}\n"
            f"Tổng bản ghi        : {report['total']}\n"
            f"Đã tính đầy đủ      : {report['computed']}\n"
            f"Chờ thu hồi nguồn   : {report['pending_recovery']}\n"
            f"Loại trừ khỏi gộp   : {report['excluded']}\n"
            f"delta_r khác 0      : {report['delta_nonzero']}\n"
        )
        for eid, why in excluded:
            f.write(f"  {eid}: {why}\n")
        f.write(
            "\n== BA CON SỐ CHO THẢO LUẬN P6 "
            "(ước lượng nhanh DL hai cấp trên thang z — chỉ để định hướng; "
            "con số chính thức từ metafor ba cấp, bước 5) ==\n"
            f"r̄ mô hình chính (observed)      : {_fmt(pool_main)}\n"
            f"r̄ độ nhạy (+ imputed_pb2005)    : {_fmt(pool_sens)}\n"
            f"Bị loại trừ                     : {report['excluded']} bản ghi "
            "(danh sách ở trên)\n"
        )
        if report["pending_recovery"]:
            f.write(
                f"CHÚ Ý: còn {report['pending_recovery']} bản ghi chờ thu hồi — "
                "ba con số trên CHƯA phải bản cuối.\n"
            )
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_v711")
    ap.add_argument("out_dir")
    ap.add_argument("--recovered", default=None,
                    help="bảng thu hồi đã điền; có nó thì 47 bản ghi được tính nốt")
    a = ap.parse_args()
    rep = migrate(a.csv_v711, a.out_dir, a.recovered)
    print(f"Tổng: {rep['total']} · đã tính: {rep['computed']} · "
          f"chờ thu hồi: {rep['pending_recovery']} · loại trừ: {rep['excluded']}")
    if rep["pending_recovery"]:
        print("Điền bảng thu_hoi_thong_ke_nguon_47.csv rồi chạy lại với --recovered")
    p = rep.get("pool_main")
    if p:
        print(f"r̄ định hướng (observed): {p['r']:+.4f} "
              f"[k = {p['k_studies']}, K = {p['K_effects']}] — xem bao_cao_di_tru.txt")
    sys.exit(0)
