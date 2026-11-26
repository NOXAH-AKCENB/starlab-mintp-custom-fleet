# Journal des modifications – Club de judo

Chaque modification du module est notée ici et répercutée dans le guide utilisateur (`docs/guide_utilisateur.md`).

## [17.0.1.3.0] – 2026-11-26

### Ajouté
- Catégories d'âge calculées sur la fiche adhérent, plages modifiables.
- Matériel : articles, stock (achats, ventes, inventaire), encaissement automatique des ventes, case « Kimono vendu ».
- Location de salle : salles, réservations de créneaux avec contrôle de conflit, facturation.
- Montants de départ (à remplacer) : cotisation 7 500, licence 12 500, passage de grade 5 000, location 15 000 par heure.

## [17.0.1.2.0] – 2026-11-26

### Ajouté
- Familles, photos et vue kanban des adhérents ; relances PDF par adhérent ou famille.
- Échéance des cotisations au 10 du mois (configurable).
- Passages de grade : sessions, fiche d'évaluation, facturation, promotion et procès-verbal archivé.
- États par catégorie (PDF et Excel).

## [17.0.1.1.0] – 2026-11-24

### Ajouté
- Tableau de bord : choix d'une période, puis export **PDF** (relevé), **Excel** (3 onglets : synthèse, mensuel, transactions) ou **ticket de caisse 80 mm** (situation résumée).
- Assistant « Situation financière » : boutons d'impression ticket et d'export Excel.
- Dépendance Python déclarée : `xlsxwriter`.
- Export Excel : onglet *Indicateurs* (adhérents, montant non réglé, à facturer, retards, solde des comptes) à la date de l'export.

## [17.0.1.0.0] – 2026-11-23

### Ajouté
- Adhérents, catégories, ceinture, contact comptable automatique.
- Saisons, adhésions, renouvellement et désistement.
- Cours, groupes, inscriptions avec contrôle de capacité.
- Cotisations mensuelles (génération idempotente, automatique chaque jour).
- Licences par adhésion.
- Facturation par contact : remise, frais supplémentaire, mention, coordonnées bancaires.
- Rappels e-mail pour cotisations échues et licences à facturer.
- Comptes et caisses, transactions (recettes, dépenses, remboursements).
- Situation financière (compte de résultat, trésorerie, remboursements, créances).
- Graphiques et tableau croisé recettes / dépenses par mois.
- Groupes de droits : Secrétariat, Trésorier, Administrateur.
- Tests unitaires du module.
- Guide utilisateur illustré (version 0.2).

### Ajouté (suite)
- **Relevé financier en PDF** depuis la situation financière (détail mensuel et liste des transactions).
- **Tableau de bord** en composant OWL : indicateurs, graphique 12 mois, dernières transactions.

### Multi-société
- Chaque club est une société Odoo ; toutes les données (adhérents, saisons, adhésions, cours, cotisations, licences, comptes, transactions, catégories) portent une société.
- Règles d'accès par société : un utilisateur ne voit que les clubs qu'il a sélectionnés dans le sélecteur de sociétés.
- Contrôle de cohérence entre sociétés : impossible de relier un adhérent d'un club à la saison ou au cours d'un autre.
- Cron (cotisations, rappels) exécuté club par club, dans le contexte de chaque société.
- Tableau de bord limité à la société courante.
- Test d'isolation entre deux clubs.

### Limites connues
- Pas encore de captures d'écran dans le guide (à faire sur une instance installée).
- Les paiements Odoo ne sont pas recopiés automatiquement dans les transactions du club.
- Module non encore exécuté sur une instance Odoo 17 réelle : validation statique seulement.
