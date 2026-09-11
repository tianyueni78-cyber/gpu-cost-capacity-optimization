import unittest

from saas_control.app.domain import Permission, Product, Role, TenantContext, authorize


class DomainContractTest(unittest.TestCase):
    def test_roles_follow_least_privilege(self):
        authorize(Role.ORG_ADMIN, Permission.MANAGE_MEMBERS)
        authorize(Role.ANALYST, Permission.RUN_ANALYSIS)
        authorize(Role.APPROVER, Permission.APPROVE_ACTION)
        authorize(Role.VIEWER, Permission.READ)
        with self.assertRaises(PermissionError):
            authorize(Role.VIEWER, Permission.RUN_ANALYSIS)
        with self.assertRaises(PermissionError):
            authorize(Role.ANALYST, Permission.APPROVE_ACTION)

    def test_expired_subscription_is_read_only(self):
        context = TenantContext("ORG-1", "PROJECT-1", "USER-1", Role.ORG_ADMIN, subscription_active=False)
        authorize(context.role, Permission.READ, context.subscription_active)
        with self.assertRaisesRegex(PermissionError, "只读"):
            authorize(context.role, Permission.RUN_ANALYSIS, context.subscription_active)

    def test_context_rejects_missing_tenant_identity(self):
        with self.assertRaises(ValueError):
            TenantContext("", "PROJECT-1", "USER-1", Role.VIEWER)

    def test_four_products_are_independent_entitlements(self):
        self.assertEqual({item.value for item in Product}, {"gpu-data", "gpu-optimize", "gpu-improve", "gpu-forecast"})


if __name__ == "__main__":
    unittest.main()
