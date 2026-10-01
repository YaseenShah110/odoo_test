from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ShopifyExportCustomerWizard(models.TransientModel):
    _name = 'shopify.export.customer.wizard'
    _description = 'Export Customers to Shopify Wizard'

    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True)

    def action_export(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError(_("No customers selected."))

        partners = self.env['res.partner'].browse(active_ids)
        exported_count = 0
        
        for partner in partners:
            partner.export_to_shopify(instance=self.instance_id)
            exported_count += 1
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Export Complete',
                'message': f"Successfully exported/updated {exported_count} customers to {self.instance_id.name}.",
                'type': 'success',
                'sticky': False,
            }
        }
