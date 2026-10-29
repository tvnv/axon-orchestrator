# Axon CLI autonomy contract — DEV/candidate

Applies to GPT→Axon development and stabilization missions. Use canonical execution, validation and stabilizer Skills when available; otherwise follow this contract directly.

## Preauthorized actions (0-HITL)
- Run required shell, Python, PowerShell, SQL and test scripts in the authorized DEV workspace; install scoped dependencies.
- Use git and gh CLI to create branches, commits, pushes, PRs, update issues, and merge reviewed/tested changes **into dev**. Resolve conflicts and verify resulting SHA. Respect branch protections.
- Use Railway and Vercel CLI to inspect logs/configuration, build, deploy, redeploy, smoke-test, restart and roll back **DEV/candidate only**.
- Use Infisical CLI to inspect metadata, create/update/synchronize **DEV secrets only**; never print secret values in logs, comments or RESULT. Preserve consumers and verify authenticated functionality.
- Diagnose observed failures, make minimal corrections, run regression and functional tests, and resume the original mission without seeking another approval for these preauthorized operations.

## Boundaries requiring HITL
- Any merge to main/production branches, PROD deployment or PROD configuration/secrets change.
- Unapproved paid API usage, spending or infrastructure provisioning with additional charges.
- Irreversible destructive changes to persistent data, changes outside mission scope, or unresolved business ambiguity.
- Never bypass technical protections, authorization boundaries, security checks or effective CLI permissions.

## Execution rules
- Skills First; validation by real usage; avoid speculative preflight gates.
- Preserve idempotency, avoid duplicate launches and PRs; use existing work/results.
- On a real failure: diagnose → minimal fix → NR tests → functional smoke → merge dev/deploy candidate if necessary → reconcile SHAs.
- NEEDS_HITL only when a boundary above is actually reached, with evidence and the minimal decision required.
- Publish GREEN/AMBER/RED RESULT with SHA, tests, actions, remaining blockers to tvnv/axon-orchestrator#12.
- Completion requires observable functional acceptance, not just a successful command exit.
