# -*- coding: utf-8 -*-
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JudoDashboard(models.AbstractModel):
    """Données du tableau de bord (consommées par le composant OWL judo_club.dashboard).
    Toutes les valeurs sont limitées à la société courante."""
    _name = 'judo.dashboard'
    _description = 'Tableau de bord du club'

    @api.model
    def get_dashboard_data(self):
        company = self.env.company
        co = [('company_id', '=', company.id)]
        today = fields.Date.context_today(self)
        Member = self.env['judo.member']
        Fee = self.env['judo.fee']
        Licence = self.env['judo.licence']
        Tx = self.env['judo.transaction']

        open_states = ('to_invoice', 'invoiced')
        fees_open = Fee.search(co + [('state', 'in', open_states)])
        licences_open = Licence.search(co + [('state', 'in', open_states)])

        # 12 derniers mois, du plus ancien au plus récent
        first_day = today.replace(day=1)
        months = [first_day - relativedelta(months=i) for i in range(11, -1, -1)]
        last_day = first_day + relativedelta(months=1) - timedelta(days=1)
        txs = Tx.search(co + [('date', '>=', months[0]), ('date', '<=', last_day)])
        series = []
        for m in months:
            in_month = txs.filtered(lambda t, m=m: t.date.year == m.year and t.date.month == m.month)
            series.append({
                'label': m.strftime('%m/%Y'),
                'income': sum(in_month.filtered(lambda t: t.type == 'income').mapped('amount')),
                'expense': sum(in_month.filtered(lambda t: t.type == 'expense').mapped('amount')),
            })

        banks = self.env['judo.bank.account'].search(co)
        recent = Tx.search(co, limit=5)

        return {
            'currency_id': company.currency_id.id,
            'kpis': {
                'members_active': Member.search_count(co + [('state', '=', 'active')]),
                'members_total': Member.search_count(co),
                'amount_due': sum(fees_open.mapped('amount')) + sum(licences_open.mapped('amount')),
                'to_invoice': len(fees_open.filtered(lambda f: f.state == 'to_invoice'))
                              + len(licences_open.filtered(lambda l: l.state == 'to_invoice')),
                'overdue': Fee.search_count(co + [('state', '=', 'invoiced'),
                                                  ('invoice_date_due', '<', today)]),
                'balance': sum(banks.mapped('balance')),
            },
            'series': series,
            'recent': [{
                'id': t.id,
                'date': fields.Date.to_string(t.date),
                'name': t.name,
                'amount': t.signed_amount,
            } for t in recent],
        }

    @api.model
    def export_period(self, date_from, date_to, fmt):
        """Exporte la situation financière d'une période : fmt = 'pdf', 'ticket' ou 'xlsx'."""
        if not date_from or not date_to or date_from > date_to:
            raise UserError(_("La période est invalide : la date de début doit précéder la date de fin."))
        report = self.env['judo.financial.report'].create({
            'company_id': self.env.company.id,
            'date_from': date_from,
            'date_to': date_to,
        })
        if fmt == 'pdf':
            return report.action_print_pdf()
        if fmt == 'ticket':
            return report.action_print_ticket()
        if fmt == 'xlsx':
            return report.action_export_xlsx()
        raise UserError(_("Format d'export inconnu : %s", fmt))
