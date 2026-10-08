{
    'name': 'Custom Invoice Template',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Production-grade custom invoice PDF design with a dedicated download button',
    'description': """
Custom Invoice Template
========================
Adds a brand new, standalone invoice PDF design (does not modify any core
Odoo report) plus a "Download Invoice" button on the customer invoice form
that generates and downloads this design directly.

The default Odoo invoice report (Print / Send & Print) is untouched.
""",
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'report/custom_invoice_report.xml',
        'report/custom_invoice_template.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
