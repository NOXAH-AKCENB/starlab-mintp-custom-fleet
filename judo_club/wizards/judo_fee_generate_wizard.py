# -*- coding: utf-8 -*-
from odoo import _, fields, models


class JudoFeeGenerateWizard(models.TransientModel):
    _name = 'judo.fee.generate.wizard'
    _description = 'Génération des cotisations mensuelles'

    period = fields.Date(
        string='Mois', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
        help='N\'importe quel jour du mois : la cotisation est créée pour le mois entier.')

    def action_generate(self):
        self.ensure_one()
        fees = self.env['judo.fee']._generate_fees_for_period(self.period)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cotisations générées'),
                'message': _('%s cotisation(s) créée(s) pour le mois.', len(fees)),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
