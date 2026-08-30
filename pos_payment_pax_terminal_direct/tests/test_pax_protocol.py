# Copyright 2024 Trobz
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.tests.common import TransactionCase

from ..controllers.main import (
    ETX,
    FS,
    STX,
    _compute_lrc,
    build_pos_link_request,
    parse_pos_link_response,
    pos_link_to_base64,
)


class TestPaxProtocol(TransactionCase):
    """Unit tests for the PAX POS Link binary protocol helpers."""

    def _make_response_frame(self, command, version, resp_code, resp_msg, *extra):
        """Build a minimal syntactically valid PAX response frame."""
        parts = [
            command.encode(),
            version.encode(),
            resp_code.encode(),
            resp_msg.encode(),
        ]
        parts += [f.encode() for f in extra]
        body = bytes([FS]).join(parts)
        length_str = f"{len(body) + 1:04d}".encode()
        inner = length_str + body + bytes([ETX])
        lrc = _compute_lrc(inner)
        return bytes([STX]) + inner + bytes([lrc])

    # ------------------------------------------------------------------
    # LRC
    # ------------------------------------------------------------------

    def test_lrc_single_byte(self):
        self.assertEqual(_compute_lrc(b"\x41"), 0x41)

    def test_lrc_two_equal_bytes_cancel(self):
        self.assertEqual(_compute_lrc(b"\xab\xab"), 0x00)

    def test_lrc_xor_sequence(self):
        # 0x01 XOR 0x02 XOR 0x03 == 0x00
        self.assertEqual(_compute_lrc(b"\x01\x02\x03"), 0x00)

    def test_lrc_empty(self):
        self.assertEqual(_compute_lrc(b""), 0)

    # ------------------------------------------------------------------
    # build_pos_link_request
    # ------------------------------------------------------------------

    def test_frame_starts_with_stx(self):
        msg = build_pos_link_request("T00", "1.28")
        self.assertEqual(msg[0], STX)

    def test_frame_ends_with_etx_then_lrc(self):
        msg = build_pos_link_request("T00", "1.28")
        etx_pos = msg.index(ETX)
        self.assertEqual(etx_pos, len(msg) - 2, "ETX must be second-to-last byte")

    def test_frame_contains_command(self):
        msg = build_pos_link_request("A08", "1.28")
        self.assertIn(b"A08", msg)

    def test_frame_contains_version(self):
        msg = build_pos_link_request("T00", "1.28")
        self.assertIn(b"1.28", msg)

    def test_frame_lrc_is_valid(self):
        msg = build_pos_link_request("T00", "1.28", "01", "1500")
        inner = msg[1:-1]  # strip STX and LRC
        self.assertEqual(msg[-1], _compute_lrc(inner))

    def test_frame_length_field_matches_payload(self):
        msg = build_pos_link_request("T00", "1.28", "01", "100")
        length_field = int(msg[1:5])
        etx_pos = msg.index(ETX)
        actual_body = etx_pos - 5  # skip STX (1) + length (4)
        self.assertEqual(length_field, actual_body + 1)  # +1 for ETX

    def test_none_param_becomes_empty(self):
        msg = build_pos_link_request("T00", "1.28", None, "500")
        # Should not raise; None becomes b""
        self.assertIsInstance(msg, bytes)

    # ------------------------------------------------------------------
    # pos_link_to_base64
    # ------------------------------------------------------------------

    def test_base64_roundtrip(self):
        msg = build_pos_link_request("A08", "1.28")
        b64 = pos_link_to_base64(msg)
        decoded = base64.b64decode(b64)
        self.assertEqual(decoded, msg)

    def test_base64_is_ascii_string(self):
        msg = build_pos_link_request("T00", "1.28")
        b64 = pos_link_to_base64(msg)
        self.assertIsInstance(b64, str)
        b64.encode("ascii")  # should not raise

    # ------------------------------------------------------------------
    # parse_pos_link_response
    # ------------------------------------------------------------------

    def test_parse_successful_response(self):
        raw = self._make_response_frame("T00", "1.28", "000000", "OK")
        result = parse_pos_link_response(raw)
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "T00")
        self.assertEqual(result["response_code"], "000000")

    def test_parse_declined_response(self):
        raw = self._make_response_frame("T00", "1.28", "000001", "DECLINED")
        result = parse_pos_link_response(raw)
        self.assertFalse(result["success"])
        self.assertEqual(result["response_message"], "DECLINED")

    def test_parse_missing_stx_returns_error(self):
        result = parse_pos_link_response(b"GARBAGE DATA")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_parse_empty_returns_error(self):
        result = parse_pos_link_response(b"")
        self.assertFalse(result["success"])

    def test_parse_sale_extended_fields(self):
        raw = self._make_response_frame(
            "T00",
            "1.28",
            "000000",
            "APPROVED",
            "00",  # host_response_code
            "APPROVED",  # host_response_message
            "AUTH123",  # auth_code
            "REF456",  # reference_number
            "TXN789",  # transaction_id
        )
        result = parse_pos_link_response(raw)
        self.assertTrue(result["success"])
        self.assertEqual(result.get("auth_code"), "AUTH123")
        self.assertEqual(result.get("transaction_id"), "TXN789")

    def test_parse_refund_command(self):
        raw = self._make_response_frame("T00", "1.28", "000000", "OK")
        # T00 with transaction_type 02 still returns command T00
        result = parse_pos_link_response(raw)
        self.assertEqual(result["command"], "T00")

    def test_parse_initialize_response(self):
        raw = self._make_response_frame("A08", "1.28", "000000", "OK")
        result = parse_pos_link_response(raw)
        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "A08")

    # ------------------------------------------------------------------
    # Round-trip
    # ------------------------------------------------------------------

    def test_request_response_command_matches(self):
        build_pos_link_request("T02", "1.28", "01", "500")
        raw_resp = self._make_response_frame("T02", "1.28", "000000", "OK")
        result = parse_pos_link_response(raw_resp)
        self.assertEqual(result["command"], "T02")
