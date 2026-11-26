# Zoom integration — draft design

Status: proposed, not implemented. Target: staging first, synthetic data only.

## Scope
- Create and link Zoom meetings to existing academic sessions and cohorts; expose join links in the calendar only to authorized users.
- Use server-to-server OAuth for an institution-owned Zoom account, subject to PO confirmation of account ownership and scopes. Keep credentials server-side; never commit secrets or expose host start URLs to learners.
- Synchronize attendance from participant reports after meetings. Match only verified enrollment identities; ambiguous or unmatched participants require manual review. Preserve manual attendance and audit changes; deduplicate by meeting occurrence and participant identity.
- Validate webhook signatures and timestamp freshness, reject replay, and process events idempotently. Use bounded retries and reconciliation; never infer attendance from an unverified display name.

## Implementation checklist
- [ ] Confirm Jira scope, existing session and attendance contracts, account ownership and privacy approval.
- [ ] Add disabled-by-default settings, OAuth client and mocked provider tests.
- [ ] Add meeting persistence, migration, scoped endpoints and audit events.
- [ ] Add calendar/session UI and permission checks.
- [ ] Add attendance reconciliation and signed webhook handling.
- [ ] Regenerate OpenAPI and client; test cross-cohort denial, retries, duplicates and manual overrides.
- [ ] Validate staging with synthetic participants and real provider sandbox/account; document rollback.

No runtime integration is enabled by this document. Do not merge as a completed feature until implementation and verification are complete.
