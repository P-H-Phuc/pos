## 1. Register the PAX terminal

Go to **Point of Sale → PAX Terminals → Terminals → New** and fill in:

| Field | Description |
|---|---|
| Terminal Name | Friendly name shown in the back-office |
| IP Address | LAN IP of the PAX terminal (e.g. `192.168.1.100`) |
| Port | HTTP port (default **10009**) |
| Use HTTPS | Enable if the terminal is configured for TLS |
| Timeout | Max milliseconds to wait per transaction (default 120 000) |
| Demo Mode | Simulate transactions without real hardware |
| POS Configurations | Limit this terminal to specific POS sessions |

Click **Test Connection** to verify the terminal is reachable.

![PAX Terminal payment method configuration](static/description/img/pax_terminal_payment_method.png)

## 2. Create a payment method

Go to **Point of Sale → Configuration → Payment Methods → New**:

1. Set **Payment Terminal** to **PAX Terminal**.
2. Select the **PAX Terminal** created above.
3. Set **Default Transaction Type** (usually **Sale**).

![PAX payment configuration](static/description/img/pax_payment_config.png)

## 3. Assign to a POS configuration

Go to **Point of Sale → Configuration → Point of Sale → [your shop]**:

- Under **Payments**, add the PAX Terminal payment method.

## Network requirements

The Odoo **server** must have TCP access to the PAX terminal on the configured
port. The terminal and server must be on the same LAN or connected via a
properly configured firewall rule. The browser itself does not need direct
access to the terminal — all communication is proxied through the Odoo server.

## PAX terminal setup

The PAX terminal must be running the **POS Link** HTTP server. On most PAX
models this is enabled via the terminal's admin menu:

```
Menu → Settings → Communication → Enable POS Link
```

Consult your PAX terminal model's administration guide for the exact steps.
