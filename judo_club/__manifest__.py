# -*- coding: utf-8 -*-
{
    'name': 'Club de Judo – Adhérents, cotisations, facturation et comptabilité',
    'version': '17.0.1.1.0',
    'category': 'Associations',
    'summary': 'Gestion d\'un club de judo : adhérents, cours, cotisations mensuelles, licences, '
               'facturation, comptabilité simplifiée et rapports financiers.',
    'author': 'Projet Club de Judo',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account'],
    'external_dependencies': {'python': ['xlsxwriter']},
    'data': [
        'security/judo_security.xml',
        'security/ir.model.access.csv',
        'data/judo_data.xml',
        'report/judo_report_templates.xml',
        'views/judo_dashboard_views.xml',
        'views/judo_member_views.xml',
        'views/judo_membership_views.xml',
        'views/judo_course_views.xml',
        'views/judo_billing_views.xml',
        'views/judo_accounting_views.xml',
        'views/res_company_views.xml',
        'views/judo_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'judo_club/static/src/js/judo_dashboard.js',
            'judo_club/static/src/xml/judo_dashboard.xml',
            'judo_club/static/src/scss/judo_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
