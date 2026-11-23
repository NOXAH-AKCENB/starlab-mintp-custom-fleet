# -*- coding: utf-8 -*-
from odoo import fields, models


class JudoSeason(models.Model):
    _name = 'judo.season'
    _description = 'Saison sportive'
    _order = 'date_start desc'

    name = fields.Char(string='Saison', required=True, help='Ex : 2026-2027')
    date_start = fields.Date(string='Début', required=True)
    date_end = fields.Date(string='Fin', required=True)
    licence_amount = fields.Monetary(
        string='Montant de la licence', currency_field='currency_id',
        help='Montant de la licence fédérale pour cette saison.')
    company_id = fields.Many2one(
        'res.company', string='Société', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('dates_check', 'CHECK(date_end > date_start)',
         'La fin de saison doit être postérieure à son début.'),
    ]
