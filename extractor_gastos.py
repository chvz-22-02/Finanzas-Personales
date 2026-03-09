#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║         EXTRACTOR DE GASTOS BANCARIOS  v1.1              ║
║  Fuentes: BCP · Pichincha · Yape                         ║
║  Salida:  gastos.csv                                     ║
╚══════════════════════════════════════════════════════════╝

Uso:
    python extractor_gastos.py              # últimos 90 días
    python extractor_gastos.py --dias 30    # últimos 30 días
    python extractor_gastos.py --horas 24   # últimas 24 horas
    python extractor_gastos.py --horas 6    # últimas 6 horas
    python extractor_gastos.py --todos      # todos los correos
    python extractor_gastos.py --salida mis_gastos.csv
"""

import os
import re
import csv
import base64
import argparse
import time
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup


# ══════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════

SCOPES            = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE  = 'credentials.json'   # Descargado de Google Cloud Console
TOKEN_FILE        = 'token.json'          # Se genera automáticamente tras el primer login
DEFAULT_OUTPUT    = f'data/interimn/gastos{time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())}.csv'
DEFAULT_DAYS      = 0

# Remitentes reconocidos
SENDERS = [
    'notificaciones@notificacionesbcp.com.pe',
    'app@pichincha.pe',
    'notificaciones@pichincha.pe',
    'notificaciones@yape.pe',
]

# Columnas del CSV de salida
FIELDNAMES = [
    'id', 'fecha', 'monto', 'tipo',        # gasto / ingreso
    'categoria', 'descripcion',
    'banco', 'cuenta', 'num_operacion',
]


# ══════════════════════════════════════════════════════════
# AUTENTICACIÓN GMAIL
# ══════════════════════════════════════════════════════════

def authenticate():
    """OAuth2: abre el navegador la primera vez, luego usa token.json."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"No se encontró '{CREDENTIALS_FILE}'.\n"
                    "Descárgalo desde Google Cloud Console → APIs & Services → Credentials.\n"
                    "Consulta el README.md para instrucciones detalladas."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


# ══════════════════════════════════════════════════════════
# OBTENCIÓN DE CORREOS
# ══════════════════════════════════════════════════════════

def build_query(days_back=0, hours_back=0):
    """
    Construye la query de Gmail.
    - hours_back: usa 'newer_than:Nh' (precisión por horas, soportado por Gmail)
    - days_back:  usa 'after:YYYY/MM/DD'
    - ambos 0:    sin filtro de fecha (todos los correos)
    """
    sender_q = ' OR '.join(f'from:{s}' for s in SENDERS)
    query = f'({sender_q})'
    if hours_back and hours_back > 0:
        query += f' newer_than:{hours_back}h'
    elif days_back and days_back > 0:
        after = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
        query += f' after:{after}'
    return query


def fetch_all_messages(service, days_back=0, hours_back=0):
    query = build_query(days_back=days_back, hours_back=hours_back)
    print(f"🔍 Query Gmail: {query}")
    messages, page_token = [], None
    while True:
        kwargs = dict(userId='me', q=query, maxResults=500)
        if page_token:
            kwargs['pageToken'] = page_token
        resp = service.users().messages().list(**kwargs).execute()
        messages.extend(resp.get('messages', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    print(f"📬 {len(messages)} correos encontrados")
    return messages


def get_message(service, msg_id):
    return service.users().messages().get(userId='me', id=msg_id, format='full').execute()


def get_header(msg, name):
    for h in msg.get('payload', {}).get('headers', []):
        if h['name'].lower() == name.lower():
            return h['value']
    return ''


def extract_body(payload):
    """Extrae HTML y texto plano recursivamente del payload MIME."""
    html_body, text_body = '', ''

    def recurse(part):
        nonlocal html_body, text_body
        mime = part.get('mimeType', '')
        data = part.get('body', {}).get('data', '')
        if data:
            decoded = base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
            if 'html' in mime:
                html_body += decoded
            elif 'plain' in mime:
                text_body += decoded
        for sub in part.get('parts', []):
            recurse(sub)

    recurse(payload)
    return html_body, text_body


# ══════════════════════════════════════════════════════════
# UTILIDADES DE PARSEO
# ══════════════════════════════════════════════════════════

MESES = {
    'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
    'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12
}


def parse_amount(s):
    """Extrae float de strings como 'S/ 14.99', 'S/.4.80', '105.83'."""
    if not s:
        return None
    s = s.replace(',', '.')
    m = re.search(r'\d+\.\d+', s)
    return float(m.group()) if m else None


def parse_date(s):
    """
    Parsea fechas en los múltiples formatos que usan BCP, Pichincha y Yape.

    Formatos soportados:
      "04 de marzo de 2026 - 05:49 PM"
      "22 de febrero de 2026 - 09:25 AM"
      "28 Febrero 2026 - 18:18"
      "Viernes, 27 Febrero 2026 - 05:51 P. M."
      "16 febrero 2026 - 12:03 p. m."
      "22/02/2026 12:12"
    """
    if not s:
        return None
    s = s.strip()

    # DD/MM/YYYY HH:MM
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})', s)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)),
                        int(m.group(4)), int(m.group(5)))

    # Normalizar "P. M." → "PM", "p. m." → "PM"
    s = re.sub(r'[Pp]\.\s*[Mm]\.', 'PM', s)
    s = re.sub(r'[Aa]\.\s*[Mm]\.', 'AM', s)
    # Quitar día de semana inicial ("Viernes, ")
    s = re.sub(r'^[A-Za-záéíóúÁÉÍÓÚ]+,\s*', '', s)

    # DD [de] MES [de] YYYY [- HH:MM [AM|PM]]
    pattern = (
        r'(\d{1,2})\s+(?:de\s+)?([A-Za-záéíóúÁÉÍÓÚ]+)\s+(?:de\s+)?(\d{4})'
        r'(?:\s*[-–]\s*(\d{1,2}):(\d{2})(?:\s*(AM|PM))?)?'
    )
    m = re.search(pattern, s)
    if m:
        day   = int(m.group(1))
        month = MESES.get(m.group(2).lower())
        if not month:
            return None
        year  = int(m.group(3))
        hour  = int(m.group(4)) if m.group(4) else 0
        minute= int(m.group(5)) if m.group(5) else 0
        ampm  = (m.group(6) or '').upper()
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return None
    return None


def html_table_to_dict(soup):
    """
    Extrae pares clave-valor de tablas HTML estilo BCP/Pichincha.
    Busca filas con exactamente 2 celdas <td>.
    """
    data = {}
    for row in soup.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) == 2:
            key = tds[0].get_text(' ', strip=True)
            val = tds[1].get_text(' ', strip=True)
            if key and len(key) < 60:
                data[key] = val
    return data


def first_match(patterns, text, group=1):
    """Prueba una lista de patrones y devuelve el primer grupo que coincida."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(group).strip()
    return None


# ══════════════════════════════════════════════════════════
# PARSERS POR TIPO DE CORREO
# ══════════════════════════════════════════════════════════

def parse_bcp_consumo_tc(html, text, id):
    """
    BCP – Consumo con Tarjeta de Crédito/Débito
    Asunto: "Realizaste un consumo con tu Tarjeta de Crédito BCP"
    """
    soup = BeautifulSoup(html, 'html.parser')
    tbl  = html_table_to_dict(soup)

    # Monto: primero desde el párrafo principal
    monto_str = first_match([
        r'consumo de\s+(S/\.?\s*[\d.,]+)',
        r'Total del consumo\s+(S/\.?\s*[\d.,]+)',
    ], text)
    monto = parse_amount(monto_str) or parse_amount(tbl.get('Total del consumo', ''))

    # Empresa
    descripcion = first_match([r'BCP en\s+([^\.\n]+?)\.'], text) \
               or tbl.get('Empresa', '')

    # Fecha
    fecha_str = tbl.get('Fecha y hora') \
             or first_match([r'Fecha y hora\s+(.+?)(?:Número|Empresa|$)'], text)
    fecha = parse_date(fecha_str)

    # Tarjeta y operación
    cuenta        = first_match([r'(\*{4,}\d{4})'], text) or ''
    num_operacion = tbl.get('Número de operación') \
                 or first_match([r'Número de operación\s+(\d+)'], text) or ''

    return {
        'id': id,
        'banco': 'BCP', 'tipo': 'gasto', 'categoria': 'Consumo TC',
        'monto': monto, 'descripcion': descripcion.strip(),
        'fecha': fecha, 'cuenta': cuenta, 'num_operacion': num_operacion,
    }


def parse_bcp_pago_servicio(html, text, id):
    """
    BCP – Pago de servicio (internet, agua, luz, etc.)
    Asunto: "CONSTANCIA DE PAGO DE SERVICIO - BANCA MOVIL BCP"
    """
    soup = BeautifulSoup(html, 'html.parser')
    tbl  = html_table_to_dict(soup)

    empresa    = tbl.get('Empresa:') or first_match([r'Empresa:\s*([^\n]+)'], text)
    monto      = parse_amount(tbl.get('Monto total:') or
                              first_match([r'Monto total:\s*(S/\.?\s*[\d.,]+)'], text))
    fecha_str  = tbl.get('Fecha y hora:') or first_match([r'Fecha y hora:\s*([^\n]+)'], text)
    fecha      = parse_date(fecha_str)
    num_op     = first_match([r'Número de operación:\s*</p>\s*<p[^>]*><b>(.*?)</b>'], html) or ''
    # Tarjeta origen
    cuenta     = first_match([r'(\*{4}\s*\d{4})'], text) or ''
    cuenta     = cuenta.replace(' ', '')

    return {
        'id': id,
        'banco': 'BCP', 'tipo': 'gasto', 'categoria': 'Pago de servicio',
        'monto': monto, 'descripcion': (empresa or '').strip(),
        'fecha': fecha, 'cuenta': cuenta, 'num_operacion': num_op,
    }


def parse_bcp_yapeo_recibido(html, text, id):
    """
    BCP – Yapeo recibido (INGRESO)
    Asunto: "Constancia de recepción de Yapeo a celular BCP"
    """
    soup = BeautifulSoup(html, 'html.parser')
    tbl  = html_table_to_dict(soup)

    monto     = parse_amount(
        first_match([r'Recibiste un <b>yapeo de S/\s*(.*?)</b>'], html)
    )
    enviado   = tbl.get('Enviado por') or first_match([r'Enviado por\s+([^\n]+)'], text) or ''
    fecha_str = tbl.get('Fecha y hora') or first_match([r'Fecha y hora\s+(.+?)(?:Enviado|$)'], text)
    fecha     = parse_date(fecha_str)

    return {
        'id': id,
        'banco': 'BCP', 'tipo': 'ingreso', 'categoria': 'Yapeo recibido',
        'monto': monto, 'descripcion': enviado.strip(),
        'fecha': fecha, 'cuenta': '', 'num_operacion': '',
    }


def parse_yape_yapeo_enviado(html, text, id):
    """
    Yape – Yapeo enviado (GASTO)
    Asunto: "Por tu seguridad, te notificaremos por cada yapeo que realices"
    """
    # El monto aparece partido en dos celdas en HTML ("S/" | "105.83")
    # En texto plano se concatena como "S/105.83"
    monto_str = first_match([
        r'yapeo\*?\s*S/\s*([\d.,]+)',
        r'S/\s*([\d.,]+)',
    ], text)
    monto = parse_amount(monto_str)

    beneficiario = first_match([r'Nombre del Beneficiario\s+([^\n]+)'], text) or ''
    fecha_str    = first_match([r'Fecha y Hora de la operaci[oó]n\s+([^\n]+)'], text)
    fecha        = parse_date(fecha_str)
    num_op       = first_match([r'N[oº°]\s*de operaci[oó]n\s+(\d+)'], text) or ''

    return {
        'id': id,
        'banco': 'Yape', 'tipo': 'gasto', 'categoria': 'Yapeo',
        'monto': monto, 'descripcion': f'Yapeo a: {beneficiario.strip()}',
        'fecha': fecha, 'cuenta': 'Yape', 'num_operacion': num_op,
    }


def parse_pichincha_envio(html, text, id):
    """
    Pichincha – Envío a contacto (GASTO)
    Asunto: "Envio de dinero a contacto"
    Remitente: app@pichincha.pe
    """
    soup = BeautifulSoup(html, 'html.parser')
    tbl  = html_table_to_dict(soup)

    # Monto: buscar el label-amount (clase en CSS), o caer en regex
    amount_tag = soup.find(class_=lambda c: c and 'label-amount' in c)
    if amount_tag:
        monto = parse_amount(amount_tag.get_text())
    else:
        monto = parse_amount(first_match([r'Monto Enviado\s*S/\s*([\d.,]+)',
                                          r'S/\s*([\d.,]+)'], text))

    # Fecha: en el header ("28 Febrero 2026 - 18:18")
    fecha_tag = soup.find(class_=lambda c: c and 'text-subtitle' in c)
    fecha = parse_date(fecha_tag.get_text(strip=True) if fecha_tag else
                       first_match([r'(\d{1,2}\s+[A-Za-záéíóú]+\s+\d{4}\s*[-–]\s*\d{2}:\d{2})'], text))

    # Destino
    destino = tbl.get('Cuenta de destino') \
           or first_match([r'Cuenta de destino </label>\s*<br>\s*<label class="text-column-body">(.*?)</label>\s*<br>'], html) or ''
    # Limpiar ruido (líneas de cuenta Yape/número)
    destino = destino.split('\n')[0].strip()

    # Número de operación
    num_op = first_match([r'<b>Operación:</b>&nbsp;(.*?)</label>'], html) or ''

    # Cuenta de origen
    cuenta = first_match([rf'{destino}</label>\s*<br>\s*<label class="text-column-body">(.*?)</label>\s*<br>'], html)
    cuenta = f'***{cuenta}' if cuenta else ''

    return {
        'id': id,
        'banco': 'Pichincha', 'tipo': 'gasto', 'categoria': 'Transferencia',
        'monto': monto, 'descripcion': destino,
        'fecha': fecha, 'cuenta': cuenta, 'num_operacion': num_op,
    }


def parse_pichincha_recibido(html, text, id):
    """
    Pichincha – Pago recibido (INGRESO)
    Asunto: "Has recibido un pago disponible en tu APP Pichincha"
    Remitente: notificaciones@pichincha.pe
    Formato: texto plano simple
    """
    remitente = first_match([r'Hola,\s+(.+?)\s+te ha enviado'], text) or 'Desconocido'
    monto     = parse_amount(first_match([r'Monto\s+recibido:\s*S/\.?([\d.,]+)'], text))
    fecha_str = first_match([r'Fecha y hora:\s*([\d/]+\s+[\d:]+)'], text)
    fecha     = parse_date(fecha_str)
    cuenta    = first_match([r'te ha enviado un pago por (.+?)\.\s*\n'], text) or 'Desconocido'

    return {
        'id': id,
        'banco': 'Pichincha', 'tipo': 'ingreso', 'categoria': 'Pago recibido',
        'monto': monto, 'descripcion': remitente.strip(),
        'fecha': fecha, 'cuenta': cuenta, 'num_operacion': '',
    }


def parse_bcp_retiro_agente(html, text, id):
    """
    BCP – Retiro con Tarjeta de Débito en Agente BCP
    Asunto: "Realizaste un retiro en un Agente BCP"
    """
    soup = BeautifulSoup(html, 'html.parser')
    tbl  = html_table_to_dict(soup)

    # Monto: desde el párrafo principal o desde la tabla
    monto_str = first_match([
        r'retiro de\s+(S/\.?\s*[\d.,]+)',
        r'Monto retirado\s+(S/\.?\s*[\d.,]+)',
    ], text)
    monto = parse_amount(monto_str) or parse_amount(tbl.get('Monto retirado', ''))

    # Fecha
    fecha_str = tbl.get('Fecha y hora') \
             or first_match([r'Fecha y hora\s+(.+?)(?:Número|Cuenta|Canal|$)'], text)
    fecha = parse_date(fecha_str)

    # Tarjeta de débito y cuenta de cargo
    cuenta = tbl.get('Número de Tarjeta de Débito') \
          or first_match([r'Número de Tarjeta de D[eé]bito\s+(\*+\s*\d{4})'], text) or ''
    cuenta = cuenta.replace(' ', '')

    # Canal y código de agente para la descripción
    canal        = tbl.get('Canal') or 'Agente BCP'
    cod_agente   = tbl.get('Código de agente') \
                or first_match([r'C[oó]digo de agente\s+(\S+)'], text) or ''
    descripcion  = f'{canal}' + (f' ({cod_agente})' if cod_agente else '')

    num_operacion = tbl.get('Número de operación') \
                 or first_match([r'Número de operación\s+(\S+)'], text) or ''

    return {
        'id': id,
        'banco': 'BCP', 'tipo': 'gasto', 'categoria': 'Retiro',
        'monto': monto, 'descripcion': descripcion,
        'fecha': fecha, 'cuenta': cuenta, 'num_operacion': num_operacion,
    }




def classify_and_parse(msg, id):
    sender  = get_header(msg, 'From').lower()
    subject = get_header(msg, 'Subject')
    subj_l  = subject.lower()

    html, text = extract_body(msg.get('payload', {}))

    # ── BCP ──────────────────────────────────────────────
    if 'notificacionesbcp' in sender:
        if 'consumo' in subj_l:
            return parse_bcp_consumo_tc(html, text, id)
        if 'pago de servicio' in subj_l:
            return parse_bcp_pago_servicio(html, text, id)
        if 'yapeo' in subj_l and ('recep' in subj_l or 'recib' in subj_l):
            return parse_bcp_yapeo_recibido(html, text, id)
        if 'retiro' in subj_l:
            return parse_bcp_retiro_agente(html, text, id)

    # ── Yape ─────────────────────────────────────────────
    if 'yape.pe' in sender:
        return parse_yape_yapeo_enviado(html, text, id)

    # ── Pichincha ─────────────────────────────────────────
    if 'pichincha' in sender:
        if 'app@pichincha' in sender or 'envio' in subj_l or 'envío' in subj_l:
            return parse_pichincha_envio(html, text, id)
        if 'recibido' in subj_l or 'recibiste' in subj_l:
            return parse_pichincha_recibido(html, text, id)

    return None   # Tipo de correo no reconocido


# ══════════════════════════════════════════════════════════
# SALIDA CSV
# ══════════════════════════════════════════════════════════

def save_to_csv(transactions, path):
    transactions.sort(
        key=lambda x: x.get('fecha') or datetime.min,
        reverse=True
    )
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        for t in transactions:
            row = dict(t)
            if isinstance(row.get('fecha'), datetime):
                row['fecha'] = row['fecha'].strftime('%Y-%m-%d %H:%M')
            elif row.get('fecha') is None:
                row['fecha'] = ''
            writer.writerow(row)
    print(f"\n✅ {len(transactions)} transacciones guardadas en '{path}'")


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Extractor de gastos bancarios desde Gmail')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dias',   type=int, default=None,
                        help='Correos de los últimos N días')
    group.add_argument('--horas',  type=int, default=None,
                        help='Correos de las últimas N horas (más preciso que --dias)')
    group.add_argument('--todos',  action='store_true',
                        help='Procesar todos los correos sin filtro de fecha')
    parser.add_argument('--salida', default=DEFAULT_OUTPUT,
                        help=f'Archivo CSV de salida (default: {DEFAULT_OUTPUT})')
    args = parser.parse_args()

    # Determinar modo de filtrado
    if args.todos:
        days_back, hours_back = 0, 0
        periodo_label = '∞ (todos)'
    elif args.horas is not None:
        days_back, hours_back = 0, args.horas
        periodo_label = f'últimas {hours_back} horas'
    else:
        days_back = args.dias if args.dias is not None else DEFAULT_DAYS
        hours_back = 0
        periodo_label = f'últimos {days_back} días'

    print("🔐 Autenticando con Gmail API...")
    service = authenticate()

    print(f"📬 Buscando correos ({periodo_label})...")
    messages = fetch_all_messages(service, days_back=days_back, hours_back=hours_back)

    transactions = []
    skipped_count = 0

    for i, msg_ref in enumerate(messages):
        msg    = get_message(service, msg_ref['id'])
        result = classify_and_parse(msg, msg['id'])
        subj   = get_header(msg, 'Subject')[:55]

        if result and result.get('monto') is not None:
            transactions.append(result)
            fecha_str = result['fecha'].strftime('%d/%m/%Y') if result.get('fecha') else '??/??/????'
            print(
                f"  [{i:>3}/{len(messages)}] ✓ "
                f"{'INGRESO' if result['tipo']=='ingreso' else 'GASTO  '} "
                f"S/ {result['monto']:>8.2f}  "
                f"{result['banco']:<10} "
                f"{fecha_str}  "
                f"{result.get('descripcion','')[:30]}"
            )
        else:
            skipped_count += 1
            if result is None:
                print(f"  [{i:>3}/{len(messages)}] ⚠  No reconocido: {subj}")

    print(f"\n📊 Resumen: {len(transactions)} transacciones | {skipped_count} ignorados")

    if transactions:
        save_to_csv(transactions, args.salida)
        # Mostrar totales rápidos
        gastos   = sum(t['monto'] for t in transactions if t['tipo'] == 'gasto')
        ingresos = sum(t['monto'] for t in transactions if t['tipo'] == 'ingreso')
        print(f"\n💸 Total gastos:   S/ {gastos:,.2f}")
        print(f"💰 Total ingresos: S/ {ingresos:,.2f}")
        print(f"📈 Balance:        S/ {ingresos - gastos:,.2f}")
    else:
        print("No se encontraron transacciones en el período indicado.")


if __name__ == '__main__':
    main()