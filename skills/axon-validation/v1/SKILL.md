---
skill_id: axon-validation
version: 1.0.0
purpose: Independently validate Axon delivery from durable evidence.
---
# axon-validation
Read-only verification skill. Related #35, #7, #10, #15.
## Preconditions
A WAVE/batch or mission identifier exists; access to evidence sources is available.
## Inputs
mission_id, owner_circuit, wave_id/batch_id, expected_AC, repository, target_branch.
## Procedure
1. Resolve owner-circuit channel (#15), inspect latest relevant terminal RESULT and request identity.
2. Read Axon WAVE/batch state and issue outcomes. Check N=1 sequencing or parallelism as requested.
3. Reconcile exact remote Git SHA, PR and actual deployed SHA only when deployment is in scope.
4. Verify test results and functional AC, not merely agent claims.
5. Check R0 once after batch terminality and bounded C1/R1 then C2/R2 if applicable.
6. Return GREEN only when all required evidence is confirmed; AMBER for gaps; RED for contradicted AC or proven failures.
## Allowed actions
Read GitHub, Axon, runtime, RESULT and test evidence; report verdict.
## Forbidden actions
Any mutation, launching work, merge, deployment, paid API call, inferring GREEN from prose.
## Evidence required
Source references and timestamps for each checked AC, SHA, tests, review and channel RESULT.
## Success criteria
Reproducible verdict and minimal next action.
## Failure modes
AMBER for inaccessible/incomplete evidence; RED for failed criteria.
## Output contract
skill_id@version, identifiers, evidence matrix, GREEN/AMBER/RED, unresolved gaps, next action.
