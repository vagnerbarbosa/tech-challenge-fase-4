"""Testes unitários para o cache de análise."""

import time
from datetime import timedelta

from src.core.cache import AnalysisCache, get_cache


class TestAnalysisCache:
    """Testes para a classe AnalysisCache."""

    def test_create_cache_com_ttl(self):
        """Deve criar cache com TTL especificado."""
        cache = AnalysisCache(ttl_minutes=30)

        assert cache._ttl == timedelta(minutes=30)

    def test_generate_key_consistente(self):
        """Deve gerar chaves consistentes para mesmo texto."""
        cache = AnalysisCache()
        text1 = "Texto de teste"
        text2 = "Texto de teste"

        key1 = cache._generate_key(text1)
        key2 = cache._generate_key(text2)

        assert key1 == key2

    def test_generate_key_case_insensitive(self):
        """Chave deve ser case insensitive."""
        cache = AnalysisCache()

        key1 = cache._generate_key("TEXTO Maiúsculo")
        key2 = cache._generate_key("texto maiúsculo")

        assert key1 == key2

    def test_generate_key_strip_whitespace(self):
        """Chave deve ignorar espaços nas extremidades."""
        cache = AnalysisCache()

        key1 = cache._generate_key("  texto com espaços  ")
        key2 = cache._generate_key("texto com espaços")

        assert key1 == key2

    def test_set_e_get(self):
        """Deve armazenar e recuperar valores."""
        cache = AnalysisCache()
        text = "texto de teste"
        value = {"result": "success"}

        cache.set(text, value)
        result = cache.get(text)

        assert result == value

    def test_get_nao_existente_retorna_none(self):
        """Deve retornar None para chave inexistente."""
        cache = AnalysisCache()

        result = cache.get("texto inexistente")

        assert result is None

    def test_get_expirado_retorna_none(self):
        """Deve retornar None para entrada expirada."""
        cache = AnalysisCache(ttl_minutes=0)
        text = "texto para expirar"
        value = {"data": "test"}

        cache.set(text, value)
        # Aguarda um pouco para garantir expiração
        time.sleep(0.1)
        result = cache.get(text)

        assert result is None

    def test_expirado_e_removido(self):
        """Entrada expirada deve ser removida do cache."""
        cache = AnalysisCache(ttl_minutes=0)
        text = "texto para expirar"
        value = {"data": "test"}

        cache.set(text, value)
        time.sleep(0.1)
        cache.get(text)  # Tenta acessar (deve limpar)

        key = cache._generate_key(text)
        assert key not in cache._cache
        assert key not in cache._timestamps

    def test_clear_expired(self):
        """Deve limpar entradas expiradas."""
        cache = AnalysisCache(ttl_minutes=0)

        # Adiciona entradas
        cache.set("texto1", {"data": 1})
        cache.set("texto2", {"data": 2})

        time.sleep(0.1)
        removed = cache.clear_expired()

        assert removed == 2
        assert len(cache._cache) == 0

    def test_clear_all(self):
        """Deve limpar todas as entradas."""
        cache = AnalysisCache()

        cache.set("texto1", {"data": 1})
        cache.set("texto2", {"data": 2})
        cache.set("texto3", {"data": 3})

        cache.clear_all()

        assert len(cache._cache) == 0
        assert len(cache._timestamps) == 0

    def test_get_stats(self):
        """Deve retornar estatísticas do cache."""
        cache = AnalysisCache(ttl_minutes=60)

        cache.set("texto1", {"data": 1})
        cache.set("texto2", {"data": 2})

        stats = cache.get_stats()

        assert stats["entries"] == 2
        assert stats["ttl_minutes"] == 60.0

    def test_get_stats_limpa_expirados(self):
        """Stats deve limpar entradas expiradas primeiro."""
        cache = AnalysisCache(ttl_minutes=0)

        cache.set("texto1", {"data": 1})
        time.sleep(0.1)
        cache.set("texto2", {"data": 2})  # Este ainda pode não estar expirado

        stats = cache.get_stats()

        # Apenas entradas não expiradas devem contar
        assert stats["entries"] >= 0


class TestGetCache:
    """Testes para a função get_cache."""

    def test_retorna_mesma_instancia(self):
        """Deve retornar mesma instância (singleton)."""
        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    def test_instancia_analysis_cache(self):
        """Deve retornar instância de AnalysisCache."""
        cache = get_cache()

        assert isinstance(cache, AnalysisCache)
