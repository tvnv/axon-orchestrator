# Audit Fonctionnel Echoline — ECHO-DEMO-01 à 09

**Run ID :** PAA-DIAG-0fx5th  
**UTC :** 2026-10-23T06:48:17Z  
**Auditeur :** Claude (session `https://claude.ai/code/session_01N1o6pYfGSRFK3Zgxp9d44r`)  
**Type :** READ-ONLY — documentaire, code, issues, tests. Aucun appel fournisseur payant.

---

## 1. SHAs audités

| Dépôt | Branche | SHA HEAD |
|---|---|---|
| `tvnv/echoline-sovereign` | `dev` | `9d6ee9edae413a5dcae8896fc932f0699b20fd3a` |
| `tvnv/axon-functional-tests` | `main` | `a2ff76c7be3827b7b756892dff19f1f00681bb49` |

> ⚠️ **Alerte déploiement** : le dernier capsule observé sur `dev` (commit `b96e51c`) indique "DEV smoke BLOCKED (deployment at 56061cf, not fd53d4a)". Le déploiement Railway DEV ne reflète pas le HEAD de `dev`. L'écart est d'au minimum 10 commits significatifs avant le HEAD actuel. Aucun smoke runtime ne peut donc être considéré comme GREEN sur le déploiement actuel.

---

## 2. État du référentiel axon-functional-tests

Le dépôt `tvnv/axon-functional-tests` contient à ce SHA :
- `echoline/coverage.md` — matrice de couverture V0.1 (2026-10-22), statut **DRAFT documentaire**
- `README.md` — catalogue de scénarios de démonstration clients

**Il n'existe aucun script de test exécutable** (Playwright, pytest, bash) pour les scénarios ECHO-DEMO-01 à 09 dans ce dépôt. La matrice est purement déclarative. Toute couverture NR existante se trouve dans `tvnv/echoline-sovereign/backend/tests/` et `demo-client/`.

---

## 3. Matrice scénario → GAP → verdict

### ECHO-DEMO-01 — Planning et contexte

| Item | Valeur |
|---|---|
| **Comportement attendu** | Choisir une visite ; retrouver bénéficiaire et contexte MA contextualisé |
| **Services actifs** | `crm_planning_gateway.py`, `visit_context_service.py`, `gde_crm_planning_import.py`, `gde_crm_planning_read.py`, `planning_crm_service.py` |
| **Frontend** | `demo-client/app/planning/page.tsx`, `demo-client/app/ma/page.tsx` |
| **Tests deterministes** | `backend/tests/test_crm_planning_gateway.py`, `backend/tests/test_visit_context.py` (12 tests), `backend/tests/test_gde_crm_planning_import.py` (6 tests) |
| **Issues** | #402 CLOSED (Planning MA contextualisé), #399 CLOSED (contexte visite persistant), #411 CLOSED (CRM/Planning simulator E2E) |
| **GAP** | Aucune fixture de démonstration bout-en-bout dans axon-functional-tests ; pas de smoke runtime confirmé sur DEV (déploiement décalé) |
| **Priorité** | MEDIUM — code et tests unitaires GREEN attendus ; manque preuve runtime |
| **Couverture NR** | PARTIELLE — tests deterministes présents, pas de NR demo-level |
| **Verdict** | **AMBER** |

---

### ECHO-DEMO-02 — Compte rendu vocal

| Item | Valeur |
|---|---|
| **Comportement attendu** | Dicter en allemand → STT → propositions CRV / Facts |
| **Services actifs** | `voice_to_conversation_adapter.py`, `voice_to_summary_orchestrator.py`, `crv_propositions_service.py`, `stt_service.py`, `conversation_engine_service.py` |
| **Frontend** | `demo-client/components/VoiceInputButton.tsx`, `demo-client/components/VoiceToSummaryRunView.tsx` |
| **Tests deterministes** | `backend/tests/test_voice_conversation_service.py` (7 tests), `backend/tests/test_crv_propositions_service.py` (19 tests), `demo-client/components/VoiceInputButton.test.tsx` |
| **Issues** | #391 CLOSED (L8A Voice/STT), #392 CLOSED (L8B Voice/CE), #393 CLOSED (TTS), #394 OPEN (L8D smoke fonctionnel réel — pas encore exécuté) |
| **GAP** | #394 toujours ouvert : smoke fonctionnel Voice réel non réalisé. DEV BLOCKED. Entrée audio réelle non confirmée sur DEV. |
| **Priorité** | HIGH — pipeline code présent mais smoke réel manquant |
| **Couverture NR** | PARTIELLE — tests unitaires mocks, pas de NR audio réel |
| **Verdict** | **AMBER** |

---

### ECHO-DEMO-03 — Alertes santé

| Item | Valeur |
|---|---|
| **Comportement attendu** | Détecter jambes lourdes / instabilité sans inventer de diagnostic |
| **Services actifs** | `medical_ai_guardrail.py` (guardrails déterministes), `headsup_service.py`, `suspicion_engine.py` |
| **Tests deterministes** | `backend/tests/test_medical_ai_guardrail.py` |
| **Issues** | #445 CLOSED (extension détection symptômes et observations de santé), remarques PROD `2c65f8d8`, `fe28f88b` rattachées |
| **GAP** | Pas de script de démonstration bout-en-bout testant la non-inférence sur des cas spécifiques (jambes lourdes / instabilité). #445 fermé mais aucune preuve runtime sur DEV. |
| **Priorité** | MEDIUM |
| **Couverture NR** | PARTIELLE — guardrail deterministe, mais pas de campagne NR sur cas réels allemands |
| **Verdict** | **AMBER** |

---

### ECHO-DEMO-04 — Correction d'un Fact

| Item | Valeur |
|---|---|
| **Comportement attendu** | Correction enregistrée, conservée après acceptation, pas d'écrasement par ancienne valeur |
| **Services actifs** | `hitl_finalization_service.py`, `visit_memory_persistence.py` |
| **Issue** | **#453 OPEN P0** — "Correction de Fact perdue lors de l'acceptation" (2026-10-20) |
| **REX PROD** | remark-id `6ec157d2` — mode=voice, retour liste après correction affiche "accepter" en vert → clic restaure l'ancien texte |
| **GAP** | Défaut démontré en PROD. Root cause non encore corrigée. Aucun correctif sur `dev` identifié dans les commits récents. |
| **Priorité** | **CRITIQUE P0** |
| **Couverture NR** | ABSENTE — aucun test déterministe du cycle édition→sauvegarde→liste→acceptation dans `backend/tests/` |
| **Verdict** | **BLOCKED** |

---

### ECHO-DEMO-05 — Tagesjournal / CRV

| Item | Valeur |
|---|---|
| **Comportement attendu** | Heures, prestations, alertes santé, informations supplémentaires ; rubriques manquantes visibles |
| **Services actifs** | `crv_propositions_service.py`, `crv_validation_service.py`, `crv_persistence_service.py`, `crv_completeness_policy.py`, `headsup_service.py` |
| **Frontend** | `demo-client/app/crv/` |
| **Tests deterministes** | `backend/tests/test_crv_api.py` (14 tests), `backend/tests/test_crv_propositions_service.py` (19 tests), `backend/tests/test_crv_validation.py` (16 tests), `tests/integration/test_basic_crv_integration.py`, `tests/integration/test_crv_rag_chain.py` |
| **Issues** | #444 CLOSED (rubriques métier rapport — remontée remark-ids `42ba7c0b`, `aead2ca0`) |
| **GAP** | Pas de script de démonstration bout-en-bout avec jeu de données MA complet ; DEV deployment décalé |
| **Priorité** | MEDIUM |
| **Couverture NR** | BONNE côté backend deterministe (49+ tests CRV) ; absente côté demo E2E |
| **Verdict** | **AMBER** |

---

### ECHO-DEMO-06 — Consultation RAG

| Item | Valeur |
|---|---|
| **Comportement attendu** | Deux questions successives, réponses fondées sur le dossier |
| **Services actifs** | `rag_query_service.py`, `rag_simulator_bridge.py` (commit `d96c4b8` du 2026-10-xx : wire RAG A2-A4 dans simulateur MA), `rag_context_service.py`, `rag_generation_service.py` |
| **Frontend** | `demo-client/app/query/page.tsx`, `demo-client/app/simulator/page.tsx` |
| **Tests deterministes** | `demo-client/app/query/page.multi-question.test.tsx` (2+ tests : plusieurs questions successives, reset champ, bouton actif), `backend/tests/test_rag_query_service.py`, `backend/tests/test_rag_http_endpoint.py` |
| **Issues** | #398 CLOSED (bouton Interroger inactif), #450 OPEN (simulateur téléphone — RAG consultatif vocal intégré, P0 du lot) |
| **GAP** | #398 corrigé au niveau frontend (test multi-question présent). Mais le simulateur (#450 OPEN) constitue le vecteur démo principal ; RAG A2-A4 nouvellement câblé via `rag_simulator_bridge.py` (`d96c4b8`) — non encore fumé sur DEV. Qdrant Cloud requis pour RAG réel (`real_rag_functional_validation` marqué BLOCKED_AT_SNAPSHOT). |
| **Priorité** | HIGH — scénario central de la démo |
| **Couverture NR** | PARTIELLE — multi-question test frontend mocké, pas de NR RAG réel Qdrant |
| **Verdict** | **AMBER** (risque BLOCKED si Qdrant injoignable sur DEV) |

---

### ECHO-DEMO-07 — Médicaments

| Item | Valeur |
|---|---|
| **Comportement attendu** | Distinguer rappel effectué / pilulier encore plein, sans inférer la prise |
| **Services actifs** | `medical_ai_guardrail.py` (non-inférence médicale), `crv_propositions_service.py` |
| **Tests deterministes** | `backend/tests/test_medical_ai_guardrail.py` (guardrail generique) |
| **Issues** | Aucune issue dédiée — couverture.md indique "DRAFT — à cadrer" |
| **GAP** | Scénario non cadré : pas de requirements précis, pas de transcript de référence, pas de cas discriminant medicament rappel/pilulier. Remarque PROD 14/09 mentionnée mais non tracée en issue. |
| **Priorité** | LOW-MEDIUM — après WAVE C |
| **Couverture NR** | ABSENTE pour le scénario spécifique |
| **Verdict** | **AMBER** (scénario à définir avant toute NR) |

---

### ECHO-DEMO-08 — Préférences et prestations

| Item | Valeur |
|---|---|
| **Comportement attendu** | Regrouper sans doublons soupe, douche, physio, souhaits, budget, Pflegegrad |
| **Services actifs** | `crv_propositions_service.py` (déduplication sémantique), `hitl_finalization_service.py`, restitution thématique |
| **Issues** | #415 CLOSED (déduplication sémantique des Facts + regroupement thématique allemand — remarques `922f191f`, `6688ca15`, `13f57f2a` rattachées) |
| **GAP** | #415 CLOSED mais pas de script de démonstration avec le jeu de données spécifique (soupe/douche/physio/budget/Pflegegrad). Aucune preuve E2E. |
| **Priorité** | MEDIUM |
| **Couverture NR** | PARTIELLE — déduplication sémantique fermée dans le code, pas de NR demo-level |
| **Verdict** | **AMBER** |

---

### ECHO-DEMO-09 — Entités et vocabulaire DE

| Item | Valeur |
|---|---|
| **Comportement attendu** | Distinguer patient/MA/responsable ; 09:20 ; Pflegedienstleistung vs Pflegedienstleitung |
| **Services actifs** | `agency_context_service.py`, `agency_dictionary_service.py`, `current_knowledge_service.py`, `stt_context_builder.py`, `stt_context_renderers.py` |
| **Tests deterministes** | `backend/tests/test_agency_context.py` (23 tests), `backend/tests/test_current_knowledge_service.py` (19 tests) |
| **Issues** | #401 CLOSED (dictionnaire agence Dispoline DE + modèles Officium), #403 CLOSED (enrichissement dictionnaire depuis écran Remarques), #451 CLOSED (German MA Business Baseline V1) |
| **GAP** | Pas de cas discriminant STT avec ambiguïtés phonétiques (Pflegedienstleistung vs Pflegedienstleitung). Tests agency_context déterministes présents mais ne valident pas le STT en contexte réel. |
| **Priorité** | LOW-MEDIUM |
| **Couverture NR** | BONNE côté deterministe agency_context ; absente côté STT phonétique réel |
| **Verdict** | **AMBER** |

---

## 4. Récapitulatif verdicts

| Scénario | Verdict | Priorité | Issues bloquantes |
|---|---|---|---|
| ECHO-DEMO-01 — Planning | **AMBER** | MEDIUM | DEV deployment |
| ECHO-DEMO-02 — Vocal | **AMBER** | HIGH | #394 OPEN, DEV deployment |
| ECHO-DEMO-03 — Alertes santé | **AMBER** | MEDIUM | DEV deployment |
| ECHO-DEMO-04 — Correction Fact | **BLOCKED** | CRITIQUE P0 | #453 OPEN |
| ECHO-DEMO-05 — Tagesjournal | **AMBER** | MEDIUM | DEV deployment |
| ECHO-DEMO-06 — RAG Consultation | **AMBER** | HIGH | #450 OPEN, Qdrant requis |
| ECHO-DEMO-07 — Médicaments | **AMBER** | LOW-MEDIUM | Scénario non cadré |
| ECHO-DEMO-08 — Préférences | **AMBER** | MEDIUM | DEV deployment |
| ECHO-DEMO-09 — Vocab DE | **AMBER** | LOW-MEDIUM | DEV deployment |

**Verdict global : AMBER** — 1 scénario BLOCKED (P0), 8 AMBER, 0 GREEN.

Aucun scénario ne peut être déclaré GREEN : ni preuve d'exécution runtime sur le déploiement courant DEV, ni script E2E exécutable dans `axon-functional-tests`.

---

## 5. Lots WAVE indépendants

### WAVE A — Prérequis déploiement (BLOQUANT pour tout smoke runtime)
- Résoudre le décalage Railway DEV (issue #446 OPEN)
- Vérifier que le HEAD `9d6ee9e` est bien déployé et smoke backend accessible
- Durée estimée : courte si pipeline Railway débloqué

### WAVE B — Correctif P0 ECHO-DEMO-04 (BLOQUANT pour la démo)
- Corriger #453 : perte correction Fact lors de l'acceptation
- Services : `hitl_finalization_service.py`, `visit_memory_persistence.py`, cycle HITL → acceptation
- Ajouter test NR deterministe du cycle édition→sauvegarde→liste→acceptation
- Prérequis : aucun (peut être développé en parallèle de WAVE A)

### WAVE C — Smoke E2E par scénario (après WAVE A)
- ECHO-DEMO-01 : smoke planning → contexte visite → MA contextuel
- ECHO-DEMO-02 : smoke vocal réel → STT → CRV (close #394)
- ECHO-DEMO-03 : smoke alertes santé → guardrail non-inférence
- ECHO-DEMO-05 : smoke CRV Tagesjournal complet
- ECHO-DEMO-06 : smoke RAG 2 questions successives (simulateur MA + Qdrant)
- ECHO-DEMO-08 : smoke déduplication prestations/préférences
- ECHO-DEMO-09 : smoke STT entités DE phonétiques
- Prérequis : WAVE A + WAVE B

### WAVE D — Cadrage et définition ECHO-DEMO-07
- Rédiger requirements médicaments (rappel effectué vs pilulier plein)
- Définir transcript DE de référence et résultat attendu (non-inférence)
- Créer issue dédiée dans `echoline-sovereign`
- Prérequis : décision HITL sur le périmètre guardrail médicaments

---

## 6. Oracles NR — état et lacunes

### Oracles existants (déterministes, échelons T0-T2)

| Composant | Fichier | Tests | Statut |
|---|---|---|---|
| CRV pipeline | `test_crv_api.py`, `test_crv_propositions_service.py`, `test_crv_validation.py` | 49 | Exécutables |
| RAG query | `test_rag_query_service.py`, `test_rag_http_endpoint.py` | Présents | Exécutables |
| RAG multi-question frontend | `page.multi-question.test.tsx` | 2+ | Exécutables (jest) |
| Guardrail médical | `test_medical_ai_guardrail.py` | Présents | Exécutables |
| Agency context | `test_agency_context.py` | 23 | Exécutables |
| Current knowledge | `test_current_knowledge_service.py` | 19 | Exécutables |
| Voice service | `test_voice_conversation_service.py` | 7 | Exécutables |
| Visit context | `test_visit_context.py` | 12 | Exécutables |
| CRM planning | `test_crm_planning_gateway.py`, `test_gde_crm_planning_import.py` | 6+ | Exécutables |
| Hitl finalization | `test_v3_runtime_pipeline.py` | 19 | Exécutables |

### Oracles manquants (T3 demo-level, NR E2E)

| Scénario | Lacune | Validation requise |
|---|---|---|
| ECHO-DEMO-04 | Cycle édition→sauvegarde→acceptation déterministe | Automatisable (sans LLM) |
| ECHO-DEMO-02 | Smoke audio réel STT→CRV | HITL (audio réel DE) |
| ECHO-DEMO-06 | Smoke RAG réel Qdrant 2 questions | HITL (Qdrant requis) |
| ECHO-DEMO-07 | Cas discriminant médicament pilulier/rappel | HITL (définition scénario) |
| Tous | Script axon-functional-tests exécutable | HITL (fixtures + assertions) |

### Oracles nécessitant validation HITL

- **ECHO-DEMO-04** : validation HITL que la correction persistée est bien la version éditée (et non l'ancienne) après le cycle complet
- **ECHO-DEMO-02** : écoute et vérification qu'aucune écriture silencieuse n'est faite sur ambiguïté STT
- **ECHO-DEMO-06** : vérification que les réponses RAG sont bien fondées sur les facts du dossier (et non inventées)
- **ECHO-DEMO-07** : arbitrage sur la frontière guardrail médicaments/rappel (AGENTS.md §3 : "ne pas prématurément cristalliser les comportements exploratoires")

---

## 7. Réconciliation issues PROD → scénarios

| remark-id (préfixe) | Issue | Scénario | Statut |
|---|---|---|---|
| `6ec157d2` | #453 OPEN | ECHO-DEMO-04 | **BLOCKING** |
| `3b5e4840` | #398 CLOSED | ECHO-DEMO-06 | Corrigé code, non fumé DEV |
| `2c65f8d8` | #445 CLOSED | ECHO-DEMO-03 | Corrigé code |
| `fe28f88b` | #445 CLOSED | ECHO-DEMO-03 | Corrigé code |
| `42ba7c0b` | #444 CLOSED | ECHO-DEMO-05 | Corrigé code |
| `aead2ca0` | #444 CLOSED | ECHO-DEMO-05 | Corrigé code |
| `922f191f` | #415 CLOSED | ECHO-DEMO-08 | Corrigé code |
| `6688ca15` | #415 CLOSED | ECHO-DEMO-08 | Corrigé code |
| `13f57f2a` | #415 CLOSED | ECHO-DEMO-08 | Corrigé code |
| `daa3064f` | #391 CLOSED | ECHO-DEMO-02 | Corrigé code |
| `a2f8ec2c` | #399 CLOSED | ECHO-DEMO-01 | Corrigé code |
| `bf66f242` | REX positif | — | Aucune action corrective |

---

## 8. Anomalies et blocages

1. **DEV deployment décalé (#446 OPEN)** : Railway DEV ne reflète pas le HEAD dev. Tout smoke runtime (ECHO-DEMO-01 à 09) est invalide tant que ce blocage persiste.
2. **#453 P0 OPEN** : défaut démontré en PROD, non corrigé sur `dev`. Scénario ECHO-DEMO-04 inutilisable en démonstration.
3. **axon-functional-tests vide de scripts** : la matrice de couverture est purement documentaire. Aucun test exécutable n'existe pour aucun des 9 scénarios.
4. **Qdrant Cloud inaccessible depuis agent cloud** : `real_rag_functional_validation` marqué BLOCKED_AT_SNAPSHOT. ECHO-DEMO-06 nécessite un réseau Qdrant réel.
5. **#394 OPEN** : smoke Voice réel (L8D) jamais exécuté — ECHO-DEMO-02 sans preuve runtime.
6. **test_strategy_snapshot.yaml** : `snapshot_commit = c290ca70` (2026-09-27), dev HEAD = `9d6ee9e` (2026-10-23). Écart de ~26 jours de développement. Invalider les entrées du snapshot touchées par les commits récents (#449, #450, #454) avant de les utiliser.

---

## 9. Preuves et références

- `tvnv/echoline-sovereign@9d6ee9e` — HEAD dev audité
- `tvnv/axon-functional-tests@a2ff76c` — HEAD main (coverage.md V0.1)
- `backend/app/services/medical_ai_guardrail.py` — guardrail médical déterministe
- `backend/app/services/rag_simulator_bridge.py` — commit `d96c4b8` câble A2-A4 dans simulateur MA
- `demo-client/app/query/page.multi-question.test.tsx` — oracle multi-question RAG
- `backend/app/services/hitl_finalization_service.py` — point d'entrée cycle HITL
- `docs/agent_context/test_strategy_snapshot.yaml` — snapshot `c290ca70` (stale de 26 jours)
- Issue #453 : https://github.com/tvnv/echoline-sovereign/issues/453
- Issue #446 : https://github.com/tvnv/echoline-sovereign/issues/446
- Issue #450 : https://github.com/tvnv/echoline-sovereign/issues/450
- Issue #394 : https://github.com/tvnv/echoline-sovereign/issues/394

---

## 10. Actions requises avant GREEN

| Priorité | Action | Propriétaire |
|---|---|---|
| P0 | Débloquer Railway DEV et déployer HEAD `9d6ee9e` | OPS |
| P0 | Corriger #453 (perte correction Fact) | Dev |
| P1 | Écrire script smoke ECHO-DEMO-02 (Voice réel, fermer #394) | Dev |
| P1 | Valider ECHO-DEMO-06 avec Qdrant réel sur DEV | Dev |
| P2 | Écrire scripts E2E axon-functional-tests pour ECHO-DEMO-01, 03, 05, 08, 09 | Dev |
| P3 | Cadrer ECHO-DEMO-07 (médicaments) : requirements + transcript DE | HITL |

---

**IDENTIFIANTS POUR REVUE GPT**  
Dépôt : tvnv/echoline-sovereign@9d6ee9e (dev) · tvnv/axon-functional-tests@a2ff76c (main)  
Issue bloquante P0 : #453 · Déploiement DEV bloqué : #446 · Smoke Voice manquant : #394  
Verdict : AMBER (1 BLOCKED, 8 AMBER, 0 GREEN)
