/**
 * Minimal bilingual strings (English default, Vietnamese) for the 8.0 screens.
 *
 * The scientific panels (verification, derived quantities) stay in English:
 * their vocabulary mirrors the data dictionary and the dissertation, and a
 * second rendering of every field label would double the surface to keep in
 * sync. Navigation, sign-in, dashboard, jobs and account text are translated.
 */

import { createContext, useContext } from "react";

export type Lang = "en" | "vi";

const STORAGE_KEY = "maida_lang";

const en = {
  nav_dashboard: "Dashboard",
  nav_extract: "Extract",
  nav_verify: "Verify & Lock",
  nav_account: "Account",
  sign_out: "Sign out",
  signed_in_as: "Signed in as",
  credits: "credits",
  credit_one: "credit",
  // sign-in
  login_title: "Sign in to M-AIDA",
  login_intro:
    "Upload a paper, let the model propose the effect size with verbatim evidence, verify it yourself and lock the record. Each extraction uses one credit.",
  login_email: "E-mail address",
  login_send_link: "Send me a sign-in link",
  login_google: "Continue with Google",
  login_link_sent: "Check your inbox: the sign-in link is valid for a few minutes.",
  login_mock_hint: "Test mode: any e-mail signs in immediately, no password.",
  login_mock_button: "Sign in (test mode)",
  login_or: "or",
  // dashboard
  dash_title: "Your workspace",
  dash_credits: "Credits left",
  dash_studies: "Studies",
  dash_locked: "Locked",
  dash_recent_jobs: "Recent extractions",
  dash_no_jobs: "No extraction yet. Go to Extract and upload a PDF.",
  dash_new_extraction: "New extraction",
  job_status_queued: "queued",
  job_status_running: "running",
  job_status_succeeded: "done",
  job_status_rejected: "rejected",
  job_status_failed: "failed",
  job_file: "File",
  job_status: "Status",
  job_result: "Result",
  job_when: "When",
  job_open_study: "Open record",
  job_refunded: "credit refunded",
  // extraction
  ex_queued: "Uploaded. Waiting for a slot…",
  ex_running: "The model is reading the paper…",
  ex_rejected: "Rejected: no usable evidence. The credit is kept because the model was called.",
  ex_failed: "Failed on our side. Your credit has been refunded.",
  ex_no_credits: "You have no credits left. Ask the operator for more.",
  ex_cost_note: "One credit per upload. Rejected extractions (no verbatim evidence in the paper) also use the credit; failures on our side are refunded automatically.",
  // account
  acc_title: "Account",
  acc_email: "E-mail",
  acc_role: "Role",
  acc_balance: "Credit balance",
  acc_ledger: "Credit history",
  acc_export: "Download all my data (JSON)",
  acc_ledger_empty: "No credit movements yet.",
  reason_grant_beta: "Beta grant",
  reason_extraction: "Extraction",
  reason_refund: "Refund",
  reason_adjust_admin: "Granted by operator",
  reason_purchase: "Purchase",
  // admin
  admin_title: "Operator tools",
  admin_grant: "Grant credits",
  admin_grant_email: "User e-mail",
  admin_grant_amount: "Credits",
  admin_grant_button: "Grant",
  admin_usage: "Model usage (last 30 days)",
  admin_calls: "calls",
  admin_cost: "estimated cost",
  admin_users: "Accounts",
  // legal
  legal_terms: "Terms of Service",
  legal_privacy: "Privacy Policy",
  login_legal_prefix: "By signing in you accept the",
  login_legal_and: "and the",
  // misc
  loading: "Loading…",
  error_generic: "Something went wrong.",
  lang_switch: "Tiếng Việt",
};

const vi: typeof en = {
  nav_dashboard: "Bảng điều khiển",
  nav_extract: "Trích xuất",
  nav_verify: "Duyệt & Khóa",
  nav_account: "Tài khoản",
  sign_out: "Đăng xuất",
  signed_in_as: "Đang đăng nhập",
  credits: "tín dụng",
  credit_one: "tín dụng",
  login_title: "Đăng nhập M-AIDA",
  login_intro:
    "Tải bài báo lên, mô hình đề xuất hệ số hiệu ứng kèm câu trích nguyên văn, cô/thầy tự kiểm tra rồi khóa bản ghi. Mỗi lượt trích xuất dùng một tín dụng.",
  login_email: "Địa chỉ e-mail",
  login_send_link: "Gửi liên kết đăng nhập",
  login_google: "Tiếp tục với Google",
  login_link_sent: "Kiểm tra hộp thư: liên kết đăng nhập có hiệu lực vài phút.",
  login_mock_hint: "Chế độ thử: nhập e-mail bất kỳ là vào ngay, không cần mật khẩu.",
  login_mock_button: "Đăng nhập (chế độ thử)",
  login_or: "hoặc",
  dash_title: "Không gian làm việc",
  dash_credits: "Tín dụng còn lại",
  dash_studies: "Bản ghi",
  dash_locked: "Đã khóa",
  dash_recent_jobs: "Lượt trích xuất gần đây",
  dash_no_jobs: "Chưa có lượt trích xuất nào. Vào mục Trích xuất và tải PDF lên.",
  dash_new_extraction: "Trích xuất mới",
  job_status_queued: "chờ",
  job_status_running: "đang chạy",
  job_status_succeeded: "xong",
  job_status_rejected: "từ chối",
  job_status_failed: "lỗi",
  job_file: "Tệp",
  job_status: "Trạng thái",
  job_result: "Kết quả",
  job_when: "Lúc",
  job_open_study: "Mở bản ghi",
  job_refunded: "đã hoàn tín dụng",
  ex_queued: "Đã tải lên. Đang chờ đến lượt…",
  ex_running: "Mô hình đang đọc bài báo…",
  ex_rejected: "Bị từ chối: không có bằng chứng dùng được. Tín dụng vẫn tính vì mô hình đã được gọi.",
  ex_failed: "Lỗi phía hệ thống. Tín dụng đã được hoàn.",
  ex_no_credits: "Đã hết tín dụng. Liên hệ người vận hành để được cấp thêm.",
  ex_cost_note: "Mỗi lượt tải lên tính một tín dụng. Lượt bị từ chối (bài không có câu trích nguyên văn) vẫn tính; lỗi phía hệ thống được hoàn tự động.",
  acc_title: "Tài khoản",
  acc_email: "E-mail",
  acc_role: "Vai trò",
  acc_balance: "Số dư tín dụng",
  acc_ledger: "Lịch sử tín dụng",
  acc_export: "Tải toàn bộ dữ liệu của tôi (JSON)",
  acc_ledger_empty: "Chưa có giao dịch tín dụng.",
  reason_grant_beta: "Cấp beta",
  reason_extraction: "Trích xuất",
  reason_refund: "Hoàn",
  reason_adjust_admin: "Người vận hành cấp",
  reason_purchase: "Mua",
  admin_title: "Công cụ vận hành",
  admin_grant: "Cấp tín dụng",
  admin_grant_email: "E-mail người dùng",
  admin_grant_amount: "Số tín dụng",
  admin_grant_button: "Cấp",
  admin_usage: "Sử dụng mô hình (30 ngày qua)",
  admin_calls: "lượt gọi",
  admin_cost: "chi phí ước tính",
  admin_users: "Tài khoản",
  legal_terms: "Điều khoản dịch vụ",
  legal_privacy: "Chính sách riêng tư",
  login_legal_prefix: "Khi đăng nhập, bạn chấp nhận",
  login_legal_and: "và",
  loading: "Đang tải…",
  error_generic: "Có lỗi xảy ra.",
  lang_switch: "English",
};

export type StringKey = keyof typeof en;

const DICTS: Record<Lang, typeof en> = { en, vi };

export function readLang(): Lang {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "vi" ? "vi" : "en";
  } catch {
    return "en";
  }
}

export function storeLang(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // ignore: language just won't persist
  }
}

export function translate(lang: Lang, key: StringKey): string {
  return DICTS[lang][key] ?? en[key] ?? key;
}

export interface I18n {
  lang: Lang;
  t: (key: StringKey) => string;
  setLang: (lang: Lang) => void;
}

export const I18nContext = createContext<I18n>({
  lang: "en",
  t: (key) => en[key],
  setLang: () => undefined,
});

export function useI18n(): I18n {
  return useContext(I18nContext);
}
