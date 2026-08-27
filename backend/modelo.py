"""
Modelo predictivo personalizado mediante el método de random forest, MICE para tratar el caso de los datos
faltantes.

Dado que entrenar un modelo para cada niño es extremadamente costoso cuando la
cantidad de estos vaya creciendo, se opta por una personalización  respecto a
los datos ingresados, esto es, se distingue dormir 6 horas cuando lo habitual es 6.5
a dormir 6 horas cuando en promedio se duermen 9.



"""
import numpy as np
import pandas as pd

from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestClassifier

import personalizacion

FEATURES = [
    "horas_sueno",
    "calidad_sueno",
    "estado_basal",
    "nivel_apoyo",
    "salud_gi",
    "cambio_rutina",
    "desregulaciones_previas",
]
FEATURES_Z = [f + "_z" for f in FEATURES]
COLUMNAS_MODELO = FEATURES + FEATURES_Z  # el RF ve el valor crudo Y el relativo
LABEL = "crisis_24h"

COLS_ORDINALES = [
    "calidad_sueno",
    "estado_basal",
    "nivel_apoyo",
    "salud_gi",
    "cambio_rutina",
    "desregulaciones_previas",
]

# Shrinkage corresponte a los días donde la población tiene más peso en la
# predicción
# 
# 
# Con shrinkage=10 un niño con 10 días propios de historial pesa 50/50 entre 
# su propio promedio y el de la población.
# Despúes de un mes su propio registro tiene más peso.
K_SHRINKAGE = 10
STD_MINIMO = 0.25  # tener mínimo evita problemas de redondeo para valores pequeño

# conteo de desregulaciones en últimos 3 dias
VENTANA_DESREGULACIONES_DIAS = 3

# Dirección de riesgo de cada variable

DIRECCION_RIESGO = {
    "horas_sueno": "bajo",
    "calidad_sueno": "bajo",
    "estado_basal": "bajo",
    "nivel_apoyo": "neutro",
    "salud_gi": "alto",
    "cambio_rutina": "alto",
    "desregulaciones_previas": "alto",
}

# Plantillas de explicación 
PLANTILLAS_RIESGO = {
    "horas_sueno": "Durmió {intensidad} menos horas que su propio promedio habitual.",
    "calidad_sueno": "La calidad del sueño de anoche fue {intensidad} peor que lo habitual para él o ella.",
    "estado_basal": "Su ánimo hoy está {intensidad} más irritable que su estado basal habitual.",
    "salud_gi": "El malestar gastrointestinal de hoy es {intensidad} mayor que lo habitual para él o ella.",
    "cambio_rutina": "El cambio de rutina de hoy es {intensidad} mayor de lo que suele manejar sin dificultad.",
    "desregulaciones_previas": "Las desregulaciones en los últimos {ventana} días son {intensidad} más frecuentes que su patrón habitual.",
    "nivel_apoyo": "El apoyo disponible hoy es {intensidad} menor que lo habitual para él o ella.",
}
PLANTILLAS_PROTECTOR = {
    "horas_sueno": "Durmió una cantidad de horas similar o mejor que su propio promedio.",
    "calidad_sueno": "La calidad del sueño de hoy está en línea con lo habitual para él o ella.",
    "estado_basal": "Su ánimo hoy está dentro de su rango habitual de tranquilidad.",
    "salud_gi": "No hay malestar gastrointestinal por sobre lo habitual para él o ella.",
    "cambio_rutina": "No hay cambios de rutina por sobre lo que suele manejar bien.",
    "desregulaciones_previas": "Las desregulaciones en los últimos {ventana} días están dentro de su patrón habitual.",
    "nivel_apoyo": "El apoyo disponible hoy está en línea con lo habitual.",
}

ACCIONES = {
    "horas_sueno": "Prioriza una siesta corta o un descanso temprano esta noche.",
    "calidad_sueno": "Refuerza la rutina de sueño: luces bajas, mismo horario y baja estimulación antes de dormir.",
    "estado_basal": "Anticipa transiciones con aviso previo y ten disponible un espacio de calma.",
    "salud_gi": "Registra la alimentación de hoy y coméntalo con el equipo terapéutico si el malestar persiste.",
    "cambio_rutina": "Reintroduce anclas conocidas (objeto, música, horario) para compensar el cambio.",
    "desregulaciones_previas": "Reduce estímulos sensoriales en las próximas horas y prioriza pausas de descanso.",
    "nivel_apoyo": "Coordina con la red de apoyo (familia, escuela, terapeuta) para reforzar la contención hoy.",
}


def cargar_datos(ruta_csv: str) -> pd.DataFrame:
    return pd.read_csv(ruta_csv)




def calcular_baselines(df_historico: pd.DataFrame, columnas=None, k_shrinkage: int = K_SHRINKAGE):
    
    columnas = list(columnas) if columnas is not None else FEATURES
    return personalizacion.calcular_baselines(
        df_historico, columnas, id_col="usuario_id", k_shrinkage=k_shrinkage, std_minimo=STD_MINIMO
    )


def _agregar_zscores(df: pd.DataFrame, baseline_df: pd.DataFrame, baseline_poblacion: dict, columnas=None) -> pd.DataFrame:
    columnas = list(columnas) if columnas is not None else FEATURES
    return personalizacion.agregar_zscores(
        df, baseline_df, baseline_poblacion, columnas, id_col="usuario_id", std_minimo=STD_MINIMO
    )


def _dias_historial_usuario(baseline_df: pd.DataFrame, usuario_id) -> int:
    return personalizacion.dias_historial(baseline_df, usuario_id, id_col="usuario_id")



def entrenar_modelo(df_historico: pd.DataFrame):
    baseline_df, baseline_poblacion = calcular_baselines(df_historico)

    df_etiquetado = df_historico.dropna(subset=[LABEL])
    df_etiquetado = df_etiquetado[df_etiquetado[LABEL] != ""]

    X_raw = df_etiquetado[FEATURES].apply(pd.to_numeric, errors="coerce")
    imputador = IterativeImputer(max_iter=10, random_state=42, sample_posterior=False)
    X_imputado = pd.DataFrame(
        imputador.fit_transform(X_raw), columns=FEATURES, index=df_etiquetado.index
    )
    for col in COLS_ORDINALES:
        X_imputado[col] = X_imputado[col].round()
    X_imputado["usuario_id"] = df_etiquetado["usuario_id"].values

    X_con_z = _agregar_zscores(X_imputado, baseline_df, baseline_poblacion)
    X_final = X_con_z[COLUMNAS_MODELO]
    y = df_etiquetado[LABEL].astype(int)

    modelo_rf = RandomForestClassifier(n_estimators=200, random_state=42)
    modelo_rf.fit(X_final, y)

    return modelo_rf, imputador, baseline_df, baseline_poblacion


def _completitud(registro: dict) -> float:
    provistos = sum(1 for f in FEATURES if registro.get(f) is not None)
    return provistos / len(FEATURES)


def predecir(
    registro: dict,
    usuario_id,
    modelo_rf,
    imputador,
    baseline_df: pd.DataFrame,
    baseline_poblacion: dict,
    n_historico: int,
):

    fila = pd.DataFrame([{f: registro.get(f, np.nan) for f in FEATURES}])
    fila = fila.apply(pd.to_numeric, errors="coerce")
    fila_imputada = pd.DataFrame(imputador.transform(fila), columns=FEATURES)
    for col in COLS_ORDINALES:
        fila_imputada[col] = fila_imputada[col].round()
    fila_imputada["usuario_id"] = usuario_id

    fila_con_z = _agregar_zscores(fila_imputada, baseline_df, baseline_poblacion)
    X_pred = fila_con_z[COLUMNAS_MODELO]

    probabilidad = float(modelo_rf.predict_proba(X_pred)[0][1]) * 100

    if probabilidad < 33:
        nivel = "bajo"
    elif probabilidad < 66:
        nivel = "medio"
    else:
        nivel = "alto"

    dias_historial = _dias_historial_usuario(baseline_df, usuario_id)
    completitud = _completitud(registro)
    # La confianza combina cuántos campos informó la familia hoy, cuántos
    # registros históricos respaldan al modelo en general, y cuánto
    # historial propio tiene este niño para que su baseline sea confiable.
    confianza = 100 * (
        0.45 * completitud
        + 0.30 * min(n_historico / 500, 1.0)
        + 0.25 * min(dias_historial / 20, 1.0)
    )
    confianza = max(20.0, min(99.0, confianza))

    importancias = dict(zip(COLUMNAS_MODELO, modelo_rf.feature_importances_))
    contribuciones = []
    for f in FEATURES:
        z = float(fila_con_z.iloc[0][f + "_z"])
        direccion = DIRECCION_RIESGO[f]
        if direccion == "bajo":
            hacia_riesgo = -z
        elif direccion == "alto":
            hacia_riesgo = z
        else:
            hacia_riesgo = 0
        contribuciones.append((f, z, importancias[f + "_z"] * hacia_riesgo))

    contribuciones.sort(key=lambda x: x[2], reverse=True)

    factores, acciones = [], []
    for f, z, score in contribuciones:
        if len(factores) >= 3:
            break
        if score <= 0:
            continue
        intensidad = "considerablemente" if abs(z) >= 1.5 else "levemente"
        factores.append(PLANTILLAS_RIESGO[f].format(intensidad=intensidad, ventana=VENTANA_DESREGULACIONES_DIAS))
        acciones.append(ACCIONES[f])

    if not factores:
        for f, _, _ in contribuciones[:2]:
            factores.append(PLANTILLAS_PROTECTOR[f].format(ventana=VENTANA_DESREGULACIONES_DIAS))
        acciones.append("Mantén la rutina actual: hoy no hay señales que sugieran ajustes.")

    notas = []
    if completitud < 1.0:
        faltantes = [f for f in FEATURES if registro.get(f) is None]
        notas.append(
            f"Se imputaron {len(faltantes)} de {len(FEATURES)} variables por falta de registro."
        )
    if dias_historial < 5:
        notas.append(
            f"Este niño/a aún tiene poco historial propio ({dias_historial} días); "
            "la predicción se apoya principalmente en el patrón poblacional."
        )

    return {
        "risk_level": nivel,
        "probability": round(probabilidad, 1),
        "confidence": round(confianza, 1),
        "factors": factores[:3],
        "actions": acciones[:3],
        "completeness_note": " ".join(notas),
    }
