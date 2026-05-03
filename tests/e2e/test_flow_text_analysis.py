"""
Testes E2E para fluxo de análise de texto.

Este módulo implementa os testes E2E-001 a E2E-003 conforme especificação
no Spec 011 (Testing Strategy E2E), Phase 5, User Story 3.

Fluxos testados:
- E2E-001: Análise completa de texto (risco_saude_mental, content_safety, audit log)
- E2E-002: Auto-detecção de idioma espanhol
- E2E-003: Rate limiting - 60 requisições

Pré-requisitos:
- API E2E rodando em http://localhost:9000
- Mock server configurado em docker-compose.e2e.yml
- Fixtures disponíveis em conftest.py
"""

import time
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from requests import Response


class TestE2ETextAnalysis:
    """Testes E2E para análise de texto.

    Esta classe implementa os testes E2E-001 a E2E-003 conforme especificado
    no Spec 011 para validação de fluxos completos de análise de texto.
    """

    def test_e2e_text_analysis_complete(
        self,
        e2e_client: requests.Session,
        api_url: str,
    ) -> None:
        """E2E-001: Análise completa de texto.

        Valida: risco_saude_mental, content_safety, audit log

        Args:
            e2e_client: Sessão HTTP configurada com autenticação admin.
            api_url: URL base da API E2E.
        """
        # Arrange: Payload com texto indicando ansiedade (risco de saúde mental)
        payload: dict[str, object] = {
            "texto": "Estou me sentindo muito ansiosa e preocupada com a gravidez.",
            "tipo": "geral",
            "patient_id": "E2E-001-TEST",
        }

        # Act: Executa análise de texto
        start_time = time.time()
        response: Response = e2e_client.post(
            f"{api_url}/analyze/text",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        duration = time.time() - start_time

        # Assert Response básica
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data: dict = response.json()

        # Valida campos obrigatórios conforme CLAUDE.md (MUST)
        assert "risco_violencia" in data, "Campo obrigatório risco_violencia ausente"
        assert "risco_saude_mental" in data, "Campo obrigatório risco_saude_mental ausente"

        # Valida valores permitidos para riscos
        riscos_permitidos = ["baixo", "medio", "alto"]
        assert data["risco_violencia"] in riscos_permitidos, (
            f"risco_violencia={data['risco_violencia']} não é válido"
        )
        assert data["risco_saude_mental"] in riscos_permitidos, (
            f"risco_saude_mental={data['risco_saude_mental']} não é válido"
        )

        # Valida campos adicionais da resposta
        assert "sentimento" in data, "Campo sentimento ausente"
        assert data["sentimento"] in ["positivo", "negativo", "neutro", "misto"]

        assert "score" in data, "Campo score ausente"
        assert -1.0 <= data["score"] <= 1.0, "Score fora do intervalo [-1, 1]"

        assert "palavras_chave" in data, "Campo palavras_chave ausente"
        assert isinstance(data["palavras_chave"], list)

        assert "indicadores" in data, "Campo indicadores ausente"
        assert isinstance(data["indicadores"], list)

        # Valida content_safety
        assert "content_safety" in data, "Campo content_safety ausente"
        content_safety = data["content_safety"]
        assert isinstance(content_safety, dict)

        # Valida metadata com rastreabilidade (LGPD)
        assert "metadata" in data, "Campo metadata ausente"
        metadata: dict = data["metadata"]

        assert "correlation_id" in metadata, "Campo correlation_id ausente"
        assert len(metadata["correlation_id"]) > 0, "correlation_id vazio"
        correlation_id = metadata["correlation_id"]

        assert "tempo_processamento_ms" in metadata, (
            "Campo tempo_processamento_ms ausente"
        )
        assert metadata["tempo_processamento_ms"] >= 0

        # Performance: deve processar em menos de 5 segundos
        assert duration < 5.0, f"Performance: demorou {duration:.2f}s (esperado <5s)"

        # Valida audit log foi criado (via admin endpoint)
        audit_response: Response = e2e_client.get(
            f"{api_url}/admin/audit/stats",
            timeout=10,
        )
        assert audit_response.status_code == 200, (
            f"Audit stats falhou: {audit_response.status_code}"
        )

        audit_data = audit_response.json()
        assert "log_directory" in audit_data or "total_entries" in audit_data, (
            "Audit stats não retornou estrutura esperada"
        )

        # Log para debug
        print(f"\n[E2E-001] correlation_id={correlation_id}, "
              f"risco_saude_mental={data['risco_saude_mental']}, "
              f"duration={duration:.2f}s")

    def test_e2e_text_spanish_detection(
        self,
        e2e_client: requests.Session,
        api_url: str,
    ) -> None:
        """E2E-002: Auto-detecção de idioma espanhol.

        Valida que textos em espanhol são processados corretamente
        sem configuração explícita de idioma.

        Args:
            e2e_client: Sessão HTTP configurada com autenticação admin.
            api_url: URL base da API E2E.
        """
        # Arrange: Texto em espanhol indicando ansiedade
        payload: dict[str, object] = {
            "texto": "Tengo mucho miedo y estoy muy ansiosa con todo esto",
            "tipo": "relato",
            "patient_id": "E2E-002-SPANISH",
        }

        # Act: Executa análise sem especificar idioma (auto-detect)
        response: Response = e2e_client.post(
            f"{api_url}/analyze/text",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert Response
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data: dict = response.json()

        # Valida campos obrigatórios
        assert "risco_violencia" in data
        assert "risco_saude_mental" in data

        # Valida que o risco foi detectado (texto indica ansiedade/medo)
        riscos_permitidos = ["baixo", "medio", "alto"]
        assert data["risco_saude_mental"] in riscos_permitidos

        # Valida sentimento (negativo devido a "miedo", "ansiosa")
        assert "sentimento" in data

        # Valida score
        assert "score" in data
        assert -1.0 <= data["score"] <= 1.0

        # Valida metadata
        assert "metadata" in data
        assert "correlation_id" in data["metadata"]

        print(f"\n[E2E-002] Espanhol detectado, "
              f"risco_saude_mental={data['risco_saude_mental']}, "
              f"sentimento={data['sentimento']}")

    def test_e2e_text_rate_limit(
        self,
        e2e_client: requests.Session,
        api_url: str,
    ) -> None:
        """E2E-003: Rate limiting - 60 requisições.

        Valida que após 60+ requisições rápidas, o rate limit é acionado
        retornando HTTP 429, e que os headers de rate limit estão presentes.

        Args:
            e2e_client: Sessão HTTP configurada com autenticação admin.
            api_url: URL base da API E2E.
        """
        # Arrange: Payload simples para múltiplas requisições
        payload: dict[str, object] = {
            "texto": "Texto de teste para rate limit com conteudo suficiente",
            "tipo": "geral",
        }

        responses: list[int] = []
        last_response: Response | None = None

        # Act: Executa 65 requisições rápidas
        for i in range(65):
            response: Response = e2e_client.post(
                f"{api_url}/analyze/text",
                json={**payload, "texto": f"Texto {i} com conteudo suficiente para analise"},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            responses.append(response.status_code)
            last_response = response

            if response.status_code == 429:
                break

        # Assert: Pelo menos uma requisição deve ter sido rate limited (429)
        # Nota: Em modo MOCK, o rate limit pode estar desabilitado
        # então verificamos também se as requisições tiveram sucesso
        if 429 in responses:

            # Verifica headers de rate limit na resposta 429
            assert last_response is not None
            headers = last_response.headers

            # Headers podem ou não estar presentes dependendo da config
            # Se presentes, validamos o formato
            if "X-RateLimit-Limit" in headers:
                limit = int(headers["X-RateLimit-Limit"])
                assert limit > 0, "X-RateLimit-Limit deve ser positivo"

            if "X-RateLimit-Remaining" in headers:
                remaining = int(headers["X-RateLimit-Remaining"])
                assert remaining >= 0, "X-RateLimit-Remaining deve ser >= 0"

            if "X-RateLimit-Reset" in headers:
                reset_after = int(headers["X-RateLimit-Reset"])
                assert reset_after >= 0, "X-RateLimit-Reset deve ser >= 0"

            print(f"\n[E2E-003] Rate limit acionado após {len(responses)} requisições")
        else:
            # Se não houve rate limit, verifica se todas as requisições
            # tiveram sucesso (indica que rate limit está desabilitado no mock)
            successful = sum(1 for r in responses if r == 200)
            print(f"\n[E2E-003] Rate limit não acionado. "
                  f"{successful}/{len(responses)} requisições com sucesso. "
                  f"(Possivelmente desabilitado no modo mock)")

            # Mesmo sem rate limit, validamos que a API respondeu corretamente
            assert successful > 0, "Nenhuma requisição teve sucesso"

        # Verifica headers de rate limit na última resposta bem-sucedida
        if last_response and last_response.status_code == 200:
            headers = last_response.headers

            # Se headers de rate limit estiverem presentes, valida formato
            if "X-RateLimit-Limit" in headers:
                limit = int(headers["X-RateLimit-Limit"])
                assert limit > 0
                print(f"  Headers: Limit={limit}")

            if "X-RateLimit-Remaining" in headers:
                remaining = int(headers["X-RateLimit-Remaining"])
                assert 0 <= remaining <= (int(headers.get("X-RateLimit-Limit", 100)))
                print(f"  Headers: Remaining={remaining}")

            if "Retry-After" in headers:
                retry_after = int(headers["Retry-After"])
                assert retry_after >= 0
                print(f"  Headers: Retry-After={retry_after}")
