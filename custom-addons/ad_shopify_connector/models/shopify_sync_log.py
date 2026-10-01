from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ShopifySyncLog(models.Model):
    _name = 'shopify.sync.log'
    _description = 'Shopify Sync Log'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    instance_id = fields.Many2one('shopify.instance', string='Instance', ondelete='cascade', index=True)
    sync_type = fields.Selection([
        ('products', 'Products'),
        ('orders', 'Orders'),
        ('customers', 'Customers'),
        ('inventory', 'Inventory'),
        ('locations', 'Locations'),
        ('fulfillment', 'Fulfillment'),
        ('webhook', 'Webhook'),
    ], string='Sync Type', required=True)
    state = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('error', 'Error'),
    ], string='Status', default='success')
    records_processed = fields.Integer(string='Records Processed', default=0)
    records_failed = fields.Integer(string='Records Failed', default=0)
    message = fields.Text(string='Message / Error Details')
    create_date = fields.Datetime(string='Sync Date', readonly=True)

    @api.depends('instance_id', 'sync_type', 'create_date')
    def _compute_name(self):
        for rec in self:
            inst = rec.instance_id.name if rec.instance_id else 'N/A'
            rec.name = f"[{rec.sync_type}] {inst}"

    @api.model
    def log_sync(self, instance, sync_type, records_processed=0,
                 records_failed=0, message='', state=None):
        if state is None:
            state = 'error' if records_failed and not records_processed else \
                    'partial' if records_failed else 'success'
        self.create({
            'instance_id': instance.id,
            'sync_type': sync_type,
            'state': state,
            'records_processed': records_processed,
            'records_failed': records_failed,
            'message': message,
        })
        instance.sudo().write({'last_sync_date': fields.Datetime.now()})
