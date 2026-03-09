# Extractor de Gastos Bancarios desde Gmail

(Hecho con la inestimable ayuda de Claude.ai)

Extrae automáticamente tus transacciones de los correos de **BCP**, **Pichincha** y **Yape**
y las exporta a un archivo `gastos.csv` listo para analizar en Excel o Google Sheets.

## Correos soportados

| Banco / App | Tipo de correo | Tipo en CSV |
|---|---|---|
| BCP | Consumo con Tarjeta de Crédito/Débito | gasto |
| BCP | Pago de servicios (Banca Móvil) | gasto |
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

### Ejecución básica (últimos 90 días)
```bash
python extractor_gastos.py
```

### Últimos 30 días
```bash
python extractor_gastos.py --dias 30
```

### Todos los correos
```bash
python extractor_gastos.py --todos
```

### Con nombre de archivo personalizado
```bash
python extractor_gastos.py --dias 60 --salida febrero_marzo.csv
```

**Primera ejecución:** se abrirá el navegador para que autorices el acceso.
Tras aceptar, se guarda `token.json` y no vuelves a necesitar autorizarlo.

---

## Formato del CSV de salida

| Columna | Descripción | Ejemplo |
|---|---|---|
| `fecha` | Fecha y hora de la operación | `2026-03-04 17:49` |
| `monto` | Monto en soles | `14.99` |
| `tipo` | `gasto` o `ingreso` | `gasto` |
| `categoria` | Tipo de transacción | `Consumo TC/TD` |
| `descripcion` | Empresa o beneficiario | `ADM CLIN RICARDO PALMA` |
| `banco` | Banco de origen | `BCP` |
| `cuenta` | Últimos 4 dígitos | `************1756` |
| `num_operacion` | Número de operación | `0000383035` |

---

## Archivos generados

- `token.json` — Token de acceso a Gmail (no compartir)
- `gastos.csv` — Resultado de la extracción

---

## Para agregar un nuevo banco

En `extractor_gastos.py`:
1. Agrega el remitente a la lista `SENDERS`
2. Crea una función `parse_nuevo_banco(html, text)`
3. Agrega la condición en la función `classify_and_parse()`
