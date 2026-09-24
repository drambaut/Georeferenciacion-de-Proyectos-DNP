"""
subir_a_supabase.py
Sube a Supabase Storage (bucket 'sentinel-images') las imagenes locales que
todavia no existen alla -- de paso, extrae las de Santa Marta del zip de
respaldo, ya que esas no tienen copia suelta en disco. Usa la service_role
key (bypasa RLS) porque la anon key es de solo lectura.

Solo lee de Imagenes/ y del zip -- nunca borra nada local (ver nota en
pipeline.py sobre BORRAR_LOCAL_TRAS_SUBIR).

Uso:
    python subir_a_supabase.py
"""
import os
import zipfile
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET = "sentinel-images"

CARPETA_LOCAL = r"Imagenes"
ZIP_SANTA_MARTA = r"C:\DNP\Proyecto satelital\Sentinel2_2025002470027.zip"
CARPETA_SANTA_MARTA = "sentinel2_2025002470027"


def subir(sb, ruta_destino: str, data: bytes) -> bool:
    try:
        sb.storage.from_(BUCKET).upload(
            path=ruta_destino, file=data,
            file_options={"content-type": "image/tiff", "upsert": "true"},
        )
        print(f"  OK  {ruta_destino}  ({len(data):,} bytes)")
        return True
    except Exception as e:
        print(f"  ERROR  {ruta_destino}: {e}")
        return False


def main():
    faltantes = [v for v in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY") if not os.getenv(v)]
    if faltantes:
        print("Faltan variables de entorno en .env:", ", ".join(faltantes))
        return

    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    ok, error, saltados = 0, 0, 0

    # ── 1. Santa Marta, desde el zip de respaldo ─────────────────────
    # (revisa primero que exista en Supabase antes de subir -- igual que la
    # seccion 2 -- para no volver a mandar los mismos 6 archivos cada vez
    # que se corre el script)
    print(f"=== Santa Marta (desde {os.path.basename(ZIP_SANTA_MARTA)}) ===")
    try:
        existentes_sm = {
            it.get("name") for it in sb.storage.from_(BUCKET).list(CARPETA_SANTA_MARTA)
        }
    except Exception:
        existentes_sm = set()

    with zipfile.ZipFile(ZIP_SANTA_MARTA) as z:
        for name in z.namelist():
            if not name.lower().endswith(".tiff"):
                continue
            archivo = os.path.basename(name)
            if archivo in existentes_sm:
                saltados += 1
                continue  # ya esta en Supabase, no volver a subir
            destino = f"{CARPETA_SANTA_MARTA}/{archivo}"
            data = z.read(name)
            if subir(sb, destino, data):
                ok += 1
            else:
                error += 1

    # ── 2. Los 16 archivos sueltos que faltaban en las demas carpetas ─
    print(f"\n=== Resto de proyectos (carpeta local {CARPETA_LOCAL}/) ===")
    for carpeta in sorted(os.listdir(CARPETA_LOCAL)):
        ruta_carpeta = os.path.join(CARPETA_LOCAL, carpeta)
        if not os.path.isdir(ruta_carpeta) or not carpeta.startswith("sentinel2_"):
            continue
        if carpeta == CARPETA_SANTA_MARTA:
            continue  # ya se subio arriba desde el zip

        try:
            existentes_remoto = {
                it.get("name") for it in sb.storage.from_(BUCKET).list(carpeta)
            }
        except Exception:
            existentes_remoto = set()

        for archivo in sorted(os.listdir(ruta_carpeta)):
            if not archivo.endswith(".tiff"):
                continue
            if archivo in existentes_remoto:
                saltados += 1
                continue  # ya esta en Supabase, no volver a subir

            ruta_local = os.path.join(ruta_carpeta, archivo)
            with open(ruta_local, "rb") as f:
                data = f.read()
            destino = f"{carpeta}/{archivo}"
            if subir(sb, destino, data):
                ok += 1
            else:
                error += 1

    print(f"\n--- Resumen ---")
    print(f"  Subidas OK : {ok}")
    print(f"  Ya existian (saltadas): {saltados}")
    print(f"  Errores    : {error}")


if __name__ == "__main__":
    main()
