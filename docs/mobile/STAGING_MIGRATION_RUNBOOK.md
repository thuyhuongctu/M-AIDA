# Protected staging migration and smoke test

This runbook applies only to the controlled M-AIDA staging deployment. It does
not authorize production migration, App Store submission, Google Play
submission, or commercialization.

## Protection model

The workflow `.github/workflows/staging-migration.yml` is manual and references
the GitHub Environment named `staging`. Configure that Environment with required
reviewers before adding secrets. The workflow then requires:

1. an exact 40-character deployed commit SHA;
2. the exact confirmation phrase `MIGRATE-STAGING`;
3. a clean remote checkout at that exact SHA;
4. an existing SQLite database file;
5. SQLite `quick_check` and `foreign_key_check` success;
6. a timestamped online backup before any write;
7. an exclusive transaction with rollback on failure;
8. a read-only smoke test after migration.

## Required staging Environment configuration

Variables:

- `STAGING_APP_DIR`: absolute path of the deployed repository checkout;
- `STAGING_DB_PATH`: absolute path of the mounted staging SQLite file;
- `STAGING_BASE_URL`: HTTPS origin of the staging backend, without a trailing slash.

Secrets:

- `STAGING_SSH_HOST`;
- `STAGING_SSH_USER`;
- `STAGING_SSH_PRIVATE_KEY`;
- `STAGING_SSH_KNOWN_HOSTS`: pinned known-hosts entry, not an `ssh-keyscan`
  result generated during the workflow;
- `STAGING_SMOKE_TOKEN`: optional bearer token when the staging gateway requires one.

The SSH principal should have the minimum permissions needed to read the deploy
checkout and update only the staging SQLite file and its backup directory.

## Before running

- Put the staging service in maintenance mode or otherwise stop write traffic.
- Confirm `MAIDA_DEMO_MODE=false` for any staging instance containing real
  research data.
- Confirm the deployed checkout is clean and its SHA is the exact candidate to
  test.
- Confirm there is enough disk space for one full database backup.

## Run sequence

1. Open **Actions → Protected staging migration → Run workflow**.
2. Enter the exact deployed SHA.
3. Enter `MIGRATE-STAGING`.
4. First run with **Apply migration = false**. This performs all preflight checks.
5. Review the preflight output and obtain the required Environment approval.
6. Run again with **Apply migration = true**.
7. Download the `staging-migration-smoke-<sha>` evidence artifact.

## Smoke assertions

The smoke command is read-only. It verifies:

- SQLite integrity and schema version;
- the `studies` table and migration index;
- `/api/health` returns `status=ok` and `storage=sqlite`;
- demo mode is off;
- `/api/studies` returns a list;
- study counts agree across the database, health response, and API listing.

## Rollback

The migration itself is transactional. A failed migration rolls back before the
workflow exits. The timestamped backup is retained even after success. To roll
back a successful migration:

1. stop the staging service;
2. preserve the failed database for evidence;
3. restore the backup path recorded in `maida-staging-migration.json`;
4. restart staging;
5. rerun the read-only smoke test;
6. document the failure and do not promote the candidate SHA.
