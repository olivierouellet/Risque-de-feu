<p align="center">
  <img src="https://raw.githubusercontent.com/olivierouellet/Risque-de-feu/main/assets/icon.svg" alt="Logo de Risque de feu" width="128" height="128">
</p>

<h1 align="center">Risque de feu</h1>

<p align="center">Le danger d’incendie de forêt au Québec dans Home Assistant · Québec’s forest fire danger in Home Assistant</p>

<p align="center"><b><a href="#français">Français</a> · <a href="#english">English</a></b></p>

---

## Français

Pendant la saison des feux, la [SOPFEU](https://www.sopfeu.qc.ca/) publie chaque jour le **danger d’incendie** de 64 zones du Québec, sur cinq niveaux : **bas, modéré, élevé, très élevé et extrême**, pour aujourd’hui, demain et après-demain. Elle décrète aussi des **mesures préventives**, dont l’interdiction de faire des feux à ciel ouvert. Risque de feu les suit pour vous dans Home Assistant et vous permet d’**afficher une carte seulement quand le risque est réel**.

Le projet comporte deux parties :

| Partie | Dépôt | Rôle |
|---|---|---|
| **Intégration Risque de feu** (`risque_de_feu`) | ce dépôt | Choisissez un endroit : géolocalisation, municipalité ou zone de la SOPFEU. Crée les capteurs de danger des trois jours, un capteur d’interdiction de feux et un capteur *Alerte* pour la visibilité des cartes. |
| **Risque-de-feu-Carte** | [Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte) | Une carte de tableau de bord : le niveau du jour sur l’échelle de la SOPFEU, les trois jours, l’interdiction de feux et les autres mesures en vigueur. En français et en anglais. |

### Fonctionnalités

- **Configuration dans l’interface** : *Paramètres → Appareils et services → Ajouter une intégration → Risque de feu*, puis choisissez comment trouver l’endroit :
  - **Géolocaliser** : un point sur la carte, l’emplacement de votre domicile au départ. La SOPFEU trouve la zone de ce point, et les mesures préventives sont celles qui s’appliquent exactement là. Un point hors du Québec est refusé.
  - **Municipalité** : tapez pour chercher parmi les 1 300 municipalités; celle de votre domicile est déjà choisie. Une grande municipalité (La Tuque, Eeyou Istchee Baie-James) peut couvrir plusieurs zones : les capteurs montrent alors le **danger le plus élevé**, et chaque zone est dans les attributs.
  - **Zone de la SOPFEU** : l’une des 64 zones de danger d’incendie; celle de votre domicile est déjà choisie.
- **Plusieurs endroits** : ajoutez l’intégration une fois par endroit (la maison, le chalet).
- **Seuil d’alerte** (*Élevé* par défaut) et, en option, l’alerte pendant une **interdiction de feux**, peu importe le danger. Changez-les plus tard avec *Configurer*.
- Le danger et les mesures sont vérifiés toutes les 30 minutes. À minuit, « aujourd’hui » passe au jour suivant du calcul de la SOPFEU sans attendre un nouveau calcul. Si le service est injoignable, les dernières données sont conservées.
- Hors saison, quand la SOPFEU ne publie plus de danger récent, les capteurs de danger passent à *inconnu* et l’alerte s’éteint.
- Interface en français et en anglais.

### Capteurs

Les capteurs sont regroupés dans un appareil nommé « Risque de feu » suivi de l’endroit. Les identifiants dépendent de la langue de Home Assistant au moment de l’ajout. En français, pour Saguenay :

| Entité | État | Détails |
|---|---|---|
| `binary_sensor.risque_de_feu_saguenay_alerte` | allumé quand le danger d’aujourd’hui atteint le seuil, ou pendant une interdiction de feux si l’option est cochée | Attributs : `level`, `levels` (3 jours), `threshold`, `fire_ban`, `fire_zones`, `restrictions`, `calculated`. C’est le capteur que lit la carte. |
| `sensor.risque_de_feu_saguenay_danger` | `low`, `moderate`, `high`, `very_high` ou `extreme` (affichés *Bas* à *Extrême*) | Attributs : `level` (1 à 5), `date`, `zones`. |
| `sensor.risque_de_feu_saguenay_danger_demain` | le danger de demain | |
| `sensor.risque_de_feu_saguenay_danger_apres_demain` | le danger d’après-demain | |
| `binary_sensor.risque_de_feu_saguenay_interdiction_de_feux` | allumé pendant une interdiction de faire des feux à ciel ouvert en forêt ou à proximité | Attribut `restrictions` : toutes les mesures en vigueur (interdiction, restrictions de travaux en forêt, fermetures, etc.) avec leurs dates. |

En anglais : `binary_sensor.risque_de_feu_saguenay_alert`, `sensor.risque_de_feu_saguenay_danger`, `sensor.risque_de_feu_saguenay_danger_tomorrow`, `sensor.risque_de_feu_saguenay_danger_day_after_tomorrow`, `binary_sensor.risque_de_feu_saguenay_fire_ban`.

### Afficher une carte seulement quand le risque est réel

**N’importe quelle carte** : dans l’onglet *Visibilité* de la carte, ajoutez une condition *État de l’entité* sur *Alerte* = *Dangereux* (allumé). En YAML :

```yaml
visibility:
  - condition: state
    entity: binary_sensor.risque_de_feu_saguenay_alerte
    state: "on"
```

Pour un autre seuil sur une seule carte, utilisez le niveau directement :

```yaml
visibility:
  - condition: state
    entity: sensor.risque_de_feu_saguenay_danger
    state: [very_high, extreme]
```

**Risque-de-feu-Carte** a aussi son option *Masquer la carte sous le seuil d’alerte*.

Pour une jauge ou un graphique, l’attribut `level` donne le niveau en chiffre (1 à 5) :

```yaml
template:
  - sensor:
      - name: Niveau de danger
        state: "{{ state_attr('sensor.risque_de_feu_saguenay_danger', 'level') }}"
```

### Installation

**Avec HACS (recommandé)**

[![Ouvrir votre instance Home Assistant et ce dépôt dans HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=olivierouellet&repository=Risque-de-feu&category=integration)

1. Dans Home Assistant, ouvrez **HACS** → **⋮** (en haut à droite) → **Dépôts personnalisés**.
2. Dépôt : `https://github.com/olivierouellet/Risque-de-feu`, type : **Intégration**, puis **Ajouter**. (Le bouton ci-dessus fait les étapes 1 et 2 pour vous.)
3. Cherchez **Risque de feu**, ouvrez-la et cliquez sur **Télécharger**.
4. Redémarrez Home Assistant.
5. Ajoutez l’intégration : *Paramètres → Appareils et services → Ajouter une intégration → Risque de feu*.

**Manuellement** : copiez `custom_components/risque_de_feu` dans le dossier `config/custom_components/` de Home Assistant, redémarrez, puis ajoutez l’intégration comme à l’étape 5.

**La carte** : installez [Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte) de la même façon, comme dépôt personnalisé HACS de type **Dashboard**.

### Développement

- Tests : `uv venv && uv pip install -r requirements_test.txt`, puis `pytest` (Python 3.13). Ils utilisent des réponses enregistrées du service dans `tests/fixtures`.
- Style : `ruff check` et `ruff format`.
- L’icône est dans `custom_components/risque_de_feu/brand/` (Home Assistant 2026.3 ou plus récent l’affiche). Sa source est `assets/icon.svg`; après l’avoir modifiée, exportez `icon@2x.png` en 512 × 512 et `icon.png` en 256 × 256.
- Voir [CONTRIBUTING.md](CONTRIBUTING.md).

Données : [API publique de la SOPFEU](https://geofeux.sopfeu.qc.ca/sopfeu-api/swagger/index.html) (Société de protection des forêts contre le feu). La référence reste le site de la SOPFEU : [danger d’incendie](https://www.sopfeu.qc.ca/prevention/danger-incendie/) et [mesures préventives](https://www.sopfeu.qc.ca/prevention/mesures-preventives-et-restrictions/). Les municipalités peuvent aussi interdire les feux sur leur territoire : vérifiez auprès de la vôtre. Risque de feu n’est pas affilié à la SOPFEU ni au gouvernement du Québec.

---

## English

During the fire season, [SOPFEU](https://www.sopfeu.qc.ca/en/) (Québec’s forest fire protection agency) publishes the **fire danger** of 64 zones every day, on five levels: **low, moderate, high, very high and extreme**, for today, tomorrow and the day after. It also orders **preventive measures**, including bans on open fires. Risque de feu (*fire risk*) follows them for you in Home Assistant and lets you **show a card only when the risk is real**.

It has two parts:

| Part | Repository | What it does |
|---|---|---|
| **Risque de feu integration** (`risque_de_feu`) | this one | Pick a place: geolocation, municipality or SOPFEU zone. Creates danger sensors for the three days, a fire ban sensor and an *Alert* sensor for card visibility. |
| **Risque-de-feu-Carte** | [Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte#english) | A dashboard card: today’s level on SOPFEU’s scale, the three days, the fire ban and the other measures in effect. In French and English. |

### Features

- **Set up from the UI**: *Settings → Devices & services → Add integration → Risque de feu*, then choose how to find the place:
  - **Geolocate**: a point on the map, your home location to start with. SOPFEU finds that point’s zone, and the preventive measures are the ones that apply exactly there. A point outside Québec is refused.
  - **Municipality**: type to search the 1,300 municipalities; your home’s is already chosen. A large municipality (La Tuque, Eeyou Istchee Baie-James) can span several zones: the sensors then show the **highest danger**, with each zone in the attributes.
  - **SOPFEU zone**: one of the 64 fire danger zones; your home’s is already chosen.
- **Several places**: add the integration once per place (home, cottage).
- **Alert threshold** (*High* by default) and, optionally, an alert during a **fire ban** whatever the danger. Change them later under *Configure*.
- The danger and measures are checked every 30 minutes. At midnight, “today” moves to the next day of SOPFEU’s calculation without waiting for a new one. If the service can’t be reached, the last data is kept.
- Off season, when SOPFEU no longer publishes a recent danger, the danger sensors become *unknown* and the alert turns off.
- Interface in French and English.

### Sensors

The sensors are grouped in a device named “Risque de feu” followed by the place. Entity IDs depend on Home Assistant’s language when the integration is added. In English, for Saguenay:

| Entity | State | Details |
|---|---|---|
| `binary_sensor.risque_de_feu_saguenay_alert` | on when today’s danger reaches the threshold, or during a fire ban if that option is on | Attributes: `level`, `levels` (3 days), `threshold`, `fire_ban`, `fire_zones`, `restrictions`, `calculated`. The card reads this sensor. |
| `sensor.risque_de_feu_saguenay_danger` | `low`, `moderate`, `high`, `very_high` or `extreme` | Attributes: `level` (1 to 5), `date`, `zones`. |
| `sensor.risque_de_feu_saguenay_danger_tomorrow` | tomorrow’s danger | |
| `sensor.risque_de_feu_saguenay_danger_day_after_tomorrow` | the day after’s danger | |
| `binary_sensor.risque_de_feu_saguenay_fire_ban` | on during a ban on open fires in or near the forest | Attribute `restrictions`: every measure in effect (fire ban, forestry restrictions, closures, and so on) with its dates. |

In French: `binary_sensor.risque_de_feu_saguenay_alerte`, `sensor.risque_de_feu_saguenay_danger`, `sensor.risque_de_feu_saguenay_danger_demain`, `sensor.risque_de_feu_saguenay_danger_apres_demain`, `binary_sensor.risque_de_feu_saguenay_interdiction_de_feux`.

### Show a card only when the risk is real

**Any card**: in the card’s *Visibility* tab, add an *Entity state* condition on *Alert* = *Unsafe* (on). In YAML:

```yaml
visibility:
  - condition: state
    entity: binary_sensor.risque_de_feu_saguenay_alert
    state: "on"
```

For another threshold on a single card, use the level directly:

```yaml
visibility:
  - condition: state
    entity: sensor.risque_de_feu_saguenay_danger
    state: [very_high, extreme]
```

**Risque-de-feu-Carte** also has a *Hide the card below the alert threshold* option.

For a gauge or a graph, the `level` attribute gives the level as a number (1 to 5):

```yaml
template:
  - sensor:
      - name: Fire danger level
        state: "{{ state_attr('sensor.risque_de_feu_saguenay_danger', 'level') }}"
```

### Installation

**With HACS (recommended)**

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=olivierouellet&repository=Risque-de-feu&category=integration)

1. In Home Assistant, open **HACS** → **⋮** (top right) → **Custom repositories**.
2. Repository: `https://github.com/olivierouellet/Risque-de-feu`, type: **Integration**, then **Add**. (The button above does steps 1 and 2 for you.)
3. Search for **Risque de feu**, open it and click **Download**.
4. Restart Home Assistant.
5. Add the integration: *Settings → Devices & services → Add integration → Risque de feu*.

**Manually:** copy `custom_components/risque_de_feu` into your Home Assistant `config/custom_components/` folder, restart, and add the integration as in step 5.

**The card:** install [Risque-de-feu-Carte](https://github.com/olivierouellet/Risque-de-feu-Carte#english) the same way, as a HACS custom repository of type **Dashboard**.

### Development

- Tests: `uv venv && uv pip install -r requirements_test.txt`, then `pytest` (Python 3.13). They use recorded service responses in `tests/fixtures`.
- Style: `ruff check` and `ruff format`.
- The icon lives in `custom_components/risque_de_feu/brand/` (Home Assistant 2026.3 or later shows it). Its source is `assets/icon.svg`; after editing it, export `icon@2x.png` at 512×512 and `icon.png` at 256×256.
- See [CONTRIBUTING.md](CONTRIBUTING.md).

Data: [SOPFEU public API](https://geofeux.sopfeu.qc.ca/sopfeu-api/swagger/index.html) (Société de protection des forêts contre le feu). The reference remains SOPFEU’s website: [fire danger](https://www.sopfeu.qc.ca/en/prevention/fire-danger-index/) and [preventive measures](https://www.sopfeu.qc.ca/en/prevention/preventive-measures-and-restrictions/). Municipalities can also ban fires on their territory: check with yours. Risque de feu is not affiliated with SOPFEU or the Government of Québec.
