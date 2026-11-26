# -*- coding: utf-8 -*-
from odoo import api, fields, models


class JudoFamily(models.Model):
    """Regroupement d'adhérents de la même famille : suivi des impayés et relance par famille."""
    _name = 'judo.family'
    _description = 'Famille'
    _order = 'name'

    company_id = fields.Many2one(
        'res.company', string='Club (société)', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    name = fields.Char(string='Nom de la famille', required=True)
    responsible_name = fields.Char(string='Responsable légal')
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    quartier = fields.Char(string='Quartier')
    member_ids = fields.One2many('judo.member', 'family_id', string='Membres')
    member_count = fields.Integer(string='Membres', compute='_compute_totals')
    amount_due = fields.Monetary(string='Montant non réglé', compute='_compute_totals',
                                 currency_field='currency_id')

    @api.depends('member_ids.amount_due')
    def _compute_totals(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)
            rec.amount_due = sum(rec.member_ids.mapped('amount_due'))

    def action_print_relance(self):
        self.ensure_one()
        return self.env.ref('judo_club.action_report_relance_family').report_action(self)
