##############################################################################
#
#    Copyright since 2009 Trobz (<https://trobz.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_amount = fields.Float(
        string="Available Credit",
        digits=0,
    )
    credit_line_ids = fields.Many2many(
        comodel_name="pos.payment",
        string="Credit History",
        compute="_compute_credit_line",
    )

    def _compute_credit_line(self):
        for partner in self:
            pos_payments = (
                self.env["pos.payment"]
                .sudo()
                .search(
                    [
                        ("partner_id", "in", partner.ids),
                        ("payment_method_id.is_credit", "=", True),
                    ],
                    order="payment_date desc",
                )
            )
            partner.credit_line_ids = pos_payments

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        res += ["credit_amount"]
        return res
