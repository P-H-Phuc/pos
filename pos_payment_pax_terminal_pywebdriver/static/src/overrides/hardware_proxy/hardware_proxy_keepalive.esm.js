import {HardwareProxy} from "@point_of_sale/app/hardware_proxy/hardware_proxy_service";
import {patch} from "@web/core/utils/patch";

patch(HardwareProxy.prototype, {
    async keepalive() {
        await super.keepalive();
        const hasPax = this.pos.models["pos.payment.method"]
            .getAll()
            .some(
                (pm) =>
                    pm.use_payment_terminal === "pax_pywebdriver" &&
                    pm.pax_pw_terminal_ip
            );
        if (hasPax) {
            this.message("pax/status", {}).catch(() => {
                // Noop — keepalive failure is non-fatal
            });
        }
    },
});
