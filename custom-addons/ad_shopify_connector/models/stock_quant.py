from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_create_multi
    def create(self, vals_list):
        quants = super(StockQuant, self).create(vals_list)
        for quant in quants:
            quant._sync_stock_to_shopify()
        return quants

    def write(self, vals):
        res = super(StockQuant, self).write(vals)
        if 'inventory_quantity' in vals or 'reserved_quantity' in vals or 'quantity' in vals:
            for quant in self:
                quant._sync_stock_to_shopify()
        return res

    def _sync_stock_to_shopify(self):
        if self.location_id.shopify_location_id and self.location_id.shopify_instance_id:
            self.location_id.sync_product_stock(self.product_id)
