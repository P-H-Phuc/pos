/* License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */
import {AlertDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {PaymentScreen} from "@point_of_sale/app/screens/payment_screen/payment_screen";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        if (!isForceValidate) {
            const order = this.pos.get_order();
            const hasCreditPayment = (order.payment_ids || []).some(
                (line) => line.payment_method_id?.use_payment_terminal === "credit"
            );
            if (hasCreditPayment && this.pos.get_cashier()._role !== "manager") {
                this.dialog.add(AlertDialog, {
                    title: _t("Manager Required"),
                    body: _t(
                        "A manager must be logged in to validate orders with credit payments."
                    ),
                });
                return;
            }
        }
        return super.validateOrder(isForceValidate);
    },
});
