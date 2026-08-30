# Copyright 2024 Trobz
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

import requests as req_lib

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, mute_logger

from ..controllers.main import PaxTerminalController


class TestPaxPaymentMethod(TransactionCase):
    """Integration tests for the PAX terminal payment method and models."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.terminal = cls.env["pax.terminal"].create(
            {
                "name": "Test PAX A920",
                "ip_address": "192.168.1.50",
                "port": 10009,
                "timeout": 60000,
                "demo_mode": False,
            }
        )
        cls.payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "PAX Terminal Test",
                "use_payment_terminal": "pax_terminal",
                "pax_terminal_id": cls.terminal.id,
                "pax_transaction_type": "01",
                "receivable_account_id": cls.env["account.account"]
                .search([("account_type", "=", "asset_receivable")], limit=1)
                .id,
            }
        )

    # ------------------------------------------------------------------
    # pax.terminal model
    # ------------------------------------------------------------------

    def test_terminal_created(self):
        self.assertTrue(self.terminal.id)
        self.assertEqual(self.terminal.ip_address, "192.168.1.50")
        self.assertEqual(self.terminal.port, 10009)

    def test_terminal_default_active(self):
        self.assertTrue(self.terminal.active)

    # ------------------------------------------------------------------
    # pos.payment.method
    # ------------------------------------------------------------------

    def test_payment_terminal_selection_includes_pax(self):
        selections = self.payment_method._get_payment_terminal_selection()
        codes = [s[0] for s in selections]
        self.assertIn("pax_terminal", codes)

    def test_pax_terminal_ip_relayed(self):
        self.assertEqual(self.payment_method.pax_terminal_ip, "192.168.1.50")

    def test_pax_terminal_port_relayed(self):
        self.assertEqual(self.payment_method.pax_terminal_port, 10009)

    def test_load_pos_data_fields_includes_pax(self):
        config = self.env["pos.config"].search([], limit=1)
        if not config:
            self.skipTest("No POS config found in the database")
        fields = self.payment_method._load_pos_data_fields(config.id)
        for f in [
            "pax_terminal_id",
            "pax_terminal_ip",
            "pax_terminal_port",
            "pax_transaction_type",
        ]:
            self.assertIn(f, fields)

    def test_constraint_requires_terminal_when_pax_selected(self):
        with self.assertRaises(ValidationError):
            self.env["pos.payment.method"].create(
                {
                    "name": "PAX No Terminal",
                    "use_payment_terminal": "pax_terminal",
                    "pax_terminal_id": False,
                    "receivable_account_id": self.env["account.account"]
                    .search([("account_type", "=", "asset_receivable")], limit=1)
                    .id,
                }
            )

    # ------------------------------------------------------------------
    # pax_send_payment — mocked terminal response
    # ------------------------------------------------------------------

    def test_pax_send_payment_success(self):
        mock_result = {
            "success": True,
            "response_code": "000000",
            "response_message": "APPROVED",
            "auth_code": "AUTH99",
            "transaction_id": "TXN001",
            "last_four": "4242",
            "card_holder_name": "JOHN DOE",
        }
        with patch.object(
            self.terminal.__class__, "_send_command", return_value=mock_result
        ):
            result = self.payment_method.pax_send_payment(
                {
                    "terminal_ip": "192.168.1.50",
                    "terminal_port": 10009,
                    "amount_cents": 1500,
                    "currency_code": "840",
                    "order_id": "POS00001",
                    "transaction_type": "01",
                    "timeout": 60,
                    "use_https": False,
                }
            )
        self.assertEqual(result["payment_status"], "success")
        self.assertEqual(result["auth_code"], "AUTH99")
        self.assertEqual(result["transaction_id"], "TXN001")

    def test_pax_send_payment_declined(self):
        mock_result = {
            "success": False,
            "response_code": "000001",
            "response_message": "DECLINED",
        }
        with patch.object(
            self.terminal.__class__, "_send_command", return_value=mock_result
        ):
            result = self.payment_method.pax_send_payment(
                {
                    "terminal_ip": "192.168.1.50",
                    "terminal_port": 10009,
                    "amount_cents": 500,
                    "currency_code": "840",
                    "order_id": "POS00002",
                    "transaction_type": "01",
                    "timeout": 60,
                    "use_https": False,
                }
            )
        self.assertEqual(result["payment_status"], "failure")
        self.assertIn("DECLINED", result["response_message"])

    def test_pax_send_payment_demo_mode(self):
        self.terminal.demo_mode = True
        try:
            result = self.payment_method.pax_send_payment(
                {
                    "terminal_ip": "192.168.1.50",
                    "terminal_port": 10009,
                    "amount_cents": 2000,
                    "currency_code": "840",
                    "order_id": "DEMO001",
                    "transaction_type": "01",
                    "timeout": 10,
                    "use_https": False,
                }
            )
            self.assertEqual(result["payment_status"], "success")
            self.assertIn("DEMO", result["response_message"])
        finally:
            self.terminal.demo_mode = False

    def test_pax_send_payment_logs_transaction(self):
        mock_result = {
            "success": True,
            "response_code": "000000",
            "response_message": "APPROVED",
            "auth_code": "AX1234",
            "transaction_id": "TXN999",
            "last_four": "1111",
            "card_holder_name": "",
        }
        before_count = self.env["pax.transaction.log"].search_count(
            [("terminal_id", "=", self.terminal.id)]
        )
        with patch.object(
            self.terminal.__class__, "_send_command", return_value=mock_result
        ):
            self.payment_method.pax_send_payment(
                {
                    "terminal_ip": "192.168.1.50",
                    "terminal_port": 10009,
                    "amount_cents": 750,
                    "currency_code": "840",
                    "order_id": "POS00003",
                    "transaction_type": "01",
                    "timeout": 60,
                    "use_https": False,
                }
            )
        after_count = self.env["pax.transaction.log"].search_count(
            [("terminal_id", "=", self.terminal.id)]
        )
        self.assertEqual(after_count, before_count + 1)

    # ------------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------------

    def test_controller_builds_correct_url(self):
        ctrl = PaxTerminalController()
        with patch(
            "odoo.addons.pos_payment_pax_terminal_direct.controllers.main.requests.get"
        ) as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = b""
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            with patch(
                "odoo.addons.pos_payment_pax_terminal_direct.controllers.main.parse_pos_link_response",
                return_value={"success": True},
            ):
                ctrl.do_credit(
                    terminal_ip="192.168.1.50",
                    terminal_port=10009,
                    amount_cents=1000,
                    currency_code="840",
                    order_id="CTRL001",
                )

        url = mock_get.call_args[0][0]
        self.assertIn("192.168.1.50:10009", url)
        self.assertTrue(url.startswith("http://"))
        # URL should have base64 query string
        self.assertIn("?", url)

    def test_controller_uses_https_when_flag_set(self):
        ctrl = PaxTerminalController()
        with patch(
            "odoo.addons.pos_payment_pax_terminal_direct.controllers.main.requests.get"
        ) as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = b""
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            with patch(
                "odoo.addons.pos_payment_pax_terminal_direct.controllers.main.parse_pos_link_response",
                return_value={"success": True},
            ):
                ctrl.do_credit(
                    terminal_ip="192.168.1.50",
                    terminal_port=10009,
                    amount_cents=100,
                    currency_code="840",
                    order_id="CTRL002",
                    use_https=True,
                )

        url = mock_get.call_args[0][0]
        self.assertTrue(url.startswith("https://"))

    @mute_logger("odoo.addons.pos_payment_pax_terminal_direct.controllers.main")
    def test_controller_timeout_returns_error(self):
        ctrl = PaxTerminalController()
        with patch(
            "odoo.addons.pos_payment_pax_terminal_direct.controllers.main.requests.get",
            side_effect=req_lib.exceptions.Timeout,
        ):
            result = ctrl.do_credit(
                terminal_ip="10.0.0.99",
                terminal_port=10009,
                amount_cents=500,
                currency_code="840",
                order_id="ERR001",
            )
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])

    @mute_logger("odoo.addons.pos_payment_pax_terminal_direct.controllers.main")
    def test_controller_connection_error(self):
        ctrl = PaxTerminalController()
        with patch(
            "odoo.addons.pos_payment_pax_terminal_direct.controllers.main.requests.get",
            side_effect=req_lib.exceptions.ConnectionError("refused"),
        ):
            result = ctrl.initialize(terminal_ip="10.0.0.99", terminal_port=10009)
        self.assertFalse(result["success"])
        self.assertIn("connect", result["error"].lower())
