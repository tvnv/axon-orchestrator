# Axon — Registre historique des intentions projet

> Export de contexte compressé — 2026-10-09. **Document de travail**, non preuve d'implémentation. À versionner dans `.axon/intent/project-intent.md`.
>
> Sources : synthèses de mémoire conversationnelle accessibles et rappels historiques retrouvés. Les références aux dates, dépôts et issues servent de pistes de vérification, pas de liens probants vérifiés dans Git au moment de cet export.

## 1. Intention directrice

**Assurer la continuité autonome des WAVE Axon, avec un minimum d'interventions humaines.** La vitesse de développement et le benchmark des modèles sont désormais secondaires : le goulot se situe dans la continuité d'exécution, la validation fonctionnelle et la convergence après livraison.

- Axon C est l'exécuteur unique des WAVE (décision du 07/10/2026).
- Axon-stabilizer observe, détecte, diagnostique et orchestre les corrections/reprises ; Axon S peut intervenir pour corriger Axon C, mais ne doit pas devenir un second exécuteur des WAVE.
- GPT réalise la revue indépendante au niveau WAVE, compare le code livré aux intentions, produit des écarts et prépare des issues/WAVE de convergence, idéalement en asynchrone et 0 HITL.
- Git distant est la source de vérité durable pour le code, les décisions et les preuves de livraison ; les états d'exécution doivent être persistants et réconciliables.

## 2. Modèle opérationnel WAVE (priorité élevée, 09/10/2026)

1. Une **WAVE** est une liste d'issues à traiter.
2. Une **issue** contient une liste de tâches et ses propres critères d'acceptation (AC).
3. Une issue est traitée lorsque toutes ses tâches sont terminées et que ses AC sont atteints.
4. Après interruption, reprendre à la **dernière tâche non terminée** ; ne pas recommencer les tâches déjà acquises.
5. Éviter les boucles infinies : une issue **AMBER** peut être acceptée pour terminer la WAVE, avec reprise/convergence dans une WAVE suivante. AMBER n'équivaut pas à conformité complète.
6. Chercher une qualité minimale suffisante pour terminer la WAVE et évaluer l'ensemble ; ne pas attendre la perfection à chaque issue.
7. La revue GPT de fin de WAVE juge la conformité à l'intention globale et crée/priorise les corrections. Ne pas bloquer systématiquement l'exécution sur des reviewers par issue.
8. La WAVE en cours continue pendant la préparation asynchrone des WAVE de convergence ; celles-ci rejoignent la queue.

## 3. Décisions et arbitrages historiques

| Date | Décision / intention | Statut au 09/10 | Provenance à réconcilier |
|---|---|---|---|
| 19/09 | Continuité par commit + push + SHA distant vérifié ; conserver le travail livré malgré la perte d'un run | Actif | Conversations Axon du 19/09 ; Git |
| 20/09 | Collector déterministe permanent → snapshots factuels ; Analyzer LLM événementiel → diagnostic ; Recovery Controller → actions contrôlées | Actif | Conversations du 20/09 ; `tvnv/Axon-stabilizer` |
| 20/09 | Consolider Axon S, Axon C et Git ; ignorer les runs abandonnés pour éviter le bruit | Actif, à étendre aux autres sources | Conversations du 20/09 |
| 23–24/09 | 0 HITL pour reprise nominale, routage standard sans pin manuel, reviewer non bloquant ; pas de replay d'ACTOR livré | Actif | Issues historiques #390/#402/#403/#404 |
| 24/09 | Mettre en pause l'autonomie directe Axon S Stabilizer et prioriser Evidence Store déterministe dans `tvnv/Axon-stabilizer` | Décision historique, partiellement remplacée par la séparation des rôles du 07/10 | Conversations du 24/09 |
| 27/09 | Stabilizer peut réparer Axon C mais pas les projets métier ; Git distant reste le point de reprise | Actif | Conversations du 27/09 |
| 01/10 | Les agents doivent publier un résumé final dans leur issue de canal `tvnv/axon-orchestrator` | Actif | Règle de gouvernance des canaux |
| 03–04/10 | Secrets runtime via Infisical, éviter la duplication dans Railway ; Evidence Store multi-source | Cible active, implémentation incomplète à l'époque | `tvnv/Axon-stabilizer` #40/#51 ; `tvnv/axon-execution-mcp` #502 |
| 06/10 | Reviewer par issue inutile en mode WAVE ; revue indépendante GPT au niveau WAVE | Actif | Conversations du 06/10 |
| 07/10 | Axon C exécute les WAVE ; Axon S corrige Axon C ; priorité au canal GPT → Axon C persistant | Actif | Conversations du 07/10 ; `tvnv/axon-orchestrator` |
| 08/10 | Le stabilizer doit diagnostiquer, corriger et relancer une WAVE bloquée sans attendre un prompt HITL | Actif | REX OpenCode NUC du 07–08/10 |
| 09/10 | Simplicité WAVE → issues → tasks → AC ; AMBER accepté et reprise task-level ; validation finale GPT | **Dernier arbitrage prioritaire** | Conversations du 09/10 |
| 09/10 | Snapshots périodiques 2–3 fois/jour, pas à chaque WAVE ; paramètres globaux mutualisés par gateway, sans doublons entre serveurs | Cible | Conversation du 09/10 |

## 4. Invariants pour la revue de code

### Continuité / idempotence
- Une livraison fonctionnelle acquise ne doit pas être rejouée ; la reprise se fait sur le travail restant.
- Chaque handoff durable s'appuie sur un commit poussé et un SHA distant vérifiable ; aucun état local non commité ne doit être considéré comme acquis.
- Réconcilier les états WAVE/ACTOR obsolètes sans déclencher un replay accidentel.
- Un redémarrage/déploiement d'Axon C ne doit pas laisser une WAVE définitivement bloquée ; reprise automatique contrôlée, avec procédure en cas d'échec et flag de désactivation si nécessaire.
- Le suivi d'avancement doit être déterministe, sans confondre une erreur d'observabilité avec l'échec du travail fonctionnel.

### Livraison / Git
- `functional_delivery_sha` désigne le commit fonctionnel ; les modifications `.axon/**` sont du bookkeeping, pas une livraison métier.
- Les branches `dev` et `main` sont les branches pérennes visées pour `tvnv/axon-execution-mcp` ; nettoyage des branches éphémères après livraison.
- Les commits exclusivement consacrés aux capsules `.axon/**` ne devraient pas déclencher de builds Railway/Vercel inutiles.
- Le merge sur `dev` peut être automatisé pour éviter les stalls ; les règles de promotion `main` restent à qualifier selon le dépôt. **Ne pas généraliser** la règle Echoline (main = HITL publication) à Axon.

### Stabilizer / observabilité
- Collector et snapshots : déterministes, traçables, multi-sources, à provenance et horodatage explicites.
- Le LLM ne doit pas assurer le polling continu ni exécuter directement des commandes dangereuses : diagnostic et plan, puis contrôleur de reprise vérifiable.
- La supervision doit utiliser les API Axon disponibles ; éviter de dépendre de requêtes SQL directes pour les diagnostics courants.
- Une absence de preuve ou un `config_error` ne doit pas être présenté comme preuve d'échec fonctionnel.
- L'interface HITL doit présenter une timeline compacte, filtrable par source, avec événements de deux lignes maximum et signalement des stalls.

### Routing / ressources
- Santé, quota et capacité du provider avant optimisation du coût ; FREE → ULTRA_LOW_COST → LOW_COST → STANDARD comme principe historique.
- Optimiser le coût des tokens en cache et les modèles gratuits, mais **ne jamais sacrifier la continuité** pour une économie marginale.
- Les règles de routage horaire et de peak hours doivent être observables et testées en usage réel.
- Le reviewer non exploité ne doit pas consommer des tokens sans valeur ajoutée.
- L'exclusion historique de Claude/Anthropic concerne les routes nominales Axon ; Claude utilisé hors routage comme assistance de stabilisation est une exception historique à clarifier, non une autorisation implicite dans le resolver.

### Canal et autonomie GPT
- Le protocole de canal utilise REQUEST → ACK → WORKING → RESULT, avec `request_id` idempotent et résumé final, y compris en cas de BLOCKED.
- La queue d'issues `tvnv/axon-orchestrator` est un canal de transport/audit, **pas** un duplicata de l'état d'exécution Axon C.
- GPT doit pouvoir persister le diagnostic et les issues de convergence, y compris depuis une tâche planifiée ; les restrictions d'écriture en exécution planifiée restent un blocage à démontrer/résoudre.
- La revue GPT s'appuie sur Git, WAVE, issues, preuves d'usage et intentions historisées ; un simple contrôle statique ne suffit pas.

## 5. Retours d'expérience (REX)

| Période | Observation | Conséquence recherchée |
|---|---|---|
| 19–24/09 | Perte de continuité d'un run alors que Git reste durable ; ACTOR `RUNNING` obsolète bloque des claims | Reprise depuis état durable, sans replay des livraisons |
| 23/09 | 71 cycles `wake→lease→claim→resume→release` sans doublon ; mais risque de retries infinis | Ajouter détection de futilité et bornage des reprises |
| 24/09 | Des commits `.axon/**` ont été confondus avec livraisons fonctionnelles | Séparer SHA fonctionnel et capsules |
| 01–04/10 | Des sources Git/Provider/Railway vides ou en `config_error` produisent de faux signaux | Evidence Store multi-source, confiance et provenance explicites |
| 03/10 | Un `agent_error` pouvait écraser le verdict réel | Priorité à la réconciliation d'état et au résultat observable |
| 06/10 | Reviewers par issue coûteux et peu exploités | Déplacer la revue indépendante au niveau WAVE |
| 07–08/10 | Le stabilizer OpenCode NUC ne suit pas seul les WAVE longues ; PR parfois non mergées avant rappel HITL | Watchdog, merge dev autorisé, diagnostic/fix/reprise automatiques |
| 08–09/10 | Le coût de validation dépasse le coût de développement ; qualité des modèles jugée suffisante | Cristalliser les intentions et AC, renforcer la revue fonctionnelle |
| 09/10 | Axon qualifie mal le travail mais peut qualifier déterministiquement l'avancement | Découpler état d'avancement, qualité minimale et conformité finale GPT |
| 09/10 | Une tâche planifiée GPT lit Git mais l'écriture d'issues/commentaires semble échouer selon le contexte | Tester les canaux de persistance et documenter les permissions réelles |

## 6. Critères de revue indépendante GPT

La revue de fin de WAVE doit répondre, preuves à l'appui :

1. **Continuité** : la WAVE progresse-t-elle jusqu'à un état terminal malgré les stalls, quotas, déploiements et reprises ?
2. **Avancement** : pour chaque issue, les tasks terminées et les AC sont-ils identifiables ? Une issue AMBER a-t-elle un reliquat explicite ?
3. **Non-régression** : aucune task/ACTOR déjà livré n'a-t-il été rejoué ? Les SHA fonctionnels correspondent-ils aux commits réellement mergés ?
4. **Intentions** : le comportement livré respecte-t-il l'intention globale, y compris quand la conformité locale des issues semble GREEN ?
5. **Observabilité** : les verdicts sont-ils soutenus par des preuves multi-sources, sans faux négatifs causés par la collecte ?
6. **Autonomie** : le système peut-il corriger/reprendre sans prompt HITL ; si non, quel blocage persistant empêche la reprise ?
7. **Convergence** : quelles nouvelles issues, avec AC testables et priorité, doivent rejoindre la queue sans interrompre la WAVE en cours ?

**Sortie attendue** : `wave_id`, SHA de référence, issues et tasks, état terminal, preuves, écarts par rapport aux intentions, sévérité, proposition d'issues de convergence, décisions nécessitant HITL. Ne pas déclarer GREEN sur simple absence d'erreur.

## 7. Provenance et niveau de confiance

- **P1 — Intention explicite utilisateur retrouvée** : dates et formulations restituées à partir de résumés de conversations, particulièrement 19–27/09 et 06–09/10. Confiance élevée sur le sens, pas sur la citation verbatim.
- **P2 — Synthèse de mémoire compressée** : historiques des repos, issues, incidents et pratiques. Confiance moyenne ; peut omettre des révisions ultérieures.
- **P3 — Interprétation structurante** : regroupement en invariants, AC de revue et statut « actif ». À valider par usage et arbitrages plus récents.
- **Non effectué lors de cet export** : lecture exhaustive des fils d'origine, vérification des issues/commits GitHub, validation de l'état déployé, publication dans Git.

## 8. Incertitudes / arbitrages à réconcilier

1. **Rôle d'Axon S** : ancienne cible S→Stabilizer→C vs décision récente C exécuteur unique et S correcteur. La seconde prévaut pour l'exécution des WAVE ; les responsabilités détaillées de remédiation restent à vérifier.
2. **Acceptation AMBER** : seuil minimal de qualité, preuves requises, et traduction en état terminal Axon C non spécifiés formellement.
3. **Issue terminée vs AMBER** : « toutes tasks et AC atteints » définit la clôture conforme ; AMBER doit rester une sortie bornée avec dette reportée, pas une fausse clôture conforme.
4. **Promotions `main`** : distinguer autorisations propres à Axon C, Axon-stabilizer et Echoline ; aucune règle universelle de merge ne peut être inférée.
5. **Claude** : exclusion du routing nominal et usage ponctuel en stabilisation externe à expliciter.
6. **Gateway / queue** : emplacement exact des paramètres globaux, politique de déduplication et contrat de transport à vérifier dans le code.
7. **Persistance GPT planifiée** : capacités de création/modification/commentaire GitHub non démontrées de manière fiable depuis une tâche planifiée.
8. **Snapshots** : cible 2–3 fois par jour, à confirmer dans la configuration effective ; la fréquence de polling temps réel est distincte.
9. **Provenance** : les liens profonds vers fils/commits/PR manquent ; compléter avant de traiter ce registre comme une spécification contractuelle exhaustive.

## 9. Règles de maintenance de ce registre

- Ce document est un **snapshot daté des intentions**, pas une projection automatique de l'état du code.
- Ajouter les nouvelles décisions avec date, source et statut (`proposée`, `active`, `remplacée`, `abandonnée`).
- Ne jamais effacer silencieusement une décision ancienne : indiquer `remplacée par`.
- Distinguer clairement **intention**, **preuve d'implémentation**, **résultat de test** et **hypothèse**.
- Ne pas réécrire les intentions à chaque WAVE ; mettre à jour à cadence maîtrisée et à chaque nouvel arbitrage explicite.
- En cas de contradiction, préférer la décision explicite la plus récente ; signaler les ambiguïtés à l'HITL plutôt que les résoudre par invention.

## 10. Arbitrage du 10/10/2026 — WAVE courtes, enchaînement autonome et revue de convergence

**Statut : actif — décision explicite HITL du 10/10/2026.** Cette section prévaut sur les formulations antérieures qui associaient la continuité à une WAVE longue ou qui réservaient toute revue indépendante à GPT.

### Intention

Remplacer les WAVE longues par des **WAVE courtes et cohérentes fonctionnellement**, avec une **revue indépendante portant sur le même périmètre fonctionnel**. Conserver la continuité d'exécution autrefois obtenue par une WAVE longue grâce à l'**enchaînement autonome et fiable des WAVE** dans la queue Axon C.

### Règles

1. **Lotissement fonctionnel** : le Planner sélectionne le plus petit ensemble d'issues permettant une livraison et une revue fonctionnelle significatives. Aucun nombre fixe d'issues n'est prescrit ; éviter la fragmentation artificielle et les lots hétérogènes.
2. **Continuité inter-WAVE** : lorsqu'une WAVE se termine, Axon C démarre automatiquement la suivante disponible sans attendre une review, un nouveau prompt ni une décision HITL. La queue doit pouvoir être alimentée en avance ; les reprises après erreur/redémarrage doivent éviter doublons et replay de livraisons.
3. **Reviewer indépendant** : revue au niveau de la WAVE terminée, à partir du registre des intentions, des AC, du code Git et des résultats observables. Privilégier un **modèle gratuit** compte tenu du coût élevé en tokens et en temps des reviews.
4. **Parallélisme** : la review de WAVE N peut s'exécuter pendant WAVE N+1. Échec, indisponibilité, timeout ou verdict AMBER du reviewer **ne bloquent jamais** l'enchaînement nominal.
5. **Convergence intermédiaire** : le reviewer identifie les écarts à la cible connue ; le Planner déduplique, priorise et place les corrections pertinentes dans les WAVE suivantes, sans interrompre la WAVE active. Une review partielle exploitable a de la valeur.
6. **GPT + HITL** : checkpoints périodiques pour revoir les écarts résiduels, interpréter les ambiguïtés et faire évoluer la cible. GPT peut reprendre une review manquée ou insuffisante ; le reviewer ne crée pas seul de nouvelles exigences métier.
7. **Simplicité** : pas de sur-ingénierie des traces ni de gate supplémentaire. Le code Git reste la preuve principale de livraison ; le registre est la référence d'intention.

### Critères d'acceptation fonctionnels

- Une succession de WAVE courtes progresse sans intervention HITL, y compris si la review précédente est lente ou échoue.
- Chaque WAVE correspond à un objectif fonctionnel explicite, dont le résultat peut être confronté aux intentions et AC.
- Les écarts de review peuvent devenir des issues correctives dédupliquées, insérées dans la queue sans bloquer le flux.
- Les livraisons acquises ne sont pas rejouées après une interruption ; les états sont réconciliés.
- La prochaine revue GPT + HITL peut constater les écarts restants et ajuster la cible, sans dépendre du succès systématique des reviewers.

### Mesure de réussite

**Continuité** : capacité à enchaîner durablement les WAVE sans HITL, et non durée d'une WAVE isolée. **Convergence** : diminution des écarts fonctionnels résiduels entre deux checkpoints GPT + HITL, plutôt que nombre de remarques du reviewer. **Coût** : privilégier les modèles gratuits, sans sacrifier la continuité.

### Impact sur les règles historiques

- §1 et §2 : la revue GPT de fin de WAVE devient un recours et un checkpoint de convergence globale ; la revue indépendante par agent peut être systématisée à l'échelle de la WAVE, mais reste consultative et non bloquante.
- §3 (06/10) : la suppression des reviewers **par issue** reste valable ; elle n'implique pas la suppression des reviewers **par WAVE**.
- §6 : les critères de revue indépendante s'appliquent aussi au reviewer agent, à proportion des preuves disponibles ; GPT conserve la responsabilité de la revue globale avec HITL.
- Le présent arbitrage décrit une **cible**, pas une affirmation d'implémentation ou de smoke réussi.


## 11. Arbitrage du 10/10/2026 — stabilisation MiMo avant benchmark

**Statut : actif — décision explicite HITL du 10/10/2026.** Complète le §10 et prévaut sur les choix de reviewer antérieurs pendant la stabilisation.

### Décision
Stabiliser le processus de revue indépendante et de convergence avec **MiMo V2.6 Flash comme reviewer par défaut**. Reporter tout benchmark comparatif des modèles jusqu'à la stabilité démontrée du processus. Ce choix est temporaire, pas une preuve de supériorité générale.

### Boucle cible
WAVE courte fonctionnelle → revue indépendante MiMo asynchrone et non bloquante → findings publiés dans le canal → upsert dédupliqué des issues → planner → WAVE corrective suivante sans HITL systématique.

### Règles
- Reviewer strictement read-only : aucun code, commit, merge, PR, issue ou WAVE modifié/lancé ; seule publication du RESULT dans le canal autorisé.
- Oracle : registre d'intentions versionné, AC complètes des issues, code et SHA Git, tests et preuves d'usage réel. Les AC des items WAVE ne réduisent pas silencieusement celles des issues.
- Findings différenciés : RED reproduit, AMBER hypothèse/risque ou preuve incomplète, GREEN démontré. WAVE_DELIVERED ne vaut pas validation fonctionnelle.
- Planner : ingestion, déduplication, priorisation et réinjection des écarts dans la queue. Le reviewer ne redéfinit pas les exigences métier.
- La revue reste asynchrone et non bloquante ; son échec, délai ou verdict ne retarde pas la WAVE suivante.
- GPT + HITL : checkpoints globaux et arbitrages d'intentions ; promotion main soumise à HITL.

### Critères de stabilité préalables au benchmark
Plusieurs cycles consécutifs revue → publication → upsert → planner → WAVE corrective fonctionnent sans HITL injustifiée, findings perdus ou dupliqués, violation read-only ni confusion entre livraison et conformité. Vérifier par usage réel continuité et convergence. Aucun seuil chiffré inventé.

### Benchmark ultérieur
Une fois le processus stabilisé, comparer les modèles sur un protocole identique et des périmètres/SHA comparables : détection, preuves, reproductibilité, faux positifs, respect du rôle, délai et coût. Ne pas détourner la phase actuelle vers un benchmark exploratoire.

### REX de référence
Revue MiMo V2.6 Flash du 10/10/2026 sur les WAVE #599/#507 et #595/#600, publiée dans tvnv/axon-orchestrator#12 : respect du rôle read-only, deux défauts P0 détectés malgré des livraisons GREEN (F-01 perte de relance après crash ; F-04 incohérence terminale). Preuve ponctuelle d'utilité, pas benchmark définitif. Issues de convergence existantes mises à jour.
