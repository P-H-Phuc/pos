## Processing a payment

1. Open a POS session that has the **PAX Terminal** payment method enabled.
2. Add items to an order and proceed to the **Payment** screen.
3. Select the **PAX Terminal** payment method and enter the amount.
4. The terminal prompts the customer to swipe, insert, or tap their card.
5. Once the customer completes the interaction, the POS automatically marks the
   payment as **Done** and the order can be finalised.

## Refunds

Refunds work through the standard Odoo POS return flow. When a return order is
paid using the PAX Terminal payment method, the module sends a **Return (T00
type 02)** command to the terminal.

## Checking terminal status

Go to **Point of Sale → PAX Terminals → Terminals**, open a terminal record,
and click **Test Connection** to verify network connectivity.

## Transaction history

Go to **Point of Sale → PAX Terminals → Transactions** for a full audit log of
every transaction (approved or declined) processed through the terminals.
