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

        async _getAddProductOptions(product, code) {
            const payload = await super._getAddProductOptions(product, code);
            if (!payload) return;
            if (!payload.quantity) return payload;

            const {weight, tare} = payload.quantity;
            return {
                ...payload,
                quantity: weight,
                tare: tare,
            };
        }

        _setTareOnLastOrderLine(tare) {
            if (tare > 0) {
                const orderline = this.currentOrder.get_last_orderline();
                orderline.set_tare(tare, false);
            }
        }

        async _addProduct(product, options) {
            if (!product.to_weight || !this.env.pos.config.iface_electronic_scale) {
                return super._addProduct(product, options);
            }
            if (isNaN(options.tare)) {
                this.showPopup("ErrorPopup", {
                    title: this.env._t("Incorrect Tare Value"),
                    body: this.env._t(
                        "Please set a numeric value in the tare field, or" +
                            " let empty."
                    ),
                });
            } else if (isNaN(options.quantity)) {
                this.showPopup("ErrorPopup", {
                    title: this.env._t("Incorrect Gross Weight Value"),
                    body: this.env._t(
                        "Please set a numeric value in the gross weight field."
                    ),
                });
            } else if (options.quantity <= 0) {
                const {confirmed} = await this.showPopup("ConfirmPopup", {
                    title: this.env._t("Quantity lower or equal to zero"),
                    body: this.env._t(
                        "The quantity is lower or equal to zero." +
                            " Are you sure you want to continue ?"
                    ),
                });
                if (confirmed) {
                    await super._addProduct(product, options);
                    this._setTareOnLastOrderLine(options.tare);
                }
            } else {
                await super._addProduct(product, options);
                this._setTareOnLastOrderLine(options.tare);
            }
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
