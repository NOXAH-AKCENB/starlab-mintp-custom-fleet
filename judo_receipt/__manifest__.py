# -*- coding: utf-8 -*-
{
    'name': 'Club de Judo – Reçus et tickets de caisse',
    'version': '17.0.1.0.0',
    'category': 'Associations',
    'summary': 'Reçus numérotés par club, impression en ticket de caisse 80 mm.',
    'author': 'Projet Club de Judo',
    'license': 'LGPL-3',
    'depends': ['judo_club'],
    'data': [
        'security/judo_receipt_security.xml',
        'security/ir.model.access.csv',
        'report/judo_receipt_report.xml',
        'views/judo_receipt_views.xml',
        'views/judo_receipt_link_views.xml',
    ],
    'installable': True,
    'application': False,
}
