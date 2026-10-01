from odoo import fields, models


class ProductTemplate(models.Model):
    """Adds laptop-specific spec fields to the standard product.

    Laptops are regular Odoo products (in the "Laptops" website category),
    not a separate model: this reuses product.template as-is (pricing,
    currency, image, publishing, sale_ok, categories, ...) instead of
    duplicating what Odoo already provides, and it means laptops go
    through Odoo's standard cart/checkout/invoicing flow automatically.
    """
    _inherit = 'product.template'

    brand = fields.Char(string='Brand', help='e.g. Dell, HP, Lenovo.')
    featured = fields.Boolean(string='Featured', help='Highlight this laptop on the curated /laptops page.')
    processor = fields.Char(string='Processor', help='e.g. Intel Core i7-13700H')
    ram = fields.Char(string='RAM', help='e.g. 16 GB')
    storage = fields.Char(string='Storage', help='e.g. 512 GB SSD')
    display_size = fields.Char(string='Display Size', help='e.g. 15.6"')
    operating_system = fields.Char(string='Operating System', help='e.g. Windows 11 Home')
