# -*- coding: utf-8 -*-
from odoo import fields, models


class JudoAgeCategory(models.Model):
    """Catégorie d'âge (mini-judo, poussins, seniors…). Modifiable par le club."""
    _name = 'judo.age.category'
    _description = "Catégorie d'âge"
    _order = 'sequence, age_min'

    name = fields.Char(string='Catégorie', required=True)
    sequence = fields.Integer(default=10)
    age_min = fields.Integer(string='Âge minimum', required=True, default=0)
    age_max = fields.Integer(string='Âge maximum', required=True, default=99)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('age_range_check', 'CHECK(age_max >= age_min)', "L'âge maximum doit être supérieur ou égal à l'âge minimum."),
    ]
