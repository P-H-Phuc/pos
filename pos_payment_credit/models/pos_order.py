from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    partner_id = fields.Many2one(inverse="_inverse_partner_id")

    def _inverse_partner_id(self):
        credit_orders = self.filtered(
            lambda order: order.amount_total
            and order.partner_id
            and order.payment_ids.filtered(lambda p: p.payment_method_id.is_credit)
        )
        for order in credit_orders:
            credit_paymetns = order.payment_ids.filtered(
                lambda p: p.payment_method_id.is_credit
            )
            total_credit_amount = sum(credit_paymetns.mapped("amount"))
            order.sudo().partner_id.credit_amount -= total_credit_amount
