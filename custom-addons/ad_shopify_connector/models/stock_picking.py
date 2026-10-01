from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            if picking.picking_type_code == 'outgoing' and picking.sale_id and picking.sale_id.shopify_instance_id:
                picking._sync_fulfillment_to_shopify()
        return res

    def _sync_fulfillment_to_shopify(self):
        instance = self.sale_id.shopify_instance_id
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(instance.shop_url, instance.access_token)
        
        shopify_loc = self.env['stock.location'].search([
            ('shopify_instance_id', '=', instance.id),
            ('id', '=', self.location_id.id)
        ], limit=1)
        
        if not shopify_loc or not shopify_loc.shopify_location_id:
            shopify_loc = self.env['stock.location'].search([
                ('shopify_instance_id', '=', instance.id),
                ('shopify_location_id', '!=', False)
            ], limit=1)
            
        if not shopify_loc:
            _logger.warning(f"Could not sync fulfillment for {self.name}: No Shopify Location mapping found.")
            return False
            
        fo_data = client.get(f"orders/{self.sale_id.shopify_order_id}/fulfillment_orders")
        if fo_data and 'fulfillment_orders' in fo_data:
            for fo in fo_data['fulfillment_orders']:
                if fo['status'] == 'open':
                    fo_payload = {
                        "fulfillment": {
                            "message": "Fulfilled from Odoo",
                            "notify_customer": True,
                            "tracking_info": {
                                "number": self.carrier_tracking_ref or "",
                                "company": self.carrier_id.name if self.carrier_id else ""
                            },
                            "line_items_by_fulfillment_order": [
                                {
                                    "fulfillment_order_id": fo['id']
                                }
                            ]
                        }
                    }
                    result = client.post("fulfillments", fo_payload)
                    if result:
                        _logger.info(f"Successfully synced fulfillment for {self.name} to Shopify.")
                        self.sale_id.shopify_fulfillment_status = 'fulfilled'
                    break
