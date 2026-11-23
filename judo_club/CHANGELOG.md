# Journal des modifications – Club de judo

Chaque modification du module est notée ici et répercutée dans le guide utilisateur (`docs/guide_utilisateur.md`).

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

### Limites connues
- Pas encore de captures d'écran dans le guide (à faire sur une instance installée).
- Les paiements Odoo ne sont pas recopiés automatiquement dans les transactions du club.
- Module non encore exécuté sur une instance Odoo 17 réelle : validation statique seulement.
