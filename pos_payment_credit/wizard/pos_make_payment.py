# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PosMakePayment(models.TransientModel):
    _inherit = "pos.make.payment"

    is_credit = fields.Boolean(
        string="Allow to add credit for members", related="payment_method_id.is_credit"
    )

    def check(self):
        res = super().check()
        self._update_credit_partner()
        return res

    def _update_credit_partner(self):
        self.ensure_one()
        if not self.is_credit:
            return
        order = self.env["pos.order"].browse(self.env.context.get("active_id", False))
        order.partner_id.sudo().credit_amount -= self.amount
        channel = "res.partner.credit_amout/updated"
        self.env.user.partner_id._bus_send(
            channel,
            {
                "id": order.partner_id.id,
                "credit_amount": order.partner_id.credit_amount,
            },
        )
