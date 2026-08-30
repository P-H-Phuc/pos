import base64
import logging

import requests

from odoo import http

_logger = logging.getLogger(__name__)

# PAX POS Link special bytes
STX = 0x02
ETX = 0x03
FS = 0x1C  # Field Separator between top-level fields
US = 0x1F  # Unit Separator between sub-fields within a section


def _compute_lrc(data: bytes) -> int:
    """XOR all bytes to produce the Longitudinal Redundancy Check byte."""
    lrc = 0
    for b in data:
        lrc ^= b
    return lrc


def _encode_string(s: str) -> bytes:
    return s.encode("ascii", errors="replace")


def build_pos_link_request(command: str, version: str = "1.28", *params) -> bytes:
    """
    Build a PAX POS Link binary frame.

    Frame layout:
        STX | Length(4 ASCII) | Command | FS | Version | FS | [Param FS]… | ETX | LRC

    The resulting bytes are then base64-encoded before being appended to
    the HTTP GET query string sent to the terminal.
    """
    parts = [_encode_string(command), _encode_string(version)]
    for p in params:
        if p is None:
            parts.append(b"")
        elif isinstance(p, bytes):
            parts.append(p)
        else:
            parts.append(_encode_string(str(p)))

    body = bytes([FS]).join(parts)
    length_val = len(body) + 1  # +1 for ETX
    length_bytes = f"{length_val:04d}".encode()

    inner = length_bytes + body + bytes([ETX])
    lrc = _compute_lrc(inner)
    return bytes([STX]) + inner + bytes([lrc])


def pos_link_to_base64(frame: bytes) -> str:
    """Base64-encode a POS Link frame for use in the PAX HTTP GET request."""
    return base64.b64encode(frame).decode("ascii")


def parse_pos_link_response(raw: bytes) -> dict:
    """
    Parse the raw bytes returned by the PAX terminal HTTP endpoint.

    Response frame format:
        STX | Length(4) | Command | FS | Version | FS | RespCode | FS | RespMsg
        | FS | [fields…] | ETX | LRC
    """
    if not raw or raw[0] != STX:
        return {"success": False, "error": "Invalid response: missing STX"}

    # Find ETX
    try:
        etx_pos = raw.index(ETX, 1)
    except ValueError:
        return {"success": False, "error": "Invalid response: missing ETX"}

    # inner = everything between STX and ETX (excluding both)
    inner = raw[1:etx_pos]

    # Skip 4-byte length prefix
    payload = inner[4:]
    fields = payload.split(bytes([FS]))

    def _f(idx):
        return (
            fields[idx].decode("ascii", errors="replace") if len(fields) > idx else ""
        )

    result = {
        "command": _f(0),
        "version": _f(1),
        "response_code": _f(2),
        "response_message": _f(3),
    }
    result["success"] = result["response_code"] == "000000"

    cmd = result["command"]
    if cmd in ("T00", "T02"):  # DoCredit / DoRefund
        # Map positional fields; some sub-fields are US-separated within a field
        extra_labels = [
            "host_response_code",
            "host_response_message",
            "auth_code",
            "reference_number",
            "transaction_id",
            "extra_data",
            "trace_number",
            "eod_record",
            "avn",
            "approved_amount",
            "balance",
            "card_holder_name",
            "expiry_date",
            "first_six",
            "last_four",
        ]
        for i, label in enumerate(extra_labels, start=4):
            result[label] = _f(i)

    return result


class PaxTerminalController(http.Controller):
    """
    Server-side proxy for PAX POS Link commands.

    The browser JS layer cannot contact the PAX terminal directly (CORS / same-origin
    policy), so it calls these JSON-RPC endpoints, which forward the command to the
    terminal's HTTP server and relay the parsed response back.
    """

    def _build_terminal_url(
        self, ip: str, port: int, frame: bytes, use_https: bool
    ) -> str:
        scheme = "https" if use_https else "http"
        b64 = pos_link_to_base64(frame)
        return f"{scheme}://{ip}:{port}?{b64}"

    def _send_to_terminal(
        self, ip: str, port: int, frame: bytes, timeout: int, use_https: bool
    ) -> dict:
        url = self._build_terminal_url(ip, port, frame, use_https)
        try:
            resp = requests.get(url, timeout=timeout, verify=False)
            resp.raise_for_status()
            return parse_pos_link_response(resp.content)
        except requests.exceptions.Timeout:
            _logger.warning(
                "PAX terminal at %s:%s timed out after %ss", ip, port, timeout
            )
            return {"success": False, "error": "Terminal request timed out"}
        except requests.exceptions.ConnectionError as exc:
            _logger.error("Cannot connect to PAX terminal at %s:%s — %s", ip, port, exc)
            return {"success": False, "error": f"Cannot connect to terminal: {exc}"}
        except Exception as exc:
            _logger.exception(
                "Unexpected error communicating with PAX terminal at %s:%s", ip, port
            )
            return {"success": False, "error": str(exc)}

    @http.route(
        "/pos/pax_terminal/do_credit", type="json", auth="user", methods=["POST"]
    )
    def do_credit(
        self,
        terminal_ip,
        terminal_port,
        amount_cents,
        currency_code,
        order_id,
        transaction_type="01",
        timeout=120,
        use_https=False,
    ):
        """
        Proxy a T00 DoCredit (sale) request.

        :param transaction_type: PAX transaction type code.
            "01" = Sale, "02" = Return, "04" = Void, "05" = Auth, "06" = Post-Auth
        """
        frame = build_pos_link_request(
            "T00",
            "1.28",
            transaction_type,  # transaction type
            str(amount_cents),  # amount (cents)
            "",  # tip amount
            "",  # cash back
            "",  # merchant fee
            "",  # tax amount
            "",  # fuel amount
            "",  # service fee
            "",  # surcharge
            "",  # discount
            "",  # original amount
            "",  # invoice number
            order_id,  # reference / ECR reference
            "",  # auth code (offline)
            "",  # transaction id (for void/post-auth)
            currency_code,  # ISO 4217 numeric
        )
        return self._send_to_terminal(
            terminal_ip, terminal_port, frame, timeout, use_https
        )

    @http.route("/pos/pax_terminal/do_void", type="json", auth="user", methods=["POST"])
    def do_void(
        self,
        terminal_ip,
        terminal_port,
        original_transaction_id,
        original_auth_code,
        amount_cents,
        timeout=120,
        use_https=False,
    ):
        """Proxy a T00 Void request (transaction_type=04)."""
        frame = build_pos_link_request(
            "T00",
            "1.28",
            "04",
            str(amount_cents),
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
            "",
            original_auth_code,
            original_transaction_id,
        )
        return self._send_to_terminal(
            terminal_ip, terminal_port, frame, timeout, use_https
        )

    @http.route(
        "/pos/pax_terminal/initialize", type="json", auth="user", methods=["POST"]
    )
    def initialize(self, terminal_ip, terminal_port, timeout=30, use_https=False):
        """Send A08 Initialize — test connectivity and retrieve terminal info."""
        frame = build_pos_link_request("A08", "1.28")
        return self._send_to_terminal(
            terminal_ip, terminal_port, frame, timeout, use_https
        )
