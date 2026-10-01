# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LaptopBrand(models.Model):
    _name = 'laptop.brand'
    _description = 'Laptop Brand'
    _order = 'name'

    name = fields.Char(required=True)
    country = fields.Char()
    laptop_ids = fields.One2many('laptop.product', 'brand_id', string='Laptops')
    laptop_count = fields.Integer(compute='_compute_laptop_count')

    @api.depends('laptop_ids')
    def _compute_laptop_count(self):
        for brand in self:
            brand.laptop_count = len(brand.laptop_ids)
