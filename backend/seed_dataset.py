"""
Genera la base de datos inicial en formato csv de Bluba:

Este script se ejecuta UNA sola vez para crear base_bluba.csv.
Después de eso, app.py agrega una fila nueva cada vez que una familia
completa el micro-registro desde el HTML.

"""
import numpy as np
import pandas as pd

RUTA_CSV = "base_bluba.csv"

np.random.seed(42)

n_usuarios = 50
dias_por_usuario = 30
n_registros = n_usuarios * dias_por_usuario

print(f"Generando {n_registros} registros históricos...")

usuarios = np.repeat(np.arange(1, n_usuarios + 1), dias_por_usuario)
fecha_inicio = pd.to_datetime("2026-07-01")
fechas = pd.date_range(start=fecha_inicio, periods=dias_por_usuario).tolist() * n_usuarios

horas_sueno = np.random.normal(loc=7.0, scale=1.5, size=n_registros).clip(3, 10)
calidad_sueno = np.random.choice([1, 2, 3], size=n_registros, p=[0.3, 0.4, 0.3])  # 1 mala,2 regular,3 buena
estado_basal = np.random.choice([1, 2, 3], size=n_registros, p=[0.3, 0.5, 0.2])   # 1 irritable,2 neutro,3 tranquilo
nivel_apoyo = np.random.choice([1, 2, 3], size=n_registros, p=[0.4, 0.4, 0.2])    # 1 alto,2 medio,3 bajo
salud_gi = np.random.choice([1, 2, 3], size=n_registros, p=[0.7, 0.2, 0.1])       # 1 normal,2 leve,3 severo
cambio_rutina = np.random.choice([0, 1, 2], size=n_registros, p=[0.6, 0.3, 0.1])  # 0 ninguno,1 leve,2 drástico
desregulaciones_previas = np.random.poisson(lam=0.8, size=n_registros).clip(0, 5)

# Estas variables no se ocupan todavía para la predicción del modelo pero 
# se incluyen igual para una implementación futura
alimentacion = np.random.choice([1, 2, 3], size=n_registros, p=[0.6, 0.3, 0.1])
interaccion_social = np.random.choice([1, 2, 3, 4], size=n_registros, p=[0.4, 0.3, 0.2, 0.1])

df = pd.DataFrame({
    "usuario_id": usuarios,
    "fecha": fechas,
    "horas_sueno": horas_sueno.round(1),
    "calidad_sueno": calidad_sueno,
    "estado_basal": estado_basal,
    "nivel_apoyo": nivel_apoyo,
    "salud_gi": salud_gi,
    "cambio_rutina": cambio_rutina,
    "desregulaciones_previas": desregulaciones_previas,
    "alimentacion": alimentacion,
    "interaccion_social": interaccion_social,
    "notas": "",
})

# Formulas de riesgo sintetico para determinar las crisis en 24 h
score_riesgo = (
    (10 - df["horas_sueno"]) * 0.35
    + (4 - df["calidad_sueno"]) * 0.40
    + (4 - df["estado_basal"]) * 0.50
    + df["salud_gi"] * 0.60
    + df["cambio_rutina"] * 0.75
    + df["desregulaciones_previas"] * 0.50
)
prob_crisis = 1 / (1 + np.exp(-(score_riesgo - 6.0)))
df["crisis_24h"] = np.random.binomial(1, prob_crisis).astype(int)

df.to_csv(RUTA_CSV, index=False)
print(f"Base de datos creada: {RUTA_CSV} ({len(df)} filas)")
print(df.head())
