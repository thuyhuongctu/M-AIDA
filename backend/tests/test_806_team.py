"""8.0: Team - a shared workspace that belongs to one owner (team.py).

The owner invites by e-mail (closed-beta list only). A member works in the
owner's workspace through the X-MAIDA-Workspace header: uploads are charged to
the owner, members may verify, only the owner locks, deletes, exports and
edits the PRISMA counts. Removing a member closes the workspace to them at
once; their work stays with the owner.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from conftest import make_minimal_pdf
from test_800_cloud_multiuser import GOOD, FakeEngine, cloud  # noqa: F401  (cloud is a fixture)

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _upload(client, headers, inject):
    inject(FakeEngine(GOOD))
    pdf = make_minimal_pdf("Paper. r = 0.30 (n = 200).")
    return client.post("/api/jobs", headers=headers, files={"file": ("paper.pdf", pdf, "application/pdf")},
                       data={"title": "Team paper", "year": "2021"})


def _team(cloud_fixture):
    main, client, inject, login = cloud_fixture
    owner, member = login("owner@example.org", "Owner"), login("member@example.org", "Member")
    owner_id = client.get("/api/me", headers=owner).json()["id"]
    r = client.post("/api/team/members", headers=owner, json={"email": "Member@Example.org"})
    assert r.status_code == 201, r.text
    in_team = {**member, "X-MAIDA-Workspace": owner_id}
    return main, client, inject, login, owner, member, owner_id, in_team


def test_new_tables_are_closed_to_the_data_api():
    """Every table is listed by a lock-down migration (0002 or 0005)."""
    from db import Base

    tables: set[str] = set()
    for name in ("0002_lock_down_data_api.py", "0005_team.py"):
        spec = importlib.util.spec_from_file_location(name[:-3], VERSIONS / name)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        tables |= set(mod.TABLES)
    assert set(Base.metadata.tables) | {"alembic_version"} == tables


def test_invite_is_limited_to_the_beta_list_and_unique(cloud):  # noqa: F811  (cloud: fixture imported from test_800)
    main, client, inject, login = cloud
    owner = login("owner@example.org")
    bad = client.post("/api/team/members", headers=owner, json={"email": "someone@gmail.com"})
    assert bad.status_code == 422 and "not_invited" in bad.json()["detail"]
    assert client.post("/api/team/members", headers=owner, json={"email": "not an email"}).status_code == 422
    assert client.post("/api/team/members", headers=owner, json={"email": "owner@example.org"}).status_code == 422
    ok = client.post("/api/team/members", headers=owner, json={"email": "Ana@Example.org"})
    assert ok.status_code == 201
    assert [(m["email"], m["status"]) for m in ok.json()["members"]] == [("ana@example.org", "invited")]
    assert client.post("/api/team/members", headers=owner, json={"email": "ana@example.org"}).status_code == 409


def test_member_works_in_the_owners_workspace_and_the_owner_pays(cloud):  # noqa: F811
    main, client, inject, login, owner, member, owner_id, in_team = _team(cloud)

    # Before opening it, the member sees the invitation.
    seen = client.get("/api/team", headers=member).json()["memberships"]
    assert [(m["owner_email"], m["status"]) for m in seen] == [("owner@example.org", "invited")]

    me = client.get("/api/me", headers=in_team).json()
    assert me["workspace"] == {"owner_id": owner_id, "owner_email": "owner@example.org", "role": "member"}
    assert me["credits"] == 3 and me["own_credits"] == 3
    assert client.get("/api/team", headers=member).json()["memberships"][0]["status"] == "active"

    r = _upload(client, in_team, inject)
    assert r.status_code == 202, r.text
    job = client.get(f"/api/jobs/{r.json()['id']}", headers=in_team).json()
    assert job["status"] == "succeeded" and job["submitted_by"] != owner_id
    sid = job["study_id"]

    # The owner's credit paid; the member's own balance is untouched.
    assert client.get("/api/me", headers=owner).json()["credits"] == 2
    assert client.get("/api/me", headers=member).json()["credits"] == 3
    # The record is the owner's: visible in the owner's workspace, not in the member's own.
    assert [s["study_id"] for s in client.get("/api/studies", headers=owner).json()] == [sid]
    assert client.get("/api/studies", headers=member).json() == []
    assert client.get("/api/jobs", headers=owner).json()[0]["id"] == job["id"]

    # Members verify ...
    patch = {"study_id": sid, "pi_approved": True, "pi_notes": "checked by member", "field_overrides": {"icrv_regime": "III"}}
    v = client.patch(f"/api/studies/{sid}/verify", headers=in_team, json=patch)
    assert v.status_code == 200 and v.json()["pi_approved_at"]
    # ... but only the owner locks, deletes, exports and edits PRISMA.
    for res in (
        client.post(f"/api/studies/{sid}/lock", headers=in_team),
        client.delete(f"/api/studies/{sid}", headers=in_team),
        client.get("/api/studies/export/csv", headers=in_team),
        client.get("/api/studies/export/metafor.csv", headers=in_team),
        client.post("/api/notion/sync", headers=in_team),
        client.put("/api/me/report/prisma", headers=in_team, json={"identified": 10}),
    ):
        assert res.status_code == 403 and res.json()["detail"].startswith("owner_only"), res.text
    assert client.get("/api/me/report", headers=in_team).json()["counts"]["approved"] == 1
    assert client.post(f"/api/studies/{sid}/lock", headers=owner).status_code == 200
    assert client.get("/api/studies/export/csv", headers=owner).status_code == 200

    # The owner's audit log names the member.
    from sqlalchemy import select

    from db import AuditLog

    with main._sessions() as s:
        verify = s.scalars(select(AuditLog).where(AuditLog.owner_id == owner_id, AuditLog.action == "verify")).one()
    assert verify.detail["by_email"] == "member@example.org"


def test_strangers_and_removed_members_are_refused(cloud):  # noqa: F811
    main, client, inject, login, owner, member, owner_id, in_team = _team(cloud)
    stranger = {**login("stranger@example.org"), "X-MAIDA-Workspace": owner_id}
    r = client.get("/api/studies", headers=stranger)
    assert r.status_code == 403 and r.json()["detail"].startswith("not_member")

    assert client.get("/api/studies", headers=in_team).status_code == 200
    after = client.delete("/api/team/members/member@example.org", headers=owner)
    assert after.status_code == 200 and after.json()["members"] == []
    assert client.get("/api/studies", headers=in_team).status_code == 403
    assert client.get("/api/me", headers=member).json()["workspace"]["role"] == "owner"


def test_member_can_leave(cloud):  # noqa: F811
    main, client, inject, login, owner, member, owner_id, in_team = _team(cloud)
    assert client.get("/api/me", headers=in_team).status_code == 200
    left = client.delete(f"/api/team/memberships/{owner_id}", headers=member)
    assert left.status_code == 200 and left.json()["memberships"] == []
    assert client.get("/api/team", headers=owner).json()["members"] == []
    assert client.get("/api/me", headers=in_team).status_code == 403


def test_rate_limits_are_per_person_inside_a_team(cloud):  # noqa: F811
    main, client, inject, login, owner, member, owner_id, in_team = _team(cloud)
    admin = login("operator@example.org")
    client.post("/api/admin/credits", headers=admin, json={"email": "owner@example.org", "credits": 20})
    for _ in range(4):  # MAIDA_JOBS_PER_HOUR=4 in the fixture
        assert _upload(client, owner, inject).status_code == 202
    assert _upload(client, owner, inject).status_code == 429
    # The owner's hourly limit does not block the member, who still spends the owner's credits.
    before = client.get("/api/me", headers=owner).json()["credits"]
    assert _upload(client, in_team, inject).status_code == 202
    assert client.get("/api/me", headers=owner).json()["credits"] == before - 1
