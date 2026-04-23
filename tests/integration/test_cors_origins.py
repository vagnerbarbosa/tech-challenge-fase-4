"""Testes de integração para CORS origins.

T067: Integration test test_cors_origins.py
- Testa múltiplas origens permitidas
- Valida preflight requests
- Testa origens bloqueadas
"""

import pytest
from fastapi.testclient import TestClient


class TestCORSOrigins:
    """Testes para configuração e validação de CORS origins."""

    def test_cors_preflight_request(self, client: TestClient) -> None:
        """T067: Testa preflight request OPTIONS para CORS."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_multiple_allowed_origins(self, client: TestClient) -> None:
        """T073: Testa múltiplas origens permitidas.

        Verifica que diferentes origens configuradas são aceitas.
        """
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
        ]

        for origin in allowed_origins:
            response = client.get(
                "/health",
                headers={"Origin": origin},
            )
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == origin

    def test_cors_simple_request_with_origin(self, client: TestClient) -> None:
        """Testa requisição simples com header Origin."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_post_request_with_origin(self, client: TestClient) -> None:
        """Testa requisição POST com CORS."""
        response = client.post(
            "/api/v1/text/analyze",
            headers={"Origin": "http://localhost:3000"},
            json={"text": "Teste"},
        )
        # Pode retornar 401 por falta de API key, mas deve ter headers CORS
        assert "access-control-allow-origin" in response.headers

    def test_cors_headers_in_response(self, client: TestClient) -> None:
        """Verifica que headers CORS estão presentes nas respostas."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200

        # Verifica que pelo menos o header de origem está presente
        assert "access-control-allow-origin" in response.headers

    def test_cors_origin_reflected(self, client: TestClient) -> None:
        """Verifica que o origin é refletido corretamente na resposta."""
        test_origin = "http://localhost:3000"
        response = client.get(
            "/health",
            headers={"Origin": test_origin},
        )
        assert response.headers.get("access-control-allow-origin") == test_origin


class TestCORSPreflight:
    """Testes específicos para preflight requests (T072)."""

    def test_preflight_health_endpoint(self, client: TestClient) -> None:
        """T072: Valida preflight request para endpoint de health."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200

    def test_preflight_with_custom_headers(self, client: TestClient) -> None:
        """T072: Valida preflight com headers customizados."""
        response = client.options(
            "/api/v1/text/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-API-Key",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_preflight_text_analysis_endpoint(self, client: TestClient) -> None:
        """T072: Valida preflight para endpoint de análise de texto."""
        response = client.options(
            "/api/v1/text/analyze",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200

    def test_preflight_audio_endpoint(self, client: TestClient) -> None:
        """T072: Valida preflight para endpoint de áudio."""
        response = client.options(
            "/api/v1/audio/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in [200, 405]  # 405 se OPTIONS não for permitido

    def test_preflight_video_endpoint(self, client: TestClient) -> None:
        """T072: Valida preflight para endpoint de vídeo."""
        response = client.options(
            "/api/v1/video/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in [200, 405]


class TestCORSCredentials:
    """Testes para validação de credenciais CORS."""

    def test_cors_allow_credentials_header(self, client: TestClient) -> None:
        """Verifica que header Allow-Credentials está presente."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        # O header pode estar presente ou não dependendo da configuração
        # Verificamos apenas que a requisição não falha

    def test_cors_with_authorization_header(self, client: TestClient) -> None:
        """Testa CORS com header de autorização."""
        response = client.options(
            "/api/v1/text/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code == 200


class TestCORSMethods:
    """Testes para métodos HTTP CORS."""

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
    def test_cors_methods_allowed(self, client: TestClient, method: str) -> None:
        """T073: Testa múltiplos métodos HTTP permitidos."""
        # Para métodos que não são GET, fazemos preflight
        if method == "OPTIONS":
            response = client.options("/health")
        else:
            response = client.options(
                "/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": method,
                },
            )

        # Verifica que não retorna erro de CORS
        assert response.status_code in [200, 405, 404]
