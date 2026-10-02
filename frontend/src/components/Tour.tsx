/**
 * Tour - a guided walk through the application in plain text boxes (8.0).
 *
 * Each step names a tab and a `data-tour` target; the tour switches the tab,
 * scrolls the target into view, outlines it and places the card next to it.
 * Starts once per browser on the first sign-in (localStorage flag) and can be
 * reopened from the Guide button. No illustrations, no persona: the text says
 * what the screen does and what the rules are.
 */

import React, { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { useI18n, type Lang } from "../i18n";

export type TourTab = "dashboard" | "extract" | "verify" | "dataset";

interface Step {
  tab: TourTab | null;
  target: string | null;
  title: string;
  body: string;
}

const STEPS: Record<Lang, Step[]> = {
  en: [
    { tab: null, target: null, title: "Welcome to M-AIDA", body: "A two-minute walk through the workflow: upload a paper, read the evidence the model quoted, verify the values, lock the record, and export the dataset for the meta-analysis." },
    { tab: "dashboard", target: "credits", title: "Your credits", body: "Each extraction uses one credit. New accounts start with 10 beta credits. A paper refused by the evidence gate keeps the charge, because the model was called; failures on our side are refunded automatically. The history is under Account." },
    { tab: "extract", target: "drop", title: "Upload a PDF", body: "Drop the PDF here and fill in title, authors, year and country. Up to 40,000 characters of text are sent to the model. The PDF itself is read in memory and never stored." },
    { tab: "extract", target: "pipeline", title: "Follow the pipeline", body: "The text is read, the focal coefficient and the sample size are identified, the statistic is converted to Pearson r, then the evidence gate checks it: without a verbatim quotation and page number for both quantities the record is refused." },
    { tab: "verify", target: "queue", title: "The review queue", body: "Every machine proposal lands here. ◇ needs review, ◆ approved by you, amber ◆ locked. A confidence below 0.70 is shown in red. The keys J and K move through the list, A approves, L opens the lock dialog." },
    { tab: "verify", target: "evidence", title: "Read the evidence", body: "The verbatim sentence the model relied on, with its page, for the statistic and for the sample size, and how the server derived r from it. Compare it with the paper before trusting any number." },
    { tab: "verify", target: "stats", title: "Compare and correct", body: "The Machine column never changes. Edit the Current column when the paper says otherwise; the row is highlighted so the change stays visible, and the server re-derives the variance from what you entered." },
    { tab: "verify", target: "mods", title: "Assign the moderators", body: "ICRV, DPL, DOI and performance measures are assigned by you, not extracted. Click once to select, again to clear." },
    { tab: "verify", target: "actions", title: "Approve, then lock", body: "Write what you checked, approve, then lock. Locking asks you to type the study ID and cannot be undone; a locked record is what the export contains." },
    { tab: "dataset", target: "export", title: "Export", body: "Only locked records go into the CSV for R (metafor) or Stata, and to Notion. The forest plot above is a fixed-effect preview; the three-level model runs in metafor. Your data stays separate from other accounts; download all of it under Account." },
    { tab: null, target: null, title: "That is all", body: "Open this guide again any time from the Guide button in the header." },
  ],
  vi: [
    { tab: null, target: null, title: "Chào mừng đến M-AIDA", body: "Hai phút đi một vòng quy trình: tải bài báo, đọc bằng chứng mô hình đã trích, kiểm chứng giá trị, khóa bản ghi và xuất bộ dữ liệu cho phân tích gộp." },
    { tab: "dashboard", target: "credits", title: "Tín dụng của quý vị", body: "Mỗi lượt trích xuất dùng một tín dụng. Tài khoản mới có 10 tín dụng beta. Bài bị cổng bằng chứng từ chối vẫn tính, vì mô hình đã được gọi; lỗi phía hệ thống được hoàn tự động. Lịch sử nằm ở mục Tài khoản." },
    { tab: "extract", target: "drop", title: "Tải bài báo PDF", body: "Thả tệp PDF vào đây và điền tên bài, tác giả, năm, quốc gia. Hệ thống gửi tối đa 40.000 ký tự văn bản cho mô hình. Tệp PDF chỉ được đọc trong bộ nhớ, không bao giờ lưu." },
    { tab: "extract", target: "pipeline", title: "Theo dõi quy trình", body: "Văn bản được đọc, hệ số chính và cỡ mẫu được nhận diện, thống kê được quy đổi về r Pearson, rồi cổng bằng chứng kiểm tra: thiếu câu trích nguyên văn và số trang cho một trong hai đại lượng là bản ghi bị từ chối." },
    { tab: "verify", target: "queue", title: "Hàng chờ kiểm chứng", body: "Mọi đề xuất của máy vào đây. ◇ cần kiểm chứng, ◆ quý vị đã duyệt, ◆ hổ phách đã khóa. Tin cậy dưới 0,70 hiện màu đỏ. Phím J và K chuyển bản ghi, A duyệt, L mở hộp khóa." },
    { tab: "verify", target: "evidence", title: "Đọc bằng chứng", body: "Câu nguyên văn mô hình dựa vào, kèm số trang, cho thống kê và cho cỡ mẫu, và cách máy chủ quy đổi ra r. Đối chiếu với bài báo trước khi tin bất kỳ con số nào." },
    { tab: "verify", target: "stats", title: "Đối chiếu và sửa", body: "Cột Máy đề xuất không bao giờ thay đổi. Sửa cột Hiện tại khi bài báo nói khác; dòng được tô màu để thấy rõ chỗ đã chỉnh, và máy chủ dẫn xuất lại phương sai từ giá trị quý vị nhập." },
    { tab: "verify", target: "mods", title: "Gán biến điều tiết", body: "ICRV, DPL, đo DOI và đo hiệu quả do nhà nghiên cứu gán, máy không tự điền. Bấm một lần để chọn, bấm lại để bỏ." },
    { tab: "verify", target: "actions", title: "Duyệt, rồi khóa", body: "Ghi lại đã đối chiếu gì, bấm Duyệt, sau đó Khóa. Khi khóa phải gõ lại mã nghiên cứu và không thể hoàn tác; bản ghi đã khóa là thứ được xuất ra." },
    { tab: "dataset", target: "export", title: "Xuất dữ liệu", body: "Chỉ bản ghi đã khóa vào CSV cho R (metafor) hoặc Stata và lên Notion. Forest plot ở trên là xem trước theo hiệu ứng cố định; mô hình ba cấp chạy ở metafor. Dữ liệu của quý vị tách riêng với tài khoản khác; tải toàn bộ ở mục Tài khoản." },
    { tab: null, target: null, title: "Vậy là xong", body: "Mở lại hướng dẫn này bất cứ lúc nào bằng nút Hướng dẫn ở thanh đầu." },
  ],
};

const DONE_KEY = "maida_tour_done";

export function tourDone(): boolean {
  try {
    return localStorage.getItem(DONE_KEY) === "1";
  } catch {
    return true;
  }
}

function markDone(): void {
  try {
    localStorage.setItem(DONE_KEY, "1");
  } catch {
    // ignore
  }
}

interface TourProps {
  open: boolean;
  onClose: () => void;
  onTab: (tab: TourTab) => void;
}

export default function Tour({ open, onClose, onTab }: TourProps) {
  const { t, lang } = useI18n();
  const steps = STEPS[lang];
  const [index, setIndex] = useState(0);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    if (open) setIndex(0);
  }, [open]);

  const step = steps[Math.min(index, steps.length - 1)];

  // Switch tab, then (next frame) find the target, scroll and position the card.
  useEffect(() => {
    if (!open) return;
    if (step.tab) onTab(step.tab);
  }, [open, step.tab, onTab]);

  useLayoutEffect(() => {
    if (!open) return;
    document.querySelectorAll(".tour-target").forEach((el) => el.classList.remove("tour-target"));
    if (!step.target) {
      setPos(null);
      return;
    }
    let tries = 0;
    let timer = 0;
    const place = () => {
      const el = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
      if (!el) {
        if (tries++ < 20) timer = window.setTimeout(place, 50);
        else setPos(null);
        return;
      }
      el.classList.add("tour-target");
      el.scrollIntoView({ block: "center", behavior: "smooth" });
      const r = el.getBoundingClientRect();
      const cardW = 340;
      let left = r.right + 16;
      if (left + cardW > window.innerWidth - 16) left = Math.max(16, r.left);
      let top = r.top;
      if (left === Math.max(16, r.left) && left !== r.right + 16) top = r.bottom + 12;
      top = Math.max(16, Math.min(top, window.innerHeight - 240));
      setPos({ top, left });
    };
    timer = window.setTimeout(place, 60);
    return () => {
      window.clearTimeout(timer);
      document.querySelectorAll(".tour-target").forEach((el) => el.classList.remove("tour-target"));
    };
  }, [open, step.target, index]);

  const finish = useCallback(() => {
    markDone();
    onClose();
  }, [onClose]);

  if (!open) return null;
  const last = index >= steps.length - 1;
  const style: React.CSSProperties = pos ? { position: "fixed", top: pos.top, left: pos.left } : { position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)" };

  return (
    <div className="tour" role="dialog" aria-modal="false" aria-label={step.title} data-testid="tour">
      <div className="tour-card" style={style}>
        <span className="eyebrow mono">{index + 1} / {steps.length}</span>
        <h3 className="tour-title">{step.title}</h3>
        <p className="tour-body">{step.body}</p>
        <div className="tour-btns">
          <button type="button" className="btn btn-link" onClick={finish} data-testid="tour-skip">
            {t("tour_skip")}
          </button>
          <span className="tour-btns-right">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
              {t("tour_back")}
            </button>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => (last ? finish() : setIndex((i) => i + 1))} data-testid="tour-next">
              {last ? t("tour_done") : t("tour_next")}
            </button>
          </span>
        </div>
      </div>
    </div>
  );
}
