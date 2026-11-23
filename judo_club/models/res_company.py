# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    judo_monthly_fee = fields.Monetary(
        string='Cotisation mensuelle par défaut',
        currency_field='currency_id',
        default=0.0,
        help='Montant proposé comme cotisation mensuelle à chaque nouvelle adhésion.',
    )
    judo_reminder_days = fields.Integer(
        string='Délai entre deux rappels (jours)',
        default=7,
        help='Un rappel n\'est renvoyé au même adhérent qu\'après ce délai.',
    )
    judo_invoice_note = fields.Text(
        string='Mention en pied de facture',
        help='Texte ajouté aux factures du club (ex : conditions de paiement).',
    )
    judo_bank_details = fields.Text(
        string='Coordonnées bancaires',
        help='RIB ou références de paiement affichées sur les factures.',
    )
