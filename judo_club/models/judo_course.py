# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .judo_member import GRADES

DAYS = [
    ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'), ('3', 'Jeudi'),
    ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche'),
]


def _format_hour(value):
    hours = int(value)
    minutes = round((value - hours) * 60)
    return '%02d:%02d' % (hours, minutes)


class JudoGroup(models.Model):
    _name = 'judo.group'
    _description = 'Groupe d\'entraînement'
    _order = 'name'

    name = fields.Char(string='Groupe', required=True)
    description = fields.Text(string='Description')
    age_min = fields.Integer(string='Âge minimum')
    age_max = fields.Integer(string='Âge maximum')
    grade_min = fields.Selection(GRADES, string='Ceinture minimum')
    course_ids = fields.One2many('judo.course', 'group_id', string='Cours')


class JudoCourse(models.Model):
    _name = 'judo.course'
    _description = 'Cours'
    _order = 'day_of_week, time_start'
    _sql_constraints = [
        ('time_check', 'CHECK(time_end > time_start)',
         'L\'heure de fin doit être postérieure à l\'heure de début.'),
    ]

    name = fields.Char(string='Intitulé', required=True)
    season_id = fields.Many2one('judo.season', string='Saison', required=True, ondelete='restrict')
    group_id = fields.Many2one('judo.group', string='Groupe')
    day_of_week = fields.Selection(DAYS, string='Jour', required=True, default='0')
    time_start = fields.Float(string='Heure de début', required=True,
                              help='Format décimal : 18.5 = 18h30')
    time_end = fields.Float(string='Heure de fin', required=True, help='Format décimal : 19.5 = 19h30')
    schedule = fields.Char(string='Horaire', compute='_compute_schedule')
    instructor = fields.Char(string='Enseignant')
    room = fields.Char(string='Salle / tatami')
    capacity = fields.Integer(string='Places maximum', default=0, help='0 = nombre de places illimité')
    enrollment_ids = fields.One2many('judo.enrollment', 'course_id', string='Inscrits')
    enrolled_count = fields.Integer(string='Inscrits', compute='_compute_enrolled_count')

    @api.depends('day_of_week', 'time_start', 'time_end')
    def _compute_schedule(self):
        days = dict(DAYS)
        for rec in self:
            rec.schedule = '%s %s-%s' % (days.get(rec.day_of_week, ''),
                                        _format_hour(rec.time_start), _format_hour(rec.time_end))

    @api.depends('enrollment_ids.state')
    def _compute_enrolled_count(self):
        for rec in self:
            rec.enrolled_count = len(rec.enrollment_ids.filtered(lambda e: e.state == 'active'))


class JudoEnrollment(models.Model):
    _name = 'judo.enrollment'
    _description = 'Inscription à un cours'
    _order = 'date desc, id desc'

    member_id = fields.Many2one('judo.member', string='Adhérent', required=True,
                                ondelete='cascade', index=True)
    course_id = fields.Many2one('judo.course', string='Cours', required=True, ondelete='cascade')
    season_id = fields.Many2one(related='course_id.season_id', store=True, string='Saison')
    date = fields.Date(string='Date d\'inscription', default=fields.Date.context_today, required=True)
    state = fields.Selection([('active', 'Inscrit'), ('cancelled', 'Annulée')],
                             string='Statut', default='active', required=True)

    @api.constrains('member_id', 'course_id', 'state')
    def _check_enrollment(self):
        for rec in self.filtered(lambda e: e.state == 'active'):
            duplicates = self.search_count([
                ('id', '!=', rec.id), ('member_id', '=', rec.member_id.id),
                ('course_id', '=', rec.course_id.id), ('state', '=', 'active'),
            ])
            if duplicates:
                raise ValidationError(_("Ce membre est déjà inscrit à ce cours."))
            capacity = rec.course_id.capacity
            if capacity:
                active = self.search_count([('course_id', '=', rec.course_id.id),
                                            ('state', '=', 'active')])
                if active > capacity:
                    raise ValidationError(_("Le cours « %s » est complet.", rec.course_id.name))
