{
    'name': 'Laptop Store',
    'version': '19.0.1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Practice module: manage laptop brands, categories and stock',
    'description': """
Laptop Store
============
A small practice module for learning Odoo custom module development:
- Brands, categories and laptops with a simple stock/sale workflow
- Custom security groups (Salesperson / Manager)
- List, form, search and kanban views
""",
    'author': 'Your Company',
    'depends': ['base', 'web'],
    'data': [
        'security/laptop_security.xml',
        'security/ir.model.access.csv',
        'report/laptop_sale_receipt_report.xml',
        'report/laptop_sale_receipt_templates.xml',
        'views/laptop_category_views.xml',
        'views/laptop_brand_views.xml',
        'views/laptop_product_views.xml',
        'views/laptop_menus.xml',
    ],
    'demo': [
        'demo/laptop_demo.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
