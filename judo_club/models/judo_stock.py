# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MOVE_KINDS = [
    ('purchase', 'Entrée – achat'),
    ('sale', 'Sortie – vente'),
    ('adjust', 'Inventaire (correction)'),
]


class JudoArticle(models.Model):
    """Article vendu par le club (kimonos, ceintures, tee-shirts…)."""
    _name = 'judo.article'
    _description = 'Article (matériel)'
    _order = 'name'

    name = fields.Char(string='Article', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    purchase_price = fields.Monetary(string="Prix d'achat", currency_field='currency_id', default=0.0)
    sale_price = fields.Monetary(string='Prix de vente', currency_field='currency_id', default=0.0)
    is_kimono = fields.Boolean(string='Kimono', help='Une vente à un adhérent coche « Kimono vendu » sur sa fiche.')
    move_ids = fields.One2many('judo.stock.move', 'article_id', string='Mouvements')
    quantity = fields.Float(string='Quantité en stock', compute='_compute_quantity', digits=(12, 2))
    stock_value = fields.Monetary(string='Valeur du stock (achat)', compute='_compute_quantity',
                                  currency_field='currency_id')

    @api.depends('move_ids.signed_qty', 'move_ids.amount', 'purchase_price')
    def _compute_quantity(self):
        for rec in self:
            qty = sum(rec.move_ids.mapped('signed_qty'))
            rec.quantity = qty
            rec.stock_value = qty * rec.purchase_price


class JudoStockMove(models.Model):
    """Mouvement de stock : achat (entrée), vente (sortie avec encaissement) ou inventaire."""
    _name = 'judo.stock.move'
    _description = 'Mouvement de stock'
    _order = 'date desc, id desc'

    article_id = fields.Many2one('judo.article', string='Article', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='article_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    kind = fields.Selection(MOVE_KINDS, string='Type', required=True, default='purchase')
    quantity = fields.Float(string='Quantité', required=True, default=1.0, digits=(12, 2),
                            help='Quantité positive. Pour un inventaire, utiliser une valeur négative pour retirer.')
    signed_qty = fields.Float(string='Variation', compute='_compute_signed', store=True, digits=(12, 2))
    unit_price = fields.Monetary(string='Prix unitaire', currency_field='currency_id', default=0.0)
    amount = fields.Monetary(string='Montant', compute='_compute_signed', store=True,
                             currency_field='currency_id')
    member_id = fields.Many2one('judo.member', string='Adhérent')
    bank_account_id = fields.Many2one('judo.bank.account', string='Encaissé sur')
    category_id = fields.Many2one('judo.transaction.category', string='Catégorie de recette',
                                  domain="[('type', '=', 'income')]")
    transaction_id = fields.Many2one('judo.transaction', string='Transaction créée', readonly=True, copy=False)
    note = fields.Char(string='Note')

    @api.depends('kind', 'quantity', 'unit_price')
    def _compute_signed(self):
        for rec in self:
            sign = -1 if rec.kind == 'sale' else 1
            rec.signed_qty = sign * rec.quantity
            rec.amount = rec.quantity * rec.unit_price

    @api.onchange('kind', 'article_id')
    def _onchange_price(self):
        for rec in self.filtered('article_id'):
            if rec.kind == 'sale':
                rec.unit_price = rec.article_id.sale_price
            elif rec.kind == 'purchase':
                rec.unit_price = rec.article_id.purchase_price

    @api.constrains('article_id', 'kind', 'quantity')
    def _check_stock(self):
        for article in self.mapped('article_id'):
            available = sum(self.search([('article_id', '=', article.id)]).mapped('signed_qty'))
            if available < 0:
                raise ValidationError(_("Stock insuffisant pour « %s » (disponible : %s).",
                                        article.name, available))

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves.filtered(lambda m: m.kind == 'sale' and m.bank_account_id and m.category_id):
            move.transaction_id = self.env['judo.transaction'].create({
                'name': _('Vente : %s', move.article_id.name),
                'date': move.date,
                'bank_account_id': move.bank_account_id.id,
                'category_id': move.category_id.id,
                'amount': move.amount,
                'member_id': move.member_id.id or False,
                'note': move.note or False,
            })
            if move.member_id and move.article_id.is_kimono:
                move.member_id.kimono_sold = True
        return moves
