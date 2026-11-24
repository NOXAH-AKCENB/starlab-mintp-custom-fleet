# -*- coding: utf-8 -*-
from odoo import _
from odoo.exceptions import ValidationError


def check_same_company(records, field_names):
    """Refuse qu'un enregistrement relie des éléments appartenant à des sociétés (clubs) différentes."""
    for rec in records:
        for fname in field_names:
            related = rec[fname]
            if related and related.company_id and related.company_id != rec.company_id:
                raise ValidationError(_(
                    "Incohérence entre clubs : « %s » appartient à une autre société.",
                    related.display_name))
