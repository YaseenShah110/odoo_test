# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Theme-level, client-editable settings (e.g. toggles for optional
    # sections, social links not covered by website snippets) are added
    # here as fields + ir.config_parameter, section by section.
    # Example (not active):
    #
    # ebakery_theme_show_promo_bar = fields.Boolean(
    #     string="Show Promo Bar",
    #     config_parameter="ebakery_maxs_theme.show_promo_bar",
    # )
