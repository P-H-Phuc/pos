# Copyright 2024 Trobz
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PaxTransactionLog(models.Model):
    _name = "pax.transaction.log"
    _description = "PAX Terminal Transaction Log"
    _order = "transaction_date desc"

    terminal_id = fields.Many2one("pax.terminal", ondelete="set null")
    transaction_type = fields.Selection(
        [
            ("01", "Sale"),
            ("02", "Return"),
            ("04", "Void"),
            ("05", "Auth"),
            ("06", "Post-Auth"),
        ],
        default="01",
    )
    amount = fields.Float(digits=(16, 2))
    reference = fields.Char()
    result_code = fields.Char()
    result_message = fields.Char()
    success = fields.Boolean(string="Successful")
    auth_code = fields.Char()
    transaction_id = fields.Char(string="Terminal Transaction ID")
    card_type = fields.Char()
    last_four = fields.Char(string="Card Last Four Digits")
    raw_response = fields.Text()
    transaction_date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
    )
    pos_order_id = fields.Many2one("pos.order", ondelete="set null")
    pos_payment_id = fields.Many2one("pos.payment", ondelete="set null")

    @api.depends("reference", "transaction_date")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.reference or '—'} / {rec.transaction_date}"
