# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

PAYMENT_METHODS = [
    ('cash', 'Espèces'),
    ('mobile', 'Mobile money'),
    ('transfer', 'Virement'),
    ('cheque', 'Chèque'),
    ('card', 'Carte'),
]


class JudoReceipt(models.Model):
    """Reçu de paiement, imprimable en ticket de caisse. Numéro propre à chaque club."""
    _name = 'judo.receipt'
    _description = 'Reçu / ticket de caisse'
    _order = 'date desc, id desc'

    name = fields.Char(string='N° de reçu', readonly=True, copy=False, default='/', index=True)
    company_id = fields.Many2one(
        'res.company', string='Club (société)', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    member_id = fields.Many2one('judo.member', string='Adhérent', ondelete='set null')
    payer_name = fields.Char(string='Payé par',
                             help='Nom du payeur si ce n\'est pas un adhérent.')
    payment_method = fields.Selection(PAYMENT_METHODS, string='Mode de paiement',
                                      default='cash', required=True)
    payment_method_label = fields.Char(compute='_compute_payment_method_label')
    line_ids = fields.One2many('judo.receipt.line', 'receipt_id', string='Désignations', copy=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amount_total',
                                   store=True, currency_field='currency_id')
    transaction_id = fields.Many2one('judo.transaction', string='Transaction liée',
                                     readonly=True, copy=False, ondelete='set null')
    note = fields.Text(string='Notes')
    printed_date = fields.Datetime(string='Dernière impression', readonly=True, copy=False)

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('subtotal'))

    @api.depends('payment_method')
    def _compute_payment_method_label(self):
        labels = dict(PAYMENT_METHODS)
        for rec in self:
            rec.payment_method_label = labels.get(rec.payment_method, '')

    def _next_number(self, company):
        """Numérotation propre à chaque société : REC/<année>/00001, 00002…"""
        Seq = self.env['ir.sequence'].sudo()
        seq = Seq.search([('code', '=', 'judo.receipt'), ('company_id', '=', company.id)], limit=1)
        if not seq:
            seq = Seq.create({
                'name': _('Reçus %s', company.name),
                'code': 'judo.receipt',
                'prefix': 'REC/%(year)s/',
                'padding': 5,
                'company_id': company.id,
            })
        return seq.next_by_id()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                vals['name'] = self._next_number(company)
        return super().create(vals_list)

    def action_print(self):
        """Marque le reçu comme imprimé et lance le ticket."""
        self.ensure_one()
        self.printed_date = fields.Datetime.now()
        return self.env.ref('judo_receipt.action_report_judo_receipt').report_action(self)

    @api.model
    def _action_open(self, receipts):
        if len(receipts) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'judo.receipt',
                'res_id': receipts.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reçus créés'),
            'res_model': 'judo.receipt',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', receipts.ids)],
            'target': 'current',
        }


class JudoReceiptLine(models.Model):
    _name = 'judo.receipt.line'
    _description = 'Désignation d\'un reçu'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    receipt_id = fields.Many2one('judo.receipt', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='receipt_id.company_id', store=True)
    currency_id = fields.Many2one(related='receipt_id.currency_id')
    label = fields.Char(string='Désignation', required=True)
    quantity = fields.Float(string='Qté', default=1.0, digits='Product Unit of Measure')
    unit_price = fields.Monetary(string='Prix unitaire', currency_field='currency_id')
    subtotal = fields.Monetary(string='Montant', compute='_compute_subtotal', store=True,
                               currency_field='currency_id')

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
