"""
API Flask

Recibe el registro diario de la familia desde el html, lo agrega en el csv base 
y entrena el modelo con el modulo modelo.py y devuelve la predicción.

"""
import os
from datetime import date

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

import modelo
import sensores
import detonantes

RUTA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_bluba.csv")

app = Flask(__name__)
CORS(app) 

_cache = {"modelo": None, "imputador": None, "baseline_df": None, "baseline_poblacion": None, "n_filas": -1}


def _asegurar_csv():
    if not os.path.exists(RUTA_CSV):
        raise FileNotFoundError(
            f"No se encontró {RUTA_CSV}. Ejecuta primero: python seed_dataset.py"
        )


def _obtener_modelo():
    df = modelo.cargar_datos(RUTA_CSV)
    if _cache["modelo"] is None or _cache["n_filas"] != len(df):
        m, imp, baseline_df, baseline_poblacion = modelo.entrenar_modelo(df)
        _cache.update({
            "modelo": m,
            "imputador": imp,
            "baseline_df": baseline_df,
            "baseline_poblacion": baseline_poblacion,
            "n_filas": len(df),
        })
    return _cache["modelo"], _cache["imputador"], _cache["baseline_df"], _cache["baseline_poblacion"], len(df)


@app.get("/api/salud")
def salud():
    return jsonify({"status": "ok"})


@app.post("/api/prediccion")
def prediccion():
    """
    {
      "usuario_id": "familia_01",
      "horas_sueno": 6.5,               // null si no se registra
      "calidad_sueno": 1,                // 1 mala, 2 regular, 3 buena | null
      "estado_basal": 1,                 // 1 irritable, 2 neutro, 3 tranquilo | null
      "nivel_apoyo": 2,                  // 1 alto, 2 medio, 3 bajo | null
      "salud_gi": 2,                     // 1 normal, 2 leve, 3 severo | null
      "cambio_rutina": 2,                // 0 ninguno, 1 leve, 2 drástico | null
      "desregulaciones_previas": 1,      // conteo 0-5 | null
      "alimentacion": 1,                 // no se usa todavía
      "interaccion_social": 2,           // no se usa todavía
      "notas": "texto libre"
    }
    """
    _asegurar_csv()
    body = request.get_json(force=True) or {}

    usuario_id = str(body.get("usuario_id") or "anonimo").strip()
    registro = {f: body.get(f) for f in modelo.FEATURES}

    modelo_rf, imputador, baseline_df, baseline_poblacion, n_historico = _obtener_modelo()
    resultado = modelo.predecir(
        registro, usuario_id, modelo_rf, imputador, baseline_df, baseline_poblacion, n_historico
    )
    # Si este usuario_id corresponde a uno de los csv entregados
    # se adjunta lo que ya sabemos y qué estrategias le han funcionado antes. 
    # Para las familias sintéticas de la demo, queda en null.
    resultado["known_profile"] = detonantes.perfil_conocido(usuario_id)

    nueva_fila = {
        "usuario_id": usuario_id,
        "fecha": date.today().isoformat(),
        **registro,
        "alimentacion": body.get("alimentacion"),
        "interaccion_social": body.get("interaccion_social"),
        "notas": body.get("notas", ""),
        "crisis_24h": "",
    }
    df = pd.read_csv(RUTA_CSV)
    df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
    df.to_csv(RUTA_CSV, index=False)

    return jsonify(resultado)


@app.get("/api/historial/<usuario_id>")
def historial(usuario_id):
    _asegurar_csv()
    df = pd.read_csv(RUTA_CSV)
    df_usuario = df[df["usuario_id"].astype(str) == str(usuario_id)].tail(10)
    return jsonify(df_usuario.to_dict(orient="records"))


@app.get("/api/detonantes/<usuario_id>")
def detonantes_conocidos(usuario_id):
    """
    Detonantes y estrategias documentados para este niño
    """
    perfil = detonantes.perfil_conocido(usuario_id)
    return jsonify(perfil or {})


@app.post("/api/detonantes/<usuario_id>")
def agregar_detonante(usuario_id):
    """
    Agrega un nuevo detonante y estrategia conocido para usuario_id 
    Body: {"tipo_evento": "...", "intensidad": "...", "detonante": "...",
            "estrategia": "...", "resultado": "...", "fecha_hora": "..."? }
    """
    body = request.get_json(force=True) or {}
    detonante = (body.get("detonante") or "").strip()
    estrategia = (body.get("estrategia") or "").strip()

    if not detonante or not estrategia:
        return jsonify({"error": "detonante y estrategia son obligatorios"}), 400

    detonantes.agregar_evento(
        usuario_id=usuario_id,
        tipo_evento=body.get("tipo_evento", "Otro"),
        intensidad=body.get("intensidad", "Moderada (4-7)"),
        detonante=detonante,
        estrategia=estrategia,
        resultado=body.get("resultado", "Regulación Parcial"),
        fecha_hora=body.get("fecha_hora"),
    )
    return jsonify(detonantes.perfil_conocido(usuario_id) or {})

@app.post("/api/sensor/evento")
def sensor_evento():
    """
    bridge_bluetooth.py llama esto por cada línea que
    recibe del Arduino.
    Body: {"usuario_id": "...", "tipo": "movimiento"|"clic", "valor": number, "timestamp": number?}
    """
    body = request.get_json(force=True) or {}
    usuario_id = body.get("usuario_id")
    tipo = body.get("tipo")
    valor = body.get("valor")

    if not usuario_id or tipo not in ("movimiento", "clic") or valor is None:
        return jsonify({"error": "usuario_id, tipo ('movimiento'|'clic') y valor son obligatorios"}), 400

    fila = sensores.registrar_evento(usuario_id, tipo, float(valor), body.get("timestamp"))
    return jsonify({"ok": True, "evento": fila})


@app.get("/api/sensor/umbral/<usuario_id>")
def sensor_umbral(usuario_id):
    """
    Límites calibrados para este niño.
    """
    return jsonify(sensores.calcular_umbrales_personalizados(usuario_id))


@app.get("/api/sensor/resumen/<usuario_id>")
def sensor_resumen(usuario_id):
    """
    cuántos movimientos bruscos y clics rápidos
    tuvo en el día respecto su propio umbral.
    """
    fecha = request.args.get("fecha")
    return jsonify(sensores.resumen_diario(usuario_id, fecha))

@app.post("/api/confirmar")
def confirmar_resultado():
    """
    La familia confirma si hubo o no una desregulación en un día que
    ya registró. Esto reemplaza el valor vacío de crisis_24h de esa fila
    por un 0 o 1. 
    """
    _asegurar_csv()
    body = request.get_json(force=True) or {}
    usuario_id = str(body.get("usuario_id") or "").strip()
    fecha = str(body.get("fecha") or "").strip()
    hubo_crisis = body.get("hubo_crisis")

    if not usuario_id or not fecha or hubo_crisis is None:
        return jsonify({"error": "usuario_id, fecha y hubo_crisis son obligatorios"}), 400

    df = pd.read_csv(RUTA_CSV)
    coincidencias = df.index[
        (df["usuario_id"].astype(str) == usuario_id) & (df["fecha"].astype(str) == fecha)
    ]

    if len(coincidencias) == 0:
        return jsonify({
            "error": f"No hay un registro guardado para usuario_id={usuario_id} en fecha={fecha}."
        }), 404

    # Si hay más de un registro ese día se confirma el más reciente.
    fila_index = coincidencias[-1]
    df.loc[fila_index, "crisis_24h"] = 1 if hubo_crisis else 0
    df.to_csv(RUTA_CSV, index=False)

    return jsonify({
        "ok": True,
        "usuario_id": usuario_id,
        "fecha": fecha,
        "crisis_24h_confirmado": int(bool(hubo_crisis)),
        "mensaje": "Este resultado real ya queda disponible para la próxima vez que se entrene el modelo.",
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
