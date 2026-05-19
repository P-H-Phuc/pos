from odoo import fields, models
from odoo.tools import float_is_zero


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    change_account_id = fields.Many2one(related="journal_id.change_account_id")


class PosPayment(models.Model):
    _inherit = "pos.payment"

    change_account_id = fields.Many2one(related="payment_method_id.change_account_id")

    def _create_payment_moves(self, is_reverse=False):
        result = super()._create_payment_moves(is_reverse)
        cash_payments = self.filtered(
            lambda pay: pay._condition_create_change_payment_move()
        )
        if cash_payments:
            self._process_cash_change_payment(cash_payments)
        return result

    def _condition_create_change_payment_move(self):
        self.ensure_one()
        precision_rounding = self.pos_order_id.currency_id.rounding
        return (
            self.payment_method_id.type == "cash"
            and self.change_account_id
            and not float_is_zero(self.amount, precision_rounding=precision_rounding)
        )

    def _prepare_payment_move_change(self, payment):
        order = payment.pos_order_id
        pos_session = order.session_id
        journal = pos_session.config_id.journal_id
        payment_method = payment.payment_method_id
        payment_move_vals = {
            "journal_id": journal.id,
            "date": fields.Date.context_today(order, order.date_order),
            "ref": self.env._(
                "%(type)s Change payment for %(order)s using %(payment_method)s",
                type="Put Cash" if payment.is_change else "Give",
                order=order.name,
                account_move=order.account_move.name,
                payment_method=payment_method.name,
            ),
            "pos_payment_ids": payment.ids,
        }
        return payment_move_vals

    def _process_cash_change_payment(self, cash_payments):
        AccountMove = self.env["account.move"]
        for payment in cash_payments:
            accounting_partner = self.env["res.partner"]._find_accounting_partner(
                payment.partner_id
            )
            order = payment.pos_order_id
            pos_session = order.session_id
            payment_move_vals = self._prepare_payment_move_change(payment)
            payment_move = AccountMove.create(payment_move_vals)
            payment.write({"account_move_id": payment_move.id})
            amounts = pos_session._update_amounts(
                {"amount": 0, "amount_converted": 0},
                {"amount": payment.amount},
                payment.payment_date,
            )
            if not payment.is_change:
                credit_line_vals = pos_session._credit_amounts(
                    {
                        "account_id": payment.change_account_id.id,
                        "move_id": payment_move.id,
                        "partner_id": accounting_partner.id,
                    },
                    amounts["amount"],
                    amounts["amount_converted"],
                )
                debit_line_vals = pos_session._debit_amounts(
                    {
                        "account_id": accounting_partner.with_company(
                            order.company_id
                        ).property_account_receivable_id.id,
                        "move_id": payment_move.id,
                        "partner_id": accounting_partner.id,
                    },
                    amounts["amount"],
                    amounts["amount_converted"],
                )
                self.env["account.move.line"].create(
                    [credit_line_vals, debit_line_vals]
                )
            elif payment.is_change:
                credit_line_vals = pos_session._credit_amounts(
                    {
                        "account_id": accounting_partner.with_company(
                            order.company_id
                        ).property_account_receivable_id.id,
                        "partner_id": accounting_partner.id,
                        "move_id": payment_move.id,
                    },
                    amounts["amount"],
                    amounts["amount_converted"],
                )
                debit_line_vals = pos_session._debit_amounts(
                    {
                        "account_id": payment.change_account_id.id,
                        "move_id": payment_move.id,
                        "partner_id": accounting_partner.id,
                    },
                    amounts["amount"],
                    amounts["amount_converted"],
                )
                self.env["account.move.line"].create(
                    [credit_line_vals, debit_line_vals]
                )
            payment_move._post()
