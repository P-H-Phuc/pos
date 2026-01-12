from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    liquidity_account_id = fields.Many2one(
        "account.account",
        check_company=True,
        copy=False,
        help="The liquidity account for this statement line.",
    )

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        liquidity_line_vals, counterpart_line_vals = (
            super()._prepare_move_line_default_vals(counterpart_account_id)
        )
        if self.liquidity_account_id:
            liquidity_line_vals.update(
                {
                    "account_id": self.liquidity_account_id.id,
                }
            )
        return [liquidity_line_vals, counterpart_line_vals]
