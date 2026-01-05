import {useService} from "@web/core/utils/hooks";
import {patch} from "@web/core/utils/patch";
import {PartnerList} from "@point_of_sale/app/screens/partner_list/partner_list";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.busService = useService("bus_service");
        this.busService.subscribe("res.partner.credit_amout/updated", (payload) => {
            const partners = this.pos.models["res.partner"].getAll();
            partners.forEach((partner) => {
                if (partner.id === payload.id) {
                    partner.credit_amount = payload.credit_amount;
                }
            });
        });
    },
});
