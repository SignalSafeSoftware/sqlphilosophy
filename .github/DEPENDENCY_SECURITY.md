# Dependency security

Maintainer: SignalSafeSoftware repository owners. Review this baseline monthly and
when workflows, package managers, default branches or publishing methods change.

## Protection baseline

- Dependabot alerts, dependency graph and automatic security updates are enabled.
- `.github/dependabot.yml` schedules version updates for the repository's owned
  manifests and workflows. Keep documented compatibility ignores; a major upgrade
  requires its normal coordinated migration.
- Every pull request runs `Dependency review`: GitHub dependency review (new high/critical vulnerabilities in runtime, development and unknown scopes).
- The default branch (`main`) uses the `Dependency protection`
  repository ruleset: pull requests, resolved conversations and required checks;
  deletion and force pushes are blocked. No routine bypass is configured.
- Independent review is required where the project's contribution instructions
  require it. The ruleset does not require an unavailable second maintainer's
  approval in this single-maintainer organization.

## Required check contexts

- `Checks (Python 3.12)`
- `Checks (Python 3.13)`
- `Dependency review`
- `Smoke package`
- `Tests (Python 3.12)`
- `Tests (Python 3.13)`

These names match GitHub Actions check contexts. After a workflow/job rename,
update the ruleset in repository Settings → Rules before relying on the new name.
Keep required workflows eligible for every pull request to the protected branch;
workflow-level path filters can otherwise leave required checks pending forever.

## Handling dependency updates

Inspect the release notes and dependency diff. Merge only after the required and
applicable checks pass. Major versions, peer/runtime changes and documented
compatibility exceptions require review and relevant integration verification;
no blanket Dependabot auto-merge is configured. Vulnerability alerts can exist
before a patch is available; enabling protection does not resolve that backlog.
Do not dismiss an alert merely to obtain a passing check.
