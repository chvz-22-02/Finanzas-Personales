import pandas as pd
import os
import shutil

carpeta = "data/interimn/"
carpeta_destino = "data/interimn/processed/"
archivos_csv = [f for f in os.listdir(carpeta) if f.endswith('.csv')]
dataframes = []
for archivo in archivos_csv:
    ruta_completa = os.path.join(carpeta, archivo)
    df = pd.read_csv(ruta_completa)
    dataframes.append(df)
df_final = pd.concat(dataframes, ignore_index=True)

try:
    # df_historico = pd.read_pickle('data/processed/contabilidad.pickle')
    df_historico = pd.read_csv('data/processed/contabilidad.txt', sep='|')

    df_update = df_final[~df_final['id'].isin(df_historico['id'])]

    df_actualizado = pd.concat([df_historico, df_update])

    # df_actualizado.to_pickle('data/processed/contabilidad.pickle')
    df_actualizado.to_csv('data/processed/contabilidad.txt', sep='|', index=False)
except:
    df_final.to_csv('data/processed/contabilidad.txt', sep='|', index=False)

os.makedirs(carpeta_destino, exist_ok=True)
for archivo in archivos_csv:
    ruta_origen = os.path.join(carpeta, archivo)
    ruta_destino = os.path.join(carpeta_destino, archivo)
    shutil.move(ruta_origen, ruta_destino)