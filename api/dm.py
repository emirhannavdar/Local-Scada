from datetime import datetime
from typing import TypeVar, Generic, Optional

import psycopg
from fastapi import APIRouter, Request,HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection

dm = APIRouter()

T = TypeVar("T")

class RestApiDm(BaseModel, Generic[T]):
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

class ScadaDm(BaseModel):
    saha_id:int
    name: str
    sira: int

class ScadaDmPatch(BaseModel):
    saha_id:int | None = None
    name: str | None = None
    sira: int | None = None



def getDm():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                saha_id,
                ad,
                sira
            FROM dm
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "saha_id": row[1],
                "name": row[2],
                "sira": row[3]
            }
            for row in rows
        ]

    finally:
        connection.close()



def postDm(
        saha_id: int,
        name: str,
        sira: int,
):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO dm (saha_id, ad, sira)
                VALUES (%s, %s, %s) RETURNING *;
                """,
                (saha_id, name, sira)
            )
            sahaDm = cursor.fetchone()
            saha_post_id = sahaDm[0]

            connection.commit()
            return saha_post_id

        except Exception as e:
            connection.rollback()
            raise e


def getDmId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                dm.id,
                dm.saha_id,
                dm.ad,
                dm.sira,
                sh.*
            FROM dm dm
            LEFT JOIN saha sh ON dm.saha_id = sh.id
            WHERE dm.id = %s
            ORDER BY dm.id;
            """, (id,)
        )
        rows = cursor.fetchone()

        return rows
    finally:
        connection.close()

def delDm(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        kontrol = getDmId(id)

        if not kontrol:
            error_res = RestApiDm.error(f"Cihaz silinirken hata oluştu", 500)
            raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

        cursor.execute(
            """
            DELETE FROM dm WHERE id = %s
            """, (id, )
        )

        connection.commit()

    finally:
        connection.close()

def putDm(id, raw: ScadaDm):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dm
            SET saha_id = %s, ad = %s, sira = %s
            WHERE id = %s RETURNING id;
            """, (raw.saha_id, raw.name, raw.sira, id)
        )
        dm_saha = cursor.fetchone()
        connection.commit()
        return dm_saha[0] if dm_saha else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def patchDm(id: int, raw: ScadaDmPatch):
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
            UPDATE dm
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

@dm.get("")
def get_dm():
    try:
        data = getDm()

        return RestApiDm.ok(
            data=data,
            message="BASARILI"
        )

    except Exception as e:
        error_res = RestApiDm.error(
            message=f"Dağıtım merkezleri alınırken hata oluştu: {str(e)}",
            code=500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )

@dm.get('/{id}')
def get_dm_id(id: int):
    try:
        data = getDmId(id)
        if not data:
            return RestApiDm.error(message="Dagıtım merkezi bulunamadı", code=400)
        else:
            return RestApiDm.ok(data=data, message="BASARILI")

    except Exception as e:
        return e


@dm.post('')
def createDm(raw: ScadaDm, request: Request):
    try:
        data = postDm(raw.saha_id, raw.name, raw.sira)
        return {
            "success": True,
            "data": data,
        }
    except Exception:
        return {
            "success": False
        }
@dm.put('/{id}')
def updateDm(id: int, raw: ScadaDm, request: Request):
    try:
        dm_up = putDm(id, raw)

        if not dm_up:
            error_res = RestApiDm.error(f"{id} numaralı cihaz güncellenemedi veya bulunamadı.", 404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiDm.ok(data=dm_up, message="BASARILI")

    except Exception as e:
        error_res = RestApiDm.error(f"Cihaz güncellenirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))

@dm.delete('/{id}')
def delete_dm(id: int):
    try:
        dele = delDm(id)

        return RestApiDm.ok(data=dele, message="BASARILI")

    except Exception as e:
        error_res = RestApiDm.error(f"Cihaz silinirken hata oluştu: {str(e)}", 500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))


@dm.patch('/{id}')
def patch_dm(id: int, raw: ScadaDmPatch):
    try:
        updated_id = patchDm(id, raw)

        if not updated_id:
            error_res = RestApiDm.error(message=f"{id} numaralı cihaz bulunamadı veya güncellenemedi.", code=404)
            raise HTTPException(status_code=404, detail=jsonable_encoder(error_res))

        return RestApiDm.ok(data=updated_id, message="BASARILI")

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiDm.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )
        raise HTTPException(status_code=400, detail=jsonable_encoder(error_res))

    except Exception as e:
        error_res = RestApiDm.error(message=f"Cihaz güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
                                         code=500)
        raise HTTPException(status_code=500, detail=jsonable_encoder(error_res))