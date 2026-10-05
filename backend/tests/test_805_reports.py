"""8.0: Reports tab - hand-entered PRISMA 2020 counts and the metafor export."""

from __future__ import annotations

import csv
import io
import math

from test_800_cloud_multiuser import GOOD, FakeEngine, cloud, extract  # noqa: F401  (cloud is a fixture)


def _locked_study(client, headers, inject):
    created = extract(client, headers, inject, FakeEngine(GOOD))
    assert created.status_code == 200, created.text
    sid = created.json()["study_id"]
    patch = {"study_id": sid, "pi_approved": True, "pi_notes": "", "field_overrides": {}}
    assert client.patch(f"/api/studies/{sid}/verify", headers=headers, json=patch).status_code == 200
    assert client.post(f"/api/studies/{sid}/lock", headers=headers).status_code == 200
    return sid


def test_prisma_counts_are_saved_per_account_and_checked(cloud):  # noqa: F811  (cloud: fixture imported from test_800)
    main, client, inject, login = cloud
    alice, bob = login("alice@example.org"), login("bob@example.org")

    empty = client.get("/api/me/report", headers=alice).json()
    assert empty["prisma"] == {} and empty["counts"] == {"records": 0, "pending": 0, "approved": 0, "locked": 0}

    counts = {"identified": 412, "duplicates_removed": 40, "screened": 372, "assessed": 238}
    saved = client.put("/api/me/report/prisma", headers=alice, json=counts)
    assert saved.status_code == 200, saved.text
    assert saved.json()["prisma"] == counts and saved.json()["prisma_updated_at"]
    assert client.get("/api/me/report", headers=alice).json()["prisma"] == counts
    assert client.get("/api/me/report", headers=bob).json()["prisma"] == {}  # per account

    bad = client.put("/api/me/report/prisma", headers=alice,
                     json={"identified": 100, "duplicates_removed": 10, "screened": 95, "assessed": 96})
    assert bad.status_code == 422
    assert "screened exceed" in bad.json()["detail"] and "assessed exceed" in bad.json()["detail"]
    assert client.put("/api/me/report/prisma", headers=alice, json={"identified": -1}).status_code == 422
    # Partial entries are allowed (a search still running).
    assert client.put("/api/me/report/prisma", headers=alice, json={"identified": 50}).status_code == 200


def test_report_counts_follow_the_records(cloud):  # noqa: F811  (cloud: fixture imported from test_800)
    main, client, inject, login = cloud
    alice = login("alice@example.org")
    _locked_study(client, alice, inject)
    extract(client, alice, inject, FakeEngine(GOOD))  # left pending
    counts = client.get("/api/me/report", headers=alice).json()["counts"]
    assert counts == {"records": 2, "pending": 1, "approved": 0, "locked": 1}


def test_metafor_export_has_fisher_z_and_variance(cloud):  # noqa: F811  (cloud: fixture imported from test_800)
    main, client, inject, login = cloud
    alice, bob = login("alice@example.org"), login("bob@example.org")
    assert client.get("/api/studies/export/metafor.csv", headers=alice).status_code == 404
    sid = _locked_study(client, alice, inject)
    extract(client, alice, inject, FakeEngine(GOOD))  # pending: not exported

    res = client.get("/api/studies/export/metafor.csv", headers=alice)
    assert res.status_code == 200 and res.headers["x-maida-skipped"] == "0"
    rows = list(csv.DictReader(io.StringIO(res.text)))
    assert [r["study_id"] for r in rows] == [sid]
    row = rows[0]
    assert float(row["ri"]) == 0.3 and int(row["ni"]) == 200
    assert math.isclose(float(row["yi"]), math.atanh(0.3), abs_tol=1e-6)
    expected_vi = 1 / (200 - 3) if row["vi_source"] == "1/(n-3)" else None
    assert row["vi_source"] in ("variance_z", "1/(n-3)") and float(row["vi"]) > 0
    if expected_vi is not None:
        assert math.isclose(float(row["vi"]), expected_vi, rel_tol=1e-6)
    assert client.get("/api/studies/export/metafor.csv", headers=bob).status_code == 404
