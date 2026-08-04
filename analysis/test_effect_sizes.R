# ============================================================================
# M-AIDA · test_effect_sizes.R
# Unit tests for the corrected conversions, with hand-computed expectations.
# Run:  Rscript -e 'testthat::test_file("analysis/test_effect_sizes.R")'
# ============================================================================

library(testthat)
# Works both from the repo root and from inside analysis/.
if (file.exists("analysis/effect_sizes.R")) {
  source("analysis/effect_sizes.R")
} else {
  source("effect_sizes.R")
}

test_that("Peterson & Brown includes the lambda term", {
  expect_equal(pb_beta_to_r(0.30), 0.344)    # 0.98*0.30 + 0.05*1
  expect_equal(pb_beta_to_r(0.50), 0.540)    # domain edge, positive
  expect_equal(pb_beta_to_r(0.10), 0.148)    # 0.098 + 0.05
  expect_equal(pb_beta_to_r(0.00), 0.050)    # lambda = 1 at beta = 0
  expect_equal(pb_beta_to_r(-0.30), -0.294)  # no lambda term for beta < 0
  expect_equal(pb_beta_to_r(-0.50), -0.490)  # domain edge, negative
})

test_that("the conversion is not an odd function: |r(+b)| = |r(-b)| + .05", {
  expect_equal(pb_beta_to_r(0.3), -pb_beta_to_r(-0.3) + 0.05)
})

test_that("betas outside |0.5| return NA with a warning, never a clamp", {
  expect_warning(res <- pb_beta_to_r(c(0.51, -0.7, 1.0)))
  expect_true(all(is.na(res)))
})

test_that("df is n - p - 1, reducing to n - 2 only when p = 1", {
  expect_equal(df_regression(100, 1), 98)
  expect_equal(df_regression(231, 10), 220)
  expect_equal(df_regression(250, 12), 237)
  expect_equal(df_regression(60, 15), 44)
})

test_that("n - 2 instead of n - p - 1 understates r from a regression t", {
  # t = 2.14, n = 231, p = 10: wrong df 229 vs right df 220
  r_wrong <- t_to_r(2.14, 231 - 2)
  r_right <- t_to_r(2.14, df_regression(231, 10))
  expect_gt(r_right, r_wrong)
  expect_equal(r_right, 2.14 / sqrt(2.14^2 + 220))
})

test_that("zero-order variance: (1 - r^2)^2 / (n - 1)", {
  expect_equal(var_r(0.30, "zero_order", n = 101), 0.008281)  # .91^2 / 100
  expect_equal(var_r(0.00, "zero_order", n = 5), 0.25)        # 1 / 4
})

test_that("partial variance: (1 - r^2)^2 / df", {
  df <- df_regression(114, 13)                                # = 100
  expect_equal(df, 100)
  expect_equal(var_r(0.30, "partial", df = df), 0.008281)
})

test_that("same r, same n: partial variance exceeds zero-order (finding A3)", {
  v_zero <- var_r(0.30, "zero_order", n = 114)                # denom 113
  v_partial <- var_r(0.30, "partial", df = 100)               # denom 100
  expect_gt(v_partial, v_zero)
  expect_equal(v_zero, 0.8281 / 113)
})

test_that("missing inputs and unknown metric types are hard errors", {
  expect_error(var_r(0.3, "zero_order"))
  expect_error(var_r(0.3, "partial"))
  expect_error(var_r(0.3, "marginal", n = 100))
})
