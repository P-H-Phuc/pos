Integrates **PAX payment terminals** with Odoo 18.0 Point of Sale via a
**local pywebdriver proxy** — designed for cloud-hosted Odoo where the
PAX terminal is only reachable on the store's local network.

![PAX payment method configuration](static/description/img/payment_method_pax.png)

## How it works

The module relays PAX terminal payments through a pywebdriver instance
running on the store PC:

```
Odoo POS (browser)
    │
    │  JSON-RPC silentCall
    ▼
Odoo server (backend)
    │
    │  HTTP POST → /hw_proxy/pax/transaction_execute
    ▼
pywebdriver (store PC, default port 8069)
    │
    │  HTTP GET (POS Link binary frame) → port 10009
    ▼
PAX Terminal
```

Supported transactions:

| POS Link Command | Description |
|---|---|
| T00 DoSale | Charge a card for a sale |
| T02 DoRefund | Refund to a card |
| T04 DoVoid | Void a previous transaction |

## When to use this module

Use `pos_payment_pax_terminal_pywebdriver` when:

- Odoo is **cloud-hosted** and cannot reach the terminal's LAN IP directly
- Chrome's **Local Network Access (LNA)** enforcement (v142+) blocks direct browser-to-terminal calls

Use `pos_payment_pax_terminal_redirect` instead when Odoo is on-premise
and has direct TCP access to the terminal on port 10009.
