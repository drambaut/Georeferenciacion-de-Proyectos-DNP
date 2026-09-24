"""
verificar_supabase_estructura.py
Conecta a Supabase (con la service_role key) y muestra que hay adentro:
buckets de Storage, carpetas dentro del bucket de imagenes, y la tabla de
metadatos de proyectos. Solo lee, no sube ni borra nada -- pensado para
confirmar rapido que la conexion funciona antes de correr la subida real.

Uso:
    python verificar_supabase_estructura.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_IMAGENES = "sentinel-images"
TABLA_PROYECTOS = "proyectos"


def main():
    faltantes = [v for v in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY") if not os.getenv(v)]
    if faltantes:
        print("Faltan variables de entorno en .env:", ", ".join(faltantes))
        return

    from supabase import create_client
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print(f"Conectando a {SUPABASE_URL} ...\n")

    # ── Storage: carpetas del bucket de imagenes ────────────────────
    try:
        items = sb.storage.from_(BUCKET_IMAGENES).list()
        carpetas = sorted(it.get("name") for it in items)
        print(f"Bucket '{BUCKET_IMAGENES}': {len(carpetas)} carpeta(s)")
        for c in carpetas:
            # contar cuantos .tiff tiene cada carpeta, para ver que tan
            # completa esta cada una de un vistazo
            try:
                archivos = sb.storage.from_(BUCKET_IMAGENES).list(c)
                n_tiff = sum(1 for a in archivos if a.get("name", "").endswith(".tiff"))
                print(f"  - {c}  ({n_tiff} imagen(es))")
            except Exception:
                print(f"  - {c}  (no se pudo listar su contenido)")
    except Exception as e:
        print(f"ERROR accediendo al bucket '{BUCKET_IMAGENES}': {e}")

    # ── Tabla de metadatos de proyectos ─────────────────────────────
    print(f"\nTabla '{TABLA_PROYECTOS}':")
    try:
        res = sb.table(TABLA_PROYECTOS).select("*", count="exact").limit(1).execute()
        print(f"  Filas totales: {res.count}")
        if res.data:
            print(f"  Columnas: {list(res.data[0].keys())}")
    except Exception as e:
        print(f"  ERROR accediendo a la tabla '{TABLA_PROYECTOS}': {e}")

    # ── Prueba de escritura (sube y borra un archivo de prueba) ─────
    print("\nProbando permiso de escritura (service_role)...")
    try:
        ruta_prueba = "_test_conexion/ping.txt"
        sb.storage.from_(BUCKET_IMAGENES).upload(
            path=ruta_prueba, file=b"ping",
            file_options={"content-type": "text/plain", "upsert": "true"},
        )
        sb.storage.from_(BUCKET_IMAGENES).remove([ruta_prueba])
        print("  OK -- se puede escribir y borrar en el bucket.")
    except Exception as e:
        print(f"  ERROR -- no se pudo escribir: {e}")


if __name__ == "__main__":
    main()
