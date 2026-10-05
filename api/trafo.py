from datetime import datetime
from typing import TypeVar, Generic, Optional

import psycopg
from fastapi import APIRouter, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection

trafo = APIRouter()

T = TypeVar("T")

class RestApiTrafo(BaseModel, Generic[T]):
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


class ScadaTrafo(BaseModel):
    tm_id: int
    name: str
    guc_kva: float
    oran: str

class ScadaTrafoPatch(BaseModel):
    tm_id: int | None = None
    name: str | None = None
    guc_kva: float | None = None
    oran: str | None = None


def postTrafo(
        tm_id: int,
        name: str,
        guc_kva: float,
        oran: str
):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO trafo (tm_id, ad, guc_kva, oran)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """, (tm_id, name, guc_kva, oran)
            )
            sahaTrafo = cursor.fetchone()
            saha_post_trafo = sahaTrafo[0]

            connection.commit()
            return saha_post_trafo

        except Exception as e:
            connection.rollback()
            raise e

def GetTrafo():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                id,
                tm_id,
                ad,
                guc_kva,
                oran
            FROM trafo
            ORDER BY id;
            """
        )
        rows = cursor.fetchall()

        trfo = []

        for row in rows:
            trfo.append({
                "id": row[0],
                "tm_id": row[1],
                "ad": row[2],
                "guc_kva": row[3],
                "oran": row[4]
            })

        return trfo

    finally:
        connection.close()

def GetTrafoId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id,
                   tm_id,
                   ad,
                   guc_kva,
                   oran
            FROM trafo
            WHERE id = %s
            ORDER BY id;
            """, (id, )
        )
        rows = cursor.fetchall()

        trfo_id = []

        for row in rows:
            trfo_id.append({
                "id": row[0],
                "tm_id": row[1],
                "ad": row[2],
                "guc_kva": row[3],
                "oran": row[4]
            })
        print(trfo_id)
        return trfo_id

    finally:
        connection.close()

def delTrafo(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        kontrol = GetTrafoId(id)

        if not kontrol:
            error_res = RestApiTrafo.error(f"Cihaz silinirken hata oluştu", 500)
            raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

        cursor.execute(
            """
            DELETE
            FROM trafo
            WHERE id = %s
            """, (id,)
        )

        connection.commit()

    finally:
        connection.close()


def putTrafo(id, raw: ScadaTrafo):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE trafo
            SET tm_id = %s,
                ad      = %s,
                guc_kva    = %s,
                oran = %s
            WHERE id = %s RETURNING id;
            """, (raw.tm_id, raw.name, raw.guc_kva, raw.oran , id)
        )
        trafo_saha = cursor.fetchone()
        connection.commit()
        return trafo_saha[0] if trafo_saha else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def patchTrafo(id: int, raw: ScadaTrafoPatch):
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
            UPDATE trafo
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

@trafo.get('')
def get_trafo():
    try:
        data = GetTrafo()
        if not data:
            return RestApiTrafo.error(message="Dagıtım merkezi bulunamadı", code=400)
        else:
            return RestApiTrafo.ok(data=data, message="BASARILI")

    except Exception as e:
        return e

@trafo.get('/{id}')
def get_trafo(id: int):
    try:
        data = GetTrafoId(id)
        if not data:
            return RestApiTrafo.error(message="Dagıtım merkezi bulunamadı", code=400)
        else:
            return RestApiTrafo.ok(data=data, message="BASARILI")

    except Exception as e:
        return e

@trafo.post('')
def create_Trafo(raw: ScadaTrafo, request: Request):
    try:
        data = postTrafo(
            tm_id=raw.tm_id,
            name=raw.name,
            guc_kva=raw.guc_kva,
            oran=raw.oran
        )

        return {
            "success": True,
            "data": data,
        }

    except Exception as e:
        raise e

@trafo.delete('/{id}')
def delete_trafo(id: int):
    try:
        dele = delTrafo(id)

        return RestApiTrafo.ok(data=dele, message="BASARILI")

    except Exception as e:
        error_res = RestApiTrafo.error(f"Cihaz silinirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@trafo.put('/{id}')
def updateTrafo(id: int, raw: ScadaTrafo, request: Request):
    try:
        trafo_up = putTrafo(id, raw)

        if not trafo_up:
            error_res = RestApiTrafo.error(f"{id} numaralı cihaz güncellenemedi veya bulunamadı.", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiTrafo.ok(data=trafo_up, message="BASARILI")

    except Exception as e:
        error_res = RestApiTrafo.error(f"Cihaz güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@trafo.patch('/{id}')
def patch_trafo(id: int, raw: ScadaTrafoPatch):
    try:
        updated_id = patchTrafo(id, raw)

        if not updated_id:
            error_res = RestApiTrafo.error(message=f"{id} numaralı cihaz bulunamadı veya güncellenemedi.", code=404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiTrafo.ok(data=updated_id, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiTrafo.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))

    except Exception as e:
        error_res = RestApiTrafo.error(message=f"Cihaz güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
                                         code=500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))