def post_init_hook(env):
    """Enable the built-in Wire Transfer payment provider.

    Without at least one enabled provider, checkout has no way to
    complete, so this dev/demo module turns on Odoo's own no-gateway
    "Wire Transfer" provider (pay by bank transfer instructions) instead
    of requiring external payment API keys. Only touches it if it is
    still in its default "disabled" state, so it never overrides a
    choice made later through Website > Configuration > Payment Providers.
    """
    provider = env.ref('payment.payment_provider_transfer', raise_if_not_found=False)
    if provider and provider.state == 'disabled':
        provider.write({'state': 'enabled', 'is_published': True})
