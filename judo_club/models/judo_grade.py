# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .judo_member import GRADES

RESULTS = [('pending', 'En attente'), ('passed', 'Admis'), ('failed', 'Non admis')]


class JudoGradeSession(models.Model):
    """Session de passage de ceinture / grade. Archivée avec son procès-verbal."""
    _name = 'judo.grade.session'
    _description = 'Session de passage de grade'
    _order = 'date desc, id desc'

    name = fields.Char(string='Intitulé', required=True, help='Ex : Passage de grade décembre 2026')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Club (société)', default=lambda self: self.env.company, required=True)
    location = fields.Char(string='Lieu')
    jury = fields.Char(string='Jury / examinateur')
    state = fields.Selection([('draft', 'Planifiée'), ('done', 'Clôturée')],
                             string='Statut', default='draft', required=True)
    exam_ids = fields.One2many('judo.grade.exam', 'session_id', string='Participants')
    exam_count = fields.Integer(string='Participants', compute='_compute_exam_count')
    pv_attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Procès-verbal',
                                        domain=[('res_model', '=', 'judo.grade.session')],
                                        readonly=True)

    @api.depends('exam_ids')
    def _compute_exam_count(self):
        for rec in self:
            rec.exam_count = len(rec.exam_ids)

    def _grade_groups(self):
        """Participants regroupés par grade sollicité, dans l'ordre des ceintures."""
        self.ensure_one()
        groups = []
        for key, label in GRADES:
            exams = self.exam_ids.filtered(lambda e: e.requested_grade == key).sorted(
                lambda e: e.member_id.name or '')
            if exams:
                groups.append({'label': label, 'exams': exams})
        return groups

    def action_close(self):
        """Clôture la session : promeut les admis, archive le procès-verbal (PDF)."""
        for session in self:
            pending = session.exam_ids.filtered(lambda e: e.result == 'pending')
            if pending:
                raise UserError(_("Renseignez le résultat de tous les participants (%s en attente).",
                                  len(pending)))
            for exam in session.exam_ids.filtered(lambda e: e.result == 'passed'):
                exam.member_id.grade = exam.requested_grade
            session.state = 'done'
            session._archive_pv()
        return True

    def _archive_pv(self):
        self.ensure_one()
        pdf_content, _format = self.env['ir.actions.report']._render_qweb_pdf(
            'judo_club.action_report_grade_pv', self.ids)
        self.env['ir.attachment'].create({
            'name': 'PV_passage_%s.pdf' % (self.date or ''),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
        })

    def _result_counts(self):
        self.ensure_one()
        return {
            'passed': len(self.exam_ids.filtered(lambda e: e.result == 'passed')),
            'failed': len(self.exam_ids.filtered(lambda e: e.result == 'failed')),
            'pending': len(self.exam_ids.filtered(lambda e: e.result == 'pending')),
        }

    def action_print_evaluation(self):
        self.ensure_one()
        return self.env.ref('judo_club.action_report_grade_evaluation').report_action(self)

    def action_print_pv(self):
        self.ensure_one()
        return self.env.ref('judo_club.action_report_grade_pv').report_action(self)


class JudoGradeExam(models.Model):
    """Participation d'un adhérent à un passage de grade. Facturable comme une cotisation."""
    _name = 'judo.grade.exam'
    _inherit = ['judo.billable.mixin']
    _description = 'Passage de grade'
    _order = 'session_id desc, requested_grade, id'

    amount = fields.Monetary(string='Frais de passage', required=True, currency_field='currency_id',
                             default=lambda self: self.env.company.judo_grade_fee)
    session_id = fields.Many2one('judo.grade.session', string='Session', required=True,
                                 ondelete='cascade', index=True)
    name = fields.Char(string='Libellé', compute='_compute_name', store=True)
    current_grade = fields.Selection(related='member_id.grade', string='Ceinture actuelle')
    requested_grade = fields.Selection(GRADES, string='Grade sollicité', required=True)
    result = fields.Selection(RESULTS, string='Résultat', default='pending', required=True)
    result_label = fields.Char(string='Résultat (libellé)', compute='_compute_result_label')
    note = fields.Char(string='Observations')

    @api.depends('member_id.name', 'requested_grade')
    def _compute_name(self):
        grades = dict(GRADES)
        for rec in self:
            rec.name = _('Passage %s – %s', grades.get(rec.requested_grade, ''), rec.member_id.name or '')

    current_grade_label = fields.Char(string='Ceinture (libellé)', compute='_compute_grade_labels')
    requested_grade_label = fields.Char(string='Grade (libellé)', compute='_compute_grade_labels')

    @api.depends('current_grade', 'requested_grade')
    def _compute_grade_labels(self):
        labels = dict(GRADES)
        for rec in self:
            rec.current_grade_label = labels.get(rec.current_grade, '')
            rec.requested_grade_label = labels.get(rec.requested_grade, '')

    @api.depends('result')
    def _compute_result_label(self):
        labels = dict(RESULTS)
        for rec in self:
            rec.result_label = labels.get(rec.result, '')
