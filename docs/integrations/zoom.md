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

## Per-session participant authentication (KAN-276)
- Authorized session teachers and administrators can select open access (no Zoom account required), authenticated Zoom account access, or institutional access restricted to approved domains where supported by the Zoom account and authentication profile.
- Persist the selection per session and apply it when creating or updating the meeting. Display the access requirement before joining. Never silently downgrade to open access on provider rejection; surface unsupported settings and preserve the last confirmed configuration.
- Open Zoom access does not bypass EduGest authorization or permit attendance attribution to unverified identities. This setting is independent of server-to-server OAuth.
- Test all modes, updates, unsupported profiles, provider errors and cross-session authorization. Default mode requires PO confirmation.

Jira: https://anasfady87-1789923749606.atlassian.net/browse/KAN-276
