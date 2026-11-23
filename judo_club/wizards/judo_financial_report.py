# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class JudoFinancialReport(models.TransientModel):
    """Situation financière sur une période : compte de résultat, flux de trésorerie
    et solde de clôture. Vue synthétique (non légale) pour le pilotage du club."""
    _name = 'judo.financial.report'
    _description = 'Situation financière du club'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_from = fields.Date(string='Du', required=True,
                            default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(string='Au', required=True, default=fields.Date.context_today)
    bank_account_id = fields.Many2one('judo.bank.account', string='Compte (optionnel)',
                                      domain="[('company_id', '=', company_id)]",
                                      help='Laisser vide pour consolider tous les comptes.')

    # Soldes et flux
    opening_balance = fields.Monetary(string='Solde d\'ouverture', compute='_compute_figures',
                                      currency_field='currency_id')
    cash_in = fields.Monetary(string='Entrées de trésorerie', compute='_compute_figures',
                              currency_field='currency_id')
    cash_out = fields.Monetary(string='Sorties de trésorerie', compute='_compute_figures',
                               currency_field='currency_id')
    cash_flow = fields.Monetary(string='Flux net de la période', compute='_compute_figures',
                                currency_field='currency_id')
    closing_balance = fields.Monetary(string='Solde de clôture', compute='_compute_figures',
                                      currency_field='currency_id')
    # Compte de résultat
    total_income = fields.Monetary(string='Total des recettes', compute='_compute_figures',
                                   currency_field='currency_id')
    total_expense = fields.Monetary(string='Total des dépenses', compute='_compute_figures',
                                    currency_field='currency_id')
    result = fields.Monetary(string='Résultat de la période', compute='_compute_figures',
                             currency_field='currency_id')
    # Éléments de bilan
    refunds_in = fields.Monetary(string='Remboursements reçus', compute='_compute_figures',
                                 currency_field='currency_id')
    refunds_out = fields.Monetary(string='Remboursements versés', compute='_compute_figures',
                                  currency_field='currency_id')
    receivables = fields.Monetary(string='Factures clients à encaisser (à ce jour)',
                                  compute='_compute_figures', currency_field='currency_id')

    @api.depends('company_id', 'date_from', 'date_to', 'bank_account_id')
    def _compute_figures(self):
        Tx = self.env['judo.transaction']
        Bank = self.env['judo.bank.account']
        for rec in self:
            bank_domain = [('company_id', '=', rec.company_id.id)]
            if rec.bank_account_id:
                bank_domain.append(('id', '=', rec.bank_account_id.id))
            banks = Bank.search(bank_domain)

            opening = 0.0
            for bank in banks:
                before = Tx.search([
                    ('bank_account_id', '=', bank.id),
                    ('date', '>=', bank.opening_date),
                    ('date', '<', rec.date_from),
                ])
                opening += bank.opening_balance + sum(before.mapped('signed_amount'))

            txs = Tx.search([
                ('bank_account_id', 'in', banks.ids),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
            ])
            rec.opening_balance = opening
            rec.total_income = sum(txs.filtered(lambda t: t.type == 'income').mapped('amount'))
            rec.total_expense = sum(txs.filtered(lambda t: t.type == 'expense').mapped('amount'))
            rec.result = rec.total_income - rec.total_expense
            rec.refunds_in = sum(txs.filtered(lambda t: t.type == 'refund_in').mapped('amount'))
            rec.refunds_out = sum(txs.filtered(lambda t: t.type == 'refund_out').mapped('amount'))
            rec.cash_in = sum(txs.filtered(lambda t: t.signed_amount > 0).mapped('signed_amount'))
            rec.cash_out = sum(txs.filtered(lambda t: t.signed_amount < 0).mapped('signed_amount'))
            rec.cash_flow = rec.cash_in + rec.cash_out
            rec.closing_balance = opening + rec.cash_flow

            billables = (self.env['judo.fee'].sudo().search([
                ('company_id', '=', rec.company_id.id), ('state', '=', 'invoiced')])
                | self.env['judo.licence'].sudo().search([
                    ('company_id', '=', rec.company_id.id), ('state', '=', 'invoiced')]))
            rec.receivables = sum(billables.mapped('invoice_id').mapped('amount_residual'))

    def action_open_transactions(self):
        self.ensure_one()
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.bank_account_id:
            domain.append(('bank_account_id', '=', self.bank_account_id.id))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transactions de la période'),
            'res_model': 'judo.transaction',
            'view_mode': 'tree,form,graph,pivot',
            'domain': domain,
            'target': 'current',
        }
