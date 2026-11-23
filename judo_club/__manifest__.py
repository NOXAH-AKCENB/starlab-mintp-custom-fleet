# -*- coding: utf-8 -*-
{
    'name': 'Club de Judo – Adhérents, cotisations, facturation et comptabilité',
    'version': '17.0.1.0.0',
    'category': 'Associations',
    'summary': 'Gestion d\'un club de judo : adhérents, cours, cotisations mensuelles, licences, '
               'facturation, comptabilité simplifiée et rapports financiers.',
    'author': 'Projet Club de Judo',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account'],
    'data': [
        'security/judo_security.xml',
        'security/ir.model.access.csv',
        'data/judo_data.xml',
        'views/judo_member_views.xml',
        'views/judo_membership_views.xml',
        'views/judo_course_views.xml',
        'views/judo_billing_views.xml',
        'views/judo_accounting_views.xml',
        'views/res_company_views.xml',
        'views/judo_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
