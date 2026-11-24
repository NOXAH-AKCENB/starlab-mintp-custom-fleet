# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestJudoClub(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.judo_monthly_fee = 10000
        self.season = self.env['judo.season'].create({
            'name': '2026-2027',
            'date_start': date(2026, 9, 1),
            'date_end': date(2027, 6, 30),
            'licence_amount': 15000,
        })
        self.member = self.env['judo.member'].create({
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'email': 'jean@example.com',
        })

    def _membership(self, member=None):
        return self.env['judo.membership'].create({
            'member_id': (member or self.member).id,
            'season_id': self.season.id,
            'date_start': date(2026, 9, 1),
        })

    def test_membership_creates_partner_and_licence(self):
        membership = self._membership()
        self.assertTrue(self.member.partner_id, "Un contact comptable doit être créé")
        self.assertEqual(len(membership.licence_ids), 1)
        self.assertEqual(membership.licence_ids.amount, 15000)
        self.assertEqual(self.member.state, 'active')

    def test_fee_generation_is_idempotent(self):
        self._membership()
        first = self.env['judo.fee']._generate_fees_for_period(date(2026, 10, 1))
        again = self.env['judo.fee']._generate_fees_for_period(date(2026, 10, 15))
        self.assertEqual(len(first), 1)
        self.assertEqual(first.amount, 10000)
        self.assertEqual(len(again), 0, "Un mois déjà généré ne doit pas être recréé")

    def test_resignation_stops_future_fees(self):
        membership = self._membership()
        membership.write({'state': 'resigned', 'resignation_date': date(2026, 10, 15)})
        october = self.env['judo.fee']._generate_fees_for_period(date(2026, 10, 1))
        november = self.env['judo.fee']._generate_fees_for_period(date(2026, 11, 1))
        self.assertEqual(len(october), 1, "Le mois du désistement reste dû")
        self.assertEqual(len(november), 0, "Aucune cotisation après le désistement")

    def test_renewal_creates_next_season_membership(self):
        self._membership()
        next_season = self.env['judo.season'].create({
            'name': '2027-2028',
            'date_start': date(2027, 9, 1),
            'date_end': date(2028, 6, 30),
            'licence_amount': 16000,
        })
        old = self.env['judo.membership'].search([('member_id', '=', self.member.id)])
        old.action_renew()
        self.assertEqual(old.state, 'renewed')
        new = self.env['judo.membership'].search([('member_id', '=', self.member.id),
                                                  ('season_id', '=', next_season.id)])
        self.assertEqual(new.previous_membership_id, old)

    def test_invoice_wizard_applies_discount(self):
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.company.id)], limit=1)
        if not journal:
            self.skipTest("Aucun journal de vente : plan comptable non installé")
        self._membership()
        fees = self.env['judo.fee']._generate_fees_for_period(date(2026, 10, 1))
        wizard = self.env['judo.invoice.wizard'].create({
            'fee_ids': [(6, 0, fees.ids)],
            'discount_percent': 10,
        })
        wizard.action_create_invoices()
        self.assertEqual(fees.state, 'invoiced')
        line = fees.invoice_id.invoice_line_ids.filtered(lambda l: l.discount)
        self.assertEqual(line.discount, 10)

    def test_financial_report_figures(self):
        bank = self.env['judo.bank.account'].create({
            'name': 'Caisse',
            'opening_date': date(2026, 9, 1),
            'opening_balance': 100000,
        })
        income = self.env['judo.transaction.category'].create({'name': 'Cotisations', 'type': 'income'})
        expense = self.env['judo.transaction.category'].create({'name': 'Matériel', 'type': 'expense'})
        self.env['judo.transaction'].create([
            {'name': 'Encaissement', 'date': date(2026, 10, 5), 'bank_account_id': bank.id,
             'category_id': income.id, 'amount': 50000},
            {'name': 'Tatamis', 'date': date(2026, 10, 6), 'bank_account_id': bank.id,
             'category_id': expense.id, 'amount': 20000},
        ])
        report = self.env['judo.financial.report'].create({
            'date_from': date(2026, 10, 1),
            'date_to': date(2026, 10, 31),
        })
        self.assertEqual(report.opening_balance, 100000)
        self.assertEqual(report.total_income, 50000)
        self.assertEqual(report.total_expense, 20000)
        self.assertEqual(report.result, 30000)
        self.assertEqual(report.closing_balance, 130000)
        self.assertEqual(report._monthly_breakdown()[0]['net'], 30000)

    def test_financial_report_pdf_action(self):
        report = self.env['judo.financial.report'].create({
            'date_from': date(2026, 10, 1),
            'date_to': date(2026, 10, 31),
        })
        action = report.action_print_pdf()
        self.assertEqual(action.get('report_name'), 'judo_club.report_financial_statement')
        self.assertEqual(action.get('type'), 'ir.actions.report')

    def test_dashboard_data_shape(self):
        self._membership()
        data = self.env['judo.dashboard'].get_dashboard_data()
        self.assertEqual(len(data['series']), 12)
        self.assertEqual(data['kpis']['members_active'], 1)
        self.assertIn('balance', data['kpis'])
        self.assertIn('amount_due', data['kpis'])

    def test_multicompany_isolation(self):
        company_b = self.env['res.company'].create({'name': 'Club de judo B'})
        season_b = self.env['judo.season'].create({
            'name': '2026-2027 B', 'date_start': date(2026, 9, 1), 'date_end': date(2027, 6, 30),
            'licence_amount': 12000, 'company_id': company_b.id,
        })
        member_b = self.env['judo.member'].create({
            'first_name': 'Paul', 'last_name': 'Martin', 'company_id': company_b.id,
        })
        self.env['judo.membership'].create({
            'member_id': member_b.id, 'season_id': season_b.id, 'company_id': company_b.id,
        })
        # Une adhésion ne peut pas relier un membre d'un club à la saison d'un autre club
        with self.assertRaises((UserError, ValidationError)):
            self.env['judo.membership'].create({'member_id': member_b.id, 'season_id': self.season.id})

        user = self.env['res.users'].create({
            'name': 'Secrétaire multi-clubs', 'login': 'judo_multi_test@example.com',
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id, company_b.id])],
            'groups_id': [(6, 0, [self.env.ref('judo_club.group_judo_manager').id])],
        })
        Member = self.env['judo.member'].with_user(user)

        in_a = Member.with_context(allowed_company_ids=[self.company.id]).search([])
        self.assertIn(self.member, in_a)
        self.assertNotIn(member_b, in_a)

        in_b = Member.with_context(allowed_company_ids=[company_b.id]).search([])
        self.assertIn(member_b, in_b)
        self.assertNotIn(self.member, in_b)

        data_b = self.env['judo.dashboard'].with_user(user).with_context(
            allowed_company_ids=[company_b.id]).get_dashboard_data()
        self.assertEqual(data_b['kpis']['members_total'], 1)

    def test_export_period_formats(self):
        dashboard = self.env['judo.dashboard']
        pdf = dashboard.export_period('2026-01-01', '2026-12-31', 'pdf')
        self.assertEqual(pdf.get('report_name'), 'judo_club.report_financial_statement')
        ticket = dashboard.export_period('2026-01-01', '2026-12-31', 'ticket')
        self.assertEqual(ticket.get('report_name'), 'judo_club.report_financial_ticket')
        xlsx = dashboard.export_period('2026-01-01', '2026-12-31', 'xlsx')
        self.assertEqual(xlsx.get('type'), 'ir.actions.act_url')
        self.assertIn('/web/content/', xlsx.get('url'))

    def test_export_period_rejects_invalid_period(self):
        with self.assertRaises(UserError):
            self.env['judo.dashboard'].export_period('2026-12-31', '2026-01-01', 'pdf')

