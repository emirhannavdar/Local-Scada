from datetime import datetime
from typing import Generic, Optional, TypeVar

import psycopg
from fastapi import APIRouter, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from psycopg import cursor
from pydantic import BaseModel, Field
from database.database import get_connection

saha = APIRouter()

T = TypeVar("T")

class RestApiDevices(BaseModel, Generic[T]):
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



class Scada(BaseModel):
    name: str
    code: str
    kurulu_guc_kwp: float
    loc: str
    timeZone: str
    aktif: bool = True
    varsayilan_carpan: float = 1.0

class ScadaPatch(BaseModel):
    name: str | None = None
    code: str | None = None
    kurulu_guc_kwp: float | None = None
    loc: str | None = None
    timeZone: str | None = None
    aktif: bool | None = None
    varsayilan_carpan: float | None = None


def postSaha(
        name: str,
        code: str,
        kurulu_guc_kwp: float,
        loc: str,
        timeZone: str,
        aktif: bool = True,
        varsayilan_carpan: float = 1.0
):
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO saha (
                        ad,
                        kod,
                        kurulu_guc_kwp,
                        konum,
                        zaman_dilimi,
                        aktif,
                        varsayilan_carpan
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        name,
                        code,
                        kurulu_guc_kwp,
                        loc,
                        timeZone,
                        aktif,
                        varsayilan_carpan
                    )
                )

                saha_post_id = cursor.fetchone()[0]
                connection.commit()
                return saha_post_id
        except Exception:
            connection.rollback()
            raise



def getSahaId(saha_id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                ad,
                kod,
                kurulu_guc_kwp,
                konum,
                zaman_dilimi,
                aktif,
                varsayilan_carpan
            FROM saha
            WHERE id = %s;
            """,
            (saha_id,)
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "code": row[2],
            "kurulu_guc_kwp": row[3],
            "konum": row[4],
            "zaman_dilimi": row[5],
            "aktif": row[6],
            "varsayilan_carpan": row[7]
        }

    finally:
        connection.close()

def get_Saha():
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                ad,
                kod,
                kurulu_guc_kwp,
                konum,
                zaman_dilimi,
                aktif,
                varsayilan_carpan
            FROM saha
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        saha = []

        for row in rows:
            saha.append({
                "id": row[0],
                "name": row[1],
                "code": row[2],
                "kurulu_guc_kwp": row[3],
                "konum": row[4],
                "zaman_dilimi": row[5],
                "aktif": row[6],
                "varsayilan_carpan": row[7]
            })

        return saha

    finally:
        connection.close()

def putSaha(id, raw: Scada):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE saha
            SET ad=%s,
                kod=%s,
                kurulu_guc_kwp=%s,
                konum=%s,
                zaman_dilimi=%s,
                aktif=%s,
                varsayilan_carpan=%s
                WHERE id=%s
                RETURNING id;
            """, (raw.name, raw.code, raw.kurulu_guc_kwp, raw.loc, raw.timeZone, raw.aktif, raw.varsayilan_carpan, id)
        )
        up_saha = cursor.fetchone()
        connection.commit()
        return up_saha[0] if up_saha else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def delSaha(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        kontrol = getSahaId(id)

        if not kontrol:
            error_res = RestApiDevices.error(f"Cihaz silinirken hata oluştu", 500)
            raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

        cursor.execute(
            """
            DELETE FROM saha WHERE id=%s;
            """, (id,)
        )
        connection.commit()

    finally:
        connection.close()


def patchSaha(id: int, raw: ScadaPatch):
    update_data = raw.model_dump(exclude_unset=True)
    if not update_data:
        return id

    if "name" in update_data:
        update_data["ad"] = update_data.pop("name")

    if "code" in update_data:
        update_data["kod"] = update_data.pop("code")

    connection = get_connection()
    try:
        cursor = connection.cursor()
        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())

        query = f"""
            UPDATE saha
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

@saha.get('')
def getSaha():
    try:
        data = get_Saha()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@saha.get('/{saha_id}')
def getSaha_Id(saha_id: int):
    try:
        data = getSahaId(saha_id)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@saha.post('')
def createSaha(raw: Scada, request: Request):
    try:
        data = postSaha(
            name=raw.name,
            code=raw.code,
            kurulu_guc_kwp=raw.kurulu_guc_kwp,
            loc=raw.loc,
            timeZone=raw.timeZone,
            aktif=raw.aktif,
            varsayilan_carpan=raw.varsayilan_carpan
        )

        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@saha.put('/{id}')
def updateSaha(id: int, raw: Scada, request: Request):
    try:
        saha_up = putSaha(id, raw)

        if not saha_up:
            error_res = RestApiDevices.error(f"{id} numaralı cihaz güncellenemedi veya bulunamadı.", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiDevices.ok(data=saha_up, message="BASARILI")

    except Exception as e:
        error_res = RestApiDevices.error(f"Cihaz güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@saha.delete('/{id}')
def delete_Saha(id: int, request: Request):
    try:
        dele = delSaha(id)


        return RestApiDevices.ok(data=dele, message="BASARILI")

    except Exception as e:
        error_res = RestApiDevices.error(f"Cihaz güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@saha.patch('/{id}')
def patch_device(id: int, raw: ScadaPatch):
    try:
        updated_id = patchSaha(id, raw)

        if not updated_id:
            error_res = RestApiDevices.error(message=f"{id} numaralı cihaz bulunamadı veya güncellenemedi.", code=404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiDevices.ok(data=updated_id, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiDevices.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))

    except Exception as e:
        error_res = RestApiDevices.error(message=f"Cihaz güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
                                         code=500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))