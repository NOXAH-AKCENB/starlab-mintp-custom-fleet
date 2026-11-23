# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class JudoInvoiceWizard(models.TransientModel):
    """Crée une facture par contact à partir des cotisations et licences sélectionnées.
    Permet d'appliquer une remise et un frais supplémentaire."""
    _name = 'judo.invoice.wizard'
    _description = 'Facturation des cotisations et licences'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    fee_ids = fields.Many2many('judo.fee', 'judo_invoice_wiz_fee_rel', 'wizard_id', 'fee_id',
                               string='Cotisations')
    licence_ids = fields.Many2many('judo.licence', 'judo_invoice_wiz_licence_rel', 'wizard_id',
                                   'licence_id', string='Licences')
    invoice_date = fields.Date(string='Date de facture', required=True,
                               default=fields.Date.context_today)
    invoice_date_due = fields.Date(
        string='Échéance', required=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=30))
    discount_percent = fields.Float(string='Remise (%)', digits=(5, 2), default=0.0,
                                    help='Appliquée aux cotisations et licences.')
    extra_label = fields.Char(string='Frais supplémentaire (libellé)',
                              help='Ajouté une fois à chaque facture créée.')
    extra_amount = fields.Monetary(string='Montant du frais supplémentaire',
                                   currency_field='currency_id')
    note = fields.Text(string='Mention sur la facture',
                       default=lambda self: self.env.company.judo_invoice_note)

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        if active_model == 'judo.fee':
            fees = self.env['judo.fee'].browse(active_ids).filtered(lambda f: f.state == 'to_invoice')
            res['fee_ids'] = [(6, 0, fees.ids)]
        elif active_model == 'judo.licence':
            licences = self.env['judo.licence'].browse(active_ids).filtered(
                lambda l: l.state == 'to_invoice')
            res['licence_ids'] = [(6, 0, licences.ids)]
        return res

    def _line(self, product, label, price, discount=0.0):
        return (0, 0, {
            'product_id': product.id,
            'name': label,
            'quantity': 1.0,
            'price_unit': price,
            'discount': discount,
        })

    def _narration(self):
        parts = [p for p in (self.note, self.company_id.judo_bank_details) if p]
        return '\n'.join(parts) or False

    def action_create_invoices(self):
        self.ensure_one()
        if not 0 <= self.discount_percent <= 100:
            raise UserError(_("La remise doit être comprise entre 0 et 100 %."))

        fees = self.fee_ids.filtered(lambda f: f.state == 'to_invoice')
        licences = self.licence_ids.filtered(lambda l: l.state == 'to_invoice')
        if not fees and not licences:
            raise UserError(_("Aucune ligne à facturer. Les éléments déjà facturés sont ignorés."))

        journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_("Aucun journal de vente n'est configuré pour cette société."))

        product_fee = self.env.ref('judo_club.product_judo_fee')
        product_licence = self.env.ref('judo_club.product_judo_licence')
        product_extra = self.env.ref('judo_club.product_judo_extra')

        invoices = self.env['account.move']
        partners = (fees | licences).mapped('partner_id')
        for partner in partners:
            p_fees = fees.filtered(lambda f: f.partner_id == partner)
            p_licences = licences.filtered(lambda l: l.partner_id == partner)
            lines = [self._line(product_fee, f.name, f.amount, self.discount_percent) for f in p_fees]
            lines += [self._line(product_licence, l.name, l.amount, self.discount_percent)
                      for l in p_licences]
            if self.extra_amount and self.extra_label:
                lines.append(self._line(product_extra, self.extra_label, self.extra_amount))

            move = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'journal_id': journal.id,
                'company_id': self.company_id.id,
                'invoice_date': self.invoice_date,
                'invoice_date_due': self.invoice_date_due,
                'narration': self._narration(),
                'invoice_line_ids': lines,
            })
            p_fees.write({'invoice_id': move.id})
            p_licences.write({'invoice_id': move.id})
            invoices |= move

        return {
            'type': 'ir.actions.act_window',
            'name': _('Factures créées'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'target': 'current',
        }
