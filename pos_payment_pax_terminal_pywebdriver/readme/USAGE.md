## Processing a payment

1. Open a POS session that has the **PAX (pywebdriver)** payment method enabled.
2. Add items to an order and proceed to the **Payment** screen.
3. Select the **PAX Terminal (pywebdriver)** payment method and enter the amount.
4. The terminal prompts the customer to swipe, insert, or tap their card.
5. Once the customer completes the interaction, the POS automatically marks
   the payment as **Done** and the order can be finalised.

## Refunds

Refunds work through the standard Odoo POS return flow. When a return order
is paid using this payment method, the module sends a **Return (T00 type 02)**
command to the terminal via pywebdriver.

## Fast Payments

When **Fast Payments** is enabled (default), the payment request is sent to
the terminal as soon as the cashier selects the payment method — no manual
"Send" click is needed. Disable it to let the cashier verify the amount first.
