import {PaymentInterface} from "@point_of_sale/app/payment/payment_interface";
import {register_payment_method} from "@point_of_sale/app/store/pos_store";
import {deduceUrl} from "@point_of_sale/utils";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {_t} from "@web/core/l10n/translation";

/**
 * PAX Terminal payment interface — via pywebdriver proxy.
 *
 * Communication flow:
 *   POS JS  →  silentCall RPC  →  Odoo backend (pos_payment_pax_terminal_pywebdriver)
 *          →  HTTP POST  →  pywebdriver (/hw_proxy/pax/transaction_execute)
 *          →  HTTP GET (POS Link frame)  →  PAX Terminal
 *          ←  POS Link response  ←
 *          ←  parsed result JSON  ←  pywebdriver
 *          ←  {payment_status, ...}  ←  Odoo backend
 *          ←  silentCall result  ←
 *
 * Use this module instead of pos_payment_pax_terminal when Odoo is cloud-hosted
 * and the PAX terminal is only reachable from the local network running pywebdriver.
 */
export class PaxPywebdriverPayment extends PaymentInterface {
    // -------------------------------------------------------------------------
    // PaymentInterface overrides
    // -------------------------------------------------------------------------

    get fast_payments() {
        return this.payment_method_id.pax_pw_fast_payments ?? true;
    }

    send_payment_request(uuid) {
        super.send_payment_request(uuid);
        return this._paxDoCredit();
    }

    send_payment_cancel(order, uuid) {
        super.send_payment_cancel(order, uuid);
        // PAX terminals process cancellation locally on the device.
        // We can only reset the payment line so the cashier can retry.
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
        return this.pos.getPendingPaymentLine("pax_pywebdriver");
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

        const pm = this.payment_method_id;
        if (!pm.pax_pw_terminal_ip) {
            this._showError(
                _t(
                    "No PAX terminal IP is configured for this payment method. " +
                        "Set the Terminal IP field in the payment method settings."
                )
            );
            return false;
        }

        const amountFloat = line.amount;
        const orderId = order.name.replace(/\s/g, "").replaceAll("-", "").toUpperCase();
        const proxyIp = this.pos.config.proxy_ip;
        const pywebdriverUrl = proxyIp ? deduceUrl(proxyIp) : "http://127.0.0.1:8069";

        line.set_payment_status("waitingCard");

        const result = await this.pos.data.silentCall(
            "pos.payment.method",
            "pax_pywebdriver_send_payment",
            [[pm.id]],
            {
                data: {
                    pywebdriver_url: pywebdriverUrl,
                    terminal_ip: pm.pax_pw_terminal_ip,
                    terminal_port: pm.pax_pw_terminal_port || 10009,
                    use_https: pm.pax_pw_use_https || false,
                    amount: amountFloat,
                    currency_code: this._getIsoCurrencyNumeric(),
                    order_id: orderId,
                    transaction_type: pm.pax_pw_transaction_type || "01",
                    timeout: pm.pax_pw_timeout || 120000,
                },
            }
        );

        if (!result) {
            this._showError(_t("Network error contacting the Odoo server."));
            line.set_payment_status("retry");
            return false;
        }

        return this._handleResult(line, result);
    }

    _handleResult(line, result) {
        if (!result || result.payment_status === "error") {
            this._showError(result?.message || _t("Unknown error from pywebdriver"));
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

    /** Map currency name to ISO 4217 numeric code (PAX expects numeric string). */
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
        return map[this.pos.currency.name] || "840";
    }

    _showError(msg, title) {
        this.env.services.dialog.add(ConfirmationDialog, {
            title: title || _t("PAX Terminal Error"),
            body: msg,
            confirmLabel: _t("OK"),
            confirm: () => {
                // Noop
            },
            cancel: () => {
                // Noop
            },
        });
    }
}

register_payment_method("pax_pywebdriver", PaxPywebdriverPayment);
