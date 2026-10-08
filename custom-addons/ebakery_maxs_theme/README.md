# eBakery Max Sport Theme

Custom Odoo 19 website frontend module for the Max Sport project, built
section by section from Figma screenshots.

## Scope

- Depends on `website`, `website_sale`.
- All styling lives in SCSS design tokens (`static/src/scss/variables.scss`,
  `primary_variables.scss`) — no hardcoded colors/sizes in templates.
- All DOM interactivity uses the Interaction framework
  (`@web/public/interaction`), registered per block under
  `static/src/js/interactions/`.
- Core Odoo/website templates are never edited — only extended via
  `inherit_id` + `xpath`.

## Structure

- `controllers/` — inherited Website/WebsiteSale controllers (added only
  when a section needs server-side logic).
- `models/` — `res.config.settings` extensions for theme-level, client
  editable settings.
- `views/templates/` — one QWeb inheritance file per page section
  (header, hero, listing, product page, cart, footer, ...).
- `views/snippets/` — custom snippet definitions + snippet options.
- `static/src/scss/components/` — one SCSS partial per section.
- `static/src/js/interactions/` — one Interaction per interactive block.
- `i18n/` — German (`de.po`) translations.

## Status

Scaffold only. No UI has been built yet — see module TODO / project
conversation for section-by-section delivery order (header → hero →
listing → product page → cart → footer).
