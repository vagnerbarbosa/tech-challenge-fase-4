"""
Testes E2E para seguranca e LGPD.

Este modulo contem testes end-to-end para validacao de:
- Autenticacao e autorizacao (401/403)
- Conformidade LGPD (hash de patient_id em audit logs)
- Rate limiting por API Key

Spec: 011-testing-strategy
User Story: US3 - Fluxo de Seguranca
"""

import hashlib
import json
import time
from pathlib import Path

import pytest
import requests


class TestE2ESecurity:
    """Testes E2E para seguranca."""

    def test_e2e_invalid_auth_returns_401(self, api_url: str) -> None:
        """
        E2E-008: Autenticacao invalida retorna 401.
        Valida: X-API-Key validado
        """
        # Teste 1: Request sem header X-API-Key
        response_no_auth = requests.post(
            f"{api_url}/analyze/text",
            json={
                "texto": "Estou me sentindo ansiosa.",
                "patient_id": "TEST-001",
            },
            timeout=10,
        )
        assert response_no_auth.status_code == 401, (
            f"Esperado 401 sem auth, obtido {response_no_auth.status_code}"
        )
        error_data = response_no_auth.json()
        assert "error" in error_data or "detail" in error_data

        # Teste 2: Request com X-API-Key invalido
        response_invalid_auth = requests.post(
            f"{api_url}/analyze/text",
            json={
                "texto": "Estou me sentindo ansiosa.",
                "patient_id": "TEST-001",
            },
            headers={"X-API-Key": "invalid-key-12345"},
            timeout=10,
        )
        assert response_invalid_auth.status_code == 401, (
            f"Esperado 401 com auth invalida, obtido {response_invalid_auth.status_code}"
        )

        # Teste 3: Verifica header WWW-Authenticate (opcional)
        if "WWW-Authenticate" in response_invalid_auth.headers:
            print(f"WWW-Authenticate: {response_invalid_auth.headers['WWW-Authenticate']}")

    def test_e2e_lgpd_patient_id_hash(self, e2e_client: requests.Session, api_url: str) -> None:
        """
        E2E-009: Patient IDs hasheados em audit log.
        Valida: audit log sem dados brutos
        """
        # Gera um patient_id unico para este teste
        patient_id = f"LGPD-TEST-{int(time.time())}"
        correlation_id = f"test-{int(time.time())}"

        # Calcula o hash esperado (SHA-256, primeiros 32 caracteres com prefixo)
        expected_hash = f"sha256:{hashlib.sha256(patient_id.encode('utf-8')).hexdigest()[:32]}"

        # Faz uma requisicao que sera logada
        response = e2e_client.post(
            f"{api_url}/analyze/text",
            json={
                "texto": "Estou me sentindo muito ansiosa e preocupada.",
                "patient_id": patient_id,
            },
            headers={"X-Request-ID": correlation_id},
            timeout=30,
        )
        assert response.status_code == 200, f"Request falhou: {response.text}"

        # Aguarda um momento para o log ser escrito
        time.sleep(0.5)

        # Verifica se o patient_id foi hasheado no audit log
        # O audit log esta em logs/audit/audit-YYYY-MM-DD.log
        audit_log_dir = Path("logs/audit")
        if not audit_log_dir.exists():
            pytest.skip("Diretorio de audit log nao encontrado - possivelmente rodando em Docker")
            return

        # Procura nas entradas de log do dia atual
        today = time.strftime("%Y-%m-%d")
        log_file = audit_log_dir / f"audit-{today}.log"

        if not log_file.exists():
            pytest.skip("Arquivo de audit log nao encontrado")
            return

        found_hashed = False
        found_raw = False

        with open(log_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Verifica se esta entrada contem nosso patient_id
                    if entry.get("patient_id") == expected_hash:
                        found_hashed = True
                    # Verifica se o ID raw existe no log (deve NAO existir)
                    if patient_id in line and entry.get("patient_id") != expected_hash:
                        found_raw = True
                except json.JSONDecodeError:
                    continue

        # Assertivas
        assert found_hashed, (
            f"Patient ID hasheado nao encontrado no audit log. "
            f"Esperado hash: {expected_hash}"
        )
        assert not found_raw, (
            "Patient ID em formato raw encontrado no audit log - violacao LGPD!"
        )

    def test_e2e_rate_limit_by_api_key(self, api_url: str) -> None:
        """
        E2E-010: Rate limiting por API Key.

        Nota: Para E2E, o rate limiting pode estar desabilitado (RATE_LIMIT_ENABLED=false).
        Este teste verifica que:
        1. Headers de rate limit estao presentes nas respostas
        2. Quando rate limit e excedido, retorna 429
        """
        api_key = "test-admin-key"

        # Faz uma requisicao valida para verificar headers
        response = requests.post(
            f"{api_url}/analyze/text",
            json={"texto": "Teste de rate limit.", "patient_id": "RATE-TEST-001"},
            headers={"X-API-Key": api_key},
            timeout=10,
        )

        # Verifica se os headers de rate limit estao presentes
        has_rate_limit_headers = (
            "X-RateLimit-Limit" in response.headers
            or "X-RateLimit-Remaining" in response.headers
        )

        if response.status_code == 200 and has_rate_limit_headers:
            # Rate limiting esta ativo - verifica os headers
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")

            assert limit is not None, "Header X-RateLimit-Limit ausente"
            assert remaining is not None, "Header X-RateLimit-Remaining ausente"

            # Tenta forcar rate limit com multiplas requisicoes rapidas
            # Nota: Pode falhar se rate limit estiver desabilitado
            burst_requests = 5
            responses = []

            for i in range(burst_requests):
                r = requests.post(
                    f"{api_url}/analyze/text",
                    json={
                        "texto": f"Burst request {i}.",
                        "patient_id": f"BURST-{i}",
                    },
                    headers={"X-API-Key": api_key},
                    timeout=5,
                )
                responses.append(r)
                if r.status_code == 429:
                    break

            # Verifica se alguma resposta retornou 429 (rate limit excedido)
            # ou se todas foram bem-sucedidas (rate limit desabilitado para E2E)
            status_codes = [r.status_code for r in responses]

            if 429 in status_codes:
                # Rate limit funcionando - verifica resposta 429
                rate_limited_response = next(r for r in responses if r.status_code == 429)
                error_data = rate_limited_response.json()
                assert "error" in error_data or "detail" in error_data
                assert "RateLimit" in str(error_data.get("error", "")) or \
                       "rate limit" in str(error_data.get("message", "")).lower()

                # Verifica header Retry-After (opcional)
                if "Retry-After" in rate_limited_response.headers:
                    assert int(rate_limited_response.headers["Retry-After"]) > 0
            else:
                # Rate limit pode estar desabilitado para E2E - isso e aceitavel
                # Verificamos apenas que as requisicoes foram processadas
                assert all(r.status_code == 200 for r in responses), (
                    f"Algumas requisicoes falharam: {status_codes}"
                )

        elif response.status_code == 200:
            # Rate limiting desabilitado - apenas logamos
            pytest.skip("Rate limiting parece estar desabilitado (headers ausentes)")

        else:
            pytest.fail(f"Resposta inesperada: {response.status_code} - {response.text}")
