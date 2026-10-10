# Sécurité

Ce document décrit la posture sécurité **de SecuMerge lui-même** : ce qui est
protégé, comment, et ce qui reste à faire.

## Mesures en place

### Secrets

- `.env` n'est jamais commité (`.gitignore`) ; seul `.env.example` est versionné.
- La configuration passe par des variables d'environnement (`app/core/config.py`).
- Les identifiants PostgreSQL de développement vivent dans `.env`, pas dans le
  compose.

### Entrées non fiables

- **Uploads de rapports** : taille limitée à 10 Mo (lecture par morceaux,
  `413` au-delà), JSON strictement validé (`400` sinon), contenu jamais exécuté.
- **Parsers tolérants** : une entrée malformée est ignorée, jamais exécutée et
  jamais fatale.
- **Validation Pydantic** sur tous les paramètres d'API (scanner, filtres…).

### Base de données

- Requêtes exclusivement via SQLAlchemy (paramétrées) — aucune concaténation.
- Contraintes en base : `CHECK` sur sévérité/statut, unicité de l'empreinte par
  dépôt, clés étrangères en cascade.

### Conteneurs

- Image applicative `python:3.13-slim`, **utilisateur non-root** (`appuser`).
- Contexte de build minimal (`.dockerignore`) : pas de `.env`, pas de `.git`.

### Décisions de sécurité fonctionnelles

- **Security Gate fail-closed** : dépôt inconnu ou scanner sans scan complet →
  `FAIL`. L'absence de preuve n'est jamais un `PASS`.
- **Cycle de vie protégé** : la résolution automatique ne touche jamais
  `FALSE_POSITIVE` ni `ACCEPTED_RISK` (décisions humaines).
- **CI honnête** : le pipeline exécute réellement les contrôles et échoue
  quand une preuve manque ; pas de faux check qui passe toujours.

## Limites connues

| Limite | Impact | Suite envisagée |
|---|---|---|
| **Pas d'authentification** — l'API et le dashboard sont ouverts | Quiconque atteint le port peut lire/ingérer | Auth + rôles (Phase 7 de la spec) |
| Gate basé sur la **présence** des scanners, pas sur la criticité | Un scan complet peut passer avec des `CRITICAL` | Échouer sur les nouveaux `CRITICAL`/`HIGH` |
| Pas de **réouverture** d'un finding résolu qui réapparaît | Statut figé jusqu'à action manuelle | Réouverture automatique optionnelle |
| **Images de scanners et dépendances non épinglées** (`latest`, `>=`) | Reproductibilité imparfaite | Épingler les versions (image + CI) |
| Pas de **quota de stockage** par dépôt (rapports bruts) | La base peut grossir | Quota + purge des vieux rapports |
| Pas de **rate limiting** sur l'API | Abus possible si exposée | Middleware de limitation |
| Identifiants de dev par défaut dans `.env.example` | À changer hors développement local | Générateur de mot de passe au setup |
| Pas de scan de l'**image SecuMerge** ni de détection de **secrets** en CI | Couverture partielle du spec §14 | Ajouter Trivy image + Gitleaks |
| Pas de sauvegarde/base **managée** | Données de dev uniquement | Hors périmètre |
| `git` du labo : cibles vulnérables **assumées** | Un scanner peut les signaler si mal exclues | Exclusions vérifiées par les tests (0 fuite) |

## Signaler un problème

Le projet est un exercice pédagogique, pas un service en production. Pour un
problème de sécurité, ouvrez une issue sur le dépôt GitHub (ou contactez
l'auteur).
