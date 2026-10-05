/**
 * TeamPanel - the "Team" tab (8.0, backend/team.py).
 *
 * Two parts:
 *   - your team: the people you invited into your workspace. They upload PDFs
 *     (your credits pay) and verify records; only you lock, delete, export and
 *     edit the PRISMA counts. Invitations are limited to the closed-beta list.
 *   - workspaces you were invited into: open one to work there, or leave it.
 *
 * Which workspace is open is App's state (the X-MAIDA-Workspace header, see
 * api.ts:setWorkspace); this panel only asks App to switch.
 */

import React, { useCallback, useEffect, useState } from "react";
import { fetchTeam, inviteMember, leaveTeam, removeMember } from "../api";
import { useI18n } from "../i18n";
import type { MeResponse, TeamPayload } from "../types";
import { fmtWhen } from "./BillingPanel";

interface TeamPanelProps {
  refreshKey: number;
  me: MeResponse | null;
  /** Owner id of the open workspace, or null for the caller's own. */
  workspace: string | null;
  onOpenWorkspace: (ownerId: string | null) => void;
}

export default function TeamPanel({ refreshKey, me, workspace, onOpenWorkspace }: TeamPanelProps) {
  const { t } = useI18n();
  const [team, setTeam] = useState<TeamPayload | null>(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const errorText = useCallback(
    (err: unknown) => (err instanceof Error ? err.message.replace(/^\d{3}: /, "") : t("error_generic")),
    [t]
  );

  const load = useCallback(async () => {
    try {
      setTeam(await fetchTeam());
      setError(null);
    } catch (err: unknown) {
      setError(errorText(err));
    }
  }, [errorText]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const invite = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = email.trim();
    if (!value) return;
    setBusy("invite");
    setError(null);
    setNotice(null);
    try {
      setTeam(await inviteMember(value));
      setEmail("");
      setNotice(t("team_invited").replace("{email}", value.toLowerCase()));
    } catch (err: unknown) {
      const text = errorText(err);
      setError(text.startsWith("not_invited") ? t("team_not_on_list") : text);
    } finally {
      setBusy(null);
    }
  };

  const remove = async (address: string) => {
    setBusy(address);
    setError(null);
    setNotice(null);
    try {
      setTeam(await removeMember(address));
    } catch (err: unknown) {
      setError(errorText(err));
    } finally {
      setBusy(null);
    }
  };

  const leave = async (ownerId: string) => {
    setBusy(ownerId);
    setError(null);
    setNotice(null);
    try {
      setTeam(await leaveTeam(ownerId));
      if (workspace === ownerId) onOpenWorkspace(null);
    } catch (err: unknown) {
      setError(errorText(err));
    } finally {
      setBusy(null);
    }
  };

  const inOther = workspace !== null && me?.workspace?.role === "member";
  const members = team?.members ?? [];
  const memberships = team?.memberships ?? [];
  const full = team ? members.length >= team.max_members : false;

  return (
    <div className="panel account-panel team-panel" data-testid="team-panel">
      <div className="panel-header">
        <h2 className="panel-title">{t("team_title")}</h2>
      </div>
      {error && <p className="error-message" data-testid="team-error">{error}</p>}
      {notice && <p className="success-message" data-testid="team-notice">{notice}</p>}

      {inOther && me?.workspace && (
        <div className="team-here" data-testid="team-here">
          <span>
            {t("team_here")} <strong>{me.workspace.owner_email}</strong>
          </span>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => onOpenWorkspace(null)} data-testid="team-back">
            {t("team_back")}
          </button>
        </div>
      )}

      <section className="team-section">
        <h3 className="panel-subtitle">{t("team_yours")}</h3>
        <ul className="team-rules">
          <li>{t("team_rule_upload")}</li>
          <li>{t("team_rule_verify")}</li>
          <li>{t("team_rule_owner")}</li>
        </ul>
        <form className="team-invite" onSubmit={invite}>
          <label className="form-label" htmlFor="team-email">{t("team_invite_label")}</label>
          <div className="team-invite-row">
            <input
              id="team-email"
              className="form-input"
              type="email"
              required
              placeholder="name@university.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={full}
            />
            <button className="btn btn-primary btn-sm" type="submit" disabled={busy !== null || full} data-testid="team-invite">
              {t("team_invite")}
            </button>
          </div>
          <p className="hint-text">
            {t("team_invite_hint")}
            {team ? ` ${members.length}/${team.max_members}.` : ""}
          </p>
        </form>

        {members.length === 0 ? (
          <p className="empty-text">{t("team_none")}</p>
        ) : (
          <div className="table-container">
            <table className="studies-table team-table" data-testid="team-members">
              <thead>
                <tr>
                  <th>{t("acc_email")}</th>
                  <th>{t("job_status")}</th>
                  <th>{t("team_since")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.email} data-testid="team-member-row">
                    <td>
                      {m.email}
                      {m.name ? <span className="hint-inline"> · {m.name}</span> : null}
                    </td>
                    <td>
                      <span className={`badge ${m.status === "active" ? "badge-success" : "badge-plain"}`}>
                        {m.status === "active" ? t("team_active") : t("team_pending")}
                      </span>
                    </td>
                    <td className="mono small">{fmtWhen(m.joined_at ?? m.invited_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-link btn-danger-text"
                        disabled={busy !== null}
                        onClick={() => void remove(m.email)}
                        data-testid={`team-remove-${m.email}`}
                      >
                        {m.status === "active" ? t("team_remove") : t("team_withdraw")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="team-section">
        <h3 className="panel-subtitle">{t("team_others")}</h3>
        {memberships.length === 0 ? (
          <p className="empty-text">{t("team_others_none")}</p>
        ) : (
          <ul className="team-spaces" data-testid="team-memberships">
            {memberships.map((m) => {
              const open = workspace === m.owner_id;
              return (
                <li key={m.owner_id} className={`team-space ${open ? "team-space-open" : ""}`}>
                  <span className="team-space-who">
                    <strong>{m.owner_name || m.owner_email}</strong>
                    {m.owner_name ? <span className="hint-inline"> · {m.owner_email}</span> : null}
                    <span className="hint-inline"> · {m.status === "active" ? t("team_active") : t("team_invited_you")}</span>
                  </span>
                  <span className="team-space-actions">
                    {open ? (
                      <span className="badge badge-success">{t("team_open_now")}</span>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={busy !== null}
                        onClick={() => onOpenWorkspace(m.owner_id)}
                        data-testid={`team-open-${m.owner_email}`}
                      >
                        {t("team_open")}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-link btn-danger-text"
                      disabled={busy !== null}
                      onClick={() => void leave(m.owner_id)}
                      data-testid={`team-leave-${m.owner_email}`}
                    >
                      {m.status === "active" ? t("team_leave") : t("team_decline")}
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
