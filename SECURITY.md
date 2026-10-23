# Sécurité · Security Policy

**[Français](#français) · [English](#english)**

---

## Français

### Signaler une vulnérabilité

**N’ouvrez pas d’issue publique.** Signalez-la en privé par GitHub :

* [Signaler une vulnérabilité](https://github.com/olivierouellet/Risque-de-feu/security/advisories/new)
  dans l’onglet **Security** du dépôt, visible seulement par le responsable, ou
* écrivez directement à [@olivierouellet](https://github.com/olivierouellet).

Utile à inclure : la version, ce qu’il faut pour exploiter le problème, et une façon de le reproduire.

C’est un projet à un seul responsable, fait sur son temps libre. Comptez un accusé de réception
d’ici deux semaines; vous saurez où en est la correction. Vous serez crédité dans les notes de
version si vous le souhaitez.

### Versions prises en charge

| Version | Prise en charge |
| --- | --- |
| Dernière version publiée | ✅ |
| `main` | ✅ Les correctifs y arrivent d’abord |
| Versions antérieures | ❌ Mettez à jour avec HACS |

### Surface d’attaque

* L’intégration ne fait que des GET vers l’API publique de la SOPFEU (`geofeux.sopfeu.qc.ca`), sans clé ni compte. En mode géolocalisation, les coordonnées du point choisi (au plus cinq décimales, environ un mètre) sont envoyées à chaque mise à jour, toutes les 30 minutes. Choisissez une municipalité ou une zone pour n’envoyer aucune position.
* Les réponses sont traitées comme des données non fiables : seuls des nombres, des dates et des textes courts en sont extraits; les polygones sont ignorés.

---

## English

### Reporting a vulnerability

**Don't open a public issue.** Report privately through GitHub:

* [Report a vulnerability](https://github.com/olivierouellet/Risque-de-feu/security/advisories/new)
  from the repository's **Security** tab, visible only to the maintainer, or
* contact [@olivierouellet](https://github.com/olivierouellet) directly.

Useful to include: the version, what an attacker needs, and a way to reproduce it.

This is a one-maintainer, spare-time project. Expect acknowledgement within 2 weeks, and you'll
be told where the fix stands. Credit in the release notes if you'd like it.

### Supported versions

| Version | Supported |
| --- | --- |
| Latest release | ✅ |
| `main` | ✅ Fixes land here first |
| Earlier releases | ❌ Update through HACS |

### Attack surface

* The integration only makes GET requests to SOPFEU’s public API (`geofeux.sopfeu.qc.ca`), with no key or account. In geolocation mode, the chosen point’s coordinates (at most five decimals, about one metre) are sent with every update, every 30 minutes. Choose a municipality or a zone to send no position at all.
* Responses are treated as untrusted data: only numbers, dates and short texts are taken from them; polygons are ignored.
