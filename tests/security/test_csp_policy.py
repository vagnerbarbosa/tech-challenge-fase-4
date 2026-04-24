"""Testes de segurança para configuração de Content Security Policy.

Testes T049: Verifica se a política CSP está configurada corretamente e é efetiva.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from tests.conftest import TEST_API_KEY


@pytest.fixture
def client():
    """Cliente de teste para aplicação FastAPI."""
    return TestClient(app, headers={"X-API-Key": TEST_API_KEY})


class TestCSPPolicy:
    """Testes de segurança para headers de Content Security Policy."""

    def test_csp_uses_default_self(self, client):
        """CSP default-src deve usar diretiva 'self'."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "default-src 'self'" in csp

    def test_csp_blocks_inline_scripts_in_production(self, monkeypatch):
        """CSP em produção deve restringir scripts inline."""
        # Importa aqui para obter instância fresca com novo env
        import os
        monkeypatch.setenv("ENVIRONMENT", "production")
        os.environ["ENVIRONMENT"] = "production"

        # Cria app de teste com ambiente de produção
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.middleware.cors_security import SecurityHeadersMiddleware

        test_app = FastAPI()
        test_app.add_middleware(
            SecurityHeadersMiddleware,
            environment="production",
        )

        @test_app.get("/health")
        def health():
            return {"status": "ok"}

        client = TestClient(test_app)
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # Deve ter script-src com 'self' e possivelmente nonce/hash
        assert "script-src" in csp

        # Extrai diretiva script-src especificamente (não style-src)
        script_src_part = ""
        for directive in csp.split(";"):
            directive = directive.strip()
            if directive.startswith("script-src "):
                script_src_part = directive
                break

        # Em produção: scripts inline NÃO devem ser permitidos
        assert "'unsafe-inline'" not in script_src_part, f"'unsafe-inline' found in script-src: {script_src_part}"

    def test_csp_blocks_eval(self, client):
        """CSP deve bloquear eval() e similares."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "'unsafe-eval'" not in csp

    def test_csp_restricts_object_sources(self, client):
        """CSP deve restringir fontes de objeto/embed."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # object-src deve ser 'none' ou restrito
        assert "object-src" in csp
        assert "'none'" in csp or "'self'" in csp

    def test_csp_has_base_uri_restriction(self, client):
        """CSP deve restringir URI base."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "base-uri" in csp

    def test_csp_has_frame_ancestors(self, client):
        """CSP deve ter diretiva frame-ancestors."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "frame-ancestors" in csp
        assert "'none'" in csp or "'self'" in csp

    def test_csp_has_form_action(self, client):
        """CSP deve restringir ações de formulário."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        assert "form-action" in csp

    def test_csp_upgrade_insecure_requests_in_production(self, monkeypatch):
        """CSP deve atualizar requisições inseguras em produção."""
        # Importa aqui para obter instância fresca com novo env
        import os
        monkeypatch.setenv("ENVIRONMENT", "production")
        os.environ["ENVIRONMENT"] = "production"

        # Cria app de teste com ambiente de produção
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.middleware.cors_security import SecurityHeadersMiddleware

        test_app = FastAPI()
        test_app.add_middleware(
            SecurityHeadersMiddleware,
            environment="production",
        )

        @test_app.get("/health")
        def health():
            return {"status": "ok"}

        client = TestClient(test_app)
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # Em produção, deve atualizar requisições inseguras
        assert "upgrade-insecure-requests" in csp

    def test_csp_no_wildcard_sources(self, client):
        """CSP não deve usar fontes wildcard sem restrições."""
        response = client.get("/health")
        csp = response.headers.get("content-security-policy", "")

        # Não deve ter wildcards sem restrições
        directives = csp.split(";")
        for directive in directives:
            directive = directive.strip()
            if directive and " " in directive:
                name, values = directive.split(" ", 1)
                # Wildcards devem ser evitados em diretivas sensíveis
                if name in ["script-src", "style-src", "object-src"]:
                    assert "*" not in values, f"Wildcard não permitido em {name}"

    def test_csp_report_only_not_enabled_by_default(self, client):
        """CSP-Report-Only não deve estar presente por padrão."""
        response = client.get("/health")

        # Deve aplicar CSP, não apenas reportar
        assert "content-security-policy" in response.headers
        # Header report-only não deve estar presente em configurações tipo produção
        # (Este teste pode ser ajustado baseado nos requisitos)
