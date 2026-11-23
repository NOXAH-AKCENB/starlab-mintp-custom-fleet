# Club de Judo – module Odoo 17 Community

Module de gestion d'un club de judo : adhérents, saisons, adhésions, cours,
cotisations mensuelles, licences, facturation, comptabilité simplifiée et
situation financière.

Il couvre le cahier des charges « Logiciel de gestion de club de judo ».

## Installation

1. Installer Odoo 17 Community (modules requis : `base`, `mail`, `account`).
2. Copier le dossier `judo_club/` dans un répertoire présent dans `addons_path`.
3. Redémarrer Odoo, activer le mode développeur, puis :
   **Applications → Mettre à jour la liste → rechercher « Club de judo » → Installer**.
   En ligne de commande : `odoo -d <base> -i judo_club --stop-after-init`.
4. Lancer les tests : `odoo -d <base> -i judo_club --test-tags /judo_club --stop-after-init`.

## Premiers réglages

1. **Paramètres → Société → onglet « Club de judo »** : cotisation mensuelle par défaut,
   délai entre rappels, coordonnées bancaires et mention de pied de facture.
2. **Plan comptable** : un journal de vente doit exister (il est créé avec le plan
   comptable). La facturation s'appuie sur les produits « Cotisation mensuelle judo »,
   « Licence fédérale judo » et « Frais divers du club », créés à l'installation.
3. **Configuration → Saisons** : créer la saison (dates de début et de fin, montant de la licence).
4. **Comptabilité → Comptes et caisses** : créer au moins un compte (banque, caisse, mobile money).
5. **Comptabilité → Catégories de transactions** : ex. « Cotisations » (Recette),
   « Matériel » (Dépense), « Remboursement fédération » (Remboursement reçu).

## Utilisation courante

| Besoin du cahier des charges | Où dans l'application |
|---|---|
| Fiche adhérent (identité, contact, date de naissance) | Adhérents → Adhérents |
| Historique des adhésions, renouvellements, désistements | Fiche adhérent → onglet Adhésions ; Adhésions → boutons « Renouveler » / « Désistement » |
| Regroupement par catégories (enfants, adultes, niveaux…) | Adhérents → Catégories ; ceinture (grade) sur la fiche |
| Inscriptions aux cours, groupes, horaires | Cours → Cours et horaires / Groupes / Inscriptions |
| Cotisations mensuelles calculées et enregistrées | Cotisations → Générer les cotisations du mois (et automatiquement chaque jour) |
| Rappels automatiques des cotisations impayées | Tâche planifiée quotidienne (e-mail au contact) |
| Frais de licence par adhérent et rappels de renouvellement | Cotisations → Licences (rappel quotidien pour les licences non facturées) |
| Factures automatiques, remises, frais supplémentaires, mentions | Cotisations ou Licences → sélectionner → Action → « Facturer… » |
| Saisie quotidienne des recettes, dépenses, remboursements | Comptabilité → Transactions |
| Relevés mensuels/annuels, résultat, flux de trésorerie, bilan simplifié | Comptabilité → Situation financière |
| Graphiques et comparaison recettes / dépenses dans le temps | Comptabilité → Transactions → vues Graphique et Analyse |
| Droits d'accès | Groupes : Secrétariat, Trésorier, Administrateur |

## Droits d'accès

- **Secrétariat** : adhérents, adhésions, cours, inscriptions ; lecture des cotisations et licences.
- **Trésorier** : génération et facturation des cotisations et licences, comptes, transactions, situation financière.
- **Administrateur** : tout, y compris la configuration des saisons et la suppression.

## Cycle de facturation

1. Une adhésion active crée la licence de la saison (montant de la saison).
2. Chaque mois, une cotisation est générée pour chaque adhésion active (idempotent).
3. Le trésorier sélectionne cotisations et/ou licences « À facturer » et lance la
   facturation : une facture par contact, remise optionnelle, frais optionnel.
4. Les paiements se règlent dans la comptabilité Odoo (rapprochement bancaire) ;
   le statut « Payé » des cotisations et licences suit alors automatiquement.
5. Les rappels partent aux contacts ayant une facture échue non payée.

## Limites connues (à traiter dans les versions suivantes)

- Les factures d'un contact sont regroupées : une seule facture par contact et par lancement.
- Les paiements reçus dans Odoo ne créent pas automatiquement une ligne dans le journal
  de transactions du club ; la trésorerie du club se saisit dans **Transactions**.
- La situation financière est une synthèse de pilotage, pas un bilan ni un compte de
  résultat légal : la comptabilité officielle reste dans le module Comptabilité d'Odoo.
- Le modèle de facture reste celui d'Odoo ; seuls la mention et les coordonnées bancaires
  sont personnalisables. Un gabarit QWeb dédié peut être ajouté.
- Pas de paiement en ligne, pas de notification WhatsApp/SMS.

## Documentation

- Guide utilisateur illustré : [`docs/guide_utilisateur.md`](docs/guide_utilisateur.md) (mis à jour à chaque évolution).
- Journal des modifications : [`CHANGELOG.md`](CHANGELOG.md).
- Relevés financiers en PDF : Comptabilité → Situation financière → *Imprimer le relevé (PDF)*.
- Tableau de bord : menu *Club de judo → Tableau de bord*.
- Le partage des revenus ou le préfinancement par la Fédération (cf. chapitre « Moyens de
  financement » du cahier des charges) relèvent du contrat commercial, pas du logiciel.

## Structure

```
judo_club/
├── __manifest__.py
├── models/          # adhérents, saisons, adhésions, cours, cotisations/licences, comptabilité, société
├── wizards/         # facturation, génération des cotisations, situation financière
├── views/           # vues formulaire / liste / recherche / graphique / pivot, menus
├── security/        # groupes et droits d'accès
├── data/            # produits, modèles de mail de rappel, tâches planifiées
└── tests/           # tests unitaires (adhésions, cotisations, remises, situation financière)
```
