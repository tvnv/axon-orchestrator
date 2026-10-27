# Audit fonctionnel Echoline — ECHO-DEMO-01..09

**Run ID :** `GO-DIAG-e92057fa`  
**Owner circuit :** `opencode` (résultat publié dans `tvnv/axon-orchestrator#12`)  
**Date UTC :** `2026-10-27T17:55:58Z`  
**Mode :** lecture seule, aucun fournisseur externe, aucune modification des repos Echoline/Functional Tests  
**Verdict global :** `PARTIAL` — aucune qualification `GREEN` n'est accordée à un comportement non testé ; les acquis déterministes sont distingués des défauts démontrés et des zones non vérifiées.

---

## 1. Périmètre et méthode

- Référentiel scénarios : `tvnv/axon-functional-tests` (branche `main`).
- Cible auditée : `tvnv/echoline-sovereign` (branche `origin/dev`).
- Contrats fonctionnels et code réel inspectés dans `echoline-sovereign` (lecture seule, worktree détaché sur `origin/dev`).
- Issues GitHub lues (ouvertes et fermées) pour les lots A/B/C/D et les scénarios 01/07.
- Tests déterministes ciblés exécutés localement sans fournisseur externe (voir §9).
- Les comportements non couverts par un test déterministe ou par une preuve runtime sont classés `NON VÉRIFIÉ`, jamais `GREEN`.

---

## 2. SHA distants vérifiés

| Référentiel | Branche | SHA vérifié | Vérification |
|---|---|---|---|
| `tvnv/echoline-sovereign` | `origin/dev` | `4ade970fff6d7f3f9e7562425d367ca16953f565` | `git fetch origin dev` + `git rev-parse origin/dev` |
| `tvnv/axon-functional-tests` | `origin/main` | `a2ff76c7be3827b7b756892dff19f1f00681bb49` | `git fetch origin main` + `git rev-parse origin/main` |
| `tvnv/axon-orchestrator` | branche de travail | voir SHA de publication §11 | commit/push de ce rapport uniquement |

SHA d'acquis pertinents présents dans `origin/dev` :
- `4d1ad1fc4de2dcd926d81cdf74af4852c6c95f60` — merge PR #455 (correctif #453, Fact perdu à l'acceptation).
- `c142b056a4e318406026069aaab52ff670112414` — correctif backend/frontend #453.
- `badc322` / `b0a9f20` — acquis #445 (symptômes santé).
- `06aaf66` / `cebc523` / `b76cccd` / `966cd72` — acquis #444 (rubriques métier).

---

## 3. Matrice scénario → cible → comportement réellement vérifié → GAP → priorité → issues → couverture NR

| Scénario | Cible / lot | Comportement réellement vérifié | GAP démontré | Priorité | Issues | Couverture NR (tests) |
|---|---|---|---|---|---|---|
| **ECHO-DEMO-01** — Planning et contexte | Lot prérequis E2E | Service de contexte de visite (`create_and_persist_visit_context`, `get_visit_context`) et tests `test_visit_context.py` (11 PASS) | **DÉFAUT DÉMONTRÉ** : la persistance échoue (`VisitContextServiceError`) lorsque `planned_services` contient un `start_time` de type `datetime` (sérialisation JSON non gérée) ; 1 test en échec | P1 | #399 (CLOSED), #402 (CLOSED), #414 (CLOSED), #411 (CLOSED) | `backend/tests/test_visit_context.py` (11 pass / 1 fail), `demo-client/app/planning/page.test.tsx` (1 pass) |
| **ECHO-DEMO-02** — Compte rendu vocal | Lot D (fondation) | Moteur vocal→summary (`test_voice_to_summary_engine.py`, 13 PASS) et transports (17 PASS au run combiné antérieur) ; extraction déterministe de faits | NON VÉRIFIÉ sur transcript réel allemand bout-en-bout avec STT réel (aucun fournisseur externe dans cet audit) | P1 | #384 (CLOSED), #385 (CLOSED), #391/#392 (CLOSED), #361 (OPEN epic) | `backend/tests/test_voice_to_summary_engine.py`, `test_voice_to_summary_hitl_safety.py`, `test_voice_to_summary_transports.py` |
| **ECHO-DEMO-03** — Alertes santé | Lot C | Détection déterministe `medical_condition` incluant `Schwindel`, `Gleichgewichtsstörung`, `Sturzgefahr`, `Unsicherheit beim Gehen` ; routage vers thème `health` ; 29 tests `test_crv_propositions_service.py` PASS | Aucun défaut démontré sur la détection ; l'absence de diagnostic est préservée par construction. Non vérifié sur transcript réel complet avec ambiguïtés HITL | P2 (acquis) | #445 (CLOSED), #376 (CLOSED), #375 (CLOSED) | `backend/tests/test_crv_propositions_service.py` (29 PASS) |
| **ECHO-DEMO-04** — Validation et correction | Lot A | Correctif #453 mergé (`4d1ad1f`/`c142b05`) ; `test_echo_demo_04_edit_save_list_accept_reload_keeps_correction` PASS ; 8 tests HITL + 55 backend + 13 frontend verts selon livraison | **DÉFAUT / AC RESTANT** : validation par usage UI réel sur DEV non exécutée ; tests mockés ≠ acceptation métier. Issue #453 reste OPEN/PARTIAL | P0 | #453 (OPEN), #378 (CLOSED), #415 (CLOSED) | `backend/tests/test_voice_to_summary_hitl_safety.py` (8 PASS), `test_demo_direct_facts_workflow.py` + `test_visit_memory_persistence.py` (55 PASS rapportés) |
| **ECHO-DEMO-05** — Tagesjournal / CRV | Lot C | Politique de complétude (`crv_completeness_policy`) ; rubriques métier issues de #444 ; policy horaires manquants #374 | **DÉFAUT / ORACLE MANQUANT** : pas de champs explicites arrivée/départ dans `CrvVisit` ; le double horaire (arrivée ET départ) n'est pas prouvé comme extrait dans un même scénario (REX #444) ; complétude à 100 % peut masquer un champ manquant si le thème `time` est présent | P1 | #444 (CLOSED), #373 (CLOSED), #374 (CLOSED), #380 (CLOSED) | `backend/tests/test_crv_policies.py`, `test_crv_validation.py`, `test_crv_propositions_service.py` |
| **ECHO-DEMO-06** — Consultation RAG | Lot B | Service de requête RAG (`test_rag_query_service.py`, 7 PASS) et endpoint HTTP (7 PASS) ; démonstration multi-questions côté client (`page.multi-question.test.tsx`) | **PARTIEL** : le bouton « Interroger » et le second appel ont été corrigés (#398 CLOSED), mais la suite frontend complète présente des échecs dans notre environnement d'exécution (voir §9) ; dépendance à des faits validés persistés (#386/#388) | P1 | #398 (CLOSED), #388 (CLOSED), #362 (OPEN epic), #416 (CLOSED) | `backend/tests/test_rag_query_service.py` (7 PASS), `test_rag_http_endpoint.py` (7 PASS), `demo-client/app/query/page.multi-question.test.tsx` |
| **ECHO-DEMO-07** — Médicaments | Oracle à qualifier | Validateur V3 gère l'incertitude médicamenteuse (`v3_transcript_facts_validator.py`, branche `Medikament`/`unsicher`) ; guardrails médicaux (#376) | **NON VÉRIFIÉ / ORACLE À QUALIFIER** : aucun test scénario dédié ECHO-DEMO-07 ; le test existant est un validateur exploratoire, pas un oracle NR strict pour « rappel effectué vs pilulier plein » ; ne pas promouvoir en NR sans HITL | P2 | #376 (CLOSED), #361 (OPEN) | `backend/tests/test_v3_transcript_facts_validator.py` (exploratoire) |
| **ECHO-DEMO-08** — Préférences et prestations | Lot D | Déduplication sémantique et restitution thématique (`thematicFacts.test.ts`, 12 PASS ; `ThematicSynthesisPanel.test.tsx`, 9 PASS) ; oracles Aurélie (soupe de lentilles, douche, physiothérapie, etc.) dans `test_crv_propositions_service.py` | Aucun défaut démontré sur la dédup ; la couverture reste déterministe sur transcripts figés, non sur un transcript réel de démonstration | P2 (acquis) | #415 (CLOSED), #400 (CLOSED) | `demo-client/lib/thematicFacts.test.ts` (12 PASS), `demo-client/components/ThematicSynthesisPanel.test.tsx` (9 PASS) |
| **ECHO-DEMO-09** — Entités et vocabulaire DE | Lot D | Normalisation contextuelle (`test_voice_to_conversation_adapter_comprehensive.py`, 15 PASS) : « neun Uhr zwanzig » → « 09:20 Uhr » en contexte ; discrimination `Pflegedienstleistung`/`Pflegedienstleitung` | Couverture sur mocks, non sur STT réel ; dépendance au contexte agence (#401/#403) et au contexte de visite (#399) | P2 (acquis déterministe) | #401 (CLOSED), #403 (CLOSED), #390/#389 (CLOSED) | `backend/tests/test_voice_to_conversation_adapter_comprehensive.py` (15 PASS) |

---

## 4. Détails par scénario

### ECHO-DEMO-01 — Planning et contexte de visite
- **Cible :** `backend/app/services/visit_context_service.py` (`create_and_persist_visit_context`, `get_visit_context`) ; `backend/app/models/visit_context.py` (`PlannedService`, `VisitContext.to_dict`).
- **Vérifié :** 11 tests PASS sur `test_visit_context.py` (création, récupération, réduction d'ambiguïté).
- **Défaut démontré :** `test_context_services_reduce_interpretation_ambiguity` FAIL — `VisitContextServiceError: Object of type datetime is not JSON serializable` quand `planned_services` contient `start_time: datetime(...)`. La persistance utilise `[s.__dict__ for s in model_context.planned_services]` au lieu de la représentation sérialisée de `to_dict()` (qui convertit `start_time` en ISO).
- **Impact :** bloque le prérequis E2E dès qu'un planning réel contient des heures de service.
- **Dépendances :** CRM/Planning simulator (#411, #414 CLOSED) alimente ce contexte.

### ECHO-DEMO-02 — Compte rendu vocal
- **Cible :** `backend/app/services/voice_to_summary_*`, `direct_facts_service`, `crv_propositions_service`.
- **Vérifié :** moteur et transports verts (tests déterministes) ; extraction déterministe de faits avec heures/prestations/observations.
- **Non vérifié :** parcours STT réel (aucun fournisseur externe dans cet audit) ; distinction acquis code vs comportement runtime.
- **Issue ouverte liée :** #361 (EPIC L5, déclaration libre → CRV).

### ECHO-DEMO-03 — Alertes santé
- **Cible :** `backend/app/services/crv_propositions_service.py` (`CATEGORY_KEYWORDS_BY_LANGUAGE["de"]["medical_condition"]`) ; `medical_ai_guardrail.py`.
- **Vérifié :** #445 acquis et non rouvert ; termes santé étendus ; routage `medical_condition → health` ; négation/incertitude préservées.
- **GAP :** couverture déterministe sur mots-clés, pas sur transcript réel complet ; aucune preuve runtime DEV.

### ECHO-DEMO-04 — Validation et correction
- **Cible :** `backend/app/services/voice_to_summary_hitl_*` ; frontend `CanonicalHitlControls`.
- **Vérifié :** correctif #453 mergé sur `dev` ; `test_echo_demo_04_edit_save_list_accept_reload_keeps_correction` PASS ; 8 tests HITL PASS.
- **GAP démontré :** AC « validation par usage réel sur DEV » non exécuté (providers indisponibles au moment de la livraison) ; issue #453 reste OPEN/PARTIAL. Ne pas confondre tests mockés avec acceptation métier.
- **Priorité :** P0 (issue ouverte).

### ECHO-DEMO-05 — Tagesjournal / CRV
- **Cible :** `crv_completeness_policy.py`, `crv_models.py` (`CrvVisit`), `crv_prestation_policy.py`, `crv_validation_service.py`.
- **Vérifié :** politique de complétude et rubriques métier (#444) ; policy horaires manquants (#374).
- **GAP démontré :** absence de champs explicites arrivée/départ dans `CrvVisit` ; le REX de #444 signale que la date/heure de fin est reconnue dans `Zeit`, pas celle de début. Le double horaire (arrivée ET départ) n'est pas prouvé comme extrait et persisté dans un même scénario.
- **Oracle :** à qualifier avant toute promotion NR stricte.

### ECHO-DEMO-06 — Consultation RAG
- **Cible :** `backend/tests/test_rag_query_service.py`, `test_rag_http_endpoint.py`, `demo-client/app/query/page.tsx`.
- **Vérifié :** 7 + 7 tests backend PASS ; correction #398 (bouton inactif) ; scénario multi-questions côté client.
- **GAP / réserve :** la suite frontend complète échoue dans notre environnement d'exécution (voir §9) ; dépendance à des faits validés persistés (#386/#388). Issue épique #362 reste OPEN.

### ECHO-DEMO-07 — Médicaments
- **Cible :** `v3_transcript_facts_validator.py` (branche médicament/incertitude) ; `medical_ai_guardrail.py`.
- **Statut :** NON VÉRIFIÉ comme scénario ; oracle à qualifier. Aucun test dédié `ECHO-DEMO-07`. Le validateur existant est exploratoire et ne doit pas être transformé en oracle NR strict sans HITL.

### ECHO-DEMO-08 — Préférences et prestations
- **Cible :** `demo-client/lib/thematicFacts.ts`, `ThematicSynthesisPanel.tsx`, oracles Aurélie dans `test_crv_propositions_service.py`.
- **Vérifié :** 12 + 9 tests frontend PASS ; déduplication et restitution thématique verts sur transcripts figés.
- **Réserve :** couverture déterministe sur transcripts figés, pas sur un transcript réel de démonstration.

### ECHO-DEMO-09 — Entités et vocabulaire DE
- **Cible :** `contextual_normalization_service`, `voice_to_conversation_adapter`.
- **Vérifié :** 15 tests PASS ; normalisation « neun Uhr zwanzig » → « 09:20 Uhr » en contexte ; discrimination des termes professionnels par contexte agence.
- **Réserve :** couverture sur mocks, non sur STT réel ; dépendance aux contextes (#399/#401/#403).

---

## 5. Dépendances et indépendance des lots

| Lot | Scénarios | Dépendances | Peut tourner indépendamment ? |
|---|---|---|---|
| **A** | 04 | HITL safety, persistance VisitFact ; indépendant des lots B/C/D sur le code | Oui pour les tests déterministes ; l'AC UI dépend du runtime DEV |
| **B** | 06 | Faits validés persistés (#386/#388), contexte bénéficiaire ; dépend des données issues de 01/02/04/05 pour un E2E complet | Tests backend indépendants ; E2E bout-en-bout dépend de 01/05 |
| **C** | 03, 05 | #444/#445 (acquis), politique de complétude, extraction santé ; 05 dépend de 02 pour les faits | 03 indépendant ; 05 dépend de 02 |
| **D** | 02, 08, 09 | STT/extraction, contexte agence/visite ; fondation des autres lots | 02 est prérequis pour 05/06 ; 08/09 valident l'extraction |

Ordre recommandé pour l'E2E : **01 → 02 → 03/08/09 → 04 → 05 → 06 → 07 (qualification)**.

---

## 6. Scénario 01 — prérequis E2E

- Le contexte de visite est le prérequis de tous les scénarios (bénéficiaire, planning, services, ambiguïtés).
- Le défaut démontré (sérialisation `datetime` dans `VisitContextService`) doit être corrigé avant tout smoke E2E avec planning réel.
- **Ne pas déclarer E2E-01 GREEN** tant que ce test n'est pas vert et qu'un smoke runtime n'est pas exécuté.

---

## 7. Scénario 07 — oracle à qualifier

- Aucun oracle strict validé pour « rappel effectué vs pilulier encore plein ».
- Le validateur V3 traite l'incertitude médicamenteuse, mais c'est un mécanisme exploratoire.
- **Action :** qualifier un oracle HITL avec transcript réel fictif avant toute promotion en NR stricte. Ne pas transformer les références exploratoires en oracles stricts sans HITL.

---

## 8. Acquis #444/#445 et double horaire arrivée/départ

- #444 (rubriques métier) et #445 (symptômes santé) sont **acquis et non réimplémentés** dans cet audit.
- Le REX de #444 (remarque PROD 28/09) signale que la date/heure de **fin** de visite est reconnue dans `Zeit`, pas celle de **début**.
- **Delta ciblé :** les AC de #444 prévoient la restitution des heures arrivée/départ dans les champs obligatoires, mais ne prouvent pas que **les deux informations sont extraites** dans un même scénario.
- **Oracle à ajouter (non exécuté ici) :** une visite MA exprimant heure d'arrivée et heure de départ produit deux valeurs distinctes correctement associées, avec provenance et ambiguïtés préservées ; aucun champ obligatoire omis silencieusement.
- Ce point est un **GAP ouvert** pour ECHO-DEMO-05, indépendant de la clôture de #444.

---

## 9. Preuves déterministes exécutées dans cet audit

| Commande | Résultat |
|---|---|
| `pytest backend/tests/test_crv_propositions_service.py` | 29 PASS |
| `pytest backend/tests/test_voice_to_summary_hitl_safety.py` | 8 PASS |
| `pytest backend/tests/test_visit_context.py` | 11 PASS, 1 FAIL (`test_context_services_reduce_interpretation_ambiguity`) |
| `pytest backend/tests/test_voice_to_summary_engine.py` | 13 PASS |
| `pytest backend/tests/test_voice_to_conversation_adapter_comprehensive.py` | 15 PASS |
| `pytest backend/tests/test_rag_query_service.py` | 7 PASS |
| `pytest backend/tests/test_rag_http_endpoint.py` | 7 PASS |
| `vitest lib/thematicFacts.test.ts` | 12 PASS |
| `vitest components/ThematicSynthesisPanel.test.tsx` | 9 PASS |
| `vitest app/planning/page.test.tsx` | 1 PASS |
| `vitest app/query/page.test.tsx` (run complet) | 17 PASS, 10 FAIL dans notre environnement |
| `vitest app/query/page.multi-question.test.tsx` | 2 PASS, 4 FAIL dans notre environnement |

Les échecs frontend sont observés dans notre environnement d'exécution (Node v22.22.1) et ne sont pas, à eux seuls, une preuve de régression produit ; ils sont signalés comme **NON VÉRIFIÉ localement**. Les tests backend ciblés sont verts sauf le défaut démontré §4 (ECHO-DEMO-01).

Aucun test avec fournisseur externe n'a été exécuté.

---

## 10. Verdict

- **Verdict global :** `PARTIAL`.
- **Acquis déterministes :** ECHO-DEMO-03 (détection santé), ECHO-DEMO-08 (dédup/thématique), ECHO-DEMO-09 (normalisation contextuelle) — verts sur tests ciblés.
- **Défaut démontré :** ECHO-DEMO-01 (persistance `datetime`), ECHO-DEMO-04 (AC UI réelle non exécutée, issue OPEN), ECHO-DEMO-05 (double horaire non prouvé).
- **Non vérifié :** ECHO-DEMO-02 (STT réel), ECHO-DEMO-06 (frontend complet / runtime), ECHO-DEMO-07 (oracle à qualifier).
- **Aucun scénario n'est qualifié GREEN bout-en-bout** sur la base de ce rapport.

---

## 11. Publication

- Branche de travail : `docs/echoline-functional-audit-20261027-e92057fa`
- Fichier : `reports/echoline-sovereign/20261027T175558Z_echoline-functional-audit_GO-DIAG-e92057fa.md`
- Commit/push : uniquement ce rapport documentaire.
- SHA de publication et permalien GitHub : à compléter après push (voir commentaire final sur #12).

---

## Annexe — références

- Issues clés : #453 (OPEN), #444/#445 (CLOSED), #398 (CLOSED), #388 (CLOSED), #415 (CLOSED), #414 (CLOSED), #399/#402 (CLOSED), #401/#403 (CLOSED), #373/#374 (CLOSED), #362/#361 (OPEN epic).
- Fichiers clés : `backend/app/services/visit_context_service.py`, `backend/app/models/visit_context.py`, `backend/app/services/crv_propositions_service.py`, `backend/app/services/crv_completeness_policy.py`, `backend/app/models/crv_models.py`, `backend/app/services/v3_transcript_facts_validator.py`, `demo-client/lib/thematicFacts.ts`, `demo-client/app/query/page.tsx`.
- Tests clés : `backend/tests/test_visit_context.py`, `test_voice_to_summary_hitl_safety.py`, `test_crv_propositions_service.py`, `test_voice_to_summary_engine.py`, `test_voice_to_conversation_adapter_comprehensive.py`, `test_rag_query_service.py`, `test_rag_http_endpoint.py`, `demo-client/lib/thematicFacts.test.ts`, `demo-client/components/ThematicSynthesisPanel.test.tsx`.
