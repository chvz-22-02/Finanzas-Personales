import pandas as pd
from datetime import datetime
import subprocess
import os

df = pd.read_pickle('data/processed/contabilidad.pickle')
df['fecha'] = pd.to_datetime(df['fecha'])

fecha_max = df['fecha'].max()
ahora = datetime.now()

diferencia_horas = int((ahora - fecha_max).total_seconds() // 3600) + 1
print(f"La diferencia en horas es: {diferencia_horas - 1}")

python_venv = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe")
subprocess.run([python_venv, "extractor_gastos.py", "--horas", str(diferencia_horas)])

subprocess.run([python_venv, "almacenado_informacion.py"])