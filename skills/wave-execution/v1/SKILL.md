---
skill_id: wave-execution
version: 1.0.0
purpose: Execute an Axon WAVE with stable functional evidence.
---
# wave-execution
Canonical implementation contract for #7; registry #10.
## Preconditions
A real issue/WAVE, target repository and authorized DEV scope are identified.
## Inputs
issue_ids, wave_id or request_id, execution_mode (PARALLEL or SEQUENTIAL_N1), owner_circuit, authorized_scope.
## Procedure
1. Resolve existing WAVE/batch by identity before admission; never duplicate a root batch.
2. Read only minimal Axon/Git state needed to act; parallel-first for independent WAVE, sequential N=1 when required.
3. Admit/launch using the existing Axon MCP route; do not invent a second scheduler or provider router.
4. Observe durable WAVE state, issues, remote SHA and tests. At batch terminality, run R0 once and bounded C1/R1, C2/R2 only if necessary.
5. Hand evidence to axon-validation; publish terminal RESULT in owner-circuit channel per #15.
## Allowed actions
DEV-scoped WAVE admission, execution, tests and evidence publication.
## Forbidden actions
main/PROD without HITL; unauthorized paid API; duplicate batch; destructive replay; unbounded retries; GREEN from agent prose.
## Evidence required
batch/wave IDs, issue states, remote SHA, tests, reviewer IDs and final channel RESULT.
## Success criteria
Functional work delivered, WAVE stable, evidence independently verifiable.
## Failure modes
BLOCKED for unavailable prerequisite; FAILED for actual execution failure; ESCALATED when HITL needed.
## Output contract
skill_id@version, owner_circuit, wave/batch IDs, remote SHA, tests, reviewer result, blockers, terminal status.
