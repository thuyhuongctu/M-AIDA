# ============================================================================
# M-AIDA · effect_sizes.R
# Corrected effect-size conversion formulas (review findings A1, A2, A3).
# Source this file before building the metafor dataset; every conversion the
# Python extractor performs is mirrored here so the R release pipeline can
# recompute and cross-check any record from its raw statistics.
#
#   A1  Peterson & Brown (2005):  r = 0.98*beta + 0.05*lambda,
#       lambda = 1 if beta >= 0 else 0; valid only for |beta| <= 0.5.
#   A2  Regression t-statistic:   df = n - p - 1  (never a bare n - 2
#       unless the model is bivariate, i.e. p = 1).
#   A3  Sampling variance differs by metric type:
#       zero-order  Var(r)   = (1 - r^2)^2 / (n - 1)
#       partial     Var(r_p) = (1 - r_p^2)^2 / df
# ============================================================================

#' Convert a standardised regression coefficient to Pearson's r.
#'
#' Full Peterson & Brown (2005) formula including the lambda intercept.
#' Returns NA (with a warning) outside the derivation domain |beta| > 0.5:
#' such records are excluded from pooling, never clamped.
pb_beta_to_r <- function(beta) {
  stopifnot(is.numeric(beta))
  out_of_domain <- abs(beta) > 0.5
  if (any(out_of_domain, na.rm = TRUE)) {
    warning(sprintf(
      "%d beta value(s) outside the Peterson & Brown domain |beta| <= 0.5; returned NA",
      sum(out_of_domain, na.rm = TRUE)
    ))
  }
  lambda <- ifelse(beta >= 0, 1, 0)
  r <- 0.98 * beta + 0.05 * lambda
  r[out_of_domain] <- NA_real_
  pmax(-1, pmin(1, r))
}

#' Residual degrees of freedom for a t-statistic from a regression model.
#'
#' df = n - p - 1, where p counts every predictor (focal variable plus
#' controls, excluding the intercept). p = 1 reduces to the bivariate n - 2.
df_regression <- function(n, p) {
  stopifnot(is.numeric(n), is.numeric(p))
  df <- n - p - 1
  if (any(df <= 0, na.rm = TRUE)) {
    warning("non-positive df produced; check n and p")
  }
  df
}

#' Convert a t-statistic to Pearson's r (Cohen, 1988), sign preserved.
t_to_r <- function(t, df) {
  stopifnot(is.numeric(t), is.numeric(df))
  sign(t) * sqrt(t^2 / (t^2 + df))
}

#' Sampling variance of a correlation, by metric type.
#'
#' metric_type must be given per record; there is no silent default because
#' zero-order and partial correlations have different denominators, and a
#' wrong denominator gives every study the wrong pooling weight.
var_r <- function(r, metric_type, n = NA_real_, df = NA_real_) {
  stopifnot(is.numeric(r), is.character(metric_type))
  mapply(function(ri, mt, ni, dfi) {
    if (is.na(ri)) return(NA_real_)
    if (mt == "zero_order") {
      if (is.na(ni) || ni <= 1) stop("zero-order variance requires n > 1")
      (1 - ri^2)^2 / (ni - 1)
    } else if (mt == "partial") {
      if (is.na(dfi) || dfi <= 0) stop("partial-correlation variance requires df > 0")
      (1 - ri^2)^2 / dfi
    } else {
      stop(sprintf("unsupported metric_type: %s", mt))
    }
  }, r, metric_type, n, df)
}
