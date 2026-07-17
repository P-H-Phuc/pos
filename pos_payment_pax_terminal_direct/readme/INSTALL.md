## Prerequisites

- Odoo 18.0
- Python `requests` library (standard in Odoo installations)
- PAX terminal with **POS Link HTTP** mode enabled on the local network

## Steps

1. Copy or clone the `pos_payment_pax_terminal_direct` directory into your Odoo
   addons path (e.g. `extra_addons/pos/`).
2. Restart the Odoo server to pick up the new module.
3. Go to **Apps**, search for **POS Payment PAX Terminal**, and click **Install**.
4. Follow the [Configuration](CONFIGURATION.md) guide to register your terminal
   and create a payment method.

## No pywebdriver required

This module communicates directly with the PAX terminal over HTTP from the
Odoo server. There is no dependency on `pywebdriver` or any browser-based
hardware proxy.
