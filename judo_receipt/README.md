# Club de Judo – Reçus et tickets de caisse

Module complémentaire de `judo_club` (Odoo 17 Community). Il permet d'émettre des reçus numérotés
et de les imprimer en **ticket de caisse 80 mm** (imprimante thermique ou papier standard).

## Fonctionnalités

- **Reçu** : numéro propre à chaque club (`REC/2026/00001`, repart à 00001 pour chaque société),
  adhérent ou payeur, mode de paiement, désignations avec quantité et montant, total.
- **Depuis une recette** : bouton *Créer le reçu (ticket)* sur la transaction (recette ou remboursement reçu).
- **Depuis les cotisations ou licences** : sélectionner une ou plusieurs lignes → *Action → Créer le reçu (ticket)*.
  Un reçu est créé par adhérent, avec une ligne par élément.
- **Impression** : bouton *Imprimer le ticket* sur le reçu (PDF au format 80 mm, à imprimer sur l'imprimante thermique).
- Menu : Comptabilité → Reçus et tickets.

## Installation

1. `judo_club` doit être installé (et à jour).
2. Copier le dossier `judo_receipt/` dans `addons_path`.
3. Applications → « Reçus » → **Installer** (ou `odoo -d <base> -i judo_receipt --stop-after-init`).
4. Tests : `odoo -d <base> -i judo_receipt --test-tags /judo_receipt --stop-after-init`.

## Limites

- Impression via le navigateur (PDF 80 mm). L'impression directe ESC/POS n'est pas incluse.
- Un reçu n'est pas modifiable une fois imprimé : prévoir une annulation/avoir (non inclus).
- Le numéro n'est attribué qu'à la création du reçu.
