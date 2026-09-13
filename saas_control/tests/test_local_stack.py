import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


class LocalStackContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))

    def test_required_services_are_healthy(self):
        services = self.compose["services"]
        self.assertEqual(set(services), {"postgres", "redis", "api", "worker", "web"})
        for name in ("postgres", "redis", "api", "worker", "web"):
            self.assertIn("healthcheck", services[name])

    def test_state_is_bound_to_e_drive(self):
        services = self.compose["services"]
        self.assertIn("${DOCKER_DATA_ROOT:-E:/DockerData/gpu-saas}/postgres:/var/lib/postgresql/data", services["postgres"]["volumes"])
        self.assertIn("${DOCKER_DATA_ROOT:-E:/DockerData/gpu-saas}/redis:/data", services["redis"]["volumes"])

    def test_no_secret_is_hard_coded(self):
        text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("${LOCAL_JWT_SECRET:?set LOCAL_JWT_SECRET in .env}", text)
        self.assertIn("${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}", text)
        self.assertNotIn("service_role", text.casefold())

    def test_single_windows_entrypoint_exists(self):
        script = (ROOT / "scripts" / "local-stack.ps1").read_text(encoding="utf-8")
        self.assertIn("docker compose", script)
        self.assertIn("E:\\DockerData", script)
        self.assertIn("RandomNumberGenerator", script)
        self.assertNotIn("请修改其中", script)

    def test_product_page_can_create_a_persistent_job(self):
        page = (ROOT / "web" / "app" / "products" / "[slug]" / "product-client.js").read_text(encoding="utf-8")
        self.assertIn('"/v1/jobs"', page)
        self.assertIn("idempotency_key", page)

    def test_python_image_packages_only_the_application(self):
        project = (ROOT / "saas_control" / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[tool.setuptools.packages.find]', project)
        self.assertIn('include = ["app*"]', project)

    def test_docker_build_contexts_exclude_generated_files(self):
        self.assertIn("!saas_control/**", (ROOT / ".dockerignore").read_text(encoding="utf-8"))
        web_ignore = (ROOT / "web" / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("node_modules", web_ignore)
        self.assertIn(".next", web_ignore)

    def test_startup_stops_when_compose_fails(self):
        script = (ROOT / "scripts" / "local-stack.ps1").read_text(encoding="utf-8")
        self.assertIn('if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed', script)
        script.encode("ascii")

    def test_operations_guide_has_one_command_and_boundaries(self):
        guide = (ROOT / "docs" / "operations" / "local-stack.md").read_text(encoding="utf-8")
        self.assertIn(".\\scripts\\local-stack.ps1 start", guide)
        self.assertIn("E:\\DockerData", guide)
        self.assertIn("named pipe", guide)
        self.assertIn("尚未完成", guide)


if __name__ == "__main__":
    unittest.main()
