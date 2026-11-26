# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    judo_monthly_fee = fields.Monetary(
        string='Cotisation mensuelle par défaut',
        currency_field='currency_id',
        default=7500.0,
        help='Montant proposé comme cotisation mensuelle à chaque nouvelle adhésion.',
    )
    judo_reminder_days = fields.Integer(
        string='Délai entre deux rappels (jours)',
        default=7,
        help='Un rappel n\'est renvoyé au même adhérent qu\'après ce délai.',
    )
    judo_due_day = fields.Integer(
        string='Jour d\'échéance des cotisations', default=10,
        help='Les cotisations du mois sont payables avant ce jour (ex. 10).')
    judo_grade_fee = fields.Monetary(
        string='Frais de passage de grade', currency_field='currency_id', default=5000.0)
    judo_invoice_note = fields.Text(
        string='Mention en pied de facture',
        help='Texte ajouté aux factures du club (ex : conditions de paiement).',
    )
    judo_bank_details = fields.Text(
        string='Coordonnées bancaires',
        help='RIB ou références de paiement affichées sur les factures.',
    )
