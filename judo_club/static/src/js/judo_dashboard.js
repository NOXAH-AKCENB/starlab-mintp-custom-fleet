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
        this.notification = useService("notification");

        const today = new Date();
        const pad = (n) => String(n).padStart(2, "0");
        const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        this.state = useState({
            loading: true,
            data: null,
            exporting: false,
            // Période d'export : par défaut, de début d'année à aujourd'hui
            period: { from: iso(new Date(today.getFullYear(), 0, 1)), to: iso(today) },
        });

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

    /** Exporte la période choisie : fmt = "pdf" | "xlsx" | "ticket". */
    async exportAs(fmt) {
        const { from, to } = this.state.period;
        if (!from || !to || from > to) {
            this.notification.add("La date de début doit précéder la date de fin.", { type: "warning" });
            return;
        }
        this.state.exporting = true;
        try {
            const action = await this.orm.call("judo.dashboard", "export_period", [from, to, fmt]);
            await this.action.doAction(action);
        } catch (error) {
            this.notification.add("L'export a échoué. Vérifiez la période et réessayez.", { type: "danger" });
        } finally {
            this.state.exporting = false;
        }
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
