# Branch protection and PR enforcement

These settings live on **GitHub** (not in this repo). A maintainer with **Admin**
on `carreraGroup/cqf-bench` should apply them once CI is on `master`.

## While the repository is private

You can (and should) enable branch protection and CI **before** making the repo
public:

- **Pull requests** work among collaborators and teams with access to the private repo.
- **Fork-based contributions** from the public only work after the repository is
  **public** (and Actions must allow workflows from fork PRs — see below).
- **CODEOWNERS** ([@angelok1](https://github.com/angelok1)) auto-requests review on
  PRs once the file is on `master` and the user is a collaborator with write access.

When you open source: **Settings → General → Change visibility → Public**, then
confirm fork PR Actions settings in Option A step 2 below.

## Solo maintainer (only contributor)

If you are the only person on the repo, **do not** require approvals or Code Owner
review — you cannot approve your own PR.

Recommended rule set for `master`:

| Setting | Solo maintainer |
| --- | --- |
| Require a pull request before merging | **On** (optional but useful for CI on a branch) |
| Require approvals | **Off** (or count = 0) |
| Require review from Code Owners | **Off** |
| Require status checks (`python`, `docs`) | **On** |
| Do not allow bypassing | Your choice (see below) |

Then you: open PR → wait for green CI → **Merge** (no approval step).

**CODEOWNERS** ([@angelok1](https://github.com/angelok1)) only *requests* your review; it
does **not** block merge unless **Require review from Code Owners** is enabled.

### Alternative: merge without PRs

Turn off **Require a pull request before merging** and push directly to `master`.
CI still runs on push if the workflow is on `master`. You lose the “must pass CI
before merge” gate unless you keep PRs voluntary.

### Alternative: admin bypass

If you want approvals for *other* people later but need to merge your own work now:
enable **Allow specified actors to bypass pull request requirements** (or allow
administrators to bypass) for your account. Use sparingly.

## What you are enforcing (team / public OSS)

| Rule | Why |
| --- | --- |
| Changes via **pull request** only | No accidental direct pushes to `master` |
| **CI must pass** (`python`, `docs`) | Same checks as local CONTRIBUTING.md |
| Optional: **1 approval** | Review before merge (not for solo authors) |

Required check names match job `name:` values in [`.github/workflows/ci.yml`](workflows/ci.yml):

- `python`
- `docs`

After the first CI run on `master`, these names appear under branch protection
**Status checks that are required**.

## Option A — Classic branch protection (simplest)

1. Open **https://github.com/carreraGroup/cqf-bench/settings/branches**
2. **Add branch protection rule** (or edit existing rule for `master`).
3. Branch name pattern: `master`
4. Enable:
   - **Require a pull request before merging**
     - **Solo maintainer:** leave **Require approvals** unchecked
     - **Solo maintainer:** leave **Require review from Code Owners** unchecked
     - **Team:** enable approvals (1+) when others will review your PRs
   - **Require status checks to pass before merging**
     - Search and select: `python`, `docs`
     - Enable **Require branches to be up to date before merging** (recommended)
   - **Do not allow bypassing the above settings** (recommended for admins too)
5. Optional: **Restrict who can push to matching branches** — limit to maintainers
   if the org should not push directly even with rights.
6. Save.

## Option B — Repository rulesets (org preference)

Some organizations use **Rules → Rulesets** instead of classic rules:

1. **Repository → Settings → Rules → Rulesets → New ruleset**
2. Target: branch `master` (or default branch)
3. **Require pull request**, **Require status checks** → add `python` and `docs`
4. Apply to admins if you want no bypass.

## Allowing contributions (PR access)

For **open source** contributions from forks:

1. **Repository → Settings → General**
   - **Issues** and **Pull requests** enabled
2. **Repository → Settings → Actions → General**
   - **Fork pull request workflows**: **Run workflows from fork pull requests**
     (required so external PRs run CI)
3. Organization (if applicable): **carreraGroup → Settings → Member privileges**
   - Base permissions that allow members to open PRs on org repos, or use teams

For a **private** repo, add collaborators or team access under
**Settings → Collaborators and teams**.

## CODEOWNERS

[`.github/CODEOWNERS`](CODEOWNERS) assigns **@angelok1** as the default reviewer on
every PR. That is a reminder for you (or for others once the project grows). It
does **not** block merge unless you turn on **Require review from Code Owners**.

## Verify

1. Push this repo’s CI workflow to `master` and confirm both jobs pass.
2. Open a test PR that touches one file; confirm CI runs and merge is blocked
   until checks pass (and until approval, if enabled).
3. Confirm direct push to `master` is rejected (or only allowed for bypass roles
   you intentionally left enabled).

## CLI (optional)

If you use [GitHub CLI](https://cli.github.com/) with admin rights:

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  repos/carreraGroup/cqf-bench/branches/master/protection \
  -f required_status_checks='{"strict":true,"checks":[{"context":"python"},{"context":"docs"}]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1}' \
  -f restrictions=null
```

Adjust `required_approving_review_count` to `0` if you do not want mandatory review yet.
