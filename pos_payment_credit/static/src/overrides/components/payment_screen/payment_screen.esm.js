/* License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */

import {
    AlertDialog,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import {PaymentScreen} from "@point_of_sale/app/screens/payment_screen/payment_screen";
import {_t} from "@web/core/l10n/translation";
import {ask} from "@point_of_sale/app/store/make_awaitable_dialog";
import {patch} from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos.paymentCreditInProgress = false;
        this.pos.paymentCreditText = "";
    },

    onMounted() {
        super.onMounted(...arguments);
        const pendingPaymentLine = this.currentOrder.payment_ids.find(
            (paymentLine) => paymentLine.payment_method_id?.is_credit
        );
        if (!pendingPaymentLine) {
            return;
        }
        this.pos.paymentCreditInProgress = true;
        const amount = pendingPaymentLine.amount;
        if (this.pos.config.auto_apply_credit_amount) {
            this._handleDisplayPaymentCreditText(amount);
        }
    },

    isRefundCurrentOrder() {
        return (
            !this.currentOrder.doNotAllowRefundAndSales() &&
            this.currentOrder._isRefundOrder()
        );
    },

    isPaidWithCredit() {
        return Boolean(
            this.paymentLines.find((line) => line.payment_method_id?.is_credit)
        );
    },

    _handleDisplayPaymentCreditText(amount) {
        const amountFormatted = this.env.utils.formatCurrency(amount);
        let message = _t("The credit of ") + amountFormatted + _t(" will be used.");
        if (this.isRefundCurrentOrder()) {
            message = _t("A refund of ") + amountFormatted + _t(" will be applied.");
        }
        this.pos.paymentCreditText = message;
    },

    async addNewPaymentLine(paymentMethod) {
        if (this.pos.data.network.offline) {
            this.dialog.add(AlertDialog, {
                title: _t("Connection Lost"),
                body: _t(
                    "%s payment method cannot be used while the POS is offline.",
                    paymentMethod.name
                ),
            });
            return false;
        }
        if (this.pos.paymentCreditInProgress && paymentMethod.is_credit) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already a credit payment in progress."),
            });
            return false;
        }
        if (paymentMethod.is_credit && !this.currentOrder.get_partner()) {
            const confirmed = await ask(this.dialog, {
                title: _t("Customer Required"),
                body: _t(
                    "Customer is required for %s payment method.",
                    paymentMethod.name
                ),
            });
            if (!confirmed) {
                return false;
            }
            this.pos.selectPartner();
        }
        await super.addNewPaymentLine(paymentMethod);
        if (paymentMethod.is_credit && this.currentOrder.get_partner()) {
            // Update the amount based on the credit amount
            this.applyCreditAmount();
        }
    },

    applyCreditAmount() {
        const line = this.currentOrder.get_selected_paymentline();
        const isRefundCurrentOrder = this.isRefundCurrentOrder();
        if (line && line.payment_method_id?.is_credit) {
            this.pos.paymentCreditInProgress = true;
            const partner = this.currentOrder.get_partner();
            let amount = line.amount;
            if (!isRefundCurrentOrder) {
                amount = Math.max(0, Math.min(line.amount, partner.credit_amount));
                if (!this.pos.config.auto_apply_credit_amount) {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Confirming"),
                        body: _t("Pay using the member's available credit?"),
                        confirm: () => {
                            return;
                        },
                        cancel: () => {
                            this.currentOrder.remove_paymentline(line);
                        },
                    });
                }
            }
            line.set_amount(amount);
            this._handleDisplayPaymentCreditText(line.amount);
        }
    },

    updateSelectedPaymentline(amount = false) {
        super.updateSelectedPaymentline(amount);
        if (
            this.selectedPaymentLine &&
            this.selectedPaymentLine.payment_method_id.is_credit
        ) {
            const partner = this.currentOrder.get_partner();
            const isRefundCurrentOrder = this.isRefundCurrentOrder();
            const payAmount = this.selectedPaymentLine.amount;
            if (
                !isRefundCurrentOrder &&
                ((payAmount && payAmount > partner.credit_amount) || payAmount < 0)
            ) {
                const partnerCreditFmt = this.env.utils.formatCurrency(
                    partner.credit_amount
                );
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body:
                        _t("The credit amount is invalid. Maximum value: ") +
                        partnerCreditFmt,
                });
                this.selectedPaymentLine.set_amount(partner.credit_amount);
            }
            this._handleDisplayPaymentCreditText(this.selectedPaymentLine.amount);
        }
    },

    async _finalizeValidation() {
        if (this.isPaidWithCredit()) {
            if (this.pos.data.network.offline) {
                this.dialog.add(AlertDialog, {
                    title: _t("Connection Lost"),
                    body: _t(
                        "Payment with credit cannot be used while the POS is offline."
                    ),
                });
                return;
            }
            const credit_amount = this.paymentLines
                .filter((line) => line.payment_method_id.is_credit)
                .reduce((sum, line) => sum + line.amount, 0);
            const partner = this.currentOrder.get_partner();
            if (partner) {
                if (
                    !this.isRefundCurrentOrder() &&
                    credit_amount > partner.credit_amount
                ) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Validation Error"),
                        body: _t("The credit amount exceeds the available credit."),
                    });
                    return;
                }
                partner.credit_amount -= credit_amount;
            }
        }
        await super._finalizeValidation(...arguments);
    },

    deletePaymentLine(uuid) {
        const paymentLine = this.paymentLines.find((line) => line.uuid === uuid);
        if (paymentLine.payment_method_id.is_credit) {
            this.pos.paymentCreditInProgress = false;
            this.pos.paymentCreditText = "";
        }
        super.deletePaymentLine(uuid);
    },
});
