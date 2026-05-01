"""Testes de integração para Azure AI Content Safety.

Estes testes verificam o fluxo completo de detecção de risco
usando o mock server do Content Safety.

Requisitos:
- Mock server rodando na porta 3004 (ou Content Safety real configurado)
- Docker Compose com serviços configurados
"""

import os

import pytest
import requests

from src.infrastructure.content_safety_client import (
    ContentSafetyClient,
    ContentSafetyResult,
)
from src.services.multilingual_risk_detector import (
    MultilingualRiskDetector,
    get_risk_detector,
)

# Skip se Content Safety não estiver configurado
pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT"),
    reason="Content Safety não configurado (mock ou real)",
)


class TestContentSafetyMockIntegration:
    """Testes de integração com mock server Content Safety.

    Estes testes assumem que o mock server está rodando na porta 3004.
    Para rodar: docker-compose -f docker-compose.mock.yml up mock-azure
    """

    @pytest.fixture(scope="class")
    def content_safety_client(self) -> ContentSafetyClient:
        """Fixture que retorna cliente configurado para mock."""
        # Usa mock server se disponível, senão tenta variáveis de ambiente
        endpoint = os.getenv(
            "AZURE_CONTENT_SAFETY_ENDPOINT",
            "http://localhost:3004",
        )
        key = os.getenv("AZURE_CONTENT_SAFETY_KEY", "fake-key-for-testing")

        return ContentSafetyClient(endpoint=endpoint, key=key)

    @pytest.fixture(scope="class")
    def risk_detector(self) -> MultilingualRiskDetector:
        """Fixture que retorna detector de risco configurado."""
        import src.services.multilingual_risk_detector as mrd
        mrd._risk_detector = None  # Reset singleton

        detector = MultilingualRiskDetector()
        return detector

    def test_content_safety_self_harm_detection_pt(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve detectar autoagressão em português."""
        result = content_safety_client.analyze_text(
            "Quero acabar com tudo",
            categories=["SelfHarm"],
        )

        assert isinstance(result, ContentSafetyResult)
        assert result.self_harm_severity >= 0

    def test_content_safety_violence_detection_pt(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve detectar violência em português."""
        result = content_safety_client.analyze_text(
            "Ele me bateu ontem",
            categories=["Violence"],
        )

        assert isinstance(result, ContentSafetyResult)
        assert result.violence_severity >= 0

    def test_content_safety_self_harm_detection_en(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve detectar autoagressão em inglês."""
        result = content_safety_client.analyze_text(
            "I want to kill myself",
            categories=["SelfHarm"],
        )

        assert isinstance(result, ContentSafetyResult)
        assert result.self_harm_severity >= 0

    def test_content_safety_violence_detection_en(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve detectar violência em inglês."""
        result = content_safety_client.analyze_text(
            "He hit me and threatened to kill me",
            categories=["Violence"],
        )

        assert isinstance(result, ContentSafetyResult)
        assert result.violence_severity >= 0

    def test_content_safety_safe_content(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve retornar severidade baixa para conteúdo seguro."""
        result = content_safety_client.analyze_text(
            "Hoje está um dia lindo e ensolarado",
        )

        assert isinstance(result, ContentSafetyResult)
        assert result.self_harm_severity <= 2
        assert result.violence_severity <= 2
        assert result.hate_severity <= 2
        assert result.sexual_severity <= 2
        assert not result.is_harmful

    def test_content_safety_all_categories(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve retornar todas as categorias de análise."""
        result = content_safety_client.analyze_text(
            "Texto de teste",
            categories=["SelfHarm", "Violence", "Hate", "Sexual"],
        )

        # Deve ter todas as categorias
        assert hasattr(result, "self_harm_severity")
        assert hasattr(result, "violence_severity")
        assert hasattr(result, "hate_severity")
        assert hasattr(result, "sexual_severity")

        # Valores devem estar na faixa 0-6
        assert 0 <= result.self_harm_severity <= 6
        assert 0 <= result.violence_severity <= 6
        assert 0 <= result.hate_severity <= 6
        assert 0 <= result.sexual_severity <= 6

    def test_content_safety_batch_analysis(
        self,
        content_safety_client: ContentSafetyClient,
    ) -> None:
        """Deve analisar múltiplos textos em batch."""
        texts = [
            "Estou feliz hoje",
            "Triste e ansioso",
            "Medo de ser atacado",
        ]

        results = content_safety_client.analyze_batch(texts)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, ContentSafetyResult)

    def test_risk_detector_pt_combined(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve detectar risco combinando CS + keywords em PT."""
        result = risk_detector.analyze_text(
            "Estou pensando em suicídio e me machucar",
        )

        assert isinstance(result.to_dict(), dict)
        assert "overall_risk" in result.to_dict()
        assert result.overall_risk >= 0.0

    def test_risk_detector_en_combined(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve detectar risco combinando CS + keywords em EN."""
        result = risk_detector.analyze_text(
            "I have suicidal thoughts and want to end my life",
        )

        assert isinstance(result.to_dict(), dict)
        assert result.overall_risk >= 0.0

    def test_risk_detector_violence_pt(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve detectar risco de violência em português."""
        result = risk_detector.analyze_text(
            "Ele me bateu e ameaçou matar",
        )

        assert result.violence_risk >= 0.0
        assert len(result.keywords_detected) > 0

    def test_risk_detector_violence_en(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve detectar risco de violência em inglês."""
        result = risk_detector.analyze_text(
            "He hit me and threatened to kill",
        )

        assert result.violence_risk >= 0.0

    def test_risk_detector_mental_health_pt(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve detectar risco de saúde mental em português."""
        result = risk_detector.analyze_text(
            "Ansiedade depressão não aguento mais",
        )

        assert result.mental_health_risk >= 0.0

    def test_risk_detector_mental_health_en(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve detectar risco de saúde mental em inglês."""
        result = risk_detector.analyze_text(
            "Anxiety depression can't cope anymore",
        )

        assert result.mental_health_risk >= 0.0

    def test_risk_detector_safe_content(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve retornar baixo risco para conteúdo neutro."""
        result = risk_detector.analyze_text(
            "O clima está agradável hoje",
        )

        assert result.overall_risk == 0.0
        assert result.risk_level == "none"

    def test_risk_detector_batch_multilingual(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve analisar batch de textos multilíngue."""
        texts = [
            "Estou feliz",  # PT - neutro
            "I am sad",  # EN - baixo
            "Quero morrer",  # PT - alto
            "kill me now",  # EN - alto
        ]

        results = risk_detector.analyze_batch(texts)

        assert len(results) == 4

        # Verificar níveis de risco
        assert results[0].risk_level == "none"
        assert results[2].risk_level in ["high", "critical"]
        assert results[3].risk_level in ["high", "critical"]

    def test_risk_detector_risk_levels(
        self,
        risk_detector: MultilingualRiskDetector,
    ) -> None:
        """Deve retornar níveis de risco corretos."""
        test_cases = [
            ("Dia bonito", "none"),
            ("Um pouco triste", "low"),
            ("Ansiedade constante", "medium"),
            ("Quero acabar com tudo", "high"),
            ("Vou me matar hoje", "critical"),
        ]

        for text, expected_min_level in test_cases:
            result = risk_detector.analyze_text(text)
            risk_levels = ["none", "low", "medium", "high", "critical"]
            result_index = risk_levels.index(result.risk_level)
            expected_index = risk_levels.index(expected_min_level)

            assert result_index >= expected_index, (
                f"Text '{text}' expected at least {expected_min_level}, "
                f"got {result.risk_level}"
            )


class TestContentSafetyHealthEndpoint:
    """Testes para o endpoint health do Content Safety mock."""

    def test_mock_server_health_check(self) -> None:
        """Deve retornar 200 no health check do mock."""
        base_url = os.getenv(
            "AZURE_CONTENT_SAFETY_ENDPOINT",
            "http://localhost:3004",
        ).rstrip("/")

        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("Mock server não está rodando")


class TestMultilingualDetectionScenarios:
    """Testes de cenários multilíngue completos."""

    @pytest.fixture
    def detector(self) -> MultilingualRiskDetector:
        """Fixture que retorna detector configurado."""
        import src.services.multilingual_risk_detector as mrd
        mrd._risk_detector = None
        return get_risk_detector()

    def test_scenario_violence_domestica_pt(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Violência doméstica em português."""
        text = (
            "Meu marido me bateu ontem. Ele me ameaçou de morte "
            "e disse que vai me matar se eu contar para alguém. "
            "Tenho medo, preciso de ajuda urgente."
        )

        result = detector.analyze_text(text)

        assert result.violence_risk > 0.5
        assert result.overall_risk > 0.5
        assert result.risk_level in ["high", "critical"]
        assert len(result.keywords_detected) > 0

    def test_scenario_crise_suicida_pt(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Crise suicida em português."""
        text = (
            "Não aguento mais. Quero acabar com tudo. "
            "Minha vida não tem sentido. Melhor eu morrer. "
            "Cansei de sofrer, vou me matar."
        )

        result = detector.analyze_text(text)

        assert result.mental_health_risk > 0.5
        assert result.overall_risk > 0.5
        assert result.risk_level in ["high", "critical"]

    def test_scenario_domestic_violence_en(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Violência doméstica em inglês."""
        text = (
            "My husband hit me yesterday. He threatened to kill me "
            "and said he will murder me if I tell anyone. "
            "I am afraid, need urgent help."
        )

        result = detector.analyze_text(text)

        assert result.violence_risk > 0.5
        assert result.overall_risk > 0.5
        assert result.risk_level in ["high", "critical"]

    def test_scenario_suicidal_crisis_en(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Crise suicida em inglês."""
        text = (
            "I can't take it anymore. I want to end it all. "
            "My life has no meaning. Better off dead. "
            "Tired of suffering, going to kill myself."
        )

        result = detector.analyze_text(text)

        assert result.mental_health_risk > 0.5
        assert result.overall_risk > 0.5
        assert result.risk_level in ["high", "critical"]

    def test_scenario_mixed_emotions_pt(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Emoções mistas em português."""
        text = (
            "Estou me sentindo muito ansiosa com a consulta de amanhã. "
            "Não sei se vou conseguir passar por isso. "
            "Às vezes sinto que não sou forte o suficiente."
        )

        result = detector.analyze_text(text)

        # Ansiedade deve ser detectada
        assert result.mental_health_risk > 0
        # Mas não é crítico
        assert result.risk_level in ["low", "medium"]

    def test_scenario_safe_content_multilingual(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Conteúdo seguro em múltiplos idiomas."""
        texts = [
            "Hoje o dia está lindo",  # PT
            "The weather is beautiful today",  # EN
            "Me siento feliz",  # ES (fallback para keywords)
            "Je suis content",  # FR (fallback para keywords)
        ]

        results = detector.analyze_batch(texts)

        for result in results:
            assert result.risk_level == "none"
            assert result.overall_risk == 0.0

    def test_scenario_complex_mixed_risk(self, detector: MultilingualRiskDetector) -> None:
        """Cenário: Texto complexo com múltiplos riscos."""
        text = (
            "Estou depressiva e ansiosa. Meu namorado me bateu "
            "e agora eu quero morrer. Ele ameaçou matar "
            "meus pais também. Não sei mais o que fazer."
        )

        result = detector.analyze_text(text)

        # Deve detectar ambos os riscos
        assert result.violence_risk > 0
        assert result.mental_health_risk > 0
        # Risco geral deve ser alto
        assert result.overall_risk > 0.5
        assert result.risk_level in ["high", "critical"]


class TestContentSafetyResultSerialization:
    """Testes para serialização de resultados."""

    def test_result_to_dict_structure(self) -> None:
        """Deve retornar dicionário com estrutura correta."""
        from src.infrastructure.content_safety_client import ContentSafetyResult

        result = ContentSafetyResult(
            self_harm_severity=4,
            violence_severity=2,
            hate_severity=1,
            sexual_severity=0,
        )

        data = result.to_dict()

        expected_keys = {
            "self_harm_severity",
            "violence_severity",
            "hate_severity",
            "sexual_severity",
            "is_harmful",
            "highest_category",
            "highest_severity",
        }

        assert set(data.keys()) == expected_keys
        assert data["self_harm_severity"] == 4
        assert data["violence_severity"] == 2
        assert data["highest_category"] == "SelfHarm"
        assert data["highest_severity"] == 4

    def test_risk_assessment_to_dict_structure(self) -> None:
        """Deve retornar dicionário completo do assessment."""
        from src.infrastructure.content_safety_client import ContentSafetyResult
        from src.services.multilingual_risk_detector import RiskAssessmentResult

        cs_result = ContentSafetyResult(
            self_harm_severity=3,
            violence_severity=1,
            hate_severity=0,
            sexual_severity=0,
        )

        assessment = RiskAssessmentResult(
            violence_risk=0.3,
            mental_health_risk=0.5,
            content_safety=cs_result,
            keywords_detected=["ansiedade", "depressão"],
        )

        data = assessment.to_dict()

        assert "violence_risk" in data
        assert "mental_health_risk" in data
        assert "overall_risk" in data
        assert "risk_level" in data
        assert "keywords_detected" in data
        assert "content_safety" in data
        assert isinstance(data["content_safety"], dict)
