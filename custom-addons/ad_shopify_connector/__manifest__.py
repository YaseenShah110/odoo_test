{
    'name': 'Shopify Connector',
    'version': '19.0.2.0',
    'category': 'Sales/Sales',
    'summary': 'Advanced Bidirectional Shopify Integration',
    'website': 'https://adreaminnovations.odoo.com',
    'description': """
        Advanced Shopify ↔ Odoo integration module.

        Key Features:
        ─────────────
        ✔  Multi-instance support (connect multiple Shopify stores)
        ✔  Bidirectional Product / Variant Sync with image push
        ✔  Full Order Import with pagination (all orders, not just first 250)
        ✔  Shopify discount & shipping line mapping on orders
        ✔  Customer Import with country / state resolution
        ✔  Inventory Synchronisation (Odoo → Shopify & webhook back-sync)
        ✔  Fulfillment Sync (Odoo delivery → Shopify fulfillment)
        ✔  10 Webhook topics handled (orders, products, inventory, customers, fulfillments)
        ✔  HMAC Webhook verification
        ✔  Sync Logs model with per-instance history
        ✔  Scheduled Auto-Sync cron (configurable per instance)
        ✔  Enhanced Dashboard: revenue KPI, instance breakdown, sync activity feed
        ✔  API client with rate-limit retry and timeout handling
        ✔  Shopify product tags, order tags, financial status tracking
    """,
    'author': 'ADream Innovations',
    'depends': ['sale_management', 'stock', 'delivery'],
    'data': [
        'security/shopify_security.xml',
        'security/ir.model.access.csv',
        'data/shopify_cron.xml',
        'wizard/shopify_export_product_wizard_views.xml',
        'wizard/shopify_export_customer_wizard_views.xml',
        'views/shopify_sync_log_views.xml',
        'views/shopify_instance_views.xml',
        'views/shopify_product_views.xml',
        'views/shopify_location_views.xml',
        'views/shopify_order_views.xml',
        'views/shopify_customer_views.xml',
        'views/shopify_dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ad_shopify_connector/static/src/xml/shopify_dashboard.xml',
            'ad_shopify_connector/static/src/scss/shopify_dashboard.scss',
            'ad_shopify_connector/static/src/js/shopify_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
}
