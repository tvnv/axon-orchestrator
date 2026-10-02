# axon-orchestrator

## [Axon]

| Champ | Valeur |
|---|---|
| **Verdict** | `AXON_STABILIZER_SMOKE=PASS` |
| **Date** | 2026-10-02T20:58:29Z |
| **Session** | `session_01NF5rnvC1qLFxVHs62JzVor` |
| **Issue** | echoline-sovereign#445 |
| **WAVE batch** | `batch-b08e6b64656e47c3850064b7e8cf7684` |
| **WAVE commit** | `4bb01387` on `tvnv/echoline-sovereign:dev` |
| **Branche** | `dev` (promotion vers `main` reste HITL) |

### Chaîne d'observation validée

```
Axon C (candidate) → GET /stabilizer/runs → Axon Stabilizer → PostgreSQL
  → wave_state  src=axon_c  watch=watch-smoke-445-echoline-dev  reachable=true
  → run_status  src=axon_s  reachable=true
```

### Modifications déployées

- **axon-execution-mcp** (PR #497 · branche `ccr-f658c91b-tfyfr9`): Nouveau endpoint `GET /stabilizer/runs` avec `AXON_STABILIZER_READ_TOKEN` dédié — indépendant de `AXON_EXECUTION_EVENTS_TOKEN`, openclaw non impacté.
- **axon-stabilizer** (PR #38 · branche `ccr-f658c91b-tfyfr9`): Fix `axon_status_path` → `/stabilizer/runs?run_id={run_id}`, synchronisation tokens Axon C / Axon S.