/** @odoo-module **/

import {onMounted, useState} from "@odoo/owl";
import {Component} from "point_of_sale.Registries";
import ScaleScreen from "point_of_sale.ScaleScreen";
import {convert_mass} from "../../tools.esm";
import {useBarcodeReader} from "point_of_sale.custom_hooks";

const TareScaleScreen = (ScaleScreen_) =>
    class extends ScaleScreen_ {
        setup() {
            super.setup();
            this.state = useState({
                tare: this.props.product.tare_weight || "",
                weight: 0,
                gross_weight: "",
                gross_weight_input_valid: true,
                tare_input_valid: true,
            });
            this.updateWeight();
            if (this.env.pos.config.iface_tare_method !== "manual") {
                useBarcodeReader({
                    tare: this._barcodeTareAction,
                });
                // Don't focus fields if the tare can be input with a barcode
                // reader, as scanning the barcode would result in its value
                // being input in the field (as barcode readers are seen as
                // keyboards).
                return;
            }
            let selector = "#input_weight_tare";
            if (this.env.pos.config.iface_gross_weight_method === "manual") {
                selector = "#input_gross_weight";
            }
            onMounted(() => {
                const target = this.el.querySelectorAll(selector)[0];
                target.focus();
                target.selectionStart = 0;
                target.selectionEnd = target.value.length;
            });
        }

        get gross_uom() {
            return this.env.pos.units_by_id[this.props.product.uom_id[0]];
        }

        async _barcodeTareAction(code) {
            this.state.tare = code.value;
        }

        _readScale() {
            if (this.env.pos.config.iface_gross_weight_method === "scale") {
                super._readScale();
            }
        }

        async _setWeight() {
            await super._setWeight();
            this.state.gross_weight = this.state.weight;
            this.updateWeight();
        }

        updateWeight() {
            this.state.gross_weight_input_valid = !isNaN(this.state.gross_weight);
            this.state.tare_input_valid = !isNaN(this.state.tare);
            if (!this.state.gross_weight_input_valid || !this.state.tare_input_valid) {
                // This is to ensure that the resulting weight is invalid.
                // Without this, if the tare uom and the product uom are
                // different, convert_mass() returns 0, which results in a
                // valid weight, while it should not.
                this.state.weight = NaN;
                return;
            }
            const tare_uom_id = this.env.pos.config.iface_tare_uom_id[0];
            const tare_uom = this.env.pos.units_by_id[tare_uom_id];
            const tare_in_product_uom = convert_mass(
                this.state.tare,
                tare_uom,
                this.gross_uom
            );
            this.state.weight = this.state.gross_weight - tare_in_product_uom;
        }

        confirm() {
            // Override the parent method to define the weight as an object
            // containing the tare.
            this.props.resolve({
                confirmed: true,
                payload: {
                    weight: {
                        weight: this.state.weight,
                        tare: this.state.tare ? parseFloat(this.state.tare) : 0,
                    },
                },
            });
            this.trigger("close-temp-screen");
        }
    };

Component.extend(ScaleScreen, TareScaleScreen);

export default ScaleScreen;
