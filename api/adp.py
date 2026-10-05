from datetime import datetime
from typing import Generic, Optional, TypeVar

import psycopg
from fastapi import APIRouter, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection

adp = APIRouter()

T = TypeVar("T")

class RestApiAdp(BaseModel, Generic[T]):
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


class ScadaAdp(BaseModel):
    trafo_id: int
    name: str

class ScadaAdpPatch(BaseModel):
    trafo_id: int | None = None
    name: str | None = None

def postAdp(
        trafo_id: int,
        name: str
):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO adp (trafo_id, ad)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (trafo_id, name)
            )

            adp_id = cursor.fetchone()[0]

            connection.commit()
            return adp_id

        except Exception:
            connection.rollback()
            raise

def getAdp():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id,
                   trafo_id,
                   ad
            FROM adp
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        adp_id = []

        for row in rows:
            adp_id.append({
                "id": row[0],
                "trafo_id": row[1],
                "ad": row[2]
            })

        return adp_id

    finally:
        connection.close()


def getAdpId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id,
                   trafo_id,
                   ad
            FROM adp
            WHERE id = %s
            ORDER BY id;
            """, (id,)
        )
        rows = cursor.fetchall()

        adp_id = []

        for row in rows:
            adp_id.append({
                "id": row[0],
                "trafo_id": row[1],
                "ad": row[2]
            })

        return adp_id
    finally:
        connection.close()

def putAdp(id: int, raw: ScadaAdp):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE adp
            SET trafo_id = %s,
                ad      = %s
            WHERE id = %s RETURNING id;
            """, (raw.trafo_id, raw.name, id)
        )
        trafo_saha = cursor.fetchone()
        connection.commit()
        return trafo_saha[0] if trafo_saha else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delAdp(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        kontrol = getAdpId(id)

        if not kontrol:
            error_res = RestApiAdp.error(f"Cihaz silinirken hata oluştu", 500)
            raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

        cursor.execute(
            """
            DELETE FROM adp WHERE id = %s
            """, (id, )
        )

        connection.commit()

    finally:
        connection.close()

def patchAdp(id, raw):
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
                UPDATE adp
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

@adp.get('')
def get_dm():
    try:
        data = getAdp()
        if not data:
            return RestApiAdp.error(message="ADP merkezi bulunamadı", code=400)
        else:
            return RestApiAdp.ok(data=data, message="BASARILI")

    except Exception as e:
        return e

@adp.get('/{id}')
def get_dm_id(id: int):
    try:
        data = getAdpId(id)
        if not data:
            return RestApiAdp.error(message="ADP merkezi bulunamadı", code=400)
        else:
            return RestApiAdp.ok(data=data, message="BASARILI")

    except Exception as e:
        return e

@adp.post('')
def create_adp(raw: ScadaAdp):
    data = postAdp(
        trafo_id=raw.trafo_id,
        name=raw.name
    )

    return {
        "success": True,
        "data": data
    }

@adp.put('/{id}')
def updateAdp(id: int, raw: ScadaAdp, request: Request):
    try:
        adp_up = putAdp(id, raw)

        if not adp_up:
            error_res = RestApiAdp.error(f"{id} numaralı ADP güncellenemedi veya bulunamadı.", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiAdp.ok(data=adp_up, message="BASARILI")

    except Exception as e:
        error_res = RestApiAdp.error(f"ADP güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@adp.delete('/{id}')
def delete_adp(id: int):
    try:
        dele = delAdp(id)

        return RestApiAdp.ok(data=dele, message="BASARILI")

    except Exception as e:
        error_res = RestApiAdp.error(f"ADP silinirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@adp.patch('/{id}')
def patch_device(id: int, raw: ScadaAdpPatch):
    try:
        updated_id = patchAdp(id, raw)

        if not updated_id:
            error_res = RestApiAdp.error(message=f"{id} numaralı ADP bulunamadı veya güncellenemedi.", code=404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiAdp.ok(data=updated_id, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        # PATCH isteğinde de geçersiz ENUM veya veri tipi gönderilirse yakalar
        error_res = RestApiAdp.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))

    except Exception as e:
        error_res = RestApiAdp.error(message=f"ADP güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
                                         code=500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))