# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models

GRADES = [
    ('white', 'Blanche'),
    ('yellow', 'Jaune'),
    ('orange', 'Orange'),
    ('green', 'Verte'),
    ('blue', 'Bleue'),
    ('brown', 'Marron'),
    ('black', 'Noire'),
]


class JudoMemberCategory(models.Model):
    _name = 'judo.member.category'
    _description = 'Catégorie d\'adhérents'
    _order = 'name'

    name = fields.Char(string='Catégorie', required=True,
                       help='Ex : Enfants, Adultes, Compétiteurs')
    color = fields.Integer(string='Couleur')
    description = fields.Text(string='Description')
    member_ids = fields.Many2many(
        'judo.member', 'judo_member_category_rel', 'category_id', 'member_id',
        string='Adhérents')
    member_count = fields.Integer(compute='_compute_member_count', string='Nombre')

    @api.depends('member_ids')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)


class JudoMember(models.Model):
    _name = 'judo.member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Adhérent'
    _order = 'last_name, first_name'

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Société', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')

    first_name = fields.Char(string='Prénom', required=True, tracking=True)
    last_name = fields.Char(string='Nom', required=True, tracking=True)
    name = fields.Char(string='Nom complet', compute='_compute_name', store=True)
    birth_date = fields.Date(string='Date de naissance', tracking=True)
    age = fields.Integer(string='Âge', compute='_compute_age')
    gender = fields.Selection([('male', 'Homme'), ('female', 'Femme')], string='Sexe')
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Adresse')
    emergency_contact = fields.Char(string='Personne à contacter')
    emergency_phone = fields.Char(string='Téléphone d\'urgence')

    grade = fields.Selection(GRADES, string='Ceinture', default='white', tracking=True,
                             help='Niveau de compétence (ceinture).')
    dan = fields.Integer(string='Dan', default=0)
    category_ids = fields.Many2many(
        'judo.member.category', 'judo_member_category_rel', 'member_id', 'category_id',
        string='Catégories')

    partner_id = fields.Many2one(
        'res.partner', string='Contact comptable', copy=False, readonly=True,
        help='Fiche contact créée automatiquement pour la facturation.')

    membership_ids = fields.One2many('judo.membership', 'member_id', string='Adhésions')
    enrollment_ids = fields.One2many('judo.enrollment', 'member_id', string='Inscriptions aux cours')
    fee_ids = fields.One2many('judo.fee', 'member_id', string='Cotisations')
    licence_ids = fields.One2many('judo.licence', 'member_id', string='Licences')

    state = fields.Selection(
        [('active', 'Actif'), ('inactive', 'Inactif')],
        string='Statut', compute='_compute_state', store=True)
    amount_due = fields.Monetary(
        string='Montant non réglé', currency_field='currency_id',
        compute='_compute_amount_due')

    @api.depends('first_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            rec.name = ' '.join(p for p in [(rec.last_name or '').upper(), rec.first_name or ''] if p)

    @api.depends('birth_date')
    def _compute_age(self):
        for rec in self:
            if rec.birth_date:
                today = fields.Date.context_today(rec)
                bd = rec.birth_date
                rec.age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
            else:
                rec.age = 0

    @api.depends('membership_ids.state')
    def _compute_state(self):
        for rec in self:
            has_active = any(m.state == 'active' for m in rec.membership_ids)
            rec.state = 'active' if has_active else 'inactive'

    @api.depends('fee_ids.amount', 'fee_ids.state', 'licence_ids.amount', 'licence_ids.state')
    def _compute_amount_due(self):
        open_states = ('to_invoice', 'invoiced')
        for rec in self:
            fees = rec.fee_ids.filtered(lambda f: f.state in open_states)
            licences = rec.licence_ids.filtered(lambda l: l.state in open_states)
            rec.amount_due = sum(fees.mapped('amount')) + sum(licences.mapped('amount'))

    # ----- Contact comptable -------------------------------------------------
    def _partner_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'email': self.email or False,
            'phone': self.phone or False,
            'street': self.address or False,
        }

    def _ensure_partner(self):
        for rec in self.filtered(lambda m: not m.partner_id):
            rec.partner_id = self.env['res.partner'].create(rec._partner_vals())

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        members._ensure_partner()
        return members

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('first_name', 'last_name', 'email', 'phone', 'address')):
            for rec in self.filtered('partner_id'):
                rec.partner_id.write(rec._partner_vals())
        return res
