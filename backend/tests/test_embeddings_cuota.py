"""La indexación respeta la cuota de Gemini (100 textos por minuto).

Pasó en producción el 03/10/26: la primera organización se reindexó bien y
las seis siguientes fallaron con 429, porque una sola organización ya pasa de
100 fragmentos. Estas pruebas simulan al proveedor: ni red ni cuota real.
"""

import pytest

from assistant import embeddings
from assistant.embeddings import EmbeddingError

CUOTA = ("Gemini no respondió: 429 RESOURCE_EXHAUSTED. You exceeded your current "
         "quota ... Please retry in 37.2s.")


class GeminiSimulado:
    """Devuelve un vector por texto y falla con 429 las veces que se le pida."""

    def __init__(self, fallas_de_cuota=0, error=None):
        self.fallas = fallas_de_cuota
        self.error = error
        self.tandas = []

    def __call__(self, texts, task_type):
        if self.error:
            raise EmbeddingError(self.error)
        if self.fallas:
            self.fallas -= 1
            raise EmbeddingError(CUOTA)
        self.tandas.append(len(texts))
        return [[1.0] for _ in texts]


@pytest.fixture
def gemini(settings, monkeypatch):
    settings.ASSISTANT_EMBEDDING_PROVIDER = "gemini"

    def instalar(simulado):
        monkeypatch.setattr(embeddings, "_gemini_embeddings", simulado)
        return simulado
    return instalar


def test_manda_de_a_tandas_de_menos_de_cien(gemini):
    simulado = gemini(GeminiSimulado())
    vectores = embeddings._gemini_documents([f"t{i}" for i in range(200)], sleep=lambda s: None)
    assert len(vectores) == 200
    assert simulado.tandas == [90, 90, 20]


def test_ante_un_429_espera_lo_que_pide_gemini_y_reintenta(gemini):
    simulado = gemini(GeminiSimulado(fallas_de_cuota=2))
    esperas = []
    vectores = embeddings._gemini_documents(["a", "b"], sleep=esperas.append)
    assert len(vectores) == 2
    # Lo que pidió (37,2 s) más el margen de dos segundos, una vez por falla.
    assert esperas == [pytest.approx(39.2), pytest.approx(39.2)]


def test_un_error_que_no_es_de_cuota_no_se_reintenta(gemini):
    gemini(GeminiSimulado(error="Gemini no respondió: 400 API key not valid"))
    esperas = []
    with pytest.raises(EmbeddingError):
        embeddings._gemini_documents(["a"], sleep=esperas.append)
    assert esperas == []


def test_agotados_los_reintentos_se_rinde(gemini):
    gemini(GeminiSimulado(fallas_de_cuota=99))
    esperas = []
    with pytest.raises(EmbeddingError):
        embeddings._gemini_documents(["a"], sleep=esperas.append)
    assert len(esperas) == embeddings.QUOTA_RETRIES


def test_la_consulta_del_paciente_no_espera(gemini, monkeypatch):
    """embed_query no reintenta: el chat responde 503 y no se cuelga."""
    gemini(GeminiSimulado(fallas_de_cuota=1))
    monkeypatch.setattr("time.sleep", lambda s: pytest.fail("la consulta no debe esperar"))
    with pytest.raises(EmbeddingError):
        embeddings.embed_query("me duele la cabeza")
