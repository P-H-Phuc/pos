from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    change_account_id = fields.Many2one(
        comodel_name="account.account", string="Account for the Change"
    )
