import base64
import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_instance_id = fields.Many2one(
        'shopify.instance', string='Shopify Instance', ondelete='set null', index=True
    )
    shopify_product_id = fields.Char(string='Shopify Product ID', readonly=True, index=True)
    exported_to_shopify = fields.Boolean(default=False, readonly=True)
    shopify_product_tags = fields.Char(string='Shopify Tags')
    shopify_last_exported = fields.Datetime(string='Last Exported to Shopify', readonly=True)



    def unlink_from_shopify(self):
        for record in self:
            record.shopify_product_id = False
            record.exported_to_shopify = False
            record.product_variant_ids.write({
                'shopify_variant_id': False,
                'shopify_inventory_item_id': False,
            })

    def export_to_shopify(self, instance=False):
        for record in self:
            inst = instance or record.shopify_instance_id
            if not inst:
                inst = self.env['shopify.instance'].search([('state', '=', 'confirmed')], limit=1)
            if not inst:
                continue

            from .shopify_api_client import ShopifyAPIClient
            client = ShopifyAPIClient(inst.shop_url, inst.access_token)

            options = []
            attr_lines = record.attribute_line_ids
            for line in attr_lines[:3]:
                options.append({
                    "name": line.attribute_id.name,
                    "values": line.value_ids.mapped('name')
                })

            product_data = {
                "product": {
                    "title": record.name,
                    "body_html": record.description_sale or "",
                    "vendor": record.env.company.name,
                    "product_type": record.categ_id.name if record.categ_id else "",
                    "tags": record.shopify_product_tags or "",
                    "variants": [],
                }
            }

            if options:
                product_data["product"]["options"] = options

            for variant in record.product_variant_ids:
                variant_data = {
                    "price": str(variant.lst_price),
                    "sku": variant.default_code or "",
                    "barcode": variant.barcode or "",
                    "weight": variant.weight or 0.0,
                    "inventory_management": "shopify",
                    "inventory_policy": "deny",
                }
                if variant.shopify_variant_id:
                    variant_data["id"] = int(variant.shopify_variant_id)

                for idx, line in enumerate(attr_lines[:3]):
                    val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == line.attribute_id)
                    if val:
                        variant_data[f"option{idx+1}"] = val[0].name
                    else:
                        variant_data[f"option{idx+1}"] = "Default"

                product_data["product"]["variants"].append(variant_data)

            if record.shopify_product_id:
                result = client.put(f"products/{record.shopify_product_id}", product_data)
                if not result:
                    from odoo.exceptions import UserError
                    raise UserError(f"Failed to update product {record.name} on Shopify.")
            else:
                result = client.post("products", product_data)
                if result and 'product' in result:
                    record.write({
                        'shopify_instance_id': inst.id,
                        'shopify_product_id': str(result['product']['id']),
                        'exported_to_shopify': True,
                        'shopify_last_exported': fields.Datetime.now(),
                    })
                    for v_data in result['product']['variants']:
                        v_sku = v_data.get('sku')
                        shopify_v_id = str(v_data['id'])
                        shopify_inv_id = str(v_data.get('inventory_item_id', ''))

                        odoo_variant = False
                        if v_sku:
                            odoo_variant = record.product_variant_ids.filtered(lambda v: v.default_code == v_sku)

                        if not odoo_variant and options:
                            matched = record.product_variant_ids
                            for idx, opt in enumerate(options):
                                opt_val = v_data.get(f"option{idx+1}")
                                if opt_val:
                                    matched = matched.filtered(
                                        lambda v: any(
                                            av.attribute_id.name == opt['name'] and av.name == opt_val
                                            for av in v.product_template_attribute_value_ids
                                        )
                                    )
                            if matched:
                                odoo_variant = matched[0]

                        if not odoo_variant and len(record.product_variant_ids) == 1:
                            odoo_variant = record.product_variant_id

                        if odoo_variant:
                            odoo_variant.write({
                                'shopify_variant_id': shopify_v_id,
                                'shopify_inventory_item_id': shopify_inv_id,
                            })

                    record._push_image_to_shopify(client, result['product']['id'])

    def _push_image_to_shopify(self, client, shopify_product_id):
        self.ensure_one()
        if not self.image_1920:
            return
        try:
            img_b64 = self.image_1920.decode('utf-8') if isinstance(self.image_1920, bytes) else self.image_1920
            payload = {
                "image": {
                    "attachment": img_b64,
                    "filename": f"{self.name.replace(' ', '_')}.jpg",
                }
            }
            client.post(f"products/{shopify_product_id}/images", payload)
        except Exception as e:
            _logger.warning(f"Could not push image for product {self.name}: {e}")

    def action_push_to_shopify(self):
        return {
            'name': 'Export to Shopify',
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.export.product.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_instance_id': self.shopify_instance_id.id if len(self) == 1 and self.shopify_instance_id else False,
                'active_ids': self.ids,
                'active_model': self._name,
            }
        }

    def action_sync_from_shopify(self):
        self = self.with_context(shopify_no_sync=True)
        for record in self:
            inst = record.shopify_instance_id
            if not inst:
                inst = self.env['shopify.instance'].search([('state', '=', 'confirmed')], limit=1)
            if not inst:
                from odoo.exceptions import UserError
                raise UserError("No active Shopify instance found.")

            shopify_id = record.shopify_product_id
            if not shopify_id:
                from odoo.exceptions import UserError
                raise UserError(f"Product '{record.name}' is not linked to a Shopify product.")

            from .shopify_api_client import ShopifyAPIClient
            client = ShopifyAPIClient(inst.shop_url, inst.access_token)

            try:
                res = client.get(f"products/{shopify_id}")
            except Exception as e:
                from odoo.exceptions import UserError
                raise UserError(f"Failed to fetch product from Shopify: {e}")

            if not res or 'product' not in res:
                from odoo.exceptions import UserError
                raise UserError(f"Product {shopify_id} not found on Shopify.")

            record._update_from_shopify_data(res['product'], inst)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': 'Product(s) synced from Shopify.',
                'type': 'success',
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def _update_from_shopify_data(self, prod_data, inst):
        self.ensure_one()
        self.write({
            'name': prod_data.get('title', self.name),
            'description_sale': prod_data.get('body_html') or self.description_sale,
            'shopify_product_tags': ','.join(prod_data.get('tags', '').split(',')) if prod_data.get('tags') else '',
            'exported_to_shopify': True,
            'shopify_instance_id': inst.id,
        })

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

                attr_line = self.attribute_line_ids.filtered(lambda l: l.attribute_id == attribute)
                if not attr_line:
                    attr_line = self.env['product.template.attribute.line'].create({
                        'product_tmpl_id': self.id,
                        'attribute_id': attribute.id,
                        'value_ids': [(6, 0, value_ids)],
                    })
                else:
                    attr_line.write({'value_ids': [(6, 0, value_ids)]})

            self.env.flush_all()
            self.invalidate_recordset(['product_variant_ids'])

        for v_data in prod_data.get('variants', []):
            shopify_variant_id = str(v_data['id'])
            v_sku = v_data.get('sku')

            odoo_variant = False
            if has_options:
                matched_variants = self.product_variant_ids
                for idx, opt in enumerate(options):
                    opt_name = opt.get('name')
                    if not opt_name or opt_name == 'Title':
                        continue
                    opt_val = v_data.get(f'option{idx+1}')
                    if opt_val:
                        matched_variants = matched_variants.filtered(
                            lambda v: any(
                                ptav.name == opt_val
                                for ptav in v.product_template_attribute_value_ids
                            )
                        )
                if matched_variants:
                    odoo_variant = matched_variants[0]
            else:
                odoo_variant = self.product_variant_ids[:1]

            if odoo_variant:
                write_vals = {
                    'shopify_variant_id': shopify_variant_id,
                    'shopify_inventory_item_id': str(v_data.get('inventory_item_id') or ''),
                }
                if v_sku:
                    write_vals['default_code'] = v_sku
                if v_data.get('price'):
                    write_vals['lst_price'] = float(v_data['price'])
                if v_data.get('weight'):
                    write_vals['weight'] = float(v_data['weight'])
                if v_data.get('barcode'):
                    write_vals['barcode'] = v_data['barcode']

                odoo_variant.write(write_vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    shopify_variant_id = fields.Char(string='Shopify Variant ID', readonly=True, index=True)
    shopify_inventory_item_id = fields.Char(string='Shopify Inventory Item ID', readonly=True)
