"""

Personalización de las predicciónes según la media y desviación de los datos
de cada niño. Al principio se basa en los datos poblacionales hasta que exista
suficiente data de cada niño.
"""
import numpy as np
import pandas as pd

K_SHRINKAGE_DEFECTO = 10
STD_MINIMO_DEFECTO = 0.25


def calcular_baselines(
    df: pd.DataFrame,
    features: list,
    id_col: str = "usuario_id",
    k_shrinkage: int = K_SHRINKAGE_DEFECTO,
    std_minimo: float = STD_MINIMO_DEFECTO,
):
    """
    Entrega dic con media y desviación poblacional y personalizada para su uso cuando corresponda

    """
    baseline_poblacion = {}
    for f in features:
        serie = pd.to_numeric(df[f], errors="coerce")
        media = serie.mean()
        std = serie.std()
        baseline_poblacion[f] = {
            "media": 0.0 if pd.isna(media) else media,
            "std": std if (std and not pd.isna(std) and std > 0) else 1.0,
        }

    filas = []
    for id_valor, grupo in df.groupby(df[id_col].astype(str)):
        n = len(grupo)
        peso = n / (n + k_shrinkage)
        fila = {id_col: id_valor, "n_registros": n}
        for f in features:
            serie = pd.to_numeric(grupo[f], errors="coerce")
            media_propio, std_propio = serie.mean(), serie.std()
            media_pob, std_pob = baseline_poblacion[f]["media"], baseline_poblacion[f]["std"]
            if pd.isna(media_propio):
                media_propio = media_pob
            if pd.isna(std_propio) or std_propio == 0:
                std_propio = std_pob
            fila[f + "_media"] = peso * media_propio + (1 - peso) * media_pob
            fila[f + "_std"] = max(peso * std_propio + (1 - peso) * std_pob, std_minimo)
        filas.append(fila)

    baseline_df = pd.DataFrame(filas).set_index(id_col) if filas else pd.DataFrame()
    return baseline_df, baseline_poblacion


def agregar_zscores(
    df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    baseline_poblacion: dict,
    features: list,
    id_col: str = "usuario_id",
    std_minimo: float = STD_MINIMO_DEFECTO,
):
    """Agrega columnas {feature}_z a df usando el baseline personal de cada id_col."""
    df = df.copy()
    df[id_col] = df[id_col].astype(str)
    cols_baseline = [f + "_media" for f in features] + [f + "_std" for f in features]

    if not baseline_df.empty:
        df = df.merge(baseline_df[cols_baseline], how="left", left_on=id_col, right_index=True)
    else:
        for col in cols_baseline:
            df[col] = np.nan

    for f in features:
        media_col = df[f + "_media"].fillna(baseline_poblacion[f]["media"])
        std_col = df[f + "_std"].fillna(baseline_poblacion[f]["std"]).clip(lower=std_minimo)
        valor = pd.to_numeric(df[f], errors="coerce")
        df[f + "_z"] = (valor - media_col) / std_col

    return df.drop(columns=cols_baseline)


def dias_historial(baseline_df: pd.DataFrame, id_valor, id_col: str = "usuario_id") -> int:
    id_valor = str(id_valor)
    if baseline_df.empty or id_valor not in baseline_df.index:
        return 0
    return int(baseline_df.loc[id_valor, "n_registros"])
