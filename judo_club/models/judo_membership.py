# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JudoMembership(models.Model):
    """Adhésion d'un membre à une saison. Gère l'historique, les renouvellements
    et les désistements."""
    _name = 'judo.membership'
    _inherit = ['mail.thread']
    _description = 'Adhésion à une saison'
    _order = 'season_id desc, member_id'
    _check_company_auto = True
    _sql_constraints = [
        ('member_season_uniq', 'unique(member_id, season_id)',
         'Ce membre est déjà inscrit pour cette saison.'),
    ]

    member_id = fields.Many2one('judo.member', string='Adhérent', required=True,
                                ondelete='cascade', index=True, tracking=True, check_company=True)
    season_id = fields.Many2one('judo.season', string='Saison', required=True,
                                ondelete='restrict', tracking=True, check_company=True)
    company_id = fields.Many2one(
        'res.company', string='Société', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_start = fields.Date(string='Date d\'adhésion', default=fields.Date.context_today,
                             required=True)
    date_end = fields.Date(related='season_id.date_end', string='Fin de saison')
    monthly_fee = fields.Monetary(
        string='Cotisation mensuelle', currency_field='currency_id', tracking=True,
        default=lambda self: self.env.company.judo_monthly_fee)
    state = fields.Selection(
        [('active', 'Active'), ('renewed', 'Renouvelée'), ('resigned', 'Désistement')],
        string='Statut', default='active', required=True, tracking=True)
    resignation_date = fields.Date(string='Date de désistement', readonly=True)
    resignation_reason = fields.Char(string='Motif du désistement')
    previous_membership_id = fields.Many2one(
        'judo.membership', string='Adhésion précédente', readonly=True, copy=False)

    fee_ids = fields.One2many('judo.fee', 'membership_id', string='Cotisations')
    licence_ids = fields.One2many('judo.licence', 'membership_id', string='Licences')

    @api.model_create_multi
    def create(self, vals_list):
        memberships = super().create(vals_list)
        Licence = self.env['judo.licence']
        for m in memberships:
            if not Licence.search_count([('member_id', '=', m.member_id.id),
                                         ('season_id', '=', m.season_id.id)]):
                Licence.create({
                    'member_id': m.member_id.id,
                    'membership_id': m.id,
                    'season_id': m.season_id.id,
                    'amount': m.season_id.licence_amount,
                    'company_id': m.company_id.id,
                })
        return memberships

    def action_resign(self):
        """Désistement : l'adhésion n'est plus facturée pour les mois suivants."""
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state != 'active':
                raise UserError(_("Seule une adhésion active peut faire l'objet d'un désistement."))
        self.write({'state': 'resigned', 'resignation_date': today})

    def action_renew(self):
        """Renouvelle l'adhésion sur la saison suivante."""
        for rec in self:
            if rec.state != 'active':
                raise UserError(_("Seule une adhésion active peut être renouvelée."))
            next_season = self.env['judo.season'].search([
                ('date_start', '>', rec.season_id.date_end),
                ('company_id', '=', rec.company_id.id),
            ], order='date_start', limit=1)
            if not next_season:
                raise UserError(_("Aucune saison suivante n'est définie pour %s.", rec.season_id.name))
            if self.search_count([('member_id', '=', rec.member_id.id),
                                  ('season_id', '=', next_season.id)]):
                raise UserError(_("Ce membre est déjà inscrit pour la saison %s.", next_season.name))
            self.create({
                'member_id': rec.member_id.id,
                'season_id': next_season.id,
                'date_start': next_season.date_start,
                'monthly_fee': rec.monthly_fee,
                'previous_membership_id': rec.id,
                'company_id': rec.company_id.id,
            })
            rec.state = 'renewed'
        return True
