from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestLaptopProduct(HttpCase):

    def setUp(self):
        super().setUp()
        self.category = self.env.ref('laptop_store_website.product_public_category_laptops')

    def _create_laptop(self, **kwargs):
        vals = {
            'name': 'Test Laptop',
            'categ_id': self.env.ref('laptop_store_website.product_category_laptops').id,
            'public_categ_ids': [(6, 0, [self.category.id])],
            'sale_ok': True,
            'is_published': True,
            'list_price': 999.0,
            'brand': 'TestBrand',
            'processor': 'Test CPU',
        }
        vals.update(kwargs)
        return self.env['product.template'].create(vals)

    def test_create_laptop_product(self):
        """A laptop product can be created with spec fields set."""
        laptop = self._create_laptop()
        self.assertTrue(laptop.id)
        self.assertEqual(laptop.brand, 'TestBrand')
        self.assertFalse(laptop.featured, 'Featured should default to False.')

    def _search_as_visitor(self, category):
        """Run the same domain the /laptops page's dynamic Products snippet
        and the Shop use, but as an anonymous visitor would see it:
        sale_product_domain() only applies its is_published filter for
        non-internal users, so evaluating it as the admin (an internal
        user) would always see everything."""
        public_user = self.env.ref('base.public_user')
        website = self.env['website'].with_user(public_user).get_current_website()
        domain = website.sale_product_domain()
        domain += [('public_categ_ids', 'child_of', category.id)]
        return self.env['product.template'].sudo().search(domain)

    def test_laptop_visible_in_website_domain(self):
        """A published, sellable laptop in the Laptops category matches the
        same domain the /laptops page and the Shop use for visitors."""
        laptop = self._create_laptop()
        self.assertIn(laptop, self._search_as_visitor(self.category))

    def test_unpublished_laptop_excluded(self):
        """Unpublishing a laptop must hide it from anonymous visitors on the
        /laptops page and the Shop, without deleting the product."""
        laptop = self._create_laptop(is_published=False)
        self.assertNotIn(laptop, self._search_as_visitor(self.category))

    def test_wire_transfer_provider_enabled(self):
        """The post_init_hook should have enabled the Wire Transfer provider
        so checkout can complete without external payment credentials."""
        provider = self.env.ref('payment.payment_provider_transfer')
        self.assertEqual(provider.state, 'enabled')

    def test_laptops_page_loads(self):
        """/laptops has no custom controller - Odoo's generic page dispatch
        must serve the registered website.page directly, like any normal
        Website Builder page."""
        response = self.url_open('/laptops')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Laptop Store', response.content)
