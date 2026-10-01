{
    'name': 'Laptop Store',
    'version': '19.0.2.0.0',
    'category': 'Website/Website',
    'summary': 'Sell laptops on the website using Odoo\'s standard Shop, cart, checkout and invoicing flow',
    'description': """
Laptop Store Website
=====================
A laptop storefront built on top of Odoo's own e-commerce stack rather
than a bespoke one:

* Laptops are regular product.template records (in a "Laptops" category),
  extended with a few laptop-specific spec fields (processor, RAM, ...).
* /laptops is a plain Website page (no custom controller) built entirely
  from real Odoo snippets - a title block plus the native "Products"
  dynamic snippet pre-filtered to the Laptops category - so it is fully
  drag-and-drop customizable from the Website Builder, exactly like any
  other theme page.
* Cart, checkout, payment and invoicing are all Odoo's standard
  website_sale flow - nothing custom-built or duplicated.
""",
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['base', 'website_sale', 'payment_custom'],
    'data': [
        'data/product_category_data.xml',
        'views/product_template_views.xml',
        'views/laptop_menus.xml',
        'views/laptop_templates.xml',
        'views/product_page_templates.xml',
        'data/website_page_data.xml',
    ],
    'demo': [
        'demo/product_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'laptop_store_website/static/src/css/laptop_store.css',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
