/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class ShopifyDashboard extends Component {
    static template = "ad_shopify_connector.ShopifyDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chartCanvas = useRef("chartCanvas");

        this.state = useState({
            isLoading: true,
            data: {
                kpis: { instances: 0, orders: 0, products: 0, customers: 0, monthly_revenue: 0 },
                chart: { labels: [], data: [] },
                recent_orders: [],
                instances: [],
                recent_logs: [],
            }
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this._fetchDashboardData();
        });

        onMounted(() => {
            this._renderChart();
        });
    }

    async _fetchDashboardData() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call("shopify.dashboard", "get_dashboard_data", []);
            this.state.data = result;
            this._renderChart();
        } catch (error) {
            console.error("Error fetching Shopify Dashboard Data:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    _renderChart() {
        if (!this.chartCanvas.el) return;
        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        const ctx = this.chartCanvas.el.getContext("2d");
        let gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, "rgba(113, 75, 103, 0.45)");
        gradient.addColorStop(1, "rgba(113, 75, 103, 0.02)");

        this.chartInstance = new window.Chart(ctx, {
            type: "line",
            data: {
                labels: this.state.data.chart.labels,
                datasets: [{
                    label: "Orders / Day",
                    data: this.state.data.chart.data,
                    backgroundColor: gradient,
                    borderColor: "#714B67",
                    borderWidth: 2.5,
                    pointBackgroundColor: "#fff",
                    pointBorderColor: "#714B67",
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { borderDash: [3, 4], color: "#edf0f2" }
                    },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: "#2d2d2d",
                        padding: 12,
                        cornerRadius: 6,
                    }
                }
            }
        });
    }

    _formatCurrency(value) {
        return new Intl.NumberFormat(undefined, {
            style: "currency",
            currency: "USD",
            maximumFractionDigits: 0,
        }).format(value || 0);
    }

    _formatDate(dateStr) {
        if (!dateStr) return "";
        return dateStr.split(" ")[0];
    }

    _stateClass(state) {
        return state === "confirmed" ? "text-success" : state === "error" ? "text-danger" : "text-muted";
    }

    _logStateClass(state) {
        const map = { success: "success", partial: "warning", error: "danger" };
        return `badge bg-${map[state] || "secondary"}`;
    }

    async _openInstances() {
        await this.action.doAction("ad_shopify_connector.action_shopify_instance");
    }

    async _openOrders() {
        await this.action.doAction("ad_shopify_connector.action_shopify_sale_order");
    }

    async _openProducts() {
        await this.action.doAction("ad_shopify_connector.action_shopify_product_template");
    }

    async _openCustomers() {
        await this.action.doAction("ad_shopify_connector.action_shopify_res_partner");
    }
}

registry.category("actions").add("ad_shopify_connector.dashboard", ShopifyDashboard);
