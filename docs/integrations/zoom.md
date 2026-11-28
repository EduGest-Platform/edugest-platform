# Zoom integration — draft design

Status: partial backend implementation, disabled by default. Target: staging first, synthetic data only.

## Scope
- Create and link Zoom meetings to existing academic sessions and cohorts; expose join links in the calendar only to authorized users.
- Use server-to-server OAuth for an institution-owned Zoom account, subject to PO confirmation of account ownership and scopes. Keep credentials server-side; never commit secrets or expose host start URLs to learners.
- Synchronize attendance from participant reports after meetings. Match only verified enrollment identities; ambiguous or unmatched participants require manual review. Preserve manual attendance and audit changes; deduplicate by meeting occurrence and participant identity.
- Validate webhook signatures and timestamp freshness, reject replay, and process events idempotently. Use bounded retries and reconciliation; never infer attendance from an unverified display name.

## Implemented and pending work

The attendance screen can create and look up a meeting for an academic session when provisioning is enabled. The server persists a provisioning intent before contacting Zoom and requires a verified provider meeting to reconcile an uncertain result. OAuth, meeting persistence, authentication modes, webhook signature verification helpers and internal notes review are implemented. The automated tests use a mocked provider.

Calendar join links, incoming webhook processing, attendance reconciliation, and validation with the institution's provider account are pending. Both Zoom settings remain disabled by default. Institutional activation and real data processing require a separate decision.

## Recovery when a meeting cannot be found

An authorised staff administrator records the operation reference, academic session, configured host and expected start time, then asks the institutional Zoom account administrator to check the host's meetings and account records. If they find a candidate meeting, enter its provider ID in EduGest. EduGest verifies its operation reference, host and schedule before linking it.

If the provider lookup fails or cannot verify a candidate, keep the existing provisioning intent and escalate with the operation reference. An empty listing or an unavailable account is inconclusive. EduGest keeps creation blocked and allows another status check or a verified reconciliation. Support should use the institution's existing approved contingency to run the session if needed. Releasing a blocked intent for a new provider call requires an auditable workflow and authoritative provider evidence that the original operation did not create a meeting. That workflow is pending.

## Per-session participant authentication (KAN-276)
- Authorized session teachers and administrators can select open access (no Zoom account required), authenticated Zoom account access, or institutional access restricted to approved domains where supported by the Zoom account and authentication profile.
- Persist the selection per session and apply it when creating or updating the meeting. Display the access requirement before joining. Never silently downgrade to open access on provider rejection; surface unsupported settings and preserve the last confirmed configuration.
- Open Zoom access does not bypass EduGest authorization or permit attendance attribution to unverified identities. This setting is independent of server-to-server OAuth.
- Test all modes, updates, unsupported profiles, provider errors and cross-session authorization. Default mode requires PO confirmation.

Jira: https://anasfady87-1789923749606.atlassian.net/browse/KAN-276

## Local configuration

Both GISTAR_ZOOM_ENABLED and GISTAR_ZOOM_PROVISIONING_ENABLED default to false. Supply GISTAR_ZOOM_ACCOUNT_ID, GISTAR_ZOOM_CLIENT_ID, GISTAR_ZOOM_CLIENT_SECRET and GISTAR_ZOOM_WEBHOOK_SECRET through the Compose environment (untracked .env or exported variables). Provisioning requires GISTAR_ZOOM_HOST_ID; institutional authentication requires GISTAR_ZOOM_INSTITUTIONAL_PROFILE_ID. Leave optional variables unset rather than empty. Never commit credentials or enable provisioning before institutional approval.
