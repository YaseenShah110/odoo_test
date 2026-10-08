{
    "name": "eBakery Max Sport Theme",
    "version": "19.0.1.0.0",
    "category": "Website/Theme",
    "summary": "Custom frontend theme for the Max Sport website",
    "description": """
eBakery Max Sport Theme
========================
Custom Odoo 19 website theme built section-by-section from the client's
Figma design. Extends core website/website_sale templates via inheritance
only; no core files are modified.
""",
    "author": "eBakery",
    "website": "https://www.ebakery.de",
    "license": "LGPL-3",
    "depends": [
        "website",
        "website_sale",
    ],
    "data": [
        "views/templates/topbar.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "ebakery_maxs_theme/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "ebakery_maxs_theme/static/src/scss/variables.scss",
            "ebakery_maxs_theme/static/src/scss/theme.scss",
            "ebakery_maxs_theme/static/src/scss/components/**/*.scss",
            "ebakery_maxs_theme/static/src/js/interactions/**/*.js",
        ],
    },
    "installable": True,
    "application": False,
}
