# Propuesta Bluba — Anticipación de crisis conductual con ML

Datatón FICA UFRO × Bluba SpA. Este documento explica **cada archivo
presente en este repositorio** y cómo encaja en el esquema general del
proyecto. Todo lo descrito aquí fue verificado corriendo el backend contra
este mismo repo antes de escribirlo.

(`backend/README.md` ya no duplica esta información — apunta aquí, para
evitar que vuelvan a quedar dos documentos contradictorios como pasó antes.)

## 1. La idea en una imagen

```
                              ┌─────────────────────────────┐
                              │   propuesta-bluba-ml.html    │
                              │        (front-end)           │
                              └───┬──────────┬──────────┬────┘
                                  │          │          │
                       fetch HTTP │          │ fetch    │ Web Serial API
                    (secciones    │          │ HTTP     │ (sección
                  "Demo" y        │          │(sección  │ "Juguete en vivo")
                  "Confirmar      │          │"Confirmar│
                  resultado")     │          │resultado")│
                                  ▼          ▼          ▼
                        ┌──────────────────────┐   Arduino (USB o Bluetooth
                        │  backend/app.py       │   pareado como puerto COM),
                        │  (Flask, puerto 5000) │   firmware sketch_bluba_original.ino
                        └──────────┬───────────┘   — lectura DIRECTA desde el
                                   │                navegador, sin pasar por Flask
        ┌──────────────┬──────────┼──────────────┬───────────────┐
        ▼              ▼          ▼              ▼               ▼
 backend/modelo.py  personalizacion.py   detonantes.py     sensores.py
 (MICE + Random     (baseline +          (detonantes/       (umbrales del
 Forest)             shrinkage,           estrategias, CSV    juguete — ver
        │             compartido)         del concurso +       estado en §4.7)
        ▼                                 los agregados
 backend/base_bluba.csv                   desde el HTML)
 (la "base de datos", CSV)                      │
        ▲                                       ▼
        │ generado una vez por           backend/data/*.csv
 backend/seed_dataset.py                 (reales del concurso +
        ▲                                 eventos_registrados.csv)
        │
   POST /api/confirmar
   (la familia confirma el desenlace
   real de un día ya registrado)
```

Hay **tres caminos** desde el HTML: la sección **"Demo"** predice y guarda
el registro; la sección **"Confirmar resultado"** cierra el ciclo
sintético→real (ver §4.6); y la sección **"Juguete en vivo"** lee el
Arduino **directo desde el navegador**, sin pasar por Flask.

## 2. Archivos en la raíz

| Archivo | Qué es |
|---|---|
| `README.md` | Este documento — la referencia principal del proyecto. |
| `LICENSE` | Licencia MIT del repositorio. |
| `propuesta-bluba-ml.html` | El front-end completo: la propuesta navegable más tres piezas interactivas (demo de predicción, confirmación de resultado real, y alertas en vivo del juguete). Se abre directo en el navegador, sin build. Detalle en §3. |

## 3. `propuesta-bluba-ml.html` — secciones

En orden: **Hero**, **Organizadores**, **`#desafio`**, **`#demo`**,
**`#confirmar`** (nueva), **`#juguete`**, **`#solucion`**, **`#requisitos`**,
**`#datos`**, **metas de diseño**, **`#etica`**, **footer**.

### 3.1 `#demo` — predicción + conocimiento del niño/a

- **Formulario de registro** (`#crisis-form`): selector de `usuario_id`
  (`familia_demo_01/02/03` + los 4 casos reales `PAC-001`...`PAC-004`) y el
  micro-registro diario (sueño, ánimo, apoyo, GI, rutina, desregulaciones
  **en los últimos 3 días** —número explícito—, alimentación e interacción
  social, notas libres). `fetch` a `${API_BASE_URL}/api/prediccion`
  (`API_BASE_URL = 'http://localhost:5000'`, constante al inicio del
  `<script>`). Devuelve riesgo, probabilidad, confianza, factores y
  acciones; si el `usuario_id` tiene historial documentado, también
  "Lo que ya sabemos de este niño/a" (`known_profile`).
- **Formulario "Agregar un detonante conocido"** (`#form-detonante`, nuevo):
  siempre visible, independiente de si ya se predijo. Envía
  `POST /api/detonantes/<usuario_id>` con tipo de evento, intensidad,
  detonante, estrategia usada y resultado. Funciona para **cualquier**
  `usuario_id` — incluidas las familias sintéticas, no solo los 4 casos
  reales — y el niño/a seleccionado se toma del select de arriba. La
  respuesta actualiza en vivo el bloque "Lo que ya sabemos de este niño/a".

### 3.2 `#confirmar` — cierra el ciclo sintético → real (nueva)

Formulario (`#form-confirmar`): elige `usuario_id` + fecha de un día que
ya se registró desde `#demo`, y confirma con un radio button si hubo o no
una crisis real ese día. Envía `POST /api/confirmar`. Ver §4.6 para por
qué existe esto y qué resuelve exactamente.

### 3.3 `#juguete` — Web Serial, no usa el backend

Botón "Conectar juguete" → `navigator.serial.requestPort()`: lee línea por
línea lo que transmite `sketch_bluba_original.ino` (USB o el COM virtual
del HC-06 pareado) y muestra un banner ante `"¡ALERTA! ..."`. No llama a
Flask — el firmware sigue siendo el original, sin calibración por niño/a.
Solo Chrome/Edge de escritorio.

## 4. Carpeta `backend/`

### 4.1 Cómo correrlo

```bash
cd backend
pip install -r requirements.txt
python seed_dataset.py     # ya viene un CSV de ejemplo, pero puedes regenerarlo
python app.py              # API en http://localhost:5000
```

### 4.2 Archivo por archivo

| Archivo | Rol en el esquema general |
|---|---|
| `requirements.txt` | Dependencias del servidor: `flask`, `flask-cors`, `pandas`, `scikit-learn`, `numpy`. |
| `requirements-bridge.txt` | Dependencias (`pyserial`, `requests`) para un script puente Bluetooth que **no está en este repo** — ver §4.7. |
| `README.md` | Apunta a este documento (raíz) para no duplicar información. |
| `seed_dataset.py` | Genera `base_bluba.csv`: 50 usuarios sintéticos × 30 días, con una fórmula de riesgo que produce la etiqueta sintética `crisis_24h`. Se corre una vez; después `app.py` agrega filas reales de uso. |
| `base_bluba.csv` | La "base de datos": `usuario_id, fecha, horas_sueno, calidad_sueno, estado_basal, nivel_apoyo, salud_gi, cambio_rutina, desregulaciones_previas, alimentacion, interaccion_social, notas, crisis_24h`. Los registros nuevos guardan `crisis_24h` vacío hasta que se confirma (§4.6). |
| `personalizacion.py` | Módulo compartido: baseline (media/std) por id con *shrinkage* hacia la población, y z-scores. Lo reutilizan `modelo.py` y `sensores.py`. |
| `modelo.py` | Imputación MICE + un único `RandomForestClassifier` sobre valores crudos + z-scores personalizados. `VENTANA_DESREGULACIONES_DIAS = 3` deja explícito que `desregulaciones_previas` es un conteo de 3 días. Entrena con **cualquier** fila que tenga `crisis_24h` no vacío — sintética o real, sin distinción (clave para §4.6). |
| `detonantes.py` | Detonantes/estrategias por niño/a: combina `data/1_casos_anonimizados.csv` + `data/5_eventos_desregulacion_tutor.csv` (reales del concurso, **de solo lectura**) con `data/eventos_registrados.csv` (escribible, se crea solo). `perfil_conocido(usuario_id)` lee ambas fuentes combinadas; `agregar_evento(...)` escribe solo en la segunda — el CSV del concurso nunca se modifica. Funciona para cualquier `usuario_id`, no solo los 4 casos reales. |
| `sensores.py` | Procesamiento de las señales del juguete sensorial (ver estado real de uso en §4.7). |
| `app.py` | La API Flask. Ver tabla de endpoints en §4.3. |
| `arduino/sketch_bluba_original.ino` | Firmware del dado, sin modificar: umbrales fijos (0.6 / 300ms), igual para todos los niños. Lo lee `#juguete` por Web Serial. |
| `data/1_casos_anonimizados.csv` | Dato real del concurso: ficha de los 4 casos. Solo lectura. |
| `data/5_eventos_desregulacion_tutor.csv` | Dato real del concurso: 7 eventos de crisis documentados. Solo lectura. |
| `data/eventos_registrados.csv` | Se crea automáticamente la primera vez que alguien agrega un detonante desde el HTML. Aquí viven los eventos nuevos, separados del CSV original del concurso. |
| `sensores_bluba.csv` | Log crudo de eventos del juguete (`sensores.py`); vacío hasta que algo llame a `registrar_evento` (ver §4.7). |

### 4.3 Endpoints de la API

| Endpoint | Qué hace | Quién lo llama |
|---|---|---|
| `GET /api/salud` | Chequeo simple | manual |
| `POST /api/prediccion` | Guarda el registro del día y devuelve la predicción (con `known_profile` embebido) | sección `#demo` |
| `GET /api/historial/<usuario_id>` | Últimos 10 registros de un usuario | nadie en este repo (disponible) |
| `GET /api/detonantes/<usuario_id>` | Devuelve lo que se sabe de ese niño/a (concurso + agregado) | nadie directamente (ya viaja en `/api/prediccion`) |
| `POST /api/detonantes/<usuario_id>` | Agrega un nuevo detonante/estrategia para ese niño/a **(nuevo)** | formulario "Agregar detonante conocido" en `#demo` |
| `POST /api/confirmar` | Confirma el desenlace real de un día ya registrado, reemplazando el `crisis_24h` vacío por un 0/1 real **(nuevo)** | sección `#confirmar` |
| `POST /api/sensor/evento`, `GET /api/sensor/umbral/<id>`, `GET /api/sensor/resumen/<id>` | Delegan en `sensores.py` | nadie en este repo (ver §4.7) |

### 4.4 Personalización por niño/a

En vez de un modelo (o firmware) distinto por niño/a, se personaliza el
**input**: cada valor se compara contra el propio historial del niño/a
(z-score), con *shrinkage* hacia la población cuando el historial es
corto. Se aplica dos veces (sueño/ánimo en `modelo.py`, intensidad del
juguete en `sensores.py`), reutilizando `personalizacion.py`.

### 4.5 Detonantes y estrategias — reales + los que agregue la familia

`detonantes.py` combina dos fuentes: los 7 eventos reales del concurso
(4 niños) y cualquier evento nuevo agregado desde `#demo`, para **cualquier**
`usuario_id`. El CSV original del concurso nunca se sobrescribe — los
eventos nuevos quedan en un archivo aparte (`eventos_registrados.csv`).
Esto responde directamente al pedido de "poder añadir nuevos detonantes
para cada niño": ya no depende de que el niño/a sea uno de los 4 casos
del concurso.

### 4.6 El problema de la etiqueta sintética, y cómo se resuelve

**El problema**: `crisis_24h` en `base_bluba.csv` no viene de un desenlace
real observado — viene de una fórmula en `seed_dataset.py` que combina las
mismas variables que luego son features (menos sueño, peor GI, etc. suman
un "puntaje de riesgo", que se convierte en probabilidad y se sortea un
0/1). El Random Forest entrenado sobre esto aprende, en esencia, a
re-derivar esa fórmula — no una relación observada del mundo real. Los
datos reales del concurso con fechas de crisis (`5_eventos_desregulacion_tutor.csv`)
nunca se conectaron a este entrenamiento: viven aparte, en `detonantes.py`.

Se evaluó reemplazar la etiqueta sintética por la real, y se descartó: solo
hay ~100 días reales y 7 eventos en 4 niños — insuficiente para entrenar un
Random Forest confiable.

**La solución implementada**: en vez de reemplazar la etiqueta, se cierra
el ciclo predicción → desenlace real. `POST /api/confirmar` (sección
`#confirmar` del HTML) deja que la familia confirme, para un día ya
registrado, si hubo o no una crisis real — y eso reemplaza el `crisis_24h`
vacío de esa fila por un 0/1 **real**. `modelo.entrenar_modelo()` ya
entrena con cualquier fila con `crisis_24h` no vacío, sea sintética o
real, **sin que haya sido necesario modificar `modelo.py`**: a medida que
las familias confirman más días, la base de entrenamiento pasa a ser una
mezcla creciente de sintético + real, sin un cambio brusco de enfoque.

### 4.7 Lo que quedó pendiente / inconsistente

- **El juguete sensorial personalizado no está conectado de punta a
  punta.** `sensores.py` y sus 3 endpoints siguen en el código y
  funcionan si se llaman directo, pero el script puente que los
  alimentaría automáticamente no está en este repo, y el firmware
  presente tiene umbral fijo. Hoy el juguete solo se usa de la forma
  simple: alertas en vivo por Web Serial, sin personalización.
- **`requirements-bridge.txt`** no tiene ningún script que lo use todavía.

### 4.8 Limitaciones conocidas (para defender ante el jurado)

- El baseline de personalización usa todo el historial disponible de un
  usuario, no solo los días anteriores al registro evaluado (leve fuga de
  información). Para producción conviene una versión expansiva/rolling.
- El modelo se reentrena completo cada vez que cambia el número de filas
  del CSV; con un dataset más grande convendría cachear y reentrenar bajo
  demanda.
- Los detonantes/estrategias reales del concurso solo cubren 4 niños con
  7 eventos — un complemento puntual, que ahora cualquier familia puede
  ir ampliando por su cuenta desde el HTML.
- La confirmación de resultado real (§4.6) depende de que la familia
  efectivamente vuelva a confirmar — si nadie confirma, el modelo sigue
  entrenando 100% con datos sintéticos indefinidamente.
