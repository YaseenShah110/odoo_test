from odoo import models, fields, api

class StockLocation(models.Model):
    _inherit = 'stock.location'

    shopify_instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', ondelete='set null')
    shopify_location_id = fields.Char(string='Shopify Location ID', readonly=True)

    @api.model
    def import_locations(self, instance):
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(instance.shop_url, instance.access_token)
        
        locations = client.get('locations')
        if not locations or 'locations' not in locations:
            return False
            
        for loc_data in locations['locations']:
            shopify_id = str(loc_data.get('id'))
            name = loc_data.get('name')
            
            location = self.search([
                ('shopify_location_id', '=', shopify_id),
                ('shopify_instance_id', '=', instance.id)
            ], limit=1)
            
            if location:
                continue
                
            parent_loc = instance.warehouse_id.view_location_id
            self.create({
                'name': f"Shopify: {name}",
                'location_id': parent_loc.id if parent_loc else False,
                'usage': 'internal',
                'shopify_instance_id': instance.id,
                'shopify_location_id': shopify_id,
            })
            
        return True

    def action_export_stock(self):
        self.ensure_one()
        if not self.shopify_location_id or not self.shopify_instance_id:
            return False
            
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(self.shopify_instance_id.shop_url, self.shopify_instance_id.access_token)
        
        variants = self.env['product.product'].search([
            ('product_tmpl_id.shopify_instance_id', '=', self.shopify_instance_id.id),
            ('shopify_inventory_item_id', '!=', False)
        ])
        
        for variant in variants:
            qty = variant.with_context(location=self.id).qty_available
            payload = {
                "location_id": self.shopify_location_id,
                "inventory_item_id": variant.shopify_inventory_item_id,
                "available": int(qty)
            }
            client.post("inventory_levels/set", payload)
        return True

    def sync_product_stock(self, product):
        self.ensure_one()
        if not self.shopify_location_id or not product:
            return False
            
        if product.shopify_inventory_item_id:
            qty = product.with_context(location=self.id).qty_available
            from .shopify_api_client import ShopifyAPIClient
            client = ShopifyAPIClient(self.shopify_instance_id.shop_url, self.shopify_instance_id.access_token)
            
            payload = {
                "location_id": self.shopify_location_id,
                "inventory_item_id": product.shopify_inventory_item_id,
                "available": int(qty)
            }
            return client.post("inventory_levels/set", payload)
        return False
