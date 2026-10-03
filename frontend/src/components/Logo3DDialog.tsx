/**
 * Logo3DDialog - "M-AIDA 3D", opened by clicking the logo in the header.
 * The 3D scene (and three.js) is mounted only while the dialog is open.
 */

import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import Logo3D from "./Logo3D";

export default function Logo3DDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
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

  return (
    <dialog
      ref={ref}
      className="logo3d-dialog"
      aria-labelledby="logo3d-title"
      data-testid="logo3d-dialog"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="logo3d-dialog-head">
        <h2 id="logo3d-title">{t("logo3d_title")}</h2>
        <button type="button" className="contact-x" onClick={onClose} aria-label={t("contact_close")}>
          ×
        </button>
      </div>
      {open && <Logo3D zoom framing={1.15} className="logo3d-large" />}
      <p className="logo3d-note">{t("logo3d_note")}</p>
    </dialog>
  );
}
