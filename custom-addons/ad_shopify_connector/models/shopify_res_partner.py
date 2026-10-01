from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    shopify_instance_id = fields.Many2one(
        'shopify.instance', string='Shopify Instance', ondelete='set null', index=True
    )
    shopify_customer_id = fields.Char(string='Shopify Customer ID', readonly=True, index=True)
    shopify_marketing_opt_in = fields.Boolean(
        string='Shopify Marketing Opt-in', readonly=True
    )
    shopify_customer_tags = fields.Char(string='Shopify Customer Tags', readonly=True)

    @api.model
    def import_customers(self, instance):
        self = self.with_context(shopify_no_sync=True)
        from .shopify_api_client import ShopifyAPIClient
        client = ShopifyAPIClient(instance.shop_url, instance.access_token)

        total = 0
        since_id = 0

        while True:
            customers = client.get('customers', params={'limit': 250, 'since_id': since_id})
            if not customers or 'customers' not in customers:
                break

            batch = customers['customers']
            if not batch:
                break

            for cust_data in batch:
                try:
                    with self.env.cr.savepoint():
                        shopify_id = str(cust_data.get('id'))
                        email = cust_data.get('email')

                        partner = self.search([
                            ('shopify_customer_id', '=', shopify_id),
                            ('shopify_instance_id', '=', instance.id),
                        ], limit=1)

                        if not partner and email:
                            partner = self.search([('email', '=', email)], limit=1)

                        addr = cust_data.get('default_address', {})
                        country = False
                        if addr.get('country_code'):
                            country = self.env['res.country'].search(
                                [('code', '=', addr['country_code'])], limit=1
                            )
                        state = False
                        if addr.get('province_code') and country:
                            state = self.env['res.country.state'].search([
                                ('code', '=', addr['province_code']),
                                ('country_id', '=', country.id),
                            ], limit=1)

                        vals = {
                            'name': f"{cust_data.get('first_name', '')} {cust_data.get('last_name', '')}".strip()
                                    or 'Unknown',
                            'email': email,
                            'phone': cust_data.get('phone') or addr.get('phone'),
                            'street': addr.get('address1'),
                            'street2': addr.get('address2'),
                            'city': addr.get('city'),
                            'zip': addr.get('zip'),
                            'country_id': country.id if country else False,
                            'state_id': state.id if state else False,
                            'shopify_instance_id': instance.id,
                            'shopify_customer_id': shopify_id,
                            'shopify_marketing_opt_in': cust_data.get('accepts_marketing', False),
                            'shopify_customer_tags': cust_data.get('tags', ''),
                        }

                        if partner:
                            partner.write(vals)
                        else:
                            self.create(vals)

                        self.env.flush_all()

                    total += 1

                except Exception as e:
                    _logger.error(f"Error importing customer {cust_data.get('id')}: {e}")

            if len(batch) < 250:
                break
            since_id = batch[-1]['id']

        self.env['shopify.sync.log'].log_sync(
            instance, 'customers',
            records_processed=total,
            message=f"Imported/Updated {total} customers.",
        )
        return total



    def export_to_shopify(self, instance=False):
        for record in self:
            inst = instance or record.shopify_instance_id
            if not inst:
                inst = self.env['shopify.instance'].search([('state', '=', 'confirmed')], limit=1)
            if not inst:
                continue

            from .shopify_api_client import ShopifyAPIClient
            client = ShopifyAPIClient(inst.shop_url, inst.access_token)

            name_parts = (record.name or '').split(' ', 1)
            first_name = name_parts[0] if name_parts else (record.name or '')
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            customer_data = {
                "customer": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": record.email or "",
                    "phone": record.phone or "",
                    "addresses": []
                }
            }

            if record.street or record.city:
                customer_data["customer"]["addresses"].append({
                    "address1": record.street or "",
                    "address2": record.street2 or "",
                    "city": record.city or "",
                    "province": record.state_id.name if record.state_id else "",
                    "zip": record.zip or "",
                    "country": record.country_id.name if record.country_id else "",
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": record.phone or "",
                })

            if record.shopify_customer_id:
                result = client.put(f"customers/{record.shopify_customer_id}", customer_data)
                if not result:
                    from odoo.exceptions import UserError
                    raise UserError(f"Failed to update customer {record.name} on Shopify.")
            else:
                result = client.post("customers", customer_data)
                if result and 'customer' in result:
                    record.write({
                        'shopify_instance_id': inst.id,
                        'shopify_customer_id': str(result['customer']['id']),
                    })

    def action_push_to_shopify(self):
        return {
            'name': 'Export to Shopify',
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.export.customer.wizard',
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

            shopify_id = record.shopify_customer_id
            if not shopify_id:
                from odoo.exceptions import UserError
                raise UserError(f"Customer '{record.name}' is not linked to a Shopify customer.")

            from .shopify_api_client import ShopifyAPIClient
            client = ShopifyAPIClient(inst.shop_url, inst.access_token)

            try:
                res = client.get(f"customers/{shopify_id}")
            except Exception as e:
                from odoo.exceptions import UserError
                raise UserError(f"Failed to fetch customer from Shopify: {e}")

            if not res or 'customer' not in res:
                from odoo.exceptions import UserError
                raise UserError(f"Customer {shopify_id} not found on Shopify.")

            cust_data = res['customer']
            email = cust_data.get('email')
            addr = cust_data.get('default_address', {})
            country = False
            if addr.get('country_code'):
                country = self.env['res.country'].search(
                    [('code', '=', addr['country_code'])], limit=1
                )
            state = False
            if addr.get('province_code') and country:
                state = self.env['res.country.state'].search([
                    ('code', '=', addr['province_code']),
                    ('country_id', '=', country.id),
                ], limit=1)

            vals = {
                'name': f"{cust_data.get('first_name', '')} {cust_data.get('last_name', '')}".strip() or 'Unknown',
                'email': email,
                'phone': cust_data.get('phone') or addr.get('phone'),
                'street': addr.get('address1'),
                'street2': addr.get('address2'),
                'city': addr.get('city'),
                'zip': addr.get('zip'),
                'country_id': country.id if country else False,
                'state_id': state.id if state else False,
                'shopify_instance_id': inst.id,
                'shopify_marketing_opt_in': cust_data.get('accepts_marketing', False),
                'shopify_customer_tags': cust_data.get('tags', ''),
            }
            record.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': 'Customer(s) synced from Shopify.',
                'type': 'success',
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }
