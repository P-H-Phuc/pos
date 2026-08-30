import logging
import re

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..controllers.main import (
    build_pos_link_request,
    parse_pos_link_response,
    pos_link_to_base64,
)

_logger = logging.getLogger(__name__)

_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)


class PaxTerminal(models.Model):
    _name = "pax.terminal"
    _description = "PAX Payment Terminal"
    _inherit = ["pos.load.mixin"]

    name = fields.Char(string="Terminal Name", required=True)
    ip_address = fields.Char(
        required=True,
        help="IP address only — do not include http:// (e.g. 192.168.1.100)",
    )
    port = fields.Integer(default=10009)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    pos_config_ids = fields.Many2many(
        "pos.config",
        help="POS sessions that can use this terminal.",
    )
    payment_method_ids = fields.One2many(
        "pos.payment.method",
        "pax_terminal_id",
    )
    transaction_log_ids = fields.One2many(
        "pax.transaction.log",
        "terminal_id",
    )
    timeout = fields.Integer(
        string="Transaction Timeout (ms)",
        default=120000,
        help="Maximum time (milliseconds) to wait for a terminal response.",
    )
    use_https = fields.Boolean(
        default=False,
        help="Enable when the terminal is configured for TLS connections.",
    )
    demo_mode = fields.Boolean(
        help="Simulate transactions without contacting a real terminal.",
    )

    # ------------------------------------------------------------------
    # pos.load.mixin
    # ------------------------------------------------------------------

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = data["pos.config"]["data"][0]["id"]
        return [
            ("active", "=", True),
            ("company_id", "=", self.env.company.id),
            "|",
            ("pos_config_ids", "=", False),
            ("pos_config_ids", "in", [config_id]),
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["id", "name", "ip_address", "port", "timeout", "use_https", "demo_mode"]

    # ------------------------------------------------------------------
    # Constraints & onchange
    # ------------------------------------------------------------------

    @api.constrains("ip_address")
    def _check_ip_address(self):
        for rec in self:
            if _SCHEME_RE.match(rec.ip_address or ""):
                raise ValidationError(
                    rec.env._(
                        "IP Address should contain only the host/IP, not a URL"
                        " scheme.\nEnter '%(clean)s' instead of '%(raw)s'.",
                        clean=_SCHEME_RE.sub("", rec.ip_address).rstrip("/"),
                        raw=rec.ip_address,
                    )
                )

    @api.onchange("ip_address")
    def _onchange_ip_address_strip_scheme(self):
        """Silently strip http:// or https:// if the user pastes a full URL."""
        if self.ip_address and _SCHEME_RE.match(self.ip_address):
            self.ip_address = _SCHEME_RE.sub("", self.ip_address).rstrip("/")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_test_connection(self):
        self.ensure_one()
        result = self._send_command(build_pos_link_request("A08", "1.28"), timeout=10)
        if result.get("success"):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("Connection OK"),
                    "message": self.env._(
                        "PAX terminal '%(name)s' responded successfully.",
                        name=self.name,
                    ),
                    "type": "success",
                    "sticky": False,
                },
            }
        raise UserError(
            self.env._(
                "Cannot reach terminal '%(name)s': %(error)s",
                name=self.name,
                error=result.get("error", "Unknown error"),
            )
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send_command(self, frame: bytes, timeout: int = 120) -> dict:
        """Send a POS Link frame to this terminal and return the parsed response."""
        self.ensure_one()
        ip = _SCHEME_RE.sub("", self.ip_address or "").strip().rstrip("/")
        scheme = "https" if self.use_https else "http"
        b64 = pos_link_to_base64(frame)
        url = f"{scheme}://{ip}:{self.port}?{b64}"
        try:
            resp = requests.get(url, timeout=timeout, verify=False)
            resp.raise_for_status()
            return parse_pos_link_response(resp.content)
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Terminal request timed out"}
        except requests.exceptions.ConnectionError as exc:
            return {"success": False, "error": f"Connection error: {exc}"}
        except Exception as exc:
            _logger.exception("Unexpected error contacting PAX terminal %s", self.name)
            return {"success": False, "error": str(exc)}
