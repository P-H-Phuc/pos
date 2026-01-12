from odoo import fields, models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _prepare_account_bank_statement_line_vals(
        self, session, sign, amount, reason, extras
    ):
        res = super()._prepare_account_bank_statement_line_vals(
            session, sign, amount, reason, extras
        )
        cash_method = session.payment_method_ids.filtered("is_cash_count")[:1]
        if cash_method.change_account_id:
            res["liquidity_account_id"] = cash_method.change_account_id.id
        return res


class PoSOrder(models.Model):
    _inherit = "pos.order"

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        res = super()._process_payment_lines(pos_order, order, pos_session, draft)
        cash_method = pos_session.payment_method_ids.filtered("is_cash_count")[:1]
        if self._condition_create_cash_change_payment_move(cash_method, draft):
            self._process_cash_change_payments(
                pos_order, order, pos_session, cash_method
            )
        return res

    def _condition_create_cash_change_payment_move(self, cash_method, draft):
        return bool(not draft and cash_method and cash_method.change_account_id)

    def _prepare_account_bank_statement_line_vals(
        self,
        pos_session,
        journal,
        amount,
        counterpart_account,
        liquidity_account,
        track_number,
    ):
        return {
            "pos_session_id": pos_session.id,
            "journal_id": journal.id,
            "amount": amount,
            "date": fields.Date.context_today(self),
            "payment_ref": self._get_cash_transfer_label(pos_session, track_number),
            "counterpart_account_id": counterpart_account.id,
            "liquidity_account_id": liquidity_account.id,
        }

    def _process_cash_change_payments(self, pos_order, order, pos_session, cash_method):
        amount_total = pos_order["amount_total"]
        tracking_number = order.tracking_number
        journal = pos_session.cash_journal_id
        counterpart_account_id = journal.default_account_id
        liquidity_account_id = cash_method.change_account_id
        statement_line_vals = self._prepare_account_bank_statement_line_vals(
            pos_session,
            journal,
            amount_total,
            counterpart_account_id,
            liquidity_account_id,
            tracking_number,
        )
        self.env["account.bank.statement.line"].create(statement_line_vals)

    def _get_cash_transfer_label(self, pos_session, tracking_number):
        """Return translatable label for cash transfer."""
        return self.env._(
            "Cash transfer for session: %s - Order number: %s",
            pos_session.name,
            tracking_number,
        )
