# -*- coding: utf-8 -*-
import base64
import io
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    def _get_transactions(self):
        """Transactions de la période, triées par date (pour le relevé PDF)."""
        self.ensure_one()
        domain = [('date', '>=', self.date_from), ('date', '<=', self.date_to),
                  ('company_id', '=', self.company_id.id)]
        if self.bank_account_id:
            domain.append(('bank_account_id', '=', self.bank_account_id.id))
        return self.env['judo.transaction'].search(domain, order='date asc, id asc')

    def _monthly_breakdown(self):
        """Totaux par mois : recettes, dépenses et flux net."""
        self.ensure_one()
        months = {}
        for tx in self._get_transactions():
            key = tx.date.strftime('%Y-%m')
            row = months.setdefault(key, {'label': tx.date.strftime('%m/%Y'),
                                          'income': 0.0, 'expense': 0.0, 'net': 0.0})
            if tx.type == 'income':
                row['income'] += tx.amount
            elif tx.type == 'expense':
                row['expense'] += tx.amount
            row['net'] += tx.signed_amount
        return [months[k] for k in sorted(months)]

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('judo_club.action_report_financial_statement').report_action(self)

    def action_export_xlsx(self):
        """Exporte la situation de la période en Excel (3 onglets) et renvoie le téléchargement."""
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError as exc:  # pragma: no cover - dépend de l'installation serveur
            raise UserError(_("La bibliothèque Python xlsxwriter est requise pour l'export Excel.")) from exc

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        bold = wb.add_format({'bold': True})
        head = wb.add_format({'bold': True, 'bg_color': '#714B67', 'font_color': '#FFFFFF'})
        money = wb.add_format({'num_format': '#,##0'})
        date_fmt = wb.add_format({'num_format': 'dd/mm/yyyy'})

        ws = wb.add_worksheet(_('Synthèse'))
        ws.set_column(0, 0, 34)
        ws.set_column(1, 1, 24)
        summary = [
            (_('Période'), '%s au %s' % (self.date_from, self.date_to)),
            (_('Compte'), self.bank_account_id.name or _('Tous les comptes et caisses')),
            (_('Solde d\'ouverture'), self.opening_balance),
            (_('Total des recettes'), self.total_income),
            (_('Total des dépenses'), self.total_expense),
            (_('Résultat de la période'), self.result),
            (_('Entrées de trésorerie'), self.cash_in),
            (_('Sorties de trésorerie'), self.cash_out),
            (_('Solde de clôture'), self.closing_balance),
            (_('Remboursements reçus'), self.refunds_in),
            (_('Remboursements versés'), self.refunds_out),
            (_('Factures clients à encaisser'), self.receivables),
        ]
        for row, (label, value) in enumerate(summary):
            ws.write(row, 0, label, bold)
            if isinstance(value, (int, float)):
                ws.write_number(row, 1, float(value), money)
            else:
                ws.write(row, 1, str(value))

        # Indicateurs du tableau de bord, à la date de l'export
        kpis = self.env['judo.dashboard'].get_dashboard_data()['kpis']
        ws_k = wb.add_worksheet(_('Indicateurs'))
        ws_k.set_column(0, 0, 34)
        ws_k.set_column(1, 1, 22)
        ws_k.write(0, 0, _('Indicateurs au %s', fields.Date.context_today(self)), bold)
        indicators = [
            (_('Adhérents actifs'), kpis['members_active']),
            (_('Adhérents (total des fiches)'), kpis['members_total']),
            (_('Montant non réglé (cotisations et licences)'), kpis['amount_due']),
            (_('Éléments à facturer'), kpis['to_invoice']),
            (_('Cotisations en retard'), kpis['overdue']),
            (_('Solde des comptes et caisses'), kpis['balance']),
        ]
        for row, (label, value) in enumerate(indicators, start=2):
            ws_k.write(row, 0, label, bold)
            ws_k.write_number(row, 1, float(value), money)

        ws_m = wb.add_worksheet(_('Mensuel'))
        ws_m.set_column(0, 3, 16)
        for col, title in enumerate([_('Mois'), _('Recettes'), _('Dépenses'), _('Flux net')]):
            ws_m.write(0, col, title, head)
        for row, line in enumerate(self._monthly_breakdown(), start=1):
            ws_m.write(row, 0, line['label'])
            ws_m.write_number(row, 1, float(line['income']), money)
            ws_m.write_number(row, 2, float(line['expense']), money)
            ws_m.write_number(row, 3, float(line['net']), money)

        ws_t = wb.add_worksheet(_('Transactions'))
        ws_t.set_column(0, 0, 12)
        ws_t.set_column(1, 3, 28)
        ws_t.set_column(4, 6, 18)
        headers = [_('Date'), _('Libellé'), _('Catégorie'), _('Compte'), _('Sens'),
                   _('Référence'), _('Montant signé')]
        for col, title in enumerate(headers):
            ws_t.write(0, col, title, head)
        for row, tx in enumerate(self._get_transactions(), start=1):
            ws_t.write_datetime(row, 0, datetime.combine(tx.date, datetime.min.time()), date_fmt)
            ws_t.write(row, 1, tx.name or '')
            ws_t.write(row, 2, tx.category_id.name or '')
            ws_t.write(row, 3, tx.bank_account_id.name or '')
            ws_t.write(row, 4, dict(tx._fields['type'].selection).get(tx.type, ''))
            ws_t.write(row, 5, tx.reference or '')
            ws_t.write_number(row, 6, float(tx.signed_amount), money)
        wb.close()

        filename = 'Situation_%s_%s.xlsx' % (self.date_from, self.date_to)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_print_ticket(self):
        self.ensure_one()
        return self.env.ref('judo_club.action_report_financial_ticket').report_action(self)

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
