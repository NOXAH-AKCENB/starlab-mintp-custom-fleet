# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class JudoRoom(models.Model):
    _name = 'judo.room'
    _description = 'Salle'
    _order = 'name'

    name = fields.Char(string='Salle', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    capacity = fields.Integer(string='Capacité')
    hourly_rate = fields.Monetary(string="Tarif de location à l'heure", currency_field='currency_id',
                                  default=15000.0)
    active = fields.Boolean(default=True)


class JudoRoomBooking(models.Model):
    """Réservation d'un créneau dans une salle, pour le judo ou une autre activité."""
    _name = 'judo.room.booking'
    _description = 'Réservation de salle'
    _order = 'date desc, time_start'
    _sql_constraints = [
        ('time_check', 'CHECK(time_end > time_start)', "L'heure de fin doit être après l'heure de début."),
    ]

    name = fields.Char(string='Libellé', required=True, default=lambda self: _('Location de salle'))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    room_id = fields.Many2one('judo.room', string='Salle', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    time_start = fields.Float(string='Début', required=True, help='Ex : 18.5 = 18h30')
    time_end = fields.Float(string='Fin', required=True, help='Ex : 20 = 20h00')
    activity = fields.Char(string='Activité')
    partner_id = fields.Many2one('res.partner', string='Client (facturation)')
    amount = fields.Monetary(string='Montant', currency_field='currency_id', compute='_compute_amount',
                             store=True, readonly=False)
    state = fields.Selection([
        ('draft', 'Demande'), ('confirmed', 'Confirmée'), ('invoiced', 'Facturée'), ('cancelled', 'Annulée'),
    ], string='Statut', default='draft', required=True)
    invoice_id = fields.Many2one('account.move', string='Facture', readonly=True, copy=False)

    @api.depends('room_id.hourly_rate', 'time_start', 'time_end')
    def _compute_amount(self):
        for rec in self:
            duration = max((rec.time_end or 0) - (rec.time_start or 0), 0)
            rec.amount = (rec.room_id.hourly_rate or 0) * duration

    @api.constrains('room_id', 'date', 'time_start', 'time_end', 'state')
    def _check_overlap(self):
        for rec in self.filtered(lambda b: b.state in ('confirmed', 'invoiced')):
            clash = self.search_count([
                ('id', '!=', rec.id), ('room_id', '=', rec.room_id.id), ('date', '=', rec.date),
                ('state', 'in', ('confirmed', 'invoiced')),
                ('time_start', '<', rec.time_end), ('time_end', '>', rec.time_start),
            ])
            if clash:
                raise ValidationError(_("La salle « %s » est déjà réservée sur ce créneau.", rec.room_id.name))

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_invoice(self):
        """Crée une facture de location pour chaque réservation confirmée."""
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)
        if not journal:
            raise UserError(_("Aucun journal de vente n'est configuré pour cette société."))
        product = self.env.ref('judo_club.product_judo_room')
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Seule une réservation confirmée peut être facturée."))
            if not rec.partner_id:
                raise UserError(_("Renseignez le client (facturation) de la réservation « %s ».", rec.name))
            rec.invoice_id = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'journal_id': journal.id,
                'company_id': rec.company_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': _('Location %s le %s (%s h – %s h)', rec.room_id.name, rec.date,
                              rec.time_start, rec.time_end),
                    'quantity': 1.0,
                    'price_unit': rec.amount,
                })],
            })
            rec.state = 'invoiced'
