"""

Esto combina los datos de las bases entregadas y nuevos datos ingreados
por los usuarios sobre los detonantes de las desregulaciones, no influye

"""
import os
from datetime import datetime

import pandas as pd

_DIR_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_RUTA_CASOS = os.path.join(_DIR_DATOS, "1_casos_anonimizados.csv")
_RUTA_EVENTOS_CONCURSO = os.path.join(_DIR_DATOS, "5_eventos_desregulacion_tutor.csv")
_RUTA_EVENTOS_REGISTRADOS = os.path.join(_DIR_DATOS, "eventos_registrados.csv")

RESULTADO_EXITOSO = "Regulación Exitosa"
TIPOS_EVENTO_VALIDOS = [
    "Sobrecarga Sensorial",
    "Transición de Actividad",
    "Desregulación Emocional",
    "Alimentación",
    "Otro",
]
INTENSIDADES_VALIDAS = ["Leve (1-3)", "Moderada (4-7)", "Severa (8-10)"]
RESULTADOS_VALIDOS = ["Regulación Exitosa", "Regulación Parcial", "Sin éxito"]

_COLUMNAS = [
    "id_evento", "id_caso", "fecha_hora", "tipo_evento", "intensidad",
    "detonante_gatillante", "estrategia_calma_aplicada", "resultado_estrategia",
]


def _cargar_casos() -> pd.DataFrame:
    if not os.path.exists(_RUTA_CASOS):
        return pd.DataFrame()
    return pd.read_csv(_RUTA_CASOS, sep=";", encoding="utf-8-sig")


def _cargar_eventos_concurso() -> pd.DataFrame:
    """Datos REALES del concurso — de solo lectura, nunca se modifican."""
    if not os.path.exists(_RUTA_EVENTOS_CONCURSO):
        return pd.DataFrame(columns=_COLUMNAS)
    df = pd.read_csv(_RUTA_EVENTOS_CONCURSO, sep=";", encoding="utf-8-sig")
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def _asegurar_csv_registrados():
    if not os.path.exists(_RUTA_EVENTOS_REGISTRADOS):
        pd.DataFrame(columns=_COLUMNAS).to_csv(_RUTA_EVENTOS_REGISTRADOS, index=False, sep=";")


def _cargar_eventos_registrados() -> pd.DataFrame:
    """Eventos agregados desde el HTML — separados del CSV original del concurso."""
    _asegurar_csv_registrados()
    df = pd.read_csv(_RUTA_EVENTOS_REGISTRADOS, sep=";", encoding="utf-8-sig")
    if df.empty:
        return pd.DataFrame(columns=_COLUMNAS)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def _cargar_eventos_combinados() -> pd.DataFrame:
    concurso = _cargar_eventos_concurso()
    registrados = _cargar_eventos_registrados()
    return pd.concat([concurso, registrados], ignore_index=True)


def agregar_evento(
    usuario_id: str,
    tipo_evento: str,
    intensidad: str,
    detonante: str,
    estrategia: str,
    resultado: str,
    fecha_hora: str = None,
) -> dict:
    """
    Agrega un nuevo detonanto conocido para  el usuario_id, guardado en
    eventos_registrados.csv. 
    """
    _asegurar_csv_registrados()

    if tipo_evento not in TIPOS_EVENTO_VALIDOS:
        tipo_evento = "Otro"
    if intensidad not in INTENSIDADES_VALIDAS:
        intensidad = "Moderada (4-7)"
    if resultado not in RESULTADOS_VALIDOS:
        resultado = "Regulación Parcial"

    momento = fecha_hora or datetime.now().strftime("%Y-%m-%d %H:%M")
    nueva_fila = {
        "id_evento": f"EVT-REG-{int(datetime.now().timestamp())}",
        "id_caso": str(usuario_id),
        "fecha_hora": momento,
        "tipo_evento": tipo_evento,
        "intensidad": intensidad,
        "detonante_gatillante": detonante.strip(),
        "estrategia_calma_aplicada": estrategia.strip(),
        "resultado_estrategia": resultado,
    }

    df = pd.read_csv(_RUTA_EVENTOS_REGISTRADOS, sep=";", encoding="utf-8-sig")
    df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
    df.to_csv(_RUTA_EVENTOS_REGISTRADOS, index=False, sep=";")

    return nueva_fila


def perfil_conocido(usuario_id: str):
    """
    Devuelve lo que se sabe de este niño :
      diagnostico para los niños del csv entregados
      todos los eventos conocidos ordenados por fecha
      estrategias que lograron "Regulación Exitosa"

    Devuelve None solo si no hay NADA (ni ficha real ni eventos agregados)
    para ese usuario_id.
    """
    usuario_id = str(usuario_id)
    casos = _cargar_casos()
    eventos = _cargar_eventos_combinados()

    en_casos = not casos.empty and usuario_id in casos["id_caso"].astype(str).values
    eventos_usuario = (
        eventos[eventos["id_caso"].astype(str) == usuario_id] if not eventos.empty else eventos
    )

    if not en_casos and eventos_usuario.empty:
        return None

    perfil = {"usuario_id": usuario_id}

    if en_casos:
        fila = casos[casos["id_caso"].astype(str) == usuario_id].iloc[0]
        perfil["diagnostico"] = fila["diagnostico_principal"]
        perfil["perfil_sensorial"] = fila["perfil_sensorial_predominante"]

    eventos_usuario = eventos_usuario.sort_values("fecha_hora", ascending=False)
    perfil["eventos"] = [
        {
            "fecha": fila["fecha_hora"].strftime("%Y-%m-%d %H:%M"),
            "tipo_evento": fila["tipo_evento"],
            "intensidad": fila["intensidad"],
            "detonante": fila["detonante_gatillante"],
            "estrategia": fila["estrategia_calma_aplicada"],
            "resultado": fila["resultado_estrategia"],
        }
        for _, fila in eventos_usuario.iterrows()
    ]

    exitosas = eventos_usuario[eventos_usuario["resultado_estrategia"] == RESULTADO_EXITOSO]
    perfil["estrategias_efectivas"] = exitosas["estrategia_calma_aplicada"].drop_duplicates().tolist()

    return perfil
