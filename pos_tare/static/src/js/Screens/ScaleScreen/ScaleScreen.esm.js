/** @odoo-module **/

import {onMounted, useState} from "@odoo/owl";
import {Component} from "point_of_sale.Registries";
import ScaleScreen from "point_of_sale.ScaleScreen";

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
            if (this.env.pos.config.iface_tare_method === "barcode") {
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

        _readScale() {
            if (this.env.pos.config.iface_gross_weight_method === "scale") {
                super._readScale();
            }
        }

        async _setWeight() {
            await super._setWeight();
            this.state.gross_weight = this.state.weight;
            this.state.weight -= this.state.tare;
        }

        updateWeight() {
            this.state.gross_weight_input_valid = !isNaN(this.state.gross_weight);
            this.state.tare_input_valid = !isNaN(this.state.tare);
            this.state.weight = this.state.gross_weight - this.state.tare;
        }

        confirm() {
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
