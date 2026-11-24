# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class JudoTransactionReceipt(models.Model):
    _inherit = 'judo.transaction'

    def action_create_receipt(self):
        """Crée un reçu pour une recette (ou un remboursement reçu)."""
        Receipt = self.env['judo.receipt']
        receipts = Receipt
        for tx in self:
            if tx.type not in ('income', 'refund_in'):
                raise UserError(_("Seules les recettes peuvent donner lieu à un reçu."))
            receipts |= Receipt.create({
                'company_id': tx.company_id.id,
                'date': tx.date,
                'member_id': tx.member_id.id or False,
                'payer_name': tx.partner_id.name or False,
                'transaction_id': tx.id,
                'note': tx.reference or False,
                'line_ids': [(0, 0, {'label': tx.name, 'quantity': 1.0, 'unit_price': tx.amount})],
            })
        return Receipt._action_open(receipts)


class JudoBillableReceipt(models.AbstractModel):
    """Ajoute l'émission de reçus aux cotisations et licences (via judo.billable.mixin)."""
    _inherit = 'judo.billable.mixin'

    def action_create_receipts(self):
        """Un reçu par adhérent, avec une ligne par cotisation ou licence sélectionnée."""
        Receipt = self.env['judo.receipt']
        receipts = Receipt
        for member in self.mapped('member_id'):
            items = self.filtered(lambda b: b.member_id == member and b.state != 'cancelled')
            if not items:
                continue
            receipts |= Receipt.create({
                'company_id': items[0].company_id.id,
                'member_id': member.id,
                'line_ids': [(0, 0, {'label': i.name, 'quantity': 1.0, 'unit_price': i.amount})
                             for i in items],
            })
        if not receipts:
            raise UserError(_("Aucun élément valide : les éléments annulés sont ignorés."))
        return Receipt._action_open(receipts)
