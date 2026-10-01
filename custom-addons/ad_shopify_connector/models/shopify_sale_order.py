from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_instance_id = fields.Many2one(
        'shopify.instance', string='Shopify Instance', ondelete='set null', index=True
    )
    shopify_order_id = fields.Char(string='Shopify Order ID', readonly=True, index=True)
    shopify_order_number = fields.Char(string='Shopify Order #', readonly=True)
    shopify_fulfillment_status = fields.Char(string='Shopify Fulfillment Status', readonly=True)
    shopify_financial_status = fields.Char(string='Shopify Financial Status', readonly=True)
    shopify_tags = fields.Char(string='Shopify Tags', readonly=True)
    shopify_note = fields.Text(string='Shopify Note', readonly=True)

    @api.model
    def import_orders(self, instance, order_data=None):
        self = self.with_context(shopify_no_sync=True)
        import_stats = {'total': 0, 'imported': 0, 'skipped': 0,
                        'reason': {}, 'error': ''}

        if order_data:
            orders_list = [order_data]
            _logger.info(f"Importing specific Shopify order: {order_data.get('id')}")
        else:
            from .shopify_api_client import ShopifyAPIClient
            client = ShopifyAPIClient(instance.shop_url, instance.access_token)
            params = {
                'status': 'any',
                'fulfillment_status': 'any',
                'financial_status': 'any',
                'limit': 250,
            }
            orders_list = []
            since_id = 0
            while True:
                p = dict(params, since_id=since_id)
                orders = client.get('orders', params=p)
                if not orders or 'orders' not in orders:
                    if not orders_list:
                        _logger.warning(
                            f"No orders found on Shopify for instance {instance.name}"
                        )
                        return {'total': 0, 'imported': 0, 'skipped': 0,
                                'error': 'No response from Shopify', 'reason': {}}
                    break
                batch = orders['orders']
                if not batch:
                    break
                orders_list.extend(batch)
                _logger.info(
                    f"Fetched {len(batch)} orders (total so far: {len(orders_list)})"
                )
                if len(batch) < 250:
                    break
                since_id = batch[-1]['id']

            _logger.info(f"Total {len(orders_list)} orders to process for {instance.name}")

        import_stats['total'] = len(orders_list)

        for order_data in orders_list:
            try:
                status_update = None
                with self.env.cr.savepoint():
                    shopify_id = str(order_data.get('id'))

                    order = self.search([
                        ('shopify_order_id', '=', shopify_id),
                        ('shopify_instance_id', '=', instance.id),
                    ], limit=1)

                    if order:
                        order.write({
                            'shopify_fulfillment_status': order_data.get('fulfillment_status') or 'unfulfilled',
                            'shopify_financial_status': order_data.get('financial_status', ''),
                        })
                        status_update = 'already_exists'
                    else:
                        partner = self._resolve_partner(instance, order_data)
                        if not partner:
                            status_update = 'no_partner'
                        else:
                            default_pricelist = self.env.ref('product.list0', raise_if_not_found=False)
                            pricelist_id = instance.pricelist_id.id or \
                                (default_pricelist.id if default_pricelist else False)

                            order_vals = {
                                'partner_id': partner.id,
                                'warehouse_id': instance.warehouse_id.id,
                                'pricelist_id': pricelist_id,
                                'origin': order_data.get('name'),
                                'shopify_instance_id': instance.id,
                                'shopify_order_id': shopify_id,
                                'shopify_order_number': order_data.get('name', ''),
                                'shopify_fulfillment_status': order_data.get('fulfillment_status') or 'unfulfilled',
                                'shopify_financial_status': order_data.get('financial_status', ''),
                                'shopify_tags': order_data.get('tags', ''),
                                'shopify_note': order_data.get('note', ''),
                                'order_line': [],
                            }

                            for line in order_data.get('line_items', []):
                                product = self._resolve_product(instance, line)

                                if product:
                                    discount_pct = 0.0
                                    if line.get('discount_allocations'):
                                        total_discount = sum(
                                            float(d.get('amount', 0))
                                            for d in line['discount_allocations']
                                        )
                                        line_total = float(line.get('price', 0)) * line.get('quantity', 1)
                                        if line_total:
                                            discount_pct = round((total_discount / line_total) * 100, 2)

                                    order_vals['order_line'].append((0, 0, {
                                        'product_id': product.id,
                                        'name': line.get('title', product.name),
                                        'product_uom_qty': line.get('quantity', 1),
                                        'price_unit': float(line.get('price', 0)),
                                        'discount': discount_pct,
                                    }))
                                else:
                                    _logger.warning(
                                        f"Product variant {line.get('variant_id')} "
                                        f"(SKU: {line.get('sku')}) not found for order "
                                        f"{order_data.get('name')}. Skipping line."
                                    )

                            for shipping in order_data.get('shipping_lines', []):
                                delivery_product = self.env.ref(
                                    'sale_management.product_product_delivery', raise_if_not_found=False
                                )
                                if delivery_product and float(shipping.get('price', 0)) > 0:
                                    order_vals['order_line'].append((0, 0, {
                                        'product_id': delivery_product.product_variant_id.id,
                                        'name': shipping.get('title', 'Shipping'),
                                        'product_uom_qty': 1,
                                        'price_unit': float(shipping.get('price', 0)),
                                    }))

                            if order_vals['order_line']:
                                self.create(order_vals)
                                status_update = 'imported'
                            else:
                                _logger.error(
                                    f"No matching products for Shopify order {shopify_id}. Skipping."
                                )
                                status_update = 'no_products'

                    self.env.flush_all()

                if status_update == 'already_exists':
                    import_stats['skipped'] += 1
                    import_stats['reason']['already_exists'] = \
                        import_stats['reason'].get('already_exists', 0) + 1
                elif status_update == 'no_partner':
                    import_stats['skipped'] += 1
                    import_stats['reason']['no_partner'] = \
                        import_stats['reason'].get('no_partner', 0) + 1
                elif status_update == 'imported':
                    import_stats['imported'] += 1
                elif status_update == 'no_products':
                    import_stats['skipped'] += 1
                    import_stats['reason']['no_products'] = \
                        import_stats['reason'].get('no_products', 0) + 1

            except Exception as e:
                _logger.error(f"Error processing Shopify order {order_data.get('id')}: {e}")
                import_stats['skipped'] += 1

        self.env['shopify.sync.log'].log_sync(
            instance, 'orders',
            records_processed=import_stats['imported'],
            records_failed=import_stats['skipped'],
            message=(
                f"Total: {import_stats['total']}, "
                f"Imported: {import_stats['imported']}, "
                f"Skipped: {import_stats['skipped']}"
            ),
        )

        return import_stats

    def _resolve_partner(self, instance, order_data):
        ResPartner = self.env['res.partner']
        cust_data = order_data.get('customer')

        if cust_data:
            partner = ResPartner.search([
                ('shopify_customer_id', '=', str(cust_data.get('id'))),
                ('shopify_instance_id', '=', instance.id),
            ], limit=1)

            if not partner:
                email = cust_data.get('email')
                if email:
                    partner = ResPartner.search([('email', '=', email)], limit=1)

            if not partner:
                partner = ResPartner.create({
                    'name': f"{cust_data.get('first_name', '')} {cust_data.get('last_name', '')}".strip()
                             or 'Unknown Shopify Customer',
                    'email': cust_data.get('email'),
                    'shopify_instance_id': instance.id,
                    'shopify_customer_id': str(cust_data.get('id')),
                })
            return partner

        billing = order_data.get('billing_address', {})
        name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip() \
               or 'Shopify Guest'
        email = order_data.get('email') or order_data.get('contact_email')

        if email:
            partner = ResPartner.search([('email', '=', email)], limit=1)
            if partner:
                return partner

        return ResPartner.create({
            'name': name,
            'email': email,
            'shopify_instance_id': instance.id,
            'comment': 'Created from Shopify guest order',
        })

    def _resolve_product(self, instance, line):
        ProductProduct = self.env['product.product']
        variant_id = str(line.get('variant_id', ''))

        product = ProductProduct.search(
            [('shopify_variant_id', '=', variant_id)], limit=1
        ) if variant_id and variant_id != 'None' else None

        if not product and line.get('sku'):
            product = ProductProduct.search(
                [('default_code', '=', line['sku'])], limit=1
            )
            if product:
                product.write({
                    'shopify_variant_id': variant_id,
                    'shopify_inventory_item_id': str(line.get('inventory_item_id', '')),
                })

        return product

    def _handle_shopify_cancellation(self, data):
        self.ensure_one()
        if self.state == 'cancel':
            return True
        try:
            self.action_cancel()
            self.message_post(
                body=f"Order cancelled via Shopify Webhook. "
                     f"Reason: {data.get('cancel_reason', 'Not specified')}"
            )
        except Exception as e:
            _logger.warning(
                f"Could not auto-cancel Odoo order {self.name}: {e}"
            )
            self.message_post(
                body=f"Shopify order was cancelled but Odoo order could not be "
                     f"auto-cancelled. Error: {e}"
            )
        return True

    def action_export_to_shopify(self):
        self.ensure_one()
        if not self.shopify_instance_id:
            from odoo.exceptions import UserError
            raise UserError("Please select a Shopify Instance for this order first.")

        instance = self.shopify_instance_id
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(instance.shop_url, instance.access_token)

        payload = {
            "draft_order": {
                "line_items": [],
                "use_customer_default_address": True,
            }
        }

        if self.partner_id.shopify_customer_id:
            payload["draft_order"]["customer"] = {
                "id": int(self.partner_id.shopify_customer_id)
            }

        for line in self.order_line:
            if line.display_type:
                continue
            if line.product_id.shopify_variant_id:
                payload["draft_order"]["line_items"].append({
                    "variant_id": int(line.product_id.shopify_variant_id),
                    "quantity": int(line.product_uom_qty),
                    "price": str(line.price_unit),
                })
            else:
                payload["draft_order"]["line_items"].append({
                    "title": line.name,
                    "price": str(line.price_unit),
                    "quantity": int(line.product_uom_qty),
                })

        result = client.post("draft_orders", payload)
        if result and 'draft_order' in result:
            self.write({
                'shopify_order_id': str(result['draft_order']['id']),
                'shopify_fulfillment_status': 'draft',
            })
            self.message_post(
                body=f"Order exported to Shopify as Draft Order ID: {result['draft_order']['id']}"
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Order exported to Shopify as Draft Order.',
                    'type': 'success',
                }
            }
        return False
