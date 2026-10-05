from datetime import datetime
from typing import TypeVar, Generic, Optional

import psycopg
from fastapi import APIRouter, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection

tm = APIRouter()

T = TypeVar("T")

class RestApiTm(BaseModel, Generic[T]):
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



class ScadaTm(BaseModel):
    dm_id: int
    name: str
    sira: int

class ScadaTmPatch(BaseModel):
    dm_id: int | None = None
    name: str | None = None
    sira: int | None = None

def postTm(
        dm_id: int,
        name: str,
        sira: int,
):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO tm (dm_id, ad, sira)
                    VALUES (%s, %s, %s) RETURNING *;
                """,
                (dm_id, name, sira)
            )
            sahaTm = cursor.fetchone()
            saha_post_id = sahaTm[0]

            connection.commit()
            return saha_post_id

        except Exception as e:
            connection.rollback()
            raise e


def GetTm():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                id,
                dm_id,
                ad,
                sira
            FROM tm
            ORDER BY id;
            """
        )
        rows = cursor.fetchall()

        tm = []

        for row in rows:
            tm.append({
                "id": row[0],
                "dm_id": row[1],
                "ad": row[2],
                "sira": row[3]
            })

        return tm

    finally:
        connection.close()

def GetTmId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id,
                   dm_id,
                   ad,
                   sira
            FROM tm
            WHERE id = %s
            ORDER BY id;
            """, (id, )
        )
        rows = cursor.fetchall()

        tm_id = []

        for row in rows:
            tm_id.append({
                "id": row[0],
                "dm_id": row[1],
                "ad": row[2],
                "sira": row[3]
            })

        return tm_id

    finally:
        connection.close()


def putTm(id, raw: ScadaTm):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE tm
            SET dm_id = %s,
                ad      = %s,
                sira    = %s
            WHERE id = %s RETURNING id;
            """, (raw.dm_id, raw.name, raw.sira, id)
        )
        tm_saha = cursor.fetchone()
        connection.commit()
        return tm_saha[0] if tm_saha else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def delTm(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        kontrol = GetTmId(id)

        if not kontrol:
            error_res = RestApiTm.error(f"TM silinirken hata oluştu", 500)
            raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

        cursor.execute(
            """
            DELETE
            FROM tm
            WHERE id = %s
            """, (id,)
        )

        connection.commit()

    finally:
        connection.close()

def patchTm(id: int, raw: ScadaTmPatch):
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
            UPDATE tm
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

@tm.get('')
def get_tm():
    try:
        data = GetTm()
        if not data:
            return RestApiTm.error(message="Tm merkezi bulunamadı", code=400)
        else:
            return RestApiTm.ok(data=data, message="BASARILI")

    except Exception as e:
        return e

@tm.get('/{id}')
def get_tm_id(id: int):
    try:
        data = GetTmId(id)
        if not data:
            return RestApiTm.error(message=f"{id} id'li Tm merkezi bulunamadı", code=400)
        else:
            return RestApiTm.ok(data=data, message="BASARILI")

    except Exception as e:
        return e


@tm.post('')
def createTm(raw: ScadaTm, request: Request):
    try:
        data = postTm(
            dm_id=raw.dm_id,
            name=raw.name,
            sira=raw.sira,
        )

        return {
            "success": True,
            "data": data,
        }

    except Exception as e:
        raise e

@tm.put('/{id}')
def updateTm(id: int, raw: ScadaTm, request: Request):
    try:
        tm_up = putTm(id, raw)

        if not tm_up:
            error_res = RestApiTm.error(f"{id} numaralı TM güncellenemedi veya bulunamadı.", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiTm.ok(data=tm_up, message="BASARILI")

    except Exception as e:
        error_res = RestApiTm.error(f"TM güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))


@tm.delete('/{id}')
def delete_tm(id: int):
    try:
        dele = delTm(id)

        return RestApiTm.ok(data=dele, message="BASARILI")

    except Exception as e:
        error_res = RestApiTm.error(f"TM silinirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@tm.patch('/{id}')
def patch_dm(id: int, raw: ScadaTmPatch):
    try:
        updated_id = patchTm(id, raw)

        if not updated_id:
            error_res = RestApiTm.error(message=f"{id} numaralı cihaz bulunamadı veya güncellenemedi.", code=404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiTm.ok(data=updated_id, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiTm.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))

    except Exception as e:
        error_res = RestApiTm.error(message=f"Cihaz güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
                                         code=500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))