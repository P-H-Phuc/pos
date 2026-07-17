import random
import string

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..controllers.main import build_pos_link_request


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        res = super()._get_payment_terminal_selection()
        res.append(("pax_terminal", "PAX Terminal"))
        return res

    pax_terminal_id = fields.Many2one(
        "pax.terminal",
        help="PAX terminal device to use for this payment method.",
    )
    pax_terminal_ip = fields.Char(
        related="pax_terminal_id.ip_address",
        string="Terminal IP",
        readonly=True,
    )
    pax_terminal_port = fields.Integer(
        related="pax_terminal_id.port",
        string="Terminal Port",
        readonly=True,
    )
    pax_transaction_type = fields.Selection(
        [
            ("01", "Sale"),
            ("02", "Return/Refund"),
            ("05", "Auth Only"),
            ("06", "Post-Auth"),
        ],
        string="Default Transaction Type",
        default="01",
    )
    pax_timeout = fields.Integer(
        related="pax_terminal_id.timeout",
        string="Timeout (ms)",
        readonly=True,
    )

    @api.constrains("use_payment_terminal", "pax_terminal_id")
    def _check_pax_terminal(self):
        for rec in self:
            if rec.use_payment_terminal == "pax_terminal" and not rec.pax_terminal_id:
                raise ValidationError(
                    rec.env._(
                        "A PAX Terminal must be selected when using"
                        " the PAX payment terminal integration."
                    )
                )

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.extend(
            [
                "pax_terminal_id",
                "pax_terminal_ip",
                "pax_terminal_port",
                "pax_transaction_type",
                "pax_timeout",
            ]
        )
        return result

    def pax_send_payment(self, data):
        """
        Called via RPC from the POS JS layer (silentCall).

        :param data: dict with keys:
            - terminal_ip, terminal_port, amount_cents, currency_code,
              order_id, transaction_type, timeout, use_https
        :return: dict with 'payment_status' ("success" | "failure" | "error")
                 and optional 'transaction_id', 'auth_code', 'response_message'
        """
        self.ensure_one()
        terminal = self.pax_terminal_id
        if not terminal:
            return {"payment_status": "error", "message": "No PAX terminal configured"}

        if terminal.demo_mode:
            return self._pax_simulate_payment(data)

        frame = build_pos_link_request(
            "T00",
            "1.28",
            data.get("transaction_type", "01"),
            str(data.get("amount_cents", 0)),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            data.get("order_id", ""),
            "",
            "",
            data.get("currency_code", "840"),
        )
        timeout_s = (terminal.timeout or 120000) // 1000
        result = terminal._send_command(frame, timeout=timeout_s)

        if result.get("success"):
            self._log_transaction(terminal, data, result, success=True)
            return {
                "payment_status": "success",
                "transaction_id": result.get("transaction_id", ""),
                "auth_code": result.get("auth_code", ""),
                "response_message": result.get("response_message", ""),
                "last_four": result.get("last_four", ""),
                "card_holder_name": result.get("card_holder_name", ""),
            }

        self._log_transaction(terminal, data, result, success=False)
        return {
            "payment_status": "failure",
            "response_code": result.get("response_code", ""),
            "response_message": result.get("response_message")
            or result.get("error", ""),
        }

    def _pax_simulate_payment(self, data):
        """Return a simulated approved response for demo/testing purposes."""
        auth = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return {
            "payment_status": "success",
            "transaction_id": f"DEMO{random.randint(10000, 99999)}",
            "auth_code": auth,
            "response_message": "DEMO APPROVED",
            "last_four": "1234",
            "card_holder_name": "DEMO CUSTOMER",
        }

    def _log_transaction(self, terminal, data, result, success):
        self.env["pax.transaction.log"].create(
            {
                "terminal_id": terminal.id,
                "transaction_type": data.get("transaction_type", "01"),
                "amount": (data.get("amount_cents", 0) or 0) / 100.0,
                "reference": data.get("order_id", ""),
                "result_code": result.get("response_code", ""),
                "result_message": result.get("response_message")
                or result.get("error", ""),
                "success": success,
                "auth_code": result.get("auth_code", ""),
                "transaction_id": result.get("transaction_id", ""),
                "raw_response": str(result),
            }
        )
