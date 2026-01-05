/* License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */

import {PosStore} from "@point_of_sale/app/store/pos_store";
import {patch} from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async selectPartner(partner) {
        const res = await super.selectPartner(partner);
        // When changing a customer, we want to destroy the credit
        // payment lines
        // because they could be linked to another customer.
        // Just in case we destroy all
        this._removeAllCreditPaymentLine();
        return res;
    },
    _removeAllCreditPaymentLine() {
        this.paymentCreditInProgress = false;
        const currentOrder = this.get_order();
        const creditPaymentLine = currentOrder.payment_ids.find(
            (line) => line.payment_method_id.is_credit
        );
        if (creditPaymentLine) {
            currentOrder.remove_paymentline(creditPaymentLine);
        }
    },
});
