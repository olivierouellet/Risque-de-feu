# Contribuer · Contributing

**[Français](#français) · [English](#english)**

---

## Français

Merci de votre intérêt! En participant, vous acceptez le [code de conduite](CODE_OF_CONDUCT.md). Vous utilisez l’IA? Lisez la [politique sur l’IA](AI_POLICY.md).
Les issues et les demandes de tirage sont bienvenues en français ou en anglais.

### Installation

```bash
uv venv --python 3.13
uv pip install -r requirements_test.txt
pytest
ruff check && ruff format --check
```

Les tests n’appellent jamais le vrai service : ils utilisent des réponses enregistrées dans
`tests/fixtures/`. Pour en enregistrer une nouvelle (`test=true` donne les cinq niveaux et au moins
une mesure de chaque type) :

```bash
curl -o tests/fixtures/danger_test_zone_6.json "https://geofeux.sopfeu.qc.ca/sopfeu-api/public/danger-incendie?noZdi=6&test=true"
```

Les types de mesures préventives sont exclus par défaut : ajoutez `ifco=true` (interdiction de
feux), `rtf24=true`, etc. Voir la [documentation de l’API](https://geofeux.sopfeu.qc.ca/sopfeu-api/swagger/index.html).

### Conventions

* **Le français d’abord.** Toute documentation est bilingue, avec la section française en premier.
* **Textes de l’interface** : `strings.json` (anglais), copié tel quel dans `translations/en.json`, et
  `translations/fr.json`. Un test vérifie que les trois ont les mêmes clés.
* **La logique des jours** est dans `danger.py` et suit les mêmes règles que la carte
  (`src/danger.ts` dans [Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte)) :
  changer l’une, c’est changer l’autre.
* **Commits** : `[Sujet] Ce qui a changé`, un sujet par commit (par exemple `[Integration]`, `[Docs]`, `[Tooling]`).
* **Le danger reste celui de la SOPFEU.** L’intégration ne calcule ni ne corrige le danger publié.

---

## English

Thanks for your interest! By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Using AI tools? Read the [AI policy](AI_POLICY.md).
Issues and pull requests are welcome in French or English.

### Setup

```bash
uv venv --python 3.13
uv pip install -r requirements_test.txt
pytest
ruff check && ruff format --check
```

Tests never call the real service: they use responses recorded in `tests/fixtures/`. To record a
new one (`test=true` returns all five levels and at least one measure of each type):

```bash
curl -o tests/fixtures/danger_test_zone_6.json "https://geofeux.sopfeu.qc.ca/sopfeu-api/public/danger-incendie?noZdi=6&test=true"
```

Preventive measure types are excluded by default: add `ifco=true` (fire ban), `rtf24=true`, and so
on. See the [API documentation](https://geofeux.sopfeu.qc.ca/sopfeu-api/swagger/index.html).

### Conventions

* **French first.** All documentation is bilingual, with the French section first.
* **Interface text**: `strings.json` (English), copied as is to `translations/en.json`, and
  `translations/fr.json`. A test checks that all three have the same keys.
* **The day logic** is in `danger.py` and follows the same rules as the card
  (`src/danger.ts` in [Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte)):
  change one, change the other.
* **Commits**: `[Topic] What changed`, one topic each (for example `[Integration]`, `[Docs]`, `[Tooling]`).
* **The danger stays SOPFEU’s.** The integration never computes or corrects the published danger.
