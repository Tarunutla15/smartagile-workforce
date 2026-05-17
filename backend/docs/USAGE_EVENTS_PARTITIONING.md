# `UsageEvent` table — indexes and PostgreSQL partitioning

## Current Django model

Rows live in `smartagile_usageevent` with B-tree indexes:

- `(user_id, occurred_at DESC)` — dashboard “recent activity” style queries
- `(user_id, occurred_at ASC)` — range scans and aggregations aligned with ascending time

## When to partition

At very large row counts (tens or hundreds of millions), consider **range partitioning** on `occurred_at` (e.g. monthly partitions). PostgreSQL requires the **partition key to be part of the primary key**, which does not match Django’s default single-column `id` PK.

Practical options:

1. **TimescaleDB** hypertable on `occurred_at` (keeps a familiar PK; compression and retention policies help scale).
2. **Manual monthly partitions** with a composite PK `(id, occurred_at)` — requires `managed = False` or custom migrations and careful insert routing.
3. **Archive job** — move rows older than N months to a cold table or object storage and keep the hot table small.

## Example: monthly range partitions (advanced)

Run during a maintenance window after reviewing [PostgreSQL partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html). This is **not** applied automatically by migrations; treat as DBA-run DDL once you outgrow a single table.

```sql
-- Illustrative only — do not run blindly on production.
CREATE TABLE smartagile_usageevent_y2026m04 PARTITION OF smartagile_usageevent
  FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

Prefer Timescale or Citus if you need managed partitioning without fighting the ORM.
