/**
 * ContactDialog - who is behind M-AIDA and how to reach them.
 *
 * Opened from the login footer and the app footer. Decided 03/10/2026:
 * M-AIDA is presented as a doctoral research project (no institutional
 * address); Assoc. Prof. Phan Anh Tu agreed to his picture, e-mail and site
 * appearing here, with his academic rank and project roles only. The two
 * avatars are cropped from the project's character illustrations (see
 * assets/people/README.md); they are the only place characters appear
 * outside the sign-in page.
 */

import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import avatarHuong from "../assets/people/avatar-huong.webp";
import avatarTu from "../assets/people/avatar-tu.webp";

interface ContactDialogProps {
  open: boolean;
  onClose: () => void;
}

const BETA_EMAIL = "thuyhuongctu@gmail.com";

export default function ContactDialog({ open, onClose }: ContactDialogProps) {
  const { t } = useI18n();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const people = [
    {
      key: "huong",
      img: avatarHuong,
      name: t("contact_huong_name"),
      role: t("contact_huong_role"),
      links: [
        { href: `mailto:${BETA_EMAIL}`, label: BETA_EMAIL },
        { href: "https://github.com/thuyhuongctu/M-AIDA", label: "github.com/thuyhuongctu/M-AIDA" },
      ],
    },
    {
      key: "tu",
      img: avatarTu,
      name: t("contact_tu_name"),
      role: t("contact_tu_role"),
      links: [
        { href: "mailto:patu@ctu.edu.vn", label: "patu@ctu.edu.vn" },
        { href: "https://patueconomics.com/", label: "patueconomics.com" },
      ],
    },
  ];

  return (
    <dialog
      ref={ref}
      className="contact-dialog"
      aria-labelledby="contact-title"
      data-testid="contact-dialog"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose(); // click on the backdrop
      }}
    >
      <div className="contact-head">
        <h2 id="contact-title">{t("contact_title")}</h2>
        <button type="button" className="contact-x" onClick={onClose} aria-label={t("contact_close")}>
          ×
        </button>
      </div>
      <p className="contact-intro">{t("contact_intro")}</p>
      <div className="contact-people">
        {people.map((p) => (
          <section key={p.key} className="contact-card">
            <img className="contact-avatar" src={p.img} alt="" width={72} height={72} />
            <div className="contact-card-text">
              <h3>{p.name}</h3>
              <p className="contact-role">{p.role}</p>
              {p.links.map((l) => (
                <a
                  key={l.href}
                  className="contact-link mono"
                  href={l.href}
                  {...(l.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                >
                  {l.label}
                </a>
              ))}
            </div>
          </section>
        ))}
      </div>
      <dl className="contact-facts">
        <dt>{t("contact_beta_label")}</dt>
        <dd>
          {t("contact_beta")} <a href={`mailto:${BETA_EMAIL}`}>{BETA_EMAIL}</a>
        </dd>
      </dl>
    </dialog>
  );
}
