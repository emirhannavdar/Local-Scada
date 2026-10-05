from datetime import datetime
from typing import Generic, Optional, TypeVar
from urllib.request import Request

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection


device_profile = APIRouter()

T = TypeVar("T")


class RestApiDevicesProfile(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    dateTime: datetime = Field(default_factory=datetime.now)
    errorCode: Optional[int] = None
    message: Optional[str] = None

    @classmethod
    def ok(cls, data: T, message: Optional[str]):
        return cls(success=True, data=data, message=message)

    @classmethod
    def error(cls, message: str, code: Optional[int] = None):
        return cls(success=False, data=None, errorCode=code, message=message)

class ScadaDeviceProfile(BaseModel):
    name: str
    marka: str
    model: str
    device_type: str
    protocol: str
    surum: str | None = None
    aciklama: str | None = None
    aktif: bool = True

class ScadaDeviceProfilePatch(BaseModel):
    name: str | None = None
    marka: str | None = None
    model: str | None = None
    device_type: str | None = None
    protocol: str | None = None
    surum: str | None = None
    aciklama: str | None = None
    aktif: bool | None = None

def postDeviceProfile(raw: ScadaDeviceProfile):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO cihaz_profili (
                    ad,
                    marka,
                    model,
                    cihaz_tipi,
                    protokol,
                    surum,
                    aciklama,
                    aktif
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    raw.name,
                    raw.marka,
                    raw.model,
                    raw.device_type,
                    raw.protocol,
                    raw.surum,
                    raw.aciklama,
                    raw.aktif
                )
            )

            device_profile_id = cursor.fetchone()[0]

            connection.commit()
            return device_profile_id

        except Exception:
            connection.rollback()
            raise

def getDeviceProfile():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id,
                   ad,
                   marka,
                   model,
                   cihaz_tipi,
                   protokol,
                   surum,
                   aciklama,
                   aktif
            FROM cihaz_profili
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return result

    finally:
        connection.close()


def getDeviceProfileId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT ad,
                   marka,
                   model,
                   cihaz_tipi,
                   protokol,
                   surum,
                   aciklama,
                   aktif
            FROM cihaz_profili
            WHERE id = %s
            ORDER BY id;
            """, (id,)
        )
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return result
    finally:
        connection.close()

def putDeviceProfile(id ,raw):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE cihaz_profili
            SET ad         = %s,
                marka      = %s,
                model      = %s,
                cihaz_tipi = %s,
                protokol   = %s,
                surum      = %s,
                aciklama   = %s,
                aktif      = %s
            WHERE id = %s RETURNING id;
            """, (raw.name,
                  raw.marka,
                  raw.model,
                  raw.device_type,
                  raw.protocol,
                  raw.surum,
                  raw.aciklama,
                  raw.aktif,
                  id
                  )
        )
        connection.commit()
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def delDeviceProfile(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        kontrol = getDeviceProfileId(id)

        if not kontrol:
            error_res = RestApiDevicesProfile.error(f"Cihaz silinirken hata oluştu: Cihaz bulunamadı", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        cursor.execute(
            """
            DELETE
            FROM cihaz_profili
            WHERE id = %s
            """, (id,)
        )

        connection.commit()

        return {
            "success": True
        }

    finally:
        connection.close()

def patchDeviceProfile(id: int, raw: ScadaDeviceProfilePatch):
    update_data = raw.model_dump(exclude_unset=True)

    if not update_data:
        return id

    if "name" in update_data:
        update_data["ad"] = update_data.pop("name")

    connection = get_connection()
    try:
        cursor = connection.cursor()

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())

        query = f"""
                UPDATE cihaz_profili
                SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING id;
            """
        values.append(id)

        cursor.execute(query, tuple(values))
        connection.commit()

        row = cursor.fetchone()
        return row[0] if row else None

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

@device_profile.get('')
def get_device():
    try:
        data = getDeviceProfile()
        if not data:
            return RestApiDevicesProfile.error(message="Cihaz bulunamadı", code=404)
        return RestApiDevicesProfile.ok(data=data, message="BASARILI")
    except Exception as e:
        error_res = RestApiDevicesProfile.error(f"Sistem hatası: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))


@device_profile.get('/{id}')
def get_device_id(id: int):
    try:
        data = getDeviceProfileId(id)
        if not data:
            return RestApiDevicesProfile.error(message="Cihaz bulunamadı", code=404)
        return RestApiDevicesProfile.ok(data=data, message="BASARILI")
    except Exception as e:
        error_res = RestApiDevicesProfile.error(f"Sistem hatası: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@device_profile.post("")
def create_device_profile(raw: ScadaDeviceProfile):
    data = postDeviceProfile(raw)

    return {
        "success": True,
        "data": data
    }


@device_profile.put('/{id}')
def updateDm(id: int, raw: ScadaDeviceProfile):
    try:
        device_profile_up = putDeviceProfile(id, raw)

        if not device_profile_up:
            error_res = RestApiDevicesProfile.error(f"{id} numaralı cihaz güncellenemedi veya bulunamadı.", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiDevicesProfile.ok(data=device_profile_up, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiDevicesProfile.error(
            message=f"Güncelleme sırasında geçersiz veri formatı/ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))
    except Exception as e:
        error_res = RestApiDevicesProfile.error(f"Cihaz güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))


@device_profile.delete('/{id}')
def delete_dm(id: int):
    try:
        dele = delDeviceProfile(id)
        return RestApiDevicesProfile.ok(data=dele, message="BASARILI")

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        error_res = RestApiDevicesProfile.error(f"Cihaz silinirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))


@device_profile.patch('/{id}')
def patch_device(id: int, raw: ScadaDeviceProfilePatch):
    try:
        updated_id = patchDeviceProfile(id, raw)

        if not updated_id:
            error_res = RestApiDevicesProfile.error(message=f"{id} numaralı cihaz bulunamadı veya güncellenemedi.", code=404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiDevicesProfile.ok(data=updated_id, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiDevicesProfile.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))

    except Exception as e:
        error_res = RestApiDevicesProfile.error(message=f"Cihaz güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
                                         code=500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))