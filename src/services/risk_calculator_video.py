"""Calculadora de risco para análise de vídeo.

Este módulo calcula níveis de risco (violência e saúde mental)
com base nas detecções do vídeo.
"""

from typing import Any


def calculate_video_risk(detections: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula risco baseado nas detecções do vídeo.

    Analisa as detecções de objetos, sangramento e comportamento
    para determinar níveis de risco de violência e saúde mental.

    Args:
        detections: Lista de detecções do vídeo, cada uma contendo:
            - classe: str (nome da classe detectada)
            - confianca: float (0-1)
            - bbox: dict (opcional)
            - frame: int (opcional)
            - timestamp: float (opcional)

    Returns:
        Dicionário com:
            - risco_violencia: str ("baixo", "medio", "alto")
            - risco_saude_mental: str ("baixo", "medio", "alto")
            - alertas: list[dict] (alertas gerados)
    """
    risco_violencia = "baixo"
    risco_saude_mental = "baixo"
    alertas: list[dict[str, Any]] = []

    # Contadores para análise
    objetos_perigosos = 0
    sangramento_detectado = False

    for det in detections:
        classe = det.get("classe", "").lower()
        confianca = det.get("confianca", 0.0)
        frame_ref = det.get("frame", 0)

        # Análise de sangramento
        if classe == "sangramento":
            if confianca > 0.8:
                risco_saude_mental = "alto"
                sangramento_detectado = True
                alertas.append({
                    "tipo": "sangramento_detectado",
                    "severidade": "alta",
                    "descricao": "Possível sangramento excessivo detectado no vídeo",
                    "frame_referencia": frame_ref,
                })
            elif confianca > 0.5 and risco_saude_mental != "alto":
                risco_saude_mental = "medio"
                sangramento_detectado = True
                alertas.append({
                    "tipo": "sangramento_detectado",
                    "severidade": "media",
                    "descricao": "Possível sangramento detectado no vídeo",
                    "frame_referencia": frame_ref,
                })

        # Análise de objetos potencialmente perigosos
        elif classe in ["scissors", "knife", "knife_blade"]:
            if confianca > 0.7:
                objetos_perigosos += 1
                if risco_violencia != "alto":
                    risco_violencia = "medio"
                alertas.append({
                    "tipo": "objeto_perigoso",
                    "severidade": "media",
                    "descricao": f"Objeto potencialmente perigoso detectado: {classe}",
                    "frame_referencia": frame_ref,
                })

        # Análise de postura (linguagem corporal)
        elif classe in ["person"]:
            # Postura defensiva ou tensa seria detectada via análise de bbox
            # Aqui apenas marcamos presença de pessoa para contexto
            pass

    # Se múltiplos objetos perigosos detectados, elevar risco
    if objetos_perigosos >= 2:
        risco_violencia = "alto"
        alertas.append({
            "tipo": "multiplos_objetos_perigosos",
            "severidade": "alta",
            "descricao": "Múltiplos objetos perigosos detectados no vídeo",
            "frame_referencia": 0,
        })

    # Sangramento excessivo sempre eleva risco de saúde para alto
    if sangramento_detectado:
        # Verificar se já não foi elevado
        pass  # Já tratado acima

    return {
        "risco_violencia": risco_violencia,
        "risco_saude_mental": risco_saude_mental,
        "alertas": alertas,
    }
