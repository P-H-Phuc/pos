## Prerequisites

- Odoo 18.0
- Python `requests` library (standard in Odoo installations)
- **pywebdriver** installed on the store PC with the PAX plugin enabled
- PAX terminal with **POS Link HTTP** mode enabled on the local network

## Steps

1. Install and start pywebdriver on the store PC. Ensure the PAX plugin
   (`pax_driver.py`) is loaded and the terminal IP is reachable from that PC.
2. Copy or clone the `pos_payment_pax_terminal_pywebdriver` directory into
   your Odoo addons path (e.g. `extra_addons/pos/`).
3. Restart the Odoo server to pick up the new module.
4. Go to **Apps**, search for **POS Payment PAX (pywebdriver)**, and click
   **Install**.
5. Follow the [Configuration](CONFIGURATION.md) guide to set up the payment
   method.

## pywebdriver setup

![IoT / pywebdriver hardware proxy configuration](static/description/img/iot_config.png)

The pywebdriver instance must expose the PAX endpoint at:

```
POST http://<store-pc-ip>:<port>/hw_proxy/pax/transaction_execute
```

The default pywebdriver port is **8069**. The PAX driver plugin must be
enabled in pywebdriver's configuration.
