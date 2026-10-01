# -*- coding: utf-8 -*-
from odoo import fields, models


class LaptopCategory(models.Model):
    _name = 'laptop.category'
    _description = 'Laptop Category'
    _order = 'name'

    name = fields.Char(required=True)
    laptop_ids = fields.One2many('laptop.product', 'category_id', string='Laptops')
