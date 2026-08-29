import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        res = super()._get_payment_terminal_selection()
        res.append(("pax_pywebdriver", "PAX Terminal (pywebdriver)"))
        return res

    pax_pw_terminal_ip = fields.Char(
        string="Terminal IP",
        help="IP address of the PAX terminal reachable from pywebdriver "
        "(do not include http://).",
    )
    pax_pw_terminal_port = fields.Integer(
        string="Terminal Port",
        default=10009,
        help="TCP port of the PAX terminal HTTP server (default: 10009).",
    )
    pax_pw_transaction_type = fields.Selection(
        [
            ("01", "Sale"),
            ("02", "Return/Refund"),
            ("05", "Auth Only"),
            ("06", "Post-Auth"),
        ],
        string="Default Transaction Type",
        default="01",
    )
    pax_pw_timeout = fields.Integer(
        string="Timeout (ms)",
        default=120000,
        help="Maximum time to wait for a terminal response (milliseconds).",
    )
    pax_pw_use_https = fields.Boolean(
        string="Use HTTPS",
        default=False,
        help="Enable if the PAX terminal is configured for TLS connections.",
    )
    pax_pw_fast_payments = fields.Boolean(
        string="Fast Payments",
        default=True,
        help="When enabled, the payment request is sent automatically as soon as "
        "the PAX payment method is selected (no manual 'Send' click needed). "
        "Disable to let the cashier review the amount before sending.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.extend(
            [
                "pax_pw_terminal_ip",
                "pax_pw_terminal_port",
                "pax_pw_transaction_type",
                "pax_pw_timeout",
                "pax_pw_use_https",
                "pax_pw_fast_payments",
            ]
        )
        return result

    def pax_pywebdriver_send_payment(self, data):
        """
        Called via RPC from the POS JS layer.

        Forwards the payment request to pywebdriver's synchronous
        /hw_proxy/pax/transaction_execute endpoint.  pywebdriver then contacts
        the PAX terminal on the local network and returns the parsed result.

        :param data: dict built by the JS layer — keys:
            terminal_ip, terminal_port, use_https, amount (float),
            currency_code, order_id, transaction_type, timeout (ms)
        :return: dict with 'payment_status' ("success" | "failure" | "error")
        """
        self.ensure_one()

        pywebdriver_url = (
            data.get("pywebdriver_url") or "http://127.0.0.1:8069"
        ).rstrip("/")
        endpoint = f"{pywebdriver_url}/hw_proxy/pax/transaction_execute"

        # Add a 10 s buffer so the HTTP client doesn't time out before PAX does
        timeout_ms = data.get("timeout") or self.pax_pw_timeout or 120000
        http_timeout = timeout_ms // 1000 + 10

        _logger.info(
            "PAX pywebdriver: forwarding payment to %s — amount=%s order=%s",
            endpoint,
            data.get("amount"),
            data.get("order_id"),
        )

        try:
            resp = requests.post(
                endpoint,
                json={"params": {"payment_info": data}},
                timeout=http_timeout,
            )
            resp.raise_for_status()
            result = resp.json().get("result", {})
        except requests.exceptions.Timeout:
            _logger.error("PAX pywebdriver: request to %s timed out", endpoint)
            return {
                "payment_status": "error",
                "message": "pywebdriver request timed out",
            }
        except requests.exceptions.ConnectionError as exc:
            _logger.error("PAX pywebdriver: cannot connect to %s — %s", endpoint, exc)
            return {
                "payment_status": "error",
                "message": f"Cannot connect to pywebdriver at {pywebdriver_url}: {exc}",
            }
        except Exception as exc:
            _logger.exception("PAX pywebdriver: unexpected error")
            return {"payment_status": "error", "message": str(exc)}

        if result.get("success"):
            return {
                "payment_status": "success",
                "transaction_id": result.get("transaction_id", ""),
                "auth_code": result.get("auth_code", ""),
                "response_message": result.get("response_message", ""),
                "last_four": result.get("last_four", ""),
                "card_holder_name": result.get("card_holder_name", ""),
            }

        return {
            "payment_status": "failure",
            "response_code": result.get("response_code", ""),
            "response_message": result.get("response_message")
            or result.get("error", ""),
        }
