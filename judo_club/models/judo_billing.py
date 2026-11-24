# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from .judo_common import check_same_company
from odoo.exceptions import UserError


class JudoBillableMixin(models.AbstractModel):
    """Socle commun aux cotisations mensuelles et aux licences : montant, facture
    associée, statut de paiement et rappels."""
    _name = 'judo.billable.mixin'
    _description = 'Élément facturable (cotisation ou licence)'

    company_id = fields.Many2one(
        'res.company', string='Société', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    member_id = fields.Many2one('judo.member', string='Adhérent', required=True,
                                ondelete='cascade', index=True)
    partner_id = fields.Many2one(related='member_id.partner_id', store=True, string='Contact')
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    invoice_id = fields.Many2one('account.move', string='Facture', copy=False, readonly=True,
                                 ondelete='set null')
    invoice_date_due = fields.Date(related='invoice_id.invoice_date_due', string='Échéance')
    payment_state = fields.Selection(related='invoice_id.payment_state', string='Paiement')
    cancelled = fields.Boolean(string='Annulé', copy=False)
    last_reminder_date = fields.Date(string='Dernier rappel', copy=False, readonly=True)
    state = fields.Selection(
        [('to_invoice', 'À facturer'), ('invoiced', 'Facturé'),
         ('paid', 'Payé'), ('cancelled', 'Annulé')],
        string='Statut', compute='_compute_state', store=True)

    @api.depends('invoice_id.state', 'invoice_id.payment_state', 'cancelled')
    def _compute_state(self):
        for rec in self:
            invoice = rec.invoice_id.sudo()
            if rec.cancelled:
                rec.state = 'cancelled'
            elif not invoice or invoice.state == 'cancel':
                rec.state = 'to_invoice'
            elif invoice.payment_state in ('paid', 'in_payment'):
                rec.state = 'paid'
            else:
                rec.state = 'invoiced'

    def action_cancel_billing(self):
        for rec in self:
            if rec.invoice_id.sudo().state == 'posted':
                raise UserError(_("La facture est déjà validée : annulez-la dans la comptabilité."))
        self.write({'cancelled': True})

    def _judo_send_reminders(self, template_xmlid):
        """Envoie le modèle de mail à chaque contact, en respectant le délai entre deux rappels."""
        template = self.env.ref(template_xmlid)
        today = fields.Date.context_today(self)
        sent = self.browse()
        for rec in self:
            if not rec.partner_id.email:
                continue
            delay = rec.company_id.judo_reminder_days or 7
            if rec.last_reminder_date and (today - rec.last_reminder_date).days < delay:
                continue
            template.send_mail(rec.id, force_send=False)
            rec.last_reminder_date = today
            sent |= rec
        return sent


class JudoFee(models.Model):
    _name = 'judo.fee'
    _inherit = ['judo.billable.mixin', 'mail.thread']
    _description = 'Cotisation mensuelle'
    _order = 'period desc, id desc'
    _sql_constraints = [
        ('membership_period_uniq', 'unique(membership_id, period)',
         'Une seule cotisation par mois et par adhésion.'),
    ]

    membership_id = fields.Many2one('judo.membership', string='Adhésion', required=True,
                                    ondelete='cascade', index=True)
    period = fields.Date(string='Mois', required=True, help='Premier jour du mois concerné.')
    name = fields.Char(string='Libellé', compute='_compute_name', store=True)

    @api.depends('member_id.name', 'period')
    def _compute_name(self):
        for rec in self:
            month = rec.period.strftime('%m/%Y') if rec.period else ''
            rec.name = _('Cotisation %s – %s', month, rec.member_id.name or '')

    @api.constrains('company_id', 'member_id', 'membership_id')
    def _check_company_consistency(self):
        check_same_company(self, ('member_id', 'membership_id'))

    @api.model
    def _generate_fees_for_period(self, period):
        """Crée la cotisation du mois pour chaque adhésion active. Idempotent."""
        period = period.replace(day=1)
        memberships = self.env['judo.membership'].search([
            ('date_start', '<=', period),
            ('season_id.date_start', '<=', period),
            ('season_id.date_end', '>=', period),
            '|',
            ('state', '=', 'active'),
            '&', ('state', '=', 'resigned'), ('resignation_date', '>=', period),
        ])
        existing = set(self.search([('period', '=', period)]).membership_id.ids)
        # Cotisations créées pour la société courante uniquement (voir _cron_generate_monthly_fees)
        memberships = memberships.filtered(lambda m: m.company_id == self.env.company)
        vals = [{
            'membership_id': m.id,
            'member_id': m.member_id.id,
            'period': period,
            'amount': m.monthly_fee,
            'company_id': m.company_id.id,
        } for m in memberships if m.id not in existing]
        return self.create(vals)

    @api.model
    def _cron_generate_monthly_fees(self):
        """Exécuté pour chaque société, dans son propre contexte."""
        period = fields.Date.context_today(self).replace(day=1)
        for company in self.env['res.company'].sudo().search([]):
            self.with_company(company)._generate_fees_for_period(period)

    @api.model
    def _cron_send_reminders(self):
        today = fields.Date.context_today(self)
        for company in self.env['res.company'].sudo().search([]):
            overdue = self.with_company(company).search([
                ('company_id', '=', company.id),
                ('state', '=', 'invoiced'),
                ('invoice_date_due', '<', today),
            ])
            overdue._judo_send_reminders('judo_club.mail_template_judo_fee_reminder')


class JudoLicence(models.Model):
    _name = 'judo.licence'
    _inherit = ['judo.billable.mixin', 'mail.thread']
    _description = 'Licence fédérale'
    _order = 'season_id desc, member_id'
    _sql_constraints = [
        ('member_season_uniq', 'unique(member_id, season_id)',
         'Une licence existe déjà pour ce membre et cette saison.'),
    ]

    membership_id = fields.Many2one('judo.membership', string='Adhésion',
                                    ondelete='cascade')
    season_id = fields.Many2one('judo.season', string='Saison', required=True,
                                ondelete='restrict')
    name = fields.Char(string='Libellé', compute='_compute_name', store=True)

    @api.constrains('company_id', 'member_id', 'season_id')
    def _check_company_consistency(self):
        check_same_company(self, ('member_id', 'season_id'))

    @api.depends('member_id.name', 'season_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = _('Licence %s – %s', rec.season_id.name or '', rec.member_id.name or '')

    @api.model
    def _cron_send_reminders(self):
        for company in self.env['res.company'].sudo().search([]):
            pending = self.with_company(company).search([
                ('company_id', '=', company.id),
                ('state', '=', 'to_invoice'),
            ])
            pending._judo_send_reminders('judo_club.mail_template_judo_licence_reminder')
