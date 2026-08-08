"""
test_effect_size.py — Kiểm thử đơn vị.

Mọi giá trị kỳ vọng đều tính tay và ghi rõ phép tính trong chú thích,
để hội đồng có thể kiểm lại bằng máy tính bỏ túi.

Chạy:  python test_effect_size.py       (không cần pytest)
hoặc:  pytest test_effect_size.py
"""

import math
from effect_size import (
    convert, from_beta, from_t, from_reported_r, legacy_r,
    degrees_of_freedom, variance_zero_order, variance_partial,
    fisher_z, z_to_r, variance_z, ConversionError,
    ZERO_ORDER, PARTIAL,
)

TOL = 1e-9


def close(a, b, tol=TOL):
    assert abs(a - b) < tol, f"kỳ vọng {b}, nhận được {a}"


# =========================================================================
# A1 · Peterson & Brown — số hạng lambda
# =========================================================================

def test_A1_beta_duong_cong_them_005():
    """
    beta = 0.30, lambda = 1
    r = .98 * 0.30 + .05 * 1 = 0.294 + 0.05 = 0.344
    Cách cũ cho 0.294 — thấp hơn đúng 0.05.
    """
    rec = from_beta(0.30, n=200, n_predictors=8)
    close(rec.r, 0.344)
    close(legacy_r("beta", 0.30, 200), 0.294)
    close(rec.r - legacy_r("beta", 0.30, 200), 0.05)
    assert rec.lambda_applied is True


def test_A1_beta_am_khong_cong():
    """
    beta = -0.30, lambda = 0
    r = .98 * (-0.30) + 0 = -0.294
    Trùng cách cũ. Đây chính là chỗ lệch MỘT CHIỀU.
    """
    rec = from_beta(-0.30, n=200, n_predictors=8)
    close(rec.r, -0.294)
    close(rec.r - legacy_r("beta", -0.30, 200), 0.0)


def test_A1_lech_mot_chieu_lam_ha_uoc_luong_gop():
    """
    Bộ 4 beta cân đối hai dấu. Cách cũ hạ trung bình xuống 0.025;
    lệch không triệt tiêu vì chỉ áp lên nửa dương.
    """
    betas = [0.30, 0.20, -0.20, -0.30]
    new = [from_beta(b, n=200, n_predictors=8).r for b in betas]
    old = [legacy_r("beta", b, 200) for b in betas]
    close(sum(new) / 4 - sum(old) / 4, 0.025)


def test_A1_ngoai_khoang_bi_loai():
    """|beta| > 0.5 nằm ngoài phạm vi Peterson & Brown kiểm định."""
    for bad in (0.62, -0.75, 1.10):
        try:
            from_beta(bad, n=200, n_predictors=8)
        except ConversionError:
            continue
        raise AssertionError(f"beta = {bad} lẽ ra phải bị loại")


def test_A1_bien_khoang_van_hop_le():
    """
    beta = 0.50 (biên trên): r = .98*0.5 + .05 = 0.49 + 0.05 = 0.54
    """
    close(from_beta(0.50, n=200, n_predictors=8).r, 0.54)


# =========================================================================
# A2 · Bậc tự do
# =========================================================================

def test_A2_df_dung_cho_hoi_quy_boi():
    """n = 80, p = 12  ->  df = 80 - 12 - 1 = 67"""
    df, src = degrees_of_freedom(n=80, n_predictors=12)
    assert df == 67 and src == "derived"


def test_A2_do_lech_so_voi_cach_cu():
    """
    t = 2.5, n = 80, p = 12
      đúng: df = 67, r = 2.5 / sqrt(6.25 + 67)  = 2.5 / sqrt(73.25)
      cũ  : df = 78, r = 2.5 / sqrt(6.25 + 78)  = 2.5 / sqrt(84.25)
    Cách cũ cho r NHỎ HƠN vì mẫu số lớn hơn.
    """
    rec = from_t(2.5, n=80, n_predictors=12)
    close(rec.r, 2.5 / math.sqrt(73.25))
    close(rec.df, 67)
    old = legacy_r("t", 2.5, 80)
    close(old, 2.5 / math.sqrt(84.25))
    assert rec.r > old
    assert abs(rec.r - old) > 0.019   # ~0.0197, không phải sai số làm tròn


def test_A2_cang_nhieu_bien_kiem_soat_cang_lech():
    """Độ lệch tăng đơn điệu theo số biến giải thích."""
    lech = [abs(from_t(2.5, n=80, n_predictors=p).r - legacy_r("t", 2.5, 80))
            for p in (2, 6, 12, 20)]
    assert lech == sorted(lech)


def test_A2_thieu_p_thi_bao_loi_chu_khong_lay_mac_dinh():
    """Không được âm thầm quay về n - 2."""
    try:
        from_t(2.5, n=80)
    except ConversionError as e:
        assert "n_predictors" in str(e)
        return
    raise AssertionError("lẽ ra phải báo lỗi khi thiếu n_predictors")


def test_A2_df_bao_cao_duoc_uu_tien():
    df, src = degrees_of_freedom(n=80, n_predictors=12, df_reported=70)
    assert df == 70 and src == "reported"


# =========================================================================
# A3 · Hai đại lượng, hai công thức phương sai
# =========================================================================

def test_A3_r_bao_cao_la_bac_khong():
    rec = from_reported_r(0.24, n=231)
    assert rec.metric_type == ZERO_ORDER
    # (1 - 0.24^2)^2 / 230 = (1 - 0.0576)^2 / 230 = 0.9424^2 / 230
    close(rec.variance, (0.9424 ** 2) / 230, tol=1e-12)
    assert rec.variance_formula == "(1-r^2)^2/(n-1)"


def test_A3_t_cho_ra_rieng_phan():
    rec = from_t(2.14, n=231, n_predictors=10)
    assert rec.metric_type == PARTIAL
    assert rec.df == 220                      # 231 - 10 - 1
    close(rec.variance, variance_partial(rec.r, 220))
    assert rec.variance_formula == "(1-r^2)^2/df"


def test_A3_hai_cong_thuc_cho_ket_qua_khac_nhau():
    """
    Cùng một r, hai công thức cho hai phương sai khác nhau
    -> trọng số của nghiên cứu trong mô hình gộp khác nhau.
    """
    r, n, df = 0.20, 231, 220
    v0 = variance_zero_order(r, n)            # /230
    vp = variance_partial(r, df)              # /220
    assert vp > v0
    close(vp / v0, 230 / 220)


def test_A3_beta_la_bac_khong_suy_ra():
    """
    P&B hiệu chuẩn công thức để khôi phục r BẬC KHÔNG (số hạng .05*lambda
    tồn tại vì phép khớp với r bậc không quan sát được). metric_type mô tả
    đại lượng cần ước lượng; nguồn gốc suy ra nằm ở estimand_source.
    """
    rec = from_beta(0.30, n=200, n_predictors=8)
    assert rec.metric_type == ZERO_ORDER
    assert rec.estimand_source == "imputed_pb2005"
    assert rec.source_controls is True
    # phương sai theo đại lượng đích: (1 - 0.344^2)^2 / 199
    close(rec.variance, (1 - 0.344 ** 2) ** 2 / 199)
    assert rec.variance_formula == "(1-r^2)^2/(n-1)"


def test_A3_ba_lop_tach_bach():
    """
    r báo cáo : zero_order · observed · không kiểm soát  -> mô hình chính
    t hồi quy : partial    · observed · có kiểm soát     -> mô hình chính
    beta      : zero_order · imputed  · có kiểm soát     -> chỉ độ nhạy
    """
    r_rec = from_reported_r(0.24, n=231)
    t_rec = from_t(2.14, n=231, n_predictors=10)
    b_rec = from_beta(0.30, n=200, n_predictors=8)
    assert (r_rec.metric_type, r_rec.estimand_source, r_rec.source_controls) == \
        (ZERO_ORDER, "observed", False)
    assert (t_rec.metric_type, t_rec.estimand_source, t_rec.source_controls) == \
        (PARTIAL, "observed", True)
    assert (b_rec.metric_type, b_rec.estimand_source, b_rec.source_controls) == \
        (ZERO_ORDER, "imputed_pb2005", True)
    # chỉ bản ghi observed vào mô hình chính
    main = [x for x in (r_rec, t_rec, b_rec) if x.estimand_source == "observed"]
    assert len(main) == 2 and b_rec not in main


# =========================================================================
# A4 · Fisher z
# =========================================================================

def test_A4_z_va_nghich_dao():
    for r in (-0.6, -0.05, 0.0, 0.074, 0.42):
        close(z_to_r(fisher_z(r)), r, tol=1e-12)


def test_A4_z_cua_074():
    """z = atanh(.074) = 0.5*ln(1.074/0.926)"""
    close(fisher_z(0.074), 0.5 * math.log(1.074 / 0.926), tol=1e-12)


def test_A4_phuong_sai_z_theo_dai_luong():
    """Bậc không: 1/(n-3).  Riêng phần: 1/(df-1) = 1/(n-p-2)."""
    close(variance_z(ZERO_ORDER, n=231, df=None), 1 / 228)
    close(variance_z(PARTIAL, n=231, df=220), 1 / 219)
    close(variance_z(PARTIAL, n=231, df=220), 1 / (231 - 10 - 2))


# =========================================================================
# Toàn tuyến
# =========================================================================

def test_nguong_tin_cay():
    assert convert("r", 0.24, 231).confidence == 1.00
    assert convert("t", 2.14, 231, 10).confidence == 0.80
    b = convert("beta", 0.30, 200, 8)
    assert b.confidence == 0.60 and b.flagged is True   # 0.60 < 0.70


def test_moi_ban_ghi_deu_tai_lap_duoc():
    """Bản ghi phải mang đủ thông tin để tính lại từ đầu."""
    rec = convert("t", 2.14, 231, 10)
    assert rec.variance_formula and rec.df_source and rec.metric_type
    assert rec.source_stat == "t" and rec.source_value == 2.14


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    ok = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            ok += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
    print(f"\n{ok}/{len(tests)} kiểm thử đạt")
    raise SystemExit(0 if ok == len(tests) else 1)
