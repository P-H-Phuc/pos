## Create a payment method

Go to **Point of Sale → Configuration → Payment Methods → New**:

1. Set **Payment Terminal** to **PAX Terminal (pywebdriver)**.
2. Fill in the connection fields:

| Field | Description |
|---|---|
| Terminal IP | LAN IP of the PAX terminal as seen from the pywebdriver PC (e.g. `192.168.1.100`) |
| Terminal Port | HTTP port on the PAX terminal (default **10009**) |
| Use HTTPS | Enable if the terminal is configured for TLS |
| Timeout (ms) | Max time to wait for a terminal response (default 120 000 ms) |
| Default Transaction Type | Usually **Sale** |
| Fast Payments | Send the payment request automatically on method selection |

![PAX payment method form](static/description/img/payment_method_pax.png)

## Assign to a POS configuration

Go to **Point of Sale → Configuration → Point of Sale → [your shop]**:

- Under **Payments**, add the PAX (pywebdriver) payment method.

![POS configuration with PAX payment method](static/description/img/pos_config_payment_method_pax.png)

## pywebdriver URL

The Odoo backend forwards the payment to pywebdriver using the URL
configured in the POS hardware proxy settings. By default this is
`http://127.0.0.1:8069` (same host as Odoo). For cloud-hosted Odoo, set
the hardware proxy host to the store PC's IP or hostname where pywebdriver
is running.

## PAX terminal setup

The PAX terminal must have **POS Link HTTP** mode enabled. On most PAX models:

```
Menu → Settings → Communication → Enable POS Link → Port 10009
```

Consult your PAX terminal model's administration guide for the exact steps.
