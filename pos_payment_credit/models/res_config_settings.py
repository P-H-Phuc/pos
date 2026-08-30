from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_auto_apply_credit_amount = fields.Boolean(
        related="pos_config_id.auto_apply_credit_amount",
        readonly=False,
    )
