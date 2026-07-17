import {AlertDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {PaymentInterface} from "@point_of_sale/app/payment/payment_interface";
import {_t} from "@web/core/l10n/translation";
import {register_payment_method} from "@point_of_sale/app/store/pos_store";

/**
 * PAX Terminal payment interface — semi-integrated mode via POS Link HTTP.
 *
 * Communication flow:
 *   POS JS  →  silentCall RPC  →  Odoo backend (pos_payment_pax_terminal_direct)
 *          →  HTTP GET (POS Link frame)  →  PAX Terminal
 *          ←  POS Link response  ←
 *          ←  parsed result JSON  ←
 */
export class PaxTerminalPayment extends PaymentInterface {
    get _terminal() {
        const terminalId = this.payment_method_id.pax_terminal_id;
        if (!terminalId) return null;
        return (
            this.pos.models["pax.terminal"]?.find((t) => t.id === terminalId) || null
        );
    }

    // -------------------------------------------------------------------------
    // PaymentInterface overrides
    // -------------------------------------------------------------------------

    async send_payment_request(uuid) {
        await super.send_payment_request(uuid);
        return this._paxDoCredit();
    }

    async send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        // PAX terminals handle cancellation locally on the device; we can only
        // reset the payment line to a retryable state from the POS side.
        const line = this._getPendingLine();
        if (line) {
            line.set_payment_status("retry");
        }
        return true;
    }

    // -------------------------------------------------------------------------
    // Internal
    // -------------------------------------------------------------------------

    _getPendingLine() {
        return this.pos.getPendingPaymentLine("pax_terminal");
    }

    async _paxDoCredit() {
        const order = this.pos.get_order();
        const line = order.get_selected_paymentline();

        if (!line || line.amount <= 0) {
            this._showError(
                _t("Cannot process a transaction with a non-positive amount.")
            );
            return false;
        }

        const terminal = this._terminal;
        if (!terminal && !this.payment_method_id.pax_terminal_ip) {
            this._showError(
                _t("No PAX terminal is configured for this payment method.")
            );
            return false;
        }

        const amountCents = Math.round(line.amount * 100);
        const orderId = order.name.replace(/\s/g, "").replaceAll("-", "").toUpperCase();
        const transactionType = this.payment_method_id.pax_transaction_type || "01";

        line.set_payment_status("waitingCard");

        // SilentCall catches all exceptions internally and returns false on failure
        const result = await this.pos.data.silentCall(
            "pos.payment.method",
            "pax_send_payment",
            [[this.payment_method_id.id]],
            {
                data: {
                    terminal_ip: this.payment_method_id.pax_terminal_ip,
                    terminal_port: this.payment_method_id.pax_terminal_port || 10009,
                    amount_cents: amountCents,
                    currency_code: this._getIsoCurrencyNumeric(),
                    order_id: orderId,
                    transaction_type: transactionType,
                    timeout: Math.floor(
                        (this.payment_method_id.pax_timeout || 120000) / 1000
                    ),
                    use_https: terminal?.use_https || false,
                },
            }
        );

        if (!result) {
            this._showError(_t("Network error contacting the payment server."));
            line.set_payment_status("retry");
            return false;
        }

        return this._handleResult(line, result);
    }

    _handleResult(line, result) {
        if (!result || result.payment_status === "error") {
            const msg = result?.message || _t("Unknown error from PAX terminal");
            this._showError(msg);
            line.set_payment_status("retry");
            return false;
        }

        if (result.payment_status === "failure") {
            const code = result.response_code || "";
            const msg = result.response_message || _t("Payment declined");
            this._showError(
                _t("PAX terminal declined: %(msg)s%(code)s", {
                    msg,
                    code: code ? ` (${code})` : "",
                })
            );
            line.set_payment_status("retry");
            return false;
        }

        // Success
        if (result.transaction_id) {
            line.transaction_id = result.transaction_id;
        }
        if (result.auth_code) {
            line.card_type = result.auth_code;
        }
        if (result.card_holder_name) {
            line.cardholder_name = result.card_holder_name;
        }

        line.set_payment_status("done");
        return true;
    }

    /**
     * Map currency name to ISO 4217 numeric code (PAX expects numeric string).
     */
    _getIsoCurrencyNumeric() {
        const map = {
            USD: "840",
            EUR: "978",
            GBP: "826",
            VND: "704",
            JPY: "392",
            CAD: "124",
            AUD: "036",
            SGD: "702",
            THB: "764",
            MYR: "458",
            PHP: "608",
            IDR: "360",
            KRW: "410",
            CNY: "156",
        };
        return map[this.pos.currency?.name || "USD"] || "840";
    }

    _showError(msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("PAX Terminal Error"),
            body: msg,
        });
    }
}

register_payment_method("pax_terminal", PaxTerminalPayment);
