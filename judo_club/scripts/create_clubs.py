#!/usr/bin/env python3
"""Crée les sociétés (clubs) dans une base Odoo 17 via l'API XML-RPC.

Idempotent : une société déjà existante (même nom) est ignorée.

Variables d'environnement (à définir localement, ne pas les écrire dans le code) :
    ODOO_URL      ex. https://mon-serveur.example.com
    ODOO_DB       nom de la base
    ODOO_LOGIN    identifiant d'un administrateur
    ODOO_API_KEY  clé API de cet utilisateur (Préférences → Sécurité du compte → Nouvelle clé API)

Usage :
    python3 create_clubs.py --dry-run   # affiche ce qui serait créé, sans rien modifier
    python3 create_clubs.py             # crée les sociétés manquantes
"""
import os
import sys
import xmlrpc.client

CLUBS = [
    {
        'name': 'PANTHERS BASTOS',
        'street': 'Bastos, entre le lycée technique Charles Atangana et le commissariat du 10e',
        'street2': 'BP 13261',
        'phone': '677767137 / 694865301',
    },
    {
        'name': 'PANTHERS MEFOU ET AFAMBA',
        'street': 'Nkolfoulou, à 50 m avant le CCGMI',
        'street2': 'BP 13261',
        'phone': '677767137 / 698270673',
    },
]


def main():
    dry_run = '--dry-run' in sys.argv
    url, db = os.environ.get('ODOO_URL', '').rstrip('/'), os.environ.get('ODOO_DB', '')
    login, key = os.environ.get('ODOO_LOGIN', ''), os.environ.get('ODOO_API_KEY', '')
    if not all([url, db, login, key]):
        sys.exit('Définir ODOO_URL, ODOO_DB, ODOO_LOGIN et ODOO_API_KEY.')

    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, login, key, {})
    if not uid:
        sys.exit('Authentification refusée (login, clé API ou base incorrects).')
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    def call(model, method, *args, **kwargs):
        return models.execute_kw(db, uid, key, model, method, list(args), kwargs)

    country = call('res.country', 'search', [('code', '=', 'CM')], limit=1)
    currency = call('res.currency', 'search', [('name', '=', 'XAF')], limit=1, context={'active_test': False})

    for club in CLUBS:
        existing = call('res.company', 'search', [('name', '=', club['name'])], limit=1)
        if existing:
            print(f"= déjà présent : {club['name']} (id {existing[0]})")
            continue
        vals = {
            'name': club['name'],
            'street': club['street'],
            'street2': club['street2'],
            'phone': club['phone'],
            'country_id': country[0] if country else False,
            'currency_id': currency[0] if currency else False,
        }
        if dry_run:
            print(f"[dry-run] créerait : {vals}")
            continue
        company_id = call('res.company', 'create', vals)
        print(f"+ créée : {club['name']} (id {company_id})")


if __name__ == '__main__':
    main()
