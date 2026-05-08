import {OrderWidget} from "@point_of_sale/app/generic_components/order_widget/order_widget";
import {patch} from "@web/core/utils/patch";

patch(OrderWidget.prototype, {
    getMealVoucherTotal() {
        const lines = this.props.lines;
        return lines.reduce((sum, line) => {
            return line.product_id.meal_voucher_ok
                ? sum + line.price_subtotal_incl
                : sum;
        }, 0);
    },
});
