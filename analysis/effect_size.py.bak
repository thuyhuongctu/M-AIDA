"""
effect_size.py — Chuyển đổi cỡ ảnh hưởng cho M-AIDA.

Sửa ba lỗi trong bản v7.1.1:

  A1  Công thức Peterson & Brown thiếu số hạng lambda.
      Sai:  r = .98 * beta
      Đúng: r = .98 * beta + .05 * lambda,  lambda = 1 nếu beta >= 0, 0 nếu beta < 0
      Chỉ hợp lệ khi -0.5 <= beta <= 0.5.

  A2  Bậc tự do của thống kê t lấy từ hồi quy bội.
      Sai:  df = n - 2          (chỉ đúng cho tương quan hai biến)
      Đúng: df = n - p - 1      (p = số biến giải thích, không kể hệ số chặn)

  A3  Tương quan bậc không và tương quan riêng phần là hai đại lượng khác nhau
      và có hai công thức phương sai khác nhau. Không được gộp làm một.

Dùng:
    from effect_size import convert
    rec = convert(stat_type="t", value=2.5, n=80, n_predictors=12)
    print(rec.r, rec.metric_type, rec.variance, rec.fisher_z)
"""

from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass, asdict, field
from typing import Optional

__version__ = "8.0.0"

# Ngưỡng tin cậy: dưới mức này bản ghi bị gắn cờ chờ rà soát.
CONFIDENCE_THRESHOLD = 0.70

# Peterson & Brown (2005) chỉ kiểm định phép quy đổi trong khoảng này.
BETA_MIN, BETA_MAX = -0.50, 0.50

ZERO_ORDER = "zero_order"
PARTIAL = "partial"

# estimand_source: đại lượng là quan sát trực tiếp hay suy ra qua P&B (2005).
# metric_type mô tả ĐẠI LƯỢNG CẦN ƯỚC LƯỢNG; estimand_source mô tả NGUỒN GỐC
# con số — hai thứ khác nhau và không được lẫn.
OBSERVED = "observed"
IMPUTED_PB2005 = "imputed_pb2005"


class ConversionError(ValueError):
    """Bản ghi không đủ thông tin để chuyển đổi một cách hợp lệ."""


@dataclass
class Record:
    """Một bản ghi cỡ ảnh hưởng đã chuyển đổi, đủ trường để tái lập."""
    r: float
    metric_type: str                 # A3 — đại lượng cần ước lượng
    estimand_source: str             # observed | imputed_pb2005
    source_controls: bool            # thống kê nguồn có kiểm soát biến khác không
    variance: float                  # A3 — phương sai trên thang r
    fisher_z: float                  # A4
    var_z: float                     # A4 — phương sai trên thang z
    df: Optional[int]                # A2
    df_source: str                   # "reported" | "derived" | "not_applicable"
    n: int
    n_predictors: Optional[int]      # A2
    variance_formula: str            # A3 — ghi rõ công thức đã dùng
    lambda_applied: Optional[bool]   # A1
    beta_in_range: Optional[bool]    # A1
    confidence: float
    flagged: bool
    source_stat: str
    source_value: float
    notes: list = field(default_factory=list)

    def as_row(self) -> dict:
        d = asdict(self)
        d["notes"] = "; ".join(self.notes)
        return d


# --------------------------------------------------------------------------
# Bậc tự do
# --------------------------------------------------------------------------

def degrees_of_freedom(n: int, n_predictors: Optional[int],
                       df_reported: Optional[int] = None) -> tuple[int, str]:
    """
    A2. Trả về (df, nguồn).

    df_reported có thì luôn ưu tiên.
    Không có thì df = n - p - 1. Thiếu p thì KHÔNG được lấy mặc định n - 2:
    ném lỗi để bản ghi bị gắn cờ chờ người rà soát.
    """
    if df_reported is not None:
        if df_reported < 1:
            raise ConversionError("df báo cáo phải >= 1")
        return int(df_reported), "reported"

    if n_predictors is None:
        raise ConversionError(
            "Thiếu n_predictors. Không suy được bậc tự do cho thống kê t "
            "lấy từ hồi quy. Bản ghi phải chờ người rà soát, không lấy mặc định n-2."
        )

    df = n - n_predictors - 1
    if df < 1:
        raise ConversionError(f"df = {df} không hợp lệ (n={n}, p={n_predictors})")
    return int(df), "derived"


# --------------------------------------------------------------------------
# Phương sai — A3
# --------------------------------------------------------------------------

def variance_zero_order(r: float, n: int) -> float:
    """Var(r) = (1 - r^2)^2 / (n - 1). Dùng cho tương quan hai biến."""
    if n < 3:
        raise ConversionError("n phải >= 3")
    return (1.0 - r ** 2) ** 2 / (n - 1)


def variance_partial(r: float, df: int) -> float:
    """Var(r_p) = (1 - r_p^2)^2 / df. Dùng cho tương quan riêng phần."""
    if df < 1:
        raise ConversionError("df phải >= 1")
    return (1.0 - r ** 2) ** 2 / df


# --------------------------------------------------------------------------
# Fisher z — A4
# --------------------------------------------------------------------------

def fisher_z(r: float) -> float:
    """z = atanh(r). Gộp trên thang z, chuyển ngược khi báo cáo."""
    if not -1.0 < r < 1.0:
        raise ConversionError(f"r = {r} nằm ngoài (-1, 1)")
    return math.atanh(r)


def z_to_r(z: float) -> float:
    return math.tanh(z)


def variance_z(metric_type: str, n: int, df: Optional[int]) -> float:
    """
    Bậc không:   Var(z)   = 1 / (n - 3)
    Riêng phần:  Var(z_p) = 1 / (df - 1)

    Với df = n - p - 1, biểu thức riêng phần tương đương 1 / (n - p - 2),
    tức đúng dạng quen thuộc 1 / (n - k - 3) khi kiểm soát k = p - 1 biến.
    """
    if metric_type == ZERO_ORDER:
        if n <= 3:
            raise ConversionError("n phải > 3 cho phương sai Fisher z")
        return 1.0 / (n - 3)
    if df is None or df <= 1:
        raise ConversionError("df phải > 1 cho phương sai Fisher z riêng phần")
    return 1.0 / (df - 1)


# --------------------------------------------------------------------------
# Ba đường chuyển đổi
# --------------------------------------------------------------------------

def from_reported_r(r: float, n: int) -> Record:
    """r báo cáo trực tiếp: giữ nguyên, tin cậy 1.0, đại lượng bậc không."""
    var = variance_zero_order(r, n)
    z = fisher_z(r)
    return Record(
        r=r, metric_type=ZERO_ORDER, estimand_source=OBSERVED,
        source_controls=False, variance=var,
        fisher_z=z, var_z=variance_z(ZERO_ORDER, n, None),
        df=None, df_source="not_applicable", n=n, n_predictors=None,
        variance_formula="(1-r^2)^2/(n-1)",
        lambda_applied=None, beta_in_range=None,
        confidence=1.0, flagged=False,
        source_stat="r", source_value=r,
    )


def from_t(t: float, n: int, n_predictors: Optional[int] = None,
           df_reported: Optional[int] = None) -> Record:
    """
    A2 + A3. Thống kê t của một hệ số hồi quy cho ra TƯƠNG QUAN RIÊNG PHẦN,
    không phải tương quan bậc không.
    """
    df, df_source = degrees_of_freedom(n, n_predictors, df_reported)
    r = t / math.sqrt(t ** 2 + df)
    var = variance_partial(r, df)
    return Record(
        r=r, metric_type=PARTIAL, estimand_source=OBSERVED,
        source_controls=True, variance=var,
        fisher_z=fisher_z(r), var_z=variance_z(PARTIAL, n, df),
        df=df, df_source=df_source, n=n, n_predictors=n_predictors,
        variance_formula="(1-r^2)^2/df",
        lambda_applied=None, beta_in_range=None,
        confidence=0.80, flagged=False,
        source_stat="t", source_value=t,
        notes=["Tương quan riêng phần: không gộp chung với r bậc không "
               "nếu chưa mã hóa metric_type làm biến điều tiết."],
    )


def from_beta(beta: float, n: int, n_predictors: Optional[int] = None,
              df_reported: Optional[int] = None) -> Record:
    """
    A1. Peterson & Brown (2005): r = .98*beta + .05*lambda.

    lambda = 1 nếu beta >= 0, lambda = 0 nếu beta < 0.
    Số hạng .05 chỉ cộng cho beta không âm, nên việc bỏ quên nó làm lệch
    MỘT CHIỀU: chỉ hạ thấp các hiệu ứng dương.

    Đại lượng cần ước lượng là TƯƠNG QUAN BẬC KHÔNG: P&B hiệu chuẩn công
    thức bằng cách khớp với r bậc không quan sát được — số hạng .05*lambda
    tồn tại chính vì phép khớp đó. metric_type mô tả đại lượng cần ước
    lượng, không mô tả nguồn gốc con số; nguồn gốc (suy ra, thống kê nguồn
    có kiểm soát biến khác) nằm ở estimand_source và source_controls.
    Bản ghi suy ra KHÔNG vào mô hình chính — chỉ phân tích độ nhạy: công
    thức phương sai bậc không coi giá trị suy ra như quan sát trực tiếp,
    tức bỏ qua sai số quy đổi, nên trọng số vốn đã lớn hơn mức đáng có.
    """
    in_range = BETA_MIN <= beta <= BETA_MAX
    if not in_range:
        raise ConversionError(
            f"beta = {beta} ngoài khoảng [{BETA_MIN}, {BETA_MAX}]. "
            "Peterson & Brown không kiểm định phép quy đổi ngoài khoảng này; "
            "bản ghi phải bị loại trừ, không phải chỉ gắn cờ."
        )

    lam = 1.0 if beta >= 0 else 0.0
    r = 0.98 * beta + 0.05 * lam

    # df vẫn ghi lại nếu suy được — phục vụ kiểm toán, không dùng cho
    # phương sai (đại lượng đích là bậc không).
    try:
        df, df_source = degrees_of_freedom(n, n_predictors, df_reported)
    except ConversionError:
        df, df_source = None, "missing"

    return Record(
        r=r, metric_type=ZERO_ORDER, estimand_source=IMPUTED_PB2005,
        source_controls=True, variance=variance_zero_order(r, n),
        fisher_z=fisher_z(r), var_z=variance_z(ZERO_ORDER, n, None),
        df=df, df_source=df_source, n=n, n_predictors=n_predictors,
        variance_formula="(1-r^2)^2/(n-1)",
        lambda_applied=True, beta_in_range=True,
        confidence=0.60, flagged=True,  # 0.60 < 0.70 -> luôn chờ rà soát
        source_stat="beta", source_value=beta,
        notes=["Suy từ beta (imputed_pb2005): KHÔNG vào mô hình chính, chỉ "
               "phân tích độ nhạy. Phương sai bậc không bỏ qua sai số quy đổi "
               "nên trọng số vốn đã lớn hơn mức đáng có."],
    )


def convert(stat_type: str, value: float, n: int,
            n_predictors: Optional[int] = None,
            df_reported: Optional[int] = None) -> Record:
    """Điểm vào duy nhất. stat_type: 'r' | 't' | 'beta'."""
    st = stat_type.strip().lower()
    if st == "r":
        rec = from_reported_r(float(value), int(n))
    elif st == "t":
        rec = from_t(float(value), int(n), n_predictors, df_reported)
    elif st == "beta":
        rec = from_beta(float(value), int(n), n_predictors, df_reported)
    else:
        raise ConversionError(f"stat_type không hợp lệ: {stat_type}")
    rec.flagged = rec.flagged or rec.confidence < CONFIDENCE_THRESHOLD
    return rec


# --------------------------------------------------------------------------
# Mã lại bộ dữ liệu cũ và xuất báo cáo chênh lệch
# --------------------------------------------------------------------------

def legacy_r(stat_type: str, value: float, n: int) -> Optional[float]:
    """Tái tạo cách tính CŨ của v7.1.1, để đo mức chênh lệch."""
    st = stat_type.strip().lower()
    if st == "r":
        return float(value)
    if st == "t":
        df = n - 2                      # A2: sai
        return float(value) / math.sqrt(float(value) ** 2 + df)
    if st == "beta":
        return 0.98 * float(value)      # A1: thiếu lambda
    return None


def recode_csv(path_in: str, path_out: str) -> dict:
    """
    Đọc CSV cũ (cột: author, year, stat_type, value, n[, n_predictors, df])
    và ghi CSV mới có đủ trường, kèm cột r_legacy và delta_r.
    """
    rows, errors = [], []
    n_up = n_down = 0
    with open(path_in, newline="", encoding="utf-8") as f:
        for i, src in enumerate(csv.DictReader(f), start=2):
            try:
                rec = convert(
                    src["stat_type"], float(src["value"]), int(src["n"]),
                    int(src["n_predictors"]) if src.get("n_predictors") else None,
                    int(src["df"]) if src.get("df") else None,
                )
                old = legacy_r(src["stat_type"], float(src["value"]), int(src["n"]))
                row = {"author": src.get("author", ""), "year": src.get("year", "")}
                row.update(rec.as_row())
                row["r_legacy"] = old
                row["delta_r"] = None if old is None else rec.r - old
                if row["delta_r"]:
                    n_up += row["delta_r"] > 0
                    n_down += row["delta_r"] < 0
                rows.append(row)
            except ConversionError as e:
                errors.append({"line": i, "author": src.get("author", ""),
                               "reason": str(e)})

    if rows:
        with open(path_out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    return {"converted": len(rows), "excluded": len(errors),
            "r_increased": n_up, "r_decreased": n_down, "errors": errors}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Dùng: python effect_size.py <cu.csv> <moi.csv>")
        raise SystemExit(1)
    rep = recode_csv(sys.argv[1], sys.argv[2])
    print(f"Chuyển đổi : {rep['converted']}")
    print(f"Loại trừ   : {rep['excluded']}")
    print(f"r tăng     : {rep['r_increased']}")
    print(f"r giảm     : {rep['r_decreased']}")
    for e in rep["errors"]:
        print(f"  dòng {e['line']} · {e['author']} · {e['reason']}")
