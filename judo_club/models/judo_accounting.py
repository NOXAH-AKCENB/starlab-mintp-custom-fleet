# -*- coding: utf-8 -*-
from odoo import api, fields, models

TX_TYPES = [
    ('income', 'Recette'),
    ('expense', 'Dépense'),
    ('refund_in', 'Remboursement reçu'),
    ('refund_out', 'Remboursement versé'),
]


class JudoBankAccount(models.Model):
    _name = 'judo.bank.account'
    _description = 'Compte bancaire ou caisse du club'
    _order = 'name'

    name = fields.Char(string='Compte', required=True, help='Ex : Banque, Caisse, Mobile money')
    opening_date = fields.Date(string='Date du solde d\'ouverture', required=True,
                               default=fields.Date.context_today)
    opening_balance = fields.Monetary(string='Solde d\'ouverture', default=0.0,
                                      currency_field='currency_id')
    company_id = fields.Many2one(
        'res.company', string='Société', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    transaction_ids = fields.One2many('judo.transaction', 'bank_account_id', string='Transactions')
    balance = fields.Monetary(string='Solde actuel', compute='_compute_balance',
                              currency_field='currency_id')

    @api.depends('opening_balance', 'opening_date', 'transaction_ids.signed_amount',
                 'transaction_ids.date')
    def _compute_balance(self):
        for rec in self:
            txs = rec.transaction_ids.filtered(lambda t: t.date >= rec.opening_date)
            rec.balance = rec.opening_balance + sum(txs.mapped('signed_amount'))


class JudoTransactionCategory(models.Model):
    _name = 'judo.transaction.category'
    _description = 'Catégorie de transaction'
    _order = 'type, name'

    name = fields.Char(string='Catégorie', required=True)
    type = fields.Selection(TX_TYPES, string='Sens', required=True, default='expense')


class JudoTransaction(models.Model):
    _name = 'judo.transaction'
    _description = 'Transaction (recette, dépense, remboursement)'
    _order = 'date desc, id desc'
    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)',
         'Le montant doit être positif : le sens est donné par la catégorie.'),
    ]

    name = fields.Char(string='Libellé', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, index=True)
    bank_account_id = fields.Many2one('judo.bank.account', string='Compte', required=True,
                                      ondelete='restrict')
    category_id = fields.Many2one('judo.transaction.category', string='Catégorie', required=True)
    type = fields.Selection(related='category_id.type', store=True, string='Sens')
    company_id = fields.Many2one(related='bank_account_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    signed_amount = fields.Monetary(string='Montant signé', compute='_compute_signed_amount',
                                    store=True, currency_field='currency_id',
                                    help='Positif pour les entrées, négatif pour les sorties.')
    member_id = fields.Many2one('judo.member', string='Adhérent')
    partner_id = fields.Many2one('res.partner', string='Tiers')
    reference = fields.Char(string='Référence', help='N° de chèque, de virement, de reçu…')
    note = fields.Text(string='Notes')

    @api.depends('amount', 'type')
    def _compute_signed_amount(self):
        for rec in self:
            sign = -1 if rec.type in ('expense', 'refund_out') else 1
            rec.signed_amount = sign * rec.amount
