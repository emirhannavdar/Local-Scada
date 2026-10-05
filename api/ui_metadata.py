"""Read-only form options from the existing PostgreSQL enum catalog."""
from fastapi import APIRouter, HTTPException
from database.database import get_connection

ui_metadata = APIRouter()
TABLES = ('saha', 'cihaz', 'cihaz_profili', 'profil_register', 'okuma_grubu',
          'register', 'tag', 'sinyal_sozlugu', 'seri_hat')


def read_options():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.relname, a.attname, e.enumlabel
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                JOIN pg_type t ON t.oid = a.atttypid
                JOIN pg_enum e ON e.enumtypid = COALESCE(NULLIF(t.typbasetype, 0), t.oid)
                WHERE c.relname = ANY(%s)
                  AND n.nspname = ANY(current_schemas(false))
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY c.relname, a.attname, e.enumsortorder
            """, (list(TABLES),))
            rows = cursor.fetchall()
    tables = {}
    for table, field, value in rows:
        tables.setdefault(table, {}).setdefault(field, []).append(value)
    return {'tables': tables, 'scaling': {'applied_field': 'register.carpan',
            'site_default': 'new_register_suggestion', 'tag_scale_applied': False}}


@ui_metadata.get('/options')
def options():
    try:
        return {'success': True, 'data': read_options()}
    except Exception:
        # Never expose connection strings or credentials in form errors.
        raise HTTPException(status_code=503, detail='Form seçenekleri okunamadı. PostgreSQL bağlantısını ve katalog okuma yetkisini kontrol et.')
