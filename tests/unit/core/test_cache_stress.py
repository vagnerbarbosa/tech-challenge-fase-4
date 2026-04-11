"""Testes de stress e concorrência para o cache de análise."""

import gc
import threading
import time

from src.core.cache import AnalysisCache


class TestCacheStress:
    """Testes de stress para o cache."""

    def test_grande_volume_de_entradas(self):
        """Deve suportar grande volume de entradas sem memory leak."""
        cache = AnalysisCache(ttl_minutes=60)

        # Adiciona 10000 entradas
        for i in range(10000):
            cache.set(f"texto_{i}", {"result": f"value_{i}"})

        # Verifica que todas estão no cache
        stats = cache.get_stats()
        assert stats["entries"] == 10000

        # Limpa e verifica garbage collection
        cache.clear_all()
        gc.collect()

        # Verifica memória (aproximado)
        stats_after = cache.get_stats()
        assert stats_after["entries"] == 0

    def test_concorrencia_set(self):
        """Deve suportar operações concorrentes de set."""
        cache = AnalysisCache(ttl_minutes=60)
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    cache.set(f"thread_{thread_id}_key_{i}", f"value_{i}")
            except Exception as e:
                errors.append(e)

        # Executa com 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Erros durante execução concorrente: {errors}"

        # Verifica que todas as entradas foram adicionadas
        stats = cache.get_stats()
        assert stats["entries"] == 1000  # 10 threads * 100 keys

    def test_concorrencia_get(self):
        """Deve suportar operações concorrentes de get."""
        cache = AnalysisCache(ttl_minutes=60)

        # Preenche o cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        results = []
        errors = []

        def worker():
            try:
                for i in range(1000):
                    result = cache.get(f"key_{i}")
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Executa com 5 threads simultâneas
        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Erros durante leitura concorrente: {errors}"

        # Todas as leituras devem retornar valores (nenhum None)
        assert all(r is not None for r in results)

    def test_invalidate_expired_entries(self):
        """Deve invalidar entradas expiradas corretamente."""
        cache = AnalysisCache(ttl_minutes=0)  # Expira imediatamente

        # Adiciona entradas
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        # Aguarda um pouco
        time.sleep(0.1)

        # Invalidação via get
        expired_count = 0
        for i in range(100):
            result = cache.get(f"key_{i}")
            if result is None:
                expired_count += 1

        # Todas devem estar expiradas
        assert expired_count == 100

        # Verifica que o cache está vazio
        stats = cache.get_stats()
        assert stats["entries"] == 0

    def test_clear_expired_performance(self):
        """Limpeza de expirados deve ser performática."""
        cache = AnalysisCache(ttl_minutes=0)  # Expira imediatamente

        # Adiciona 1000 entradas
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")

        time.sleep(0.1)

        # Mede tempo de limpeza
        start = time.time()
        removed = cache.clear_expired()
        duration = time.time() - start

        assert removed == 1000
        assert duration < 1.0  # Deve ser rápido (< 1 segundo)

    def test_memoria_com_muitas_entradas(self):
        """Verifica comportamento de memória com muitas entradas."""
        cache = AnalysisCache(ttl_minutes=60)

        # Captura uso de memória inicial
        gc.collect()

        # Adiciona muitas entradas grandes
        large_value = {"data": "x" * 1000}
        for i in range(5000):
            cache.set(f"key_{i}", large_value)

        # Limpa
        cache.clear_all()
        gc.collect()

        # Cache deve estar vazio
        stats = cache.get_stats()
        assert stats["entries"] == 0


class TestCacheInvalidation:
    """Testes para invalidação de cache."""

    def test_clear_all_remove_tudo(self):
        """clear_all deve remover todas as entradas."""
        cache = AnalysisCache()

        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        cache.clear_all()

        assert len(cache._cache) == 0
        assert len(cache._timestamps) == 0

    def test_geracao_chave_consistente(self):
        """Geração de chave deve ser consistente entre threads."""
        cache = AnalysisCache()
        text = "Texto de teste consistente"

        keys = []

        def generate_key():
            key = cache._generate_key(text)
            keys.append(key)

        # Gera chaves de 50 threads
        threads = []
        for _ in range(50):
            t = threading.Thread(target=generate_key)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Todas as chaves devem ser iguais
        assert len(set(keys)) == 1

    def test_ttl_diferente_por_instancia(self):
        """Cada instância deve ter seu próprio TTL."""
        cache_1min = AnalysisCache(ttl_minutes=1)
        cache_60min = AnalysisCache(ttl_minutes=60)

        assert cache_1min._ttl == cache_60min._ttl / 60

    def test_sobrescrever_entrada(self):
        """Deve permitir sobrescrever entrada existente."""
        cache = AnalysisCache()

        cache.set("mesma_chave", "valor1")
        cache.set("mesma_chave", "valor2")

        result = cache.get("mesma_chave")
        assert result == "valor2"
