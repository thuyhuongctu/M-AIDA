## ===========================================================================
## effect_size.R — Chuyển đổi cỡ ảnh hưởng cho M-AIDA (bản đã sửa A1–A3)
##
##   A1  r = .98*beta + .05*lambda   (lambda = 1 nếu beta >= 0, 0 nếu beta < 0)
##       chỉ hợp lệ khi -0.5 <= beta <= 0.5
##   A2  df = n - p - 1  cho thống kê t lấy từ hồi quy bội (KHÔNG phải n - 2)
##   A3  tương quan bậc không và riêng phần dùng hai công thức phương sai khác nhau
##   A4  gộp trên thang Fisher z, chuyển ngược khi báo cáo
##
## Chạy kiểm tra:  Rscript effect_size.R
## ===========================================================================

BETA_MIN <- -0.50
BETA_MAX <-  0.50
CONFIDENCE_THRESHOLD <- 0.70

## --- Bậc tự do (A2) --------------------------------------------------------
degrees_of_freedom <- function(n, n_predictors = NA, df_reported = NA) {
  if (!is.na(df_reported)) {
    stopifnot(df_reported >= 1)
    return(list(df = as.integer(df_reported), source = "reported"))
  }
  if (is.na(n_predictors)) {
    stop("Thiếu n_predictors. Không suy được bậc tự do; bản ghi phải chờ ",
         "người rà soát. Tuyệt đối không lấy mặc định n - 2.")
  }
  df <- n - n_predictors - 1
  if (df < 1) stop(sprintf("df = %d không hợp lệ (n=%d, p=%d)", df, n, n_predictors))
  list(df = as.integer(df), source = "derived")
}

## --- Phương sai (A3) -------------------------------------------------------
variance_zero_order <- function(r, n)  (1 - r^2)^2 / (n - 1)
variance_partial    <- function(r, df) (1 - r^2)^2 / df

## --- Fisher z (A4) ---------------------------------------------------------
fisher_z <- function(r) atanh(r)
z_to_r   <- function(z) tanh(z)

variance_z <- function(metric_type, n, df = NA) {
  if (metric_type == "zero_order") return(1 / (n - 3))
  stopifnot(!is.na(df), df > 1)
  1 / (df - 1)                      # = 1/(n - p - 2)
}

## --- Ba đường chuyển đổi ---------------------------------------------------
from_reported_r <- function(r, n) {
  list(r = r, metric_type = "zero_order",
       variance = variance_zero_order(r, n),
       fisher_z = fisher_z(r), var_z = variance_z("zero_order", n),
       df = NA, df_source = "not_applicable",
       variance_formula = "(1-r^2)^2/(n-1)",
       lambda_applied = NA, beta_in_range = NA,
       confidence = 1.00, flagged = FALSE)
}

from_t <- function(t, n, n_predictors = NA, df_reported = NA) {
  d <- degrees_of_freedom(n, n_predictors, df_reported)
  r <- t / sqrt(t^2 + d$df)
  list(r = r, metric_type = "partial",
       variance = variance_partial(r, d$df),
       fisher_z = fisher_z(r), var_z = variance_z("partial", n, d$df),
       df = d$df, df_source = d$source,
       variance_formula = "(1-r^2)^2/df",
       lambda_applied = NA, beta_in_range = NA,
       confidence = 0.80, flagged = FALSE)
}

from_beta <- function(beta, n, n_predictors = NA, df_reported = NA) {
  if (beta < BETA_MIN || beta > BETA_MAX) {
    stop(sprintf(paste("beta = %.3f ngoài khoảng [%.2f, %.2f].",
                       "Peterson & Brown không kiểm định phép quy đổi ngoài",
                       "khoảng này; bản ghi phải bị LOẠI TRỪ, không chỉ gắn cờ."),
                 beta, BETA_MIN, BETA_MAX))
  }
  lambda <- if (beta >= 0) 1 else 0
  r <- 0.98 * beta + 0.05 * lambda
  d <- tryCatch(degrees_of_freedom(n, n_predictors, df_reported),
                error = function(e) list(df = NA, source = "missing"))
  if (!is.na(d$df)) {
    v  <- variance_partial(r, d$df); vz <- variance_z("partial", n, d$df)
    fo <- "(1-r^2)^2/df"
  } else {
    v  <- variance_zero_order(r, n); vz <- variance_z("zero_order", n)
    fo <- "(1-r^2)^2/(n-1) [tạm thời, thiếu df]"
  }
  list(r = r, metric_type = "partial", variance = v,
       fisher_z = fisher_z(r), var_z = vz,
       df = d$df, df_source = d$source, variance_formula = fo,
       lambda_applied = TRUE, beta_in_range = TRUE,
       confidence = 0.60, flagged = TRUE)
}

convert <- function(stat_type, value, n, n_predictors = NA, df_reported = NA) {
  rec <- switch(tolower(stat_type),
    "r"    = from_reported_r(value, n),
    "t"    = from_t(value, n, n_predictors, df_reported),
    "beta" = from_beta(value, n, n_predictors, df_reported),
    stop("stat_type không hợp lệ: ", stat_type))
  rec$flagged <- rec$flagged || rec$confidence < CONFIDENCE_THRESHOLD
  rec
}

## --- Cách tính CŨ, giữ lại để đo chênh lệch --------------------------------
legacy_r <- function(stat_type, value, n) {
  switch(tolower(stat_type),
    "r"    = value,
    "t"    = value / sqrt(value^2 + (n - 2)),   # A2 sai
    "beta" = 0.98 * value,                      # A1 thiếu lambda
    NA_real_)
}

## ===========================================================================
## KIỂM TRA — cùng ví dụ tính tay như bản Python
## ===========================================================================
if (sys.nframe() == 0) {
  ok <- function(a, b, lab, tol = 1e-9) {
    if (abs(a - b) < tol) cat(sprintf("  PASS  %s\n", lab))
    else stop(sprintf("FAIL %s: kỳ vọng %.10f, nhận %.10f", lab, b, a))
  }

  ## A1: beta = 0.30 -> .98*0.30 + .05 = 0.344 ; cũ = 0.294
  ok(from_beta(0.30, 200, 8)$r, 0.344, "A1 beta dương cộng thêm .05")
  ok(from_beta(0.30, 200, 8)$r - legacy_r("beta", 0.30, 200), 0.05, "A1 chênh đúng .05")
  ## A1: beta âm không cộng -> trùng cách cũ, nên lệch là MỘT CHIỀU
  ok(from_beta(-0.30, 200, 8)$r, -0.294, "A1 beta âm giữ nguyên")
  ok(from_beta(0.50, 200, 8)$r, 0.54, "A1 biên trên vẫn hợp lệ")

  ## A2: n = 80, p = 12 -> df = 67 ; t = 2.5
  ok(degrees_of_freedom(80, 12)$df, 67, "A2 df = n - p - 1")
  ok(from_t(2.5, 80, 12)$r, 2.5 / sqrt(6.25 + 67), "A2 r dùng df đúng")
  ok(legacy_r("t", 2.5, 80),  2.5 / sqrt(6.25 + 78), "A2 tái tạo cách cũ")
  stopifnot(from_t(2.5, 80, 12)$r > legacy_r("t", 2.5, 80))
  cat("  PASS  A2 cách cũ cho r nhỏ hơn\n")

  ## A3: hai công thức phương sai
  ok(from_reported_r(0.24, 231)$variance, (1 - 0.24^2)^2 / 230, "A3 phương sai bậc không")
  ok(from_t(2.14, 231, 10)$df, 220, "A3 df = 231 - 10 - 1")
  ok(variance_partial(0.20, 220) / variance_zero_order(0.20, 231), 230 / 220,
     "A3 hai công thức cho trọng số khác nhau")

  ## A4
  ok(z_to_r(fisher_z(0.074)), 0.074, "A4 z và nghịch đảo")
  ok(variance_z("partial", 231, 220), 1 / (231 - 10 - 2), "A4 var(z) riêng phần")

  ## Thiếu p thì phải báo lỗi
  e <- tryCatch({ from_t(2.5, 80); "khong loi" }, error = function(e) "co loi")
  stopifnot(e == "co loi"); cat("  PASS  A2 thiếu p thì báo lỗi\n")
  e <- tryCatch({ from_beta(0.62, 150, 7); "khong loi" }, error = function(e) "co loi")
  stopifnot(e == "co loi"); cat("  PASS  A1 ngoài khoảng thì loại trừ\n")

  cat("\nTất cả kiểm tra đạt.\n")
}

## ===========================================================================
## QUY TRÌNH GỘP — dán vào script phân tích, cần metafor
## ===========================================================================
## library(metafor); library(clubSandwich)
##
## ## 1. Tính cỡ ảnh hưởng THEO ĐÚNG ĐẠI LƯỢNG (A3 + A4)
## ##    metafor có sẵn hai thước đo tách biệt; kiểm tra tên tham số bằng ?escalc
## dat0 <- escalc(measure = "ZCOR",  ri = r, ni = n,
##                data = subset(dat, metric_type == "zero_order"))
## datp <- escalc(measure = "ZPCOR", ti = t, ni = n, mi = n_predictors,
##                data = subset(dat, metric_type == "partial"))
##
## ## 2. KHÔNG gộp hai nhóm nếu chưa mã hóa metric_type làm biến điều tiết.
## ##    Hoặc chuẩn hóa toàn bộ về ZPCOR, hoặc chạy riêng rồi so sánh.
##
## ## 3. Ba cấp so với hai cấp (C2)
## m3 <- rma.mv(yi, vi, random = ~ 1 | study_id/effect_id, data = datp, method = "REML")
## m2 <- rma.mv(yi, vi, random = ~ 1 | study_id,           data = datp, method = "REML")
## anova(m3, m2)          # ba cấp có thêm được gì không?
## m3$sigma2              # phân rã phương sai từng cấp — phải báo cáo
##
## ## 4. Phương sai vững theo cụm, gộp cả mẫu dùng chung (B4)
## coef_test(m3, vcov = "CR2", cluster = datp$sample_id)
##
## ## 5. Khoảng dự báo (C4) — với I² cao, đây mới là con số nói đúng sự thật
## predict(m3, transf = transf.ztor)
##
## ## 6. Thiên lệch công bố: một bảng nhiều ước lượng, không một con số (C3)
## datp$sei <- sqrt(datp$vi)
## pet   <- rma.mv(yi, vi, mods = ~ sei,     random = ~1|study_id/effect_id, data = datp)
## peese <- rma.mv(yi, vi, mods = ~ I(sei^2), random = ~1|study_id/effect_id, data = datp)
## ## PET-PEESE: nếu PET bác bỏ H0 hiệu ứng bằng 0 thì lấy PEESE, ngược lại lấy PET.
##
## ## 7. Giả thuyết chữ S (C1) — đóng góp lớn nhất của bài
## sc <- rma.mv(yi, vi, mods = ~ intl_level + I(intl_level^2) + I(intl_level^3),
##              random = ~ 1 | study_id/effect_id, data = datp)
## ## Dấu kỳ vọng theo Contractor et al. (2003) và Lu & Beamish (2004): - + -
