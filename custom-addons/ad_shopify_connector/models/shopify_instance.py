from odoo import models, fields, api
from . import shopify_api_client
import logging

_logger = logging.getLogger(__name__)


class ShopifyInstance(models.Model):
    _name = 'shopify.instance'
    _description = 'Shopify Instance'

    name = fields.Char(string='Instance Name', required=True)
    shop_url = fields.Char(string='Shop URL', required=True,
                           help="e.g. your-shop.myshopify.com")
    access_token = fields.Char(string='API Access Token', required=True, password=True)
    webhook_secret = fields.Char(string='Webhook Secret (API Secret Key)', password=True,
                                 help="Used to verify webhook integrity")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('error', 'Error'),
    ], string='Status', default='draft')

    warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)

    active = fields.Boolean(default=True)
    last_sync_date = fields.Datetime(string='Last Sync', readonly=True)
    webhooks_registered = fields.Boolean(string='Webhooks Registered', default=False, readonly=True)

    auto_sync_products = fields.Boolean(string='Auto Sync Products', default=False)
    auto_sync_orders = fields.Boolean(string='Auto Sync Orders', default=False)
    auto_sync_inventory = fields.Boolean(string='Auto Sync Inventory', default=False)

    sync_log_ids = fields.One2many('shopify.sync.log', 'instance_id', string='Sync Logs')
    sync_log_count = fields.Integer(compute='_compute_sync_log_count')

    product_count = fields.Integer(compute='_compute_counts')
    order_count = fields.Integer(compute='_compute_counts')
    customer_count = fields.Integer(compute='_compute_counts')

    def _compute_sync_log_count(self):
        for rec in self:
            rec.sync_log_count = self.env['shopify.sync.log'].search_count(
                [('instance_id', '=', rec.id)]
            )

    def _compute_counts(self):
        for record in self:
            record.product_count = self.env['product.template'].search_count(
                [('shopify_instance_id', '=', record.id)]
            )
            record.order_count = self.env['sale.order'].search_count(
                [('shopify_instance_id', '=', record.id)]
            )
            record.customer_count = self.env['res.partner'].search_count(
                [('shopify_instance_id', '=', record.id)]
            )

    def action_view_products(self):
        self.ensure_one()
        return {
            'name': 'Shopify Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'kanban,list,form',
            'domain': [('shopify_instance_id', '=', self.id)],
            'context': {'default_shopify_instance_id': self.id}
        }

    def action_view_orders(self):
        self.ensure_one()
        return {
            'name': 'Shopify Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('shopify_instance_id', '=', self.id)],
            'context': {'default_shopify_instance_id': self.id}
        }

    def action_view_customers(self):
        self.ensure_one()
        return {
            'name': 'Shopify Customers',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'kanban,list,form',
            'domain': [('shopify_instance_id', '=', self.id)],
            'context': {'default_shopify_instance_id': self.id}
        }

    def action_view_sync_logs(self):
        self.ensure_one()
        return {
            'name': 'Sync Logs',
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.sync.log',
            'view_mode': 'list,form',
            'domain': [('instance_id', '=', self.id)],
        }

    def action_test_connection(self):
        self.ensure_one()
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(self.shop_url, self.access_token)
        shop_data = client.get('shop')
        if shop_data:
            self.state = 'confirmed'
            return self._notify(
                'Success',
                f"Connected to {shop_data.get('shop', {}).get('name')}",
                'success'
            )
        else:
            self.state = 'error'
            return self._notify(
                'Error',
                'Connection failed. Access token might be invalid or expired.',
                'danger'
            )

    def action_register_webhooks(self):
        self.ensure_one()
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(self.shop_url, self.access_token)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        if base_url.startswith('http://'):
            if 'localhost' not in base_url and '127.0.0.1' not in base_url:
                base_url = base_url.replace('http://', 'https://')
            else:
                from odoo.exceptions import UserError
                raise UserError(
                    "Shopify webhooks require a public HTTPS URL. "
                    "Your current base URL is HTTP / localhost.\n\n"
                    "Please expose your Odoo instance via HTTPS (e.g. using ngrok) "
                    "and update the 'web.base.url' system parameter under Settings -> Technical -> System Parameters."
                )

        topics = [
            'products/create',
            'products/update',
            'products/delete',
            'orders/create',
            'orders/updated',
            'orders/cancelled',
            'orders/fulfilled',
            'inventory_levels/update',
            'customers/create',
            'customers/update',
        ]

        existing = client.get("webhooks")
        existing_webhooks = existing.get('webhooks', []) if existing else []

        success_count = 0
        updated_count = 0
        skipped_count = 0

        for topic in topics:
            webhook_url = f"{base_url}/shopify/webhook/{self.id}/{topic}"

            matched_webhook = False
            for wh in existing_webhooks:
                if wh.get('topic') == topic:
                    matched_webhook = wh
                    break

            if matched_webhook:
                if matched_webhook.get('address') == webhook_url:
                    skipped_count += 1
                else:
                    wh_id = matched_webhook['id']
                    payload = {
                        "webhook": {
                            "id": wh_id,
                            "address": webhook_url
                        }
                    }
                    result = client.put(f"webhooks/{wh_id}", payload)
                    if result:
                        updated_count += 1
            else:
                payload = {
                    "webhook": {
                        "topic": topic,
                        "address": webhook_url,
                        "format": "json",
                    }
                }
                result = client.post("webhooks", payload)
                if result:
                    success_count += 1

        total_handled = success_count + updated_count + skipped_count
        if total_handled < len(topics):
            self.webhooks_registered = False
            from odoo.exceptions import UserError
            raise UserError(
                "Failed to register all webhooks on Shopify. Please ensure Odoo's 'web.base.url' "
                "is set to a public HTTPS address and try again.\n\n"
                f"Status: {success_count} registered, {updated_count} updated, {skipped_count} skipped, "
                f"{len(topics) - total_handled} failed."
            )

        msg = f"Registered: {success_count}, Updated: {updated_count}, Kept: {skipped_count}."
        self.webhooks_registered = True
        return self._notify(
            'Webhooks Synced',
            msg,
            'success'
        )

    def action_delete_webhooks(self):
        self.ensure_one()
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(self.shop_url, self.access_token)

        existing = client.get("webhooks")
        existing_webhooks = existing.get('webhooks', []) if existing else []

        url_identifier = f"/shopify/webhook/{self.id}/"
        deleted_count = 0

        for wh in existing_webhooks:
            if url_identifier in wh.get('address', ''):
                wh_id = wh['id']
                res = client.delete(f"webhooks/{wh_id}")
                if res is not False:
                    deleted_count += 1

        self.webhooks_registered = False
        return self._notify(
            'Webhooks Deleted',
            f"Successfully deleted {deleted_count} webhooks from Shopify.",
            'success'
        )

    def action_import_locations(self):
        self.ensure_one()
        success = self.env['stock.location'].import_locations(self)
        if success:
            return self._notify('Success', 'Imported/Updated locations from Shopify.', 'success')
        return self._notify('Error', 'Failed to import locations.', 'danger')

    def action_import_customers(self):
        self.ensure_one()
        result = self.env['res.partner'].import_customers(self)
        if result:
            return self._notify('Success',
                                f"Imported/Updated {result} customers.", 'success', reload=True)
        return self._notify('Warning', 'No customers found or import failed.', 'warning')

    def action_import_orders(self):
        self.ensure_one()
        result = self.env['sale.order'].import_orders(self)

        if result.get('imported', 0) > 0:
            msg = f"Successfully synced {result['imported']} new orders."
            if result.get('skipped', 0) > 0:
                msg += f" (Skipped {result['skipped']} — see logs)"
            return self._notify('Sync Complete', msg, 'success', reload=True)

        elif result.get('total', 0) > 0:
            reasons = []
            reason_map = {
                'already_exists': 'already imported',
                'no_products': 'missing products in Odoo',
                'no_partner': 'missing customer data',
            }
            for key, label in reason_map.items():
                if result['reason'].get(key):
                    reasons.append(f"{result['reason'][key]} {label}")
            msg = f"Found {result['total']} orders, none imported: " + ', '.join(reasons)
            return self._notify('No Orders Imported', msg, 'warning', sticky=True)

        return self._notify('No Orders Found',
                            result.get('error') or 'No orders found on Shopify.',
                            'info')

    def action_import_products(self):
        self.ensure_one()
        self = self.with_context(shopify_no_sync=True)
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(self.shop_url, self.access_token)

        imported_count = 0
        updated_count = 0
        failed_count = 0
        since_id = 0

        while True:
            products = client.get('products', params={'limit': 250, 'since_id': since_id})
            if not products or 'products' not in products or not products['products']:
                break

            for prod_data in products['products']:
                try:
                    is_new = False
                    is_updated = False
                    with self.env.cr.savepoint():
                        shopify_product_id = str(prod_data['id'])
                        since_id = prod_data['id']

                        existing_product = self.env['product.template'].search([
                            ('shopify_instance_id', '=', self.id),
                            ('shopify_product_id', '=', shopify_product_id),
                        ], limit=1)

                        if existing_product:
                            existing_product.write({
                                'name': prod_data.get('title', existing_product.name),
                                'description_sale': prod_data.get('body_html') or existing_product.description_sale,
                            })
                            odoo_product = existing_product
                            is_updated = True
                        else:
                            sku = ''
                            if prod_data.get('variants'):
                                sku = prod_data['variants'][0].get('sku', '')

                            odoo_product = False
                            if sku:
                                odoo_product = self.env['product.template'].search(
                                    [('default_code', '=', sku)], limit=1
                                )

                            if not odoo_product:
                                odoo_product = self.env['product.template'].create({
                                    'name': prod_data.get('title', 'Unknown'),
                                    'description_sale': prod_data.get('body_html', ''),
                                    'default_code': sku,
                                    'type': 'consu',
                                    'shopify_instance_id': self.id,
                                    'shopify_product_id': shopify_product_id,
                                    'shopify_product_tags': ','.join(prod_data.get('tags', '').split(',')) if prod_data.get('tags') else '',
                                    'exported_to_shopify': True,
                                })
                                is_new = True
                            else:
                                odoo_product.write({
                                    'shopify_instance_id': self.id,
                                    'shopify_product_id': shopify_product_id,
                                    'exported_to_shopify': True,
                                })
                                is_updated = True

                        options = prod_data.get('options', [])
                        has_options = len(options) > 0 and not (len(options) == 1 and options[0].get('name') == 'Title')

                        if has_options:
                            for opt_data in options:
                                opt_name = opt_data.get('name')
                                opt_values = opt_data.get('values', [])
                                if not opt_name or opt_name == 'Title':
                                    continue

                                attribute = self.env['product.attribute'].search([('name', '=', opt_name)], limit=1)
                                if not attribute:
                                    attribute = self.env['product.attribute'].create({'name': opt_name})

                                value_ids = []
                                for val_name in opt_values:
                                    val = self.env['product.attribute.value'].search([
                                        ('attribute_id', '=', attribute.id),
                                        ('name', '=', val_name),
                                    ], limit=1)
                                    if not val:
                                        val = self.env['product.attribute.value'].create({
                                            'attribute_id': attribute.id,
                                            'name': val_name,
                                        })
                                    value_ids.append(val.id)

                                attr_line = odoo_product.attribute_line_ids.filtered(lambda l: l.attribute_id == attribute)
                                if not attr_line:
                                    attr_line = self.env['product.template.attribute.line'].create({
                                        'product_tmpl_id': odoo_product.id,
                                        'attribute_id': attribute.id,
                                        'value_ids': [(6, 0, value_ids)],
                                    })
                                else:
                                    attr_line.write({'value_ids': [(6, 0, value_ids)]})

                            self.env.flush_all()
                            odoo_product.invalidate_recordset(['product_variant_ids'])

                        for v_data in prod_data.get('variants', []):
                            shopify_variant_id = str(v_data['id'])
                            v_sku = v_data.get('sku')

                            odoo_variant = False
                            if has_options:
                                matched_variants = odoo_product.product_variant_ids
                                for idx, opt in enumerate(options):
                                    opt_name = opt.get('name')
                                    if not opt_name or opt_name == 'Title':
                                        continue
                                    opt_val = v_data.get(f'option{idx+1}')
                                    if opt_val:
                                        matched_variants = matched_variants.filtered(
                                            lambda v: any(
                                                av.attribute_id.name == opt_name and av.name == opt_val
                                                for av in v.product_template_attribute_value_ids
                                            )
                                        )
                                if matched_variants:
                                    odoo_variant = matched_variants[0]
                            else:
                                odoo_variant = odoo_product.product_variant_id

                            if not odoo_variant and v_sku:
                                odoo_variant = self.env['product.product'].search([
                                    ('product_tmpl_id', '=', odoo_product.id),
                                    ('default_code', '=', v_sku),
                                ], limit=1)

                            if odoo_variant:
                                vals = {
                                    'shopify_variant_id': shopify_variant_id,
                                    'shopify_inventory_item_id': str(v_data.get('inventory_item_id', '')),
                                    'lst_price': float(v_data.get('price') or 0.0) or odoo_variant.lst_price,
                                }
                                if v_sku:
                                    vals['default_code'] = v_sku
                                if v_data.get('barcode'):
                                    vals['barcode'] = v_data['barcode']
                                if v_data.get('weight'):
                                    vals['weight'] = float(v_data['weight'])

                                odoo_variant.write(vals)
                        
                        self.env.flush_all()

                    if is_new:
                        imported_count += 1
                    elif is_updated:
                        updated_count += 1

                except Exception as e:
                    _logger.error(f"Error importing Shopify product {prod_data.get('id')}: {e}")
                    failed_count += 1

            if len(products['products']) < 250:
                break

        self.env['shopify.sync.log'].log_sync(
            self, 'products',
            records_processed=imported_count + updated_count,
            records_failed=failed_count,
            message=f"Imported: {imported_count}, Updated: {updated_count}, Failed: {failed_count}",
        )

        return self._notify(
            'Sync Complete',
            f"Products synced — Imported: {imported_count}, Updated: {updated_count}"
            + (f", Failed: {failed_count}" if failed_count else ''),
            'success' if not failed_count else 'warning',
            reload=True,
        )

    def action_sync_inventory(self):
        self.ensure_one()
        locations = self.env['stock.location'].search([
            ('shopify_instance_id', '=', self.id),
            ('shopify_location_id', '!=', False),
        ])
        if not locations:
            return self._notify('Warning',
                                'No Shopify locations configured. Import locations first.',
                                'warning')

        synced = 0
        failed = 0
        for loc in locations:
            variants = self.env['product.product'].search([
                ('product_tmpl_id.shopify_instance_id', '=', self.id),
                ('shopify_inventory_item_id', '!=', False),
            ])
            for variant in variants:
                try:
                    loc.sync_product_stock(variant)
                    synced += 1
                except Exception as e:
                    _logger.error(f"Inventory sync error for variant {variant.id}: {e}")
                    failed += 1

        self.env['shopify.sync.log'].log_sync(
            self, 'inventory',
            records_processed=synced,
            records_failed=failed,
            message=f"Synced {synced} inventory levels to Shopify.",
        )
        return self._notify('Inventory Synced',
                            f"Pushed {synced} inventory records to Shopify.",
                            'success')

    @api.model
    def cron_sync_all(self):
        instances = self.search([('state', '=', 'confirmed'), ('active', '=', True)])
        for inst in instances:
            try:
                if inst.auto_sync_orders:
                    inst.action_import_orders()
                if inst.auto_sync_products:
                    inst.action_import_products()
                if inst.auto_sync_inventory:
                    inst.action_sync_inventory()
            except Exception as e:
                _logger.error(f"Cron sync failed for instance {inst.name}: {e}")
                self.env['shopify.sync.log'].log_sync(
                    inst, 'orders', records_failed=1,
                    message=str(e), state='error'
                )

    def _notify(self, title, message, msg_type, sticky=False, reload=False):
        params = {
            'title': title,
            'message': message,
            'type': msg_type,
            'sticky': sticky,
        }
        if reload:
            params['next'] = {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': params,
        }
