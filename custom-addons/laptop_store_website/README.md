# Laptop Store (`laptop_store_website`)

## 1. Purpose

A laptop storefront built **on top of Odoo's own e-commerce stack**
(`website_sale`) rather than a hand-rolled one. Laptops are real Odoo
products, so cart, checkout, payment, and invoicing are Odoo's standard,
tested flow — nothing custom-built for that part.

> **v1 → v2 → v3 note:** v1 stored laptops in a custom
> `laptop.store.laptop` model with no cart/checkout (a pure catalogue).
> v2 retired that model and migrated to real `product.template` records
> so laptops can actually be sold through Odoo's normal Sales →
> Invoicing workflow. v3 removed the custom `/laptops` controller and
> hand-built grid entirely, replacing it with a plain Website page built
> from real Odoo snippets (a title block + the native "Products" dynamic
> snippet), so the page is drag-and-drop customizable exactly like any
> other theme page. See section 12 for what that changed.

> **Naming note:** the addon's technical name is `laptop_store_website`
> rather than `laptop_store`, because an unrelated pre-existing practice
> module already uses the technical name `laptop_store`
> (`custom-addons/project_1/laptop_store`, model `laptop.product`). Both
> modules are loaded from the same `addons_path` in `config/odoo.conf`,
> and Odoo requires unique module names across the whole path, so keeping
> the old module's name was not an option without removing it.

## 2. Requirements

* Odoo 19 (this repo, `C:\odoo\odoo19`)
* PostgreSQL database configured in `config/odoo.conf`
* `website_sale` (Odoo's Shop app) and `payment_custom` (Wire Transfer
  provider) — both are dependencies of this module and get installed
  automatically with it.

## 3. Installation

1. The module lives at `C:\odoo\odoo19\custom-addons\laptop_store_website`.
2. It has been added to `addons_path` in `config/odoo.conf`.
3. Install/upgrade it against the `odoo19` database:

   ```bash
   python odoo-bin -c config/odoo.conf -d odoo19 -i laptop_store_website --stop-after-init
   ```

   To upgrade after further changes:

   ```bash
   python odoo-bin -c config/odoo.conf -d odoo19 -u laptop_store_website --stop-after-init
   ```

On install, a `post_init_hook` enables Odoo's built-in **Wire Transfer**
payment provider (if it isn't already configured), so checkout can be
completed in this dev environment without external payment API keys.

## 4. Module structure

```
laptop_store_website/
├── __init__.py
├── __manifest__.py
├── hooks.py                        # post_init_hook: enable Wire Transfer
├── models/
│   ├── __init__.py
│   └── product_template.py         # adds laptop spec fields to product.template
├── views/
│   ├── product_template_views.xml  # "Laptop Specifications" tab on the product form
│   ├── laptop_menus.xml            # Laptop Store Website > Laptops menu + action
│   ├── laptop_templates.xml        # /laptops page: s_title header + Products dynamic snippet
│   └── product_page_templates.xml  # adds a Specifications block to /shop's product page
├── data/
│   ├── product_category_data.xml   # "Laptops" product.public.category + product.category
│   └── website_page_data.xml       # registers /laptops as a manageable Website page
├── demo/
│   └── product_demo.xml            # 5 realistic demo laptop products
├── static/src/
│   └── css/laptop_store.css
├── tests/
│   ├── __init__.py
│   └── test_product_template.py
└── README.md
```

No custom model, security groups, or backend views were needed for the
product side — `product.template`'s own fields, access rights, and views
are reused and only extended.

## 5. Data model

Laptops are `product.template` records. This module adds a few fields
via `_inherit` rather than a separate model, so laptops keep using
Odoo's own price/currency/image/publishing/inventory handling:

* `brand`, `processor`, `ram`, `storage`, `display_size`,
  `operating_system` — `Char` spec fields.
* `featured` — `Boolean`, highlights a laptop on the curated `/laptops`
  page.

Categorization uses `product.public.category` ("Laptops", for the
website/Shop) and `product.category` (for backend organization).

## 6. Backend functionality

Menu: **Laptop Store Website → Laptops** — a convenience action showing
the standard product list/kanban/form views, pre-filtered to the Laptops
category (`domain=[('categ_id', '=', <Laptops category>)]`). New laptops
created from this menu default into the Laptops category and are
marked sellable/published. The product form gains a **Laptop
Specifications** tab (brand, processor, RAM, storage, display size, OS,
featured) via view inheritance — the rest of the form (pricing, taxes,
inventory, variants, website publishing, ...) is untouched, standard
Odoo.

## 7. Website functionality

* **`/laptops`** — a plain Website page, no custom controller. It's
  registered as a `website.page` (see below) and served by Odoo's own
  generic page dispatch, exactly like a page built through "+New Page".
  Its content is two real Odoo snippets: an `s_title` header, and the
  native `website_sale` **"Products" dynamic snippet**, pre-configured
  (`data-product-category-id`) to show published, sellable products in
  the Laptops category. The snippet fetches its data client-side and
  links each product to the real Shop product page.
* **`/shop`** and **`/shop/category/laptops`** — Odoo's own Shop already
  lists these same laptops (they're regular published products), with
  full search/filter/pagination for free.
* **Product page** (`/shop/<laptop>`) — the standard `website_sale`
  product page, extended (not replaced) with a **Specifications**
  section showing the laptop's spec fields, right below the existing
  add-to-cart block.

### Cart → checkout → payment → invoicing

All of this is native `website_sale`/`sale`/`account` behavior — this
module does not implement any of it:

1. **Add to Cart** on the product page → creates/updates a `sale.order`
   in `draft` state (the cart).
2. **Checkout** → delivery/billing address, then payment method
   selection (Wire Transfer is enabled by default; add others under
   *Website → Configuration → Payment Providers*).
3. **Order confirmation** → the `sale.order` is confirmed
   (`sale.order.state = 'sale'`), visible under *Sales → Orders*.
4. **Invoicing** → invoice from the confirmed order (*Sales → Orders →
   Create Invoice*), following whatever invoicing policy the product/
   company is configured with.
5. **Payment registration** → *Accounting/Invoicing → Register Payment*
   completes the cash-out.

## 8. Website Builder customization

`/laptops` is registered as a `website.page` (`data/website_page_data.xml`),
so it appears under **Website → Site → Pages** with the full Edit/
Customize toolbar and SEO fields.

Unlike v2, the *entire* page body (`#wrap`) is one single `oe_structure`
canvas — the same pattern Odoo uses for any blank page created via
"+New Page". Both blocks on it are genuine, fully-optioned snippets:

* **Header** — `s_title` (the same markup Odoo's own pages use):
  background/text colors, spacing, and alignment are all editable from
  the Customize panel, and the block can be duplicated, moved, or
  deleted like any other.
* **Laptop listing** — `s_dynamic_snippet_products`, Odoo's own native
  "Products" building block, pre-configured to the Laptops category.
  Because it fetches products client-side via JS rather than being
  server-rendered into static HTML, it's safe to live in a fully
  editable canvas: an editor gets the complete native product-block
  options (layout, columns, item count, colors, ribbons, ...) and can
  move/duplicate/remove it too — there's no risk of "freezing" a stale
  product list into the page, which was the reason v2 kept its
  hand-built grid outside the editable zones.

An editor can also drag in entirely new blocks above, below, or between
these two, exactly as on any other Odoo theme page.

## 9. Security

No custom groups or access rights are needed: laptops are ordinary
products, governed by Odoo's existing Sales/Inventory access rights and
`website_sale`'s public read rules for published products. Public
visitors get read access only to published, sellable products through
those existing rules — nothing bespoke was added or loosened.

## 10. Testing

Run the module's tests against a disposable/test database:

```bash
python odoo-bin -c config/odoo.conf -d odoo19_test -i laptop_store_website --test-enable --test-tags /laptop_store_website --stop-after-init
```

Tests cover: creating a laptop product with spec fields, that a
published/sellable laptop matches the same domain the `/laptops` page's
dynamic snippet and Shop use, that unpublishing excludes it from that
domain, that the Wire Transfer payment provider gets enabled by the
post-init hook, and that `/laptops` itself returns HTTP 200 (a basic
smoke test now that no custom controller serves it).

## 11. Upgrading the module

After changing Python/XML files:

```bash
python odoo-bin -c config/odoo.conf -d odoo19 -u laptop_store_website --stop-after-init
```

## 12. What changed from v1 (catalogue-only)

* Removed (v2): the custom `laptop.store.laptop` model, its security
  groups (`Laptop Store User`/`Manager`), and its dedicated backend
  list/form/search views.
* Added (v2): `product.template` extension fields, the Laptops
  categories, the Wire Transfer post-init hook, and the Specifications
  block on the real Shop product page.
* Removed (v3): the custom `/laptops` controller and its hand-built,
  server-rendered product grid (`t-foreach` over a Python-side query).
* Added (v3): a plain `website.page` for `/laptops` built entirely from
  real Odoo snippets (`s_title` + `s_dynamic_snippet_products`) inside a
  single editable `oe_structure` canvas, matching how any normal theme
  page is built.
* `/laptops` still exists, but now shows real sellable products and
  links to the real Shop for buying, instead of being a read-only,
  non-purchasable catalogue.

## 13. Future improvements

* A dedicated "Laptops" entry in the website's top navigation menu
  (currently reachable via `/laptops`, `/shop`, and the category sidebar
  on `/shop`, but not the main nav).
* Product comparison / filters (brand, RAM, price range) on `/laptops`.
* A contact/inquiry form generating a CRM lead for out-of-stock models.
* A real payment provider (Stripe/PayPal) in test or live mode, in
  addition to Wire Transfer.

## 14. Assumptions

* `laptop_store_website` is installed into the `odoo19` database (the one
  configured in `config/odoo.conf`), not the `medical` database.
* Wire Transfer (manual payment) is an acceptable payment method for
  this dev/demo environment; a real provider can be configured later
  under *Website → Configuration → Payment Providers* without any code
  changes.
* Brand is a free-text field for now, not a dedicated `product.brand`
  model, consistent with the original "simple showcase" scope.
