Integrates **PAX payment terminals** with Odoo 18.0 Point of Sale using the
**semi-integrated** (POS Link over HTTP) mode — no pywebdriver or hardware proxy required.

![PAX Terminal configuration form](static/description/img/pax_terminal.png)

## How it works

The module uses PAX's **POS Link protocol** to communicate directly with the
terminal over the local network via HTTP:

```
Odoo POS (browser)
    │
    │  JSON-RPC
    ▼
Odoo server (controller)
    │
    │  HTTP POST  ─  POS Link binary frame
    ▼
PAX Terminal (IP:port, default 10009)
```

Supported transactions:

| POS Link Command | Description |
|---|---|
| T00 DoSale | Charge a card for a sale |
| T02 DoRefund | Refund to a card |
| T04 DoVoid | Void a previous transaction |
| A08 GetBatchSummary | Check terminal connectivity |

## Protocol

PAX POS Link binary frame structure:

```
STX (0x02) | Length (4 ASCII digits) | Command | FS | Version | FS | [Fields…] | ETX (0x03) | LRC
```

- **FS** = 0x1C (field separator)
- **LRC** = XOR of all bytes from Length through ETX (inclusive)
