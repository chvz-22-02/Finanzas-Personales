# Extractor de Gastos Bancarios desde Gmail

(Hecho con la inestimable ayuda de Claude.ai)

Extrae automáticamente tus transacciones de los correos de **BCP**, **Pichincha** y **Yape**
y las exporta a un archivo `contabilidad.txt` listo para analizar.

## Correos soportados

| Banco / App | Tipo de correo | Tipo en CSV |
|---|---|---|
| BCP | Consumo con Tarjeta de Crédito/Débito | gasto |
| BCP | Pago de servicios (Banca Móvil) | gasto |
| BCP | Retiro en agente | gasto |
| BCP | Recepción de Yapeo | ingreso |
| Yape | Yapeo enviado | gasto |
| Pichincha | Envío a contacto | gasto |
| Pichincha | Pago recibido | ingreso |

---

## Instalación

### 1. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 2. Configurar acceso a Gmail API

Necesitas crear un proyecto en Google Cloud y habilitar la Gmail API:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto (o usa uno existente)
3. En el menú lateral: **APIs & Services → Library**
4. Busca **"Gmail API"** y haz clic en **Enable**
5. Ve a **APIs & Services → Credentials**
6. Haz clic en **"+ Create Credentials" → "OAuth client ID"**
7. Si te pide configurar la pantalla de consentimiento:
   - User type: **External**
   - App name: cualquiera (ej: "Extractor Gastos")
   - Agrega tu Gmail como **Test user**
8. Tipo de aplicación: **Desktop app**
9. Descarga el archivo JSON y renómbralo como `credentials.json`
10. Colócalo en la misma carpeta que `extractor_gastos.py`

---

## Uso
Tiene un modo de uso de actualización secuencial, pero, para la primera ejecución, operar de la siguiente manera: 

### Extracción de los correos (se puede cambiar los días a la cantidad que se deseen) y guardado
```bash
python extractor_gastos.py --dias 30
python almacenado_informacion.py
```

Para la actualización secuencial:
### Actualización secuencial
```bash
python ejecutor.py
```

**Primera ejecución:** se abrirá el navegador para que autorices el acceso.
Tras aceptar, se guarda `token.json` y no vuelves a necesitar autorizarlo a no ser que expire.
El token expira por inactividad, de ser el caso, eliminar `token.json` y ejecutar normalmente, simplemente se volverá a abrir en el navegador la autorización de acceso.

---

## Formato del CSV de salida

| Columna | Descripción | Ejemplo |
|---|---|---|
| `id` | Identificador interno del correo del movimiento | `19d54ce4f7e41031` |
| `fecha` | Fecha y hora de la operación | `2026-03-04 17:49` |
| `monto` | Monto | `14.99` |
| `tipo` | `gasto` o `ingreso` | `gasto` |
| `categoria` | Tipo de transacción | `Consumo TC/TD` |
| `descripcion` | Empresa o beneficiario | `ADM CLIN RICARDO PALMA` |
| `banco` | Entidad que notifica | `BCP` |
| `cuenta` | Últimos 4 dígitos | `************1756` |
| `num_operacion` | Número de operación | `0000383035` |
| `moneda` | Moneda de la operación | `PEN` |

---

## Archivos generados

- `token.json` — Token de acceso a Gmail (no compartir)
- `gastosyyyy-mm-dd_hh-mm-ss.csv` — Resultado de la última extracción
- `contabilidad.txt` — Consolidado de todas las extracciones

---

## Para agregar un nuevo banco

En `extractor_gastos.py`:
1. Agrega el remitente a la lista `SENDERS`
2. Crea una función `parse_nuevo_banco(html, text)`
3. Agrega la condición en la función `classify_and_parse()`

---

## Consideraciones finales

Debido a que solo soy cliente del BCP y el Pichincha, solo he tenido los correos de dichos bancos para poder hacer la función de parseo. Si quisieras colaborar para que el proyecto soporte, ¡Bienvenido sea! Asimismo, tiene un pequeño vacío en el registro de los movimientos que son los yapeos recibidos desde otro yape y los depósitos realizados mediante un agente BCP. Debido a que estas operaciones no son notificadas por correo, no se van a poder ver incluidas en el alcance de este proyecto.

Me gustaría añadir una solución amigable para el registro y edición manual de movimientos, pero, debido a que con lo realizado hasta el momento ya soluciono en buena medida la necesidad puntual de controlar mis finanzas, no es actualmente una prioridad.

