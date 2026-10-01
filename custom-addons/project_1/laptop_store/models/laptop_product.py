# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LaptopProduct(models.Model):
    _name = 'laptop.product'
    _description = 'Laptop'
    _order = 'name'

    name = fields.Char(required=True)
    serial_number = fields.Char(required=True, copy=False)
    brand_id = fields.Many2one('laptop.brand', string='Brand', required=True)
    category_id = fields.Many2one('laptop.category', string='Category')
    processor = fields.Char()
    ram_gb = fields.Integer(string='RAM (GB)', default=8)
    storage_gb = fields.Integer(string='Storage (GB)', default=256)
    price = fields.Float(string='Price')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_stock', 'In Stock'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
    ], default='draft', required=True, copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer', copy=False)
    sale_date = fields.Date(copy=False)
    active = fields.Boolean(default=True)
    image_1920 = fields.Image('Image')
    image_128 = fields.Image('Image 128', related='image_1920', max_width=128, max_height=128, store=True)

    _serial_number_unique = models.Constraint(
        'unique(serial_number)', 'Serial number must be unique.',
    )

    @api.constrains('ram_gb', 'price')
    def _check_positive_values(self):
        for laptop in self:
            if laptop.ram_gb <= 0:
                raise ValidationError('RAM must be greater than 0 GB.')
            if laptop.price < 0:
                raise ValidationError('Price cannot be negative.')

    def action_set_in_stock(self):
        self.write({'state': 'in_stock'})

    def action_reserve(self):
        for laptop in self:
            if not laptop.customer_id:
                raise ValidationError('Set a customer before reserving a laptop.')
            laptop.state = 'reserved'

    def action_sell(self):
        for laptop in self:
            if not laptop.customer_id:
                raise ValidationError('Set a customer before selling a laptop.')
            laptop.write({'state': 'sold', 'sale_date': fields.Date.context_today(laptop)})

    def action_return_to_stock(self):
        self.write({'state': 'in_stock', 'customer_id': False, 'sale_date': False})
