import json
import logging
import hmac
import hashlib
import base64
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ShopifyWebhookController(http.Controller):

    @http.route(
        '/shopify/webhook/<string:instance_id>/<path:topic>',
        type='http', auth='public', methods=['POST'], csrf=False
    )
    def handle_shopify_webhook(self, instance_id, topic, **post):
        _logger.info(f"Shopify Webhook received: instance={instance_id}, topic={topic}")
        try:
            raw_data = request.httprequest.data
            hmac_header = request.httprequest.headers.get('X-Shopify-Hmac-Sha256')

            instance = request.env['shopify.instance'].sudo().browse(int(instance_id))
            if not instance.exists():
                _logger.error(f"Shopify Webhook: Instance {instance_id} not found.")
                return request.make_response(
                    json.dumps({'error': 'Instance not found'}),
                    status=404, headers=[('Content-Type', 'application/json')]
                )

            if instance.webhook_secret:
                hash_val = hmac.new(
                    instance.webhook_secret.encode('utf-8'), raw_data, hashlib.sha256
                ).digest()
                computed_hmac = base64.b64encode(hash_val).decode('utf-8')
                if not hmac.compare_digest(computed_hmac, hmac_header or ''):
                    _logger.error("Shopify Webhook: HMAC verification failed.")
                    return request.make_response(
                        json.dumps({'error': 'Unauthorized'}),
                        status=401, headers=[('Content-Type', 'application/json')]
                    )

            data = json.loads(raw_data.decode('utf-8'))
            env = request.env(context=dict(request.env.context, shopify_no_sync=True))

            if topic == 'orders/create':
                env['sale.order'].sudo().import_orders(instance, order_data=data)

            elif topic == 'orders/updated':
                shopify_id = str(data.get('id'))
                order = env['sale.order'].sudo().search([
                    ('shopify_order_id', '=', shopify_id),
                    ('shopify_instance_id', '=', instance.id),
                ], limit=1)
                if order:
                    order.sudo().write({
                        'shopify_fulfillment_status': data.get('fulfillment_status') or 'unfulfilled',
                        'shopify_financial_status': data.get('financial_status', ''),
                    })

            elif topic == 'orders/cancelled':
                shopify_id = str(data.get('id'))
                order = env['sale.order'].sudo().search([
                    ('shopify_order_id', '=', shopify_id),
                    ('shopify_instance_id', '=', instance.id),
                ], limit=1)
                if order:
                    order._handle_shopify_cancellation(data)

            elif topic in ('products/create', 'products/update'):
                shopify_id = str(data.get('id'))
                product = env['product.template'].sudo().search([
                    ('shopify_product_id', '=', shopify_id),
                    ('shopify_instance_id', '=', instance.id),
                ], limit=1)
                if product:
                    product.sudo()._update_from_shopify_data(data, instance)
                else:
                    env['shopify.instance'].sudo().browse(instance.id).action_import_products()

            elif topic == 'products/delete':
                shopify_id = str(data.get('id'))
                product = env['product.template'].sudo().search([
                    ('shopify_product_id', '=', shopify_id),
                    ('shopify_instance_id', '=', instance.id),
                ], limit=1)
                if product:
                    product.sudo().unlink_from_shopify()

            elif topic == 'inventory_levels/update':
                inventory_item_id = str(data.get('inventory_item_id', ''))
                location_shopify_id = str(data.get('location_id', ''))
                available = data.get('available')

                if available is not None and inventory_item_id and location_shopify_id:
                    variant = env['product.product'].sudo().search([
                        ('shopify_inventory_item_id', '=', inventory_item_id),
                    ], limit=1)
                    location = env['stock.location'].sudo().search([
                        ('shopify_location_id', '=', location_shopify_id),
                        ('shopify_instance_id', '=', instance.id),
                    ], limit=1)

                    if variant and location:
                        quant = env['stock.quant'].sudo().search([
                            ('product_id', '=', variant.id),
                            ('location_id', '=', location.id),
                        ], limit=1)
                        if quant:
                            quant.sudo().write({'inventory_quantity': available})
                        else:
                            env['stock.quant'].sudo().create({
                                'product_id': variant.id,
                                'location_id': location.id,
                                'inventory_quantity': available,
                            })

            elif topic in ('customers/create', 'customers/update'):
                shopify_id = str(data.get('id'))
                email = data.get('email')
                partner = env['res.partner'].sudo().search([
                    ('shopify_customer_id', '=', shopify_id),
                    ('shopify_instance_id', '=', instance.id),
                ], limit=1)
                if not partner and email:
                    partner = env['res.partner'].sudo().search(
                        [('email', '=', email)], limit=1
                    )
                addr = data.get('default_address', {})
                vals = {
                    'name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or 'Unknown',
                    'email': email,
                    'phone': data.get('phone') or addr.get('phone'),
                    'shopify_instance_id': instance.id,
                    'shopify_customer_id': shopify_id,
                    'shopify_marketing_opt_in': data.get('accepts_marketing', False),
                }
                if partner:
                    partner.sudo().write(vals)
                else:
                    env['res.partner'].sudo().create(vals)

            elif topic == 'fulfillments/create':
                shopify_order_id = str(data.get('order_id', ''))
                order = env['sale.order'].sudo().search([
                    ('shopify_order_id', '=', shopify_order_id),
                    ('shopify_instance_id', '=', instance.id),
                ], limit=1)
                if order:
                    order.sudo().write({'shopify_fulfillment_status': 'fulfilled'})

            else:
                _logger.info(f"Shopify Webhook: Received unhandled topic '{topic}' — ignored.")

            env['shopify.sync.log'].sudo().log_sync(
                instance, 'webhook',
                records_processed=1,
                message=f"Webhook topic: {topic}",
            )

            return request.make_response(
                json.dumps({'status': 'success'}),
                status=200, headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error(f"Shopify Webhook Error: {str(e)}", exc_info=True)
            return request.make_response(
                json.dumps({'error': str(e)}),
                status=500, headers=[('Content-Type', 'application/json')]
            )
