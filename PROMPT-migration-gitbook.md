# Prompt — Migration de la documentation Apizee → GitBook (mono-repo, 8 sections)

> Coller dans une nouvelle session Claude Cowork avec le dossier `migration doc` connecté.
> Ce prompt remplace entièrement la version précédente.

---

## Contexte et mission

Les archives ClickHelp exportées (dossiers `*-exported/`) sont dans ce dossier de travail. Chaque archive contient :
- `toc.yaml` — arborescence hiérarchique, source de vérité des titres et de l'ordre
- `MD/*.md` — un fichier par topic (Markdown ClickHelp, BOM UTF-8 en tête)
- `Storage/<projet>/` — images et assets (~92 Mo par archive produit principale)

**Mission** : convertir ces archives en un **mono-repo Git** structuré pour GitBook Ultimate, organisé en **8 espaces/sections**, avec un mécanisme de réutilisation de contenu pour éviter les duplications. Produire le résultat dans `gitbook-export/` à la racine du dossier de travail. Ne rien pousser en ligne sans accord explicite.

---

## Archives à migrer (EN seulement — les archives `*fr*` et `assistance-multi-participants-*` sont en français mais sont INCLUSES car c'est le seul contenu multi-participants disponible)

| Archive | Topics | Destination |
|---|---|---|
| `video-assistance-user-en-exported` | 62 | section `video-assistance` → groupe Agents |
| `video-assistance-guest-en-exported` | 23 | section `video-assistance` → groupe Guests |
| `video-assistance-admin-en-exported` | 85 | section `video-assistance` → groupe Admins |
| `apizee-embed-for-agents-exported` | 20 | section `video-assistance` → groupe Agents (sous-groupe Embed) |
| `apizee-embed-for-guests-exported` | 13 | section `video-assistance` → groupe Guests (sous-groupe Embed) |
| `apizee-embed-for-it-operators-exported` | 16 | section `video-assistance` → groupe IT Operators |
| `assistance-multi-participants-user-exported` | 82 | section `video-assistance-multi` → groupe Agents (⚠️ contenu en français) |
| `assistance-multi-participants-guest-exported` | 40 | section `video-assistance-multi` → groupe Guests (⚠️ français) |
| `assistance-multi-participants-admin-exported` | 97 | section `video-assistance-multi` → groupe Admins (⚠️ français) |
| `apizee-meeting-user-en-exported` | 74 | section `meetings` → groupe Users |
| `apizee-meeting-guest-en-exported` | 40 | section `meetings` → groupe Guests |
| `apizee-meeting-admin-en-exported` | 92 | section `meetings` → groupe Admins |
| `health-user-exported` | 79 | section `telehealth` → groupe Practitioners |
| `health-guest-exported` | 44 | section `telehealth` → groupe Patients |
| `health-admin-exported` | 99 | section `telehealth` → groupe Admins |
| `apizee-for-salesforce-exported` | 13 | section `salesforce` |
| `apizee-for-genesys-admin-exported` | 2 | section `genesys` |
| `apizee-for-servicenow-publication-exported` | 7 | section `servicenow` |
| `faq-exported` | 19 | section `faq` (+ topics plateforme canoniques) |
| `_appvisio-reuse-publication-exported` | — | **NON migré** : projet de snippets ClickHelp, sert uniquement de source d'assets |
| `agents-tab-set-the-call-distribution-mode-exported` | 1 | section `video-assistance` → page cachée `contextual-help/` |
| `ticket-advanced-option-scan-the-guest-video-tooltip-exported` | 1 | section `video-assistance` → page cachée `contextual-help/` |
| `legal-information-exported` | 1 | section `faq` → groupe Legal |

**Archives non assignées à une section** (pose la question avant de traiter) :
- `customer-engagement-admin-en-exported` — 57 topics, produit Customer Engagement non listé dans les sections cibles
- `diag-help-desk-user-exported` — 52 topics, produit Diag Help Desk non listé

---

## Structure cible du repo

```
gitbook-export/
├── shared/
│   └── .gitbook/
│       └── includes/              ← blocs réutilisables (voir section Réutilisation)
│           ├── log-in-first-time.md
│           ├── user-roles.md
│           ├── choose-dashboard.md
│           ├── allow-browser-camera.md
│           └── ...
│
├── video-assistance/              ← espace GitBook section #1
│   ├── .gitbook.yaml
│   ├── SUMMARY.md
│   ├── README.md                  ← page d'accueil de la section
│   ├── agents/
│   │   ├── README.md
│   │   └── ... topics video-assistance-user-en + embed-for-agents
│   ├── guests/
│   │   └── ... topics video-assistance-guest-en + embed-for-guests
│   ├── admins/
│   │   └── ... topics video-assistance-admin-en
│   ├── it-operators/
│   │   └── ... topics embed-for-it-operators
│   └── contextual-help/           ← pages cachées (hors SUMMARY.md)
│       ├── agents-tab-call-distribution.md
│       └── ticket-scan-guest-video.md
│
├── video-assistance-multi/        ← espace GitBook section #2 (contenu FR)
│   ├── .gitbook.yaml
│   ├── SUMMARY.md
│   ├── agents/     ← assistance-multi-participants-user
│   ├── guests/     ← assistance-multi-participants-guest
│   └── admins/     ← assistance-multi-participants-admin
│
├── meetings/                      ← espace GitBook section #3
│   ├── users/ ├── guests/ └── admins/
│
├── telehealth/                    ← espace GitBook section #4
│   ├── practitioners/ ├── patients/ └── admins/
│
├── salesforce/                    ← espace GitBook section #5
├── genesys/                       ← espace GitBook section #6
├── servicenow/                    ← espace GitBook section #7
│
└── faq/                           ← espace GitBook section #8
    ├── .gitbook.yaml
    ├── SUMMARY.md
    ├── general/                   ← topics FAQ originaux
    ├── platform/                  ← topics plateforme canoniques (voir Réutilisation)
    │   ├── forgot-password.md
    │   ├── where-are-servers.md
    │   ├── change-subscription.md
    │   └── ...
    └── legal/
        └── ... topics legal-information
```

Chaque espace a son propre `.gitbook.yaml` :
```yaml
root: ./
structure:
  summary: SUMMARY.md
```

---

## Stratégie de réutilisation du contenu (anti-duplication)

**Constat** : ~40 slugs apparaissent dans 6 à 14 archives différentes. Après vérification par md5, ils ne sont PAS identiques entre produits — les UI diffèrent (screenshots, libellés de boutons). Il ne faut pas les fusionner mécaniquement.

Les doublons se répartissent en 3 catégories à traiter différemment :

### Catégorie A — Topics plateforme (identiques, transversaux)
Ces topics traitent de la plateforme Apizee en général, pas d'un produit spécifique.
Slugs concernés : `forgot-password`, `where-are-servers`, `change-subscription`, `cannot-add-user`, `contact-support`, `change-language`, `what-language-is-available`, `how-can-i-switch-dark-light-mode`.

**Traitement** : créer **une seule page canonique** dans `faq/platform/`, et dans chaque section produit qui contenait ce topic, remplacer la page par une **courte page de redirection** :
```markdown
---
description: See the platform FAQ for this topic.
---
# Forgot my password?

{% content-ref url="../../faq/platform/forgot-password.md" %}
[Reset your password](../../faq/platform/forgot-password.md)
{% endcontent-ref %}
```
Ne pas utiliser `{% include %}` pour ces topics : ils sont trop longs et doivent être trouvables via la recherche dans leur section FAQ native.

### Catégorie B — Onboarding commun (quasi-identiques, courts)
Slugs : `log-in-to-the-apizee-portal-for-the-first-time`, `user-roles`, `choose-my-portal-dashboard`, `allow-the-web-browser-to-access-camera`, `audio-video-settings`, `bandwidth-resolution-settings`.

**Traitement** : prendre la version la plus complète (arbitrer par taille de fichier), la placer dans `shared/.gitbook/includes/<slug>.md`, puis dans chaque section la référencer :
```markdown
{% include "../../shared/.gitbook/includes/log-in-first-time.md" %}
```
⚠️ Limitation GitBook : le contenu inclus n'apparaît pas dans la recherche des sections qui l'utilisent (seulement dans l'espace parent). Acceptable pour ces courts topics d'onboarding.

### Catégorie C — Features produit-spécifiques (même slug, contenu différent)
Slugs : `record-the-session`, `share-a-screen`, `share-the-pointer`, `take-a-picture`, `activate-microphone-camera`, etc.

**Traitement** : copie distincte par section. C'est intentionnel — l'UI varie par produit. Ne pas tenter de fusionner.

---

## Règles de conversion ClickHelp → Markdown GitBook

Écrire un script Python `scripts/convert.py`, **idempotent** (peut être rejoué depuis zéro).

1. **BOM** : retirer le BOM UTF-8 (`﻿`) en tête de chaque fichier.
2. **Assets** : 
   - Copier tous les assets référencés vers `.gitbook/assets/` de la section cible (dédupliquer par hash SHA256).
   - Réécrire les chemins `../Storage/<projet>/` → chemin relatif vers `.gitbook/assets/`.
   - Ignorer les assets du dossier `project-content-reuse/` (icônes génériques) : les remplacer lors de la conversion des callouts (voir point 3).
3. **Callouts ClickHelp** : tableaux à 2 colonnes dont la 1re cellule contient une icône de `project-content-reuse/` (info.png, warning.png, prerequis.png, tip.png, alert.png, ok.png…) → convertir en hint GitBook :
   - `info.png` / `prerequis.png` / `ok.png` → `{% hint style="info" %}`
   - `tip.png` → `{% hint style="success" %}`
   - `warning.png` → `{% hint style="warning" %}`
   - `alert.png` / `danger.png` → `{% hint style="danger" %}`
   - Contenu = 2e cellule du tableau. Remplacer les `<br>` par des sauts de ligne.
4. **HTML résiduel** : convertir `<b>` → `**`, `<i>` → `_`, supprimer les styles inline `style="..."`. Conserver les `<br>` dans les cellules de tableau (GitBook les supporte).
5. **Liens internes** : 
   - Construire d'abord une **table de mapping globale** `(archive_source, slug_topic)` → `(section_cible, chemin_relatif)` à partir de tous les `toc.yaml`.
   - Réécrire tous les liens `[texte](../MD/<slug>.md)` ou `[texte](https://doc.apizee.com/articles/<pub>/<slug>)` vers les nouveaux chemins relatifs.
   - Liens vers archives non migrées → conserver l'URL `doc.apizee.com` et loguer dans le rapport.
6. **Pages conteneurs** (entrée TOC avec `children` mais sans `file`) → créer un `README.md` de groupe avec : titre H1, liste de liens vers les enfants directs.
7. **Slugs** : conserver les slugs ClickHelp comme noms de fichiers (important pour les redirections). Pour les enfants dans un sous-dossier, le dossier porte le slug du parent.
8. **Includes catégorie B** : après conversion, remplacer le contenu des pages identifiées en catégorie B par la directive `{% include %}` correspondante. Créer les fichiers dans `shared/.gitbook/includes/` (version la plus complète).
9. **SUMMARY.md** par section : respecter l'ordre et la hiérarchie du `toc.yaml`, préfixé par les groupes de rôle. Exemple pour `video-assistance` :
   ```markdown
   # Summary
   ## For agents
   * [About video assistance](agents/about-apizee-video-assistance.md)
   * [Start a video assistance](agents/create-a-ticket-send-an-invitation.md)
     * [Quick invitation by email/SMS](agents/create-a-ticket-quick-invitation-by-email-and-or-sms.md)
   ...
   ## For guests
   ...
   ## For administrators
   ...
   ## For IT operators
   ...
   ```
10. **Table de redirections** `REDIRECTS.csv` (colonne A : URL source `https://doc.apizee.com/articles/<pub>/<slug>`, colonne B : nouveau chemin GitBook) pour TOUS les topics migrés.

---

## Déroulé pas à pas

**Étape 0 — Poser les questions bloquantes AVANT de commencer**
- Que faire de `customer-engagement-admin-en` (57 topics) et `diag-help-desk-user` (52 topics) ? Les archiver dans un dossier `_unassigned/` ou les inclure dans une section existante ?

**Étape 1 — Inventaire global**
Parser tous les `toc.yaml` → générer `INVENTAIRE.csv` : archive, slug, titre, chemin fichier, section cible, groupe de rôle, catégorie doublon (A/B/C/-). Signaler les topics présents dans `MD/` mais absents du `toc.yaml` (orphelins → groupe `_unsorted` en fin de section).

**Étape 2 — Identifier les includes (catégorie B)**
Pour chaque slug catégorie B, identifier la version la plus complète (taille maximale), la copier dans `shared/.gitbook/includes/`, noter dans l'inventaire les archives où elle sera injectée via `{% include %}`.

**Étape 3 — Conversion section par section** (ordre recommandé : `faq` d'abord pour valider la chaîne, puis `video-assistance`, puis les autres)
Pour chaque section : convertir toutes les archives assignées, appliquer les règles 1-10, générer `SUMMARY.md` et `.gitbook.yaml`.

**Étape 4 — QA automatique** (corriger puis re-vérifier)
- 0 lien interne cassé (chemins résolus)
- 0 image manquante (assets copiés)
- 0 fichier .md vide
- 0 reste de syntaxe ClickHelp (`Storage/`, BOM `﻿`, `DXR.axd`, `style="`)
- Compte de pages par section = entrées TOC + orphelins (rapport)
- Tous les `{% include %}` pointent vers des fichiers existants dans `shared/.gitbook/includes/`

**Étape 5 — Rapport final `RAPPORT-migration.md`**
- Volumétrie par section (topics convertis / orphelins / skippés)
- Includes créés et utilisés (liste avec nombre d'usages)
- Topics catégorie A avec leur page canonique FAQ et la liste des sections pointant vers elle
- Liens externes non migrés
- Archives non traitées
- Décisions restantes pour Romain

**Étape 6 — Présenter à Romain** : le rapport + 3 pages échantillon (une avec hints, une avec includes, une avec hiérarchie profonde + images) **avant** tout import GitBook.

---

## Contraintes
- Lire les archives en lecture seule, ne jamais modifier les dossiers `*-exported/`.
- Le script est rejoué par `rm -rf gitbook-export && python scripts/convert.py` → même résultat.
- En cas d'ambiguïté (structure, rattachement), poser la question plutôt que de décider seul.
- Commencer par l'étape 0 (questions bloquantes), puis l'étape 1 (inventaire) avant toute conversion.
