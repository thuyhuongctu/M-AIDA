# Data safety and privacy inventory — draft

This is a review worksheet, not the final Apple privacy declaration or Google Play Data safety form.

| Data / operation | Current mobile behavior | Release decision required |
|---|---|---|
| User-selected PDF | Sent to the configured API for extraction | Confirm processing provider, retention, encryption, and deletion |
| Bibliographic metadata | Sent with extraction request | Confirm whether any field can contain personal data |
| Extracted study records | Stored by the configured backend | Confirm operator, region, retention, access controls, and export/deletion process |
| Verification decisions | Stored by backend | Confirm audit/logging policy |
| CSV export | User-initiated local download | Verify device/share behavior on iOS and Android |
| Notion sync | User-initiated, deployment-configured | Name Notion in disclosure if enabled in production |
| Diagnostics | No analytics/crash SDK is currently bundled | Re-review if an SDK is added |
| Advertising/tracking | None | Keep tracking disabled unless separately approved and disclosed |
| Accounts | None in current frontend; current backend is not a public multi-user service | Approve a safe production access/tenant model; if accounts are added, implement in-app deletion and a public web deletion path |

The production disclosure must match the deployed backend, every third-party SDK, and actual retention behavior. Re-run this inventory after any dependency or infrastructure change.
