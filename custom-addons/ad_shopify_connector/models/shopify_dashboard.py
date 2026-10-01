from odoo import models, api
from datetime import timedelta
from odoo.fields import Datetime

class ShopifyDashboard(models.AbstractModel):
    _name = 'shopify.dashboard'
    _description = 'Shopify Dashboard'

    @api.model
    def get_dashboard_data(self):
        domain_company = [('company_id', 'in', self.env.companies.ids)]

        instances = self.env['shopify.instance'].search_count(domain_company)

        orders = self.env['sale.order'].search_count(
            [('shopify_instance_id', '!=', False)] + domain_company
        )

        products = self.env['product.template'].search_count(
            [('shopify_product_id', '!=', False)] + domain_company
        )

        customers = self.env['res.partner'].search_count(
            [('shopify_customer_id', '!=', False)] + domain_company
        )

        first_of_month = Datetime.now().replace(day=1, hour=0, minute=0, second=0)
        monthly_orders = self.env['sale.order'].search([
            ('shopify_instance_id', '!=', False),
            ('date_order', '>=', first_of_month),
            ('state', 'not in', ['cancel', 'draft']),
        ] + domain_company)
        monthly_revenue = sum(monthly_orders.mapped('amount_total'))

        thirty_days_ago = Datetime.now() - timedelta(days=30)
        recent_orders = self.env['sale.order'].read_group(
            domain=[
                ('shopify_instance_id', '!=', False),
                ('date_order', '>=', thirty_days_ago),
            ] + domain_company,
            fields=['date_order', 'id'],
            groupby=['date_order:day']
        )

        chart_labels = []
        chart_data = []
        for group in recent_orders:
            chart_labels.append(group['date_order:day'])
            chart_data.append(group['date_order_count'])

        latest_orders = self.env['sale.order'].search_read(
            domain=[('shopify_instance_id', '!=', False)] + domain_company,
            fields=['name', 'partner_id', 'amount_total', 'state',
                    'date_order', 'shopify_instance_id', 'shopify_fulfillment_status'],
            limit=10,
            order='date_order desc'
        )

        instances_data = []
        for inst in self.env['shopify.instance'].search(domain_company):
            instances_data.append({
                'id': inst.id,
                'name': inst.name,
                'shop_url': inst.shop_url,
                'state': inst.state,
                'products': inst.product_count,
                'orders': inst.order_count,
                'customers': inst.customer_count,
                'last_sync': inst.last_sync_date.strftime('%Y-%m-%d %H:%M') if inst.last_sync_date else 'Never',
            })

        recent_logs = self.env['shopify.sync.log'].search_read(
            domain=[],
            fields=['name', 'instance_id', 'sync_type', 'state',
                    'records_processed', 'records_failed', 'create_date'],
            limit=5,
            order='create_date desc'
        )

        return {
            'kpis': {
                'instances': instances,
                'orders': orders,
                'products': products,
                'customers': customers,
                'monthly_revenue': monthly_revenue,
            },
            'chart': {
                'labels': chart_labels,
                'data': chart_data,
            },
            'recent_orders': latest_orders,
            'instances': instances_data,
            'recent_logs': recent_logs,
        }
