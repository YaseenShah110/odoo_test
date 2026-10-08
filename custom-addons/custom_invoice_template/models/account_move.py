from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_download_custom_invoice(self):
        """Generate and download the custom-designed invoice PDF.

        This never touches the core 'account.report_invoice_document'
        template or the standard Print/Send actions - it uses an entirely
        separate report defined by this module.
        """
        self.ensure_one()
        report = self.env.ref('custom_invoice_template.action_report_custom_invoice')
        return report.report_action(self)
