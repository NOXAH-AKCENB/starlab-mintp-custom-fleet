/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";

export class JudoDashboard extends Component {
    static template = "judo_club.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: null });

        onWillStart(async () => {
            this.state.data = await this.orm.call("judo.dashboard", "get_dashboard_data", []);
            this.state.loading = false;
        });
    }

    money(value) {
        return formatMonetary(value || 0, { currencyId: this.state.data.currency_id });
    }

    /** Hauteur d'une barre en pourcentage du maximum de la série. */
    barHeight(value) {
        const max = Math.max(
            1,
            ...this.state.data.series.map((s) => Math.max(s.income, s.expense))
        );
        return Math.round(((value || 0) / max) * 100);
    }

    openFees() {
        this.action.doAction("judo_club.action_judo_fee");
    }

    openTransactions() {
        this.action.doAction("judo_club.action_judo_transaction");
    }

    openTransaction(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "judo.transaction",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("judo_club.dashboard", JudoDashboard);
