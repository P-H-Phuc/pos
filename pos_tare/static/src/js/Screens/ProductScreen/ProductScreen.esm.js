/** @odoo-module **/

import {Component} from "point_of_sale.Registries";
import ProductScreen from "point_of_sale.ProductScreen";
import {useBarcodeReader} from "point_of_sale.custom_hooks";

const TareProductScreen = (ProductScreen_) =>
    class extends ProductScreen_ {
        setup() {
            super.setup();
            useBarcodeReader({
                tare: this._barcodeTareAction,
            });
        }

        async _barcodeTareAction(code) {
            try {
                this.currentOrder.get_selected_orderline().set_tare(code.value, true);
            } catch (error) {
                this.showPopup("ErrorPopup", {
                    title: this.env._t("We cannot apply this tare barcode"),
                    body: error.message,
                });
            }
        }

        async _getAddProductOptions(product) {
            return super._getAddProductOptions(product).then((payload) => {
                if (!payload) return;
                if (!payload.quantity) return payload;

                const {weight, tare} = payload.quantity;
                return {
                    ...payload,
                    quantity: weight,
                    tare: tare,
                };
            });
        }

        _setValue(val) {
            super._setValue(val);
            if (this.currentOrder.get_selected_orderline()) {
                if (this.env.pos.numpadMode === "tare") {
                    if (this.env.pos.config.iface_tare_method === "barcode") {
                        this.showPopup("ErrorPopup", {
                            title: this.env._t("Feature Disabled"),
                            body: this.env._t(
                                "You can not set the tare." +
                                    " To be able to set the tare manually" +
                                    " you have to change the tare input method" +
                                    " in the POS configuration"
                            ),
                        });
                    } else {
                        try {
                            this.currentOrder
                                .get_selected_orderline()
                                .set_tare(val, true);
                        } catch (error) {
                            this.showPopup("ErrorPopup", {
                                title: this.env._t("We cannot apply this tare"),
                                body: error.message,
                            });
                        }
                    }
                }
            }
        }
    };

Component.extend(ProductScreen, TareProductScreen);

export default ProductScreen;
