# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestJudoReceipt(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.company.judo_monthly_fee = 10000
        self.season = self.env['judo.season'].create({
            'name': '2026-2027', 'date_start': date(2026, 9, 1),
            'date_end': date(2027, 6, 30), 'licence_amount': 15000,
        })
        self.member = self.env['judo.member'].create({'first_name': 'Jean', 'last_name': 'Dupont'})
        self.bank = self.env['judo.bank.account'].create({
            'name': 'Caisse', 'opening_date': date(2026, 9, 1), 'opening_balance': 0,
        })
        self.income = self.env['judo.transaction.category'].create({'name': 'Cotisations', 'type': 'income'})

    def test_receipt_from_transaction(self):
        tx = self.env['judo.transaction'].create({
            'name': 'Cotisation espèces', 'date': date(2026, 10, 5), 'bank_account_id': self.bank.id,
            'category_id': self.income.id, 'amount': 25000, 'member_id': self.member.id,
        })
        action = tx.action_create_receipt()
        receipt = self.env['judo.receipt'].browse(action['res_id'])
        self.assertEqual(receipt.amount_total, 25000)
        self.assertEqual(receipt.member_id, self.member)
        self.assertEqual(receipt.transaction_id, tx)
        self.assertTrue(receipt.name.startswith('REC/'))

    def test_receipt_from_licence_and_fee(self):
        self.env['judo.membership'].create({'member_id': self.member.id, 'season_id': self.season.id})
        licence = self.env['judo.licence'].search([('member_id', '=', self.member.id)])
        fees = self.env['judo.fee']._generate_fees_for_period(date(2026, 10, 1))
        action = (licence | fees).action_create_receipts()
        receipt = self.env['judo.receipt'].browse(action['res_id'])
        self.assertEqual(len(receipt.line_ids), 2, "Un reçu par adhérent, une ligne par élément")
        self.assertEqual(receipt.amount_total, 15000 + 10000)

    def test_numbering_is_per_company(self):
        other = self.env['res.company'].create({'name': 'Club B'})
        r1 = self.env['judo.receipt'].create({'company_id': self.company.id,
                                              'line_ids': [(0, 0, {'label': 'A', 'unit_price': 1})]})
        r2 = self.env['judo.receipt'].create({'company_id': other.id,
                                              'line_ids': [(0, 0, {'label': 'B', 'unit_price': 1})]})
        self.assertTrue(r1.name.endswith('/00001') or r1.name.endswith('/00002'))
        self.assertTrue(r2.name.endswith('/00001'), "Chaque club repart de 00001")

    def test_print_action(self):
        receipt = self.env['judo.receipt'].create({
            'line_ids': [(0, 0, {'label': 'Test', 'unit_price': 5000})],
        })
        action = receipt.action_print()
        self.assertEqual(action.get('report_name'), 'judo_receipt.report_judo_receipt_ticket')
        self.assertTrue(receipt.printed_date)
