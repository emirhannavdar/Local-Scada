from datetime import datetime
from typing import Generic, TypeVar

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from database.database import get_connection

readGroup = APIRouter()

T = TypeVar("T")


class RestApiReadGroup(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    dateTime: datetime = Field(default_factory=datetime.now)
    errorCode: int = 0
    message: str = ""

    @classmethod
    def ok(cls, data: T):
        return cls(
            success=True,
            data=data,
            message="İşlem başarılı"
        )

    @classmethod
    def error(cls, errorCode: int, message: str):
        return cls(
            success=False,
            data=None,
            errorCode=errorCode,
            message=message
        )


class ScadaReadGroup(BaseModel):
    cihaz_id: int
    name: str
    function_code: int
    baslangic_adresi: int
    bitis_adresi: int
    okuma_periyodu_ms: int
    maksimum_register: int
    aktif: bool = True
    aciklama: str


class ScadaReadGroupPatch(BaseModel):
    cihaz_id: int | None = None
    name: str | None = None
    function_code: int | None = None
    baslangic_adresi: int | None = None
    bitis_adresi: int | None = None
    okuma_periyodu_ms: int | None = None
    maksimum_register: int | None = None
    aktif: bool | None = None
    aciklama: str | None = None


def ReadGroup(raw: ScadaReadGroup):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO okuma_grubu (
                    cihaz_id,
                    ad,
                    function_code,
                    baslangic_adresi,
                    bitis_adresi,
                    okuma_periyodu_ms,
                    maksimum_register,
                    aktif,
                    aciklama
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    raw.cihaz_id,
                    raw.name,
                    raw.function_code,
                    raw.baslangic_adresi,
                    raw.bitis_adresi,
                    raw.okuma_periyodu_ms,
                    raw.maksimum_register,
                    raw.aktif,
                    raw.aciklama
                )
            )

            okuma_grup = cursor.fetchone()[0]

            connection.commit()
            return okuma_grup

        except Exception:
            connection.rollback()
            raise


def getReadGroup():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                cihaz_id,
                ad,
                function_code,
                baslangic_adresi,
                bitis_adresi,
                okuma_periyodu_ms,
                maksimum_register,
                aktif,
                aciklama
            FROM okuma_grubu
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "cihaz_id": row[1],
                "name": row[2],
                "function_code": row[3],
                "baslangic_adresi": row[4],
                "bitis_adresi": row[5],
                "okuma_periyodu_ms": row[6],
                "maksimum_register": row[7],
                "aktif": row[8],
                "aciklama": row[9]
            }
            for row in rows
        ]

    finally:
        connection.close()


def getReadGroupId(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                cihaz_id,
                ad,
                function_code,
                baslangic_adresi,
                bitis_adresi,
                okuma_periyodu_ms,
                maksimum_register,
                aktif,
                aciklama
            FROM okuma_grubu
            WHERE id = %s;
            """,
            (id,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "cihaz_id": row[1],
            "name": row[2],
            "function_code": row[3],
            "baslangic_adresi": row[4],
            "bitis_adresi": row[5],
            "okuma_periyodu_ms": row[6],
            "maksimum_register": row[7],
            "aktif": row[8],
            "aciklama": row[9]
        }

    finally:
        connection.close()


def putReadGroup(id: int, raw: ScadaReadGroup):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE okuma_grubu
            SET
                cihaz_id = %s,
                ad = %s,
                function_code = %s,
                baslangic_adresi = %s,
                bitis_adresi = %s,
                okuma_periyodu_ms = %s,
                maksimum_register = %s,
                aktif = %s,
                aciklama = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                raw.cihaz_id,
                raw.name,
                raw.function_code,
                raw.baslangic_adresi,
                raw.bitis_adresi,
                raw.okuma_periyodu_ms,
                raw.maksimum_register,
                raw.aktif,
                raw.aciklama,
                id
            )
        )

        row = cursor.fetchone()

        if not row:
            connection.rollback()
            return None

        connection.commit()
        return row[0]

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delReadGroup(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM okuma_grubu
            WHERE id = %s
            RETURNING id;
            """,
            (id,)
        )

        row = cursor.fetchone()

        if not row:
            connection.rollback()
            return None

        connection.commit()
        return row[0]

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def patchReadGroup(id: int, raw: ScadaReadGroupPatch):
    update_data = raw.model_dump(exclude_unset=True)

    if "name" in update_data:
        update_data["ad"] = update_data.pop("name")

    if not update_data:
        return id

    connection = get_connection()

    try:
        cursor = connection.cursor()

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())

        query = f"""
            UPDATE okuma_grubu
            SET {', '.join(set_clauses)}
            WHERE id = %s
            RETURNING id;
        """

        values.append(id)

        cursor.execute(query, tuple(values))

        row = cursor.fetchone()

        if not row:
            connection.rollback()
            return None

        connection.commit()

        return row[0]

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


@readGroup.get('')
def get_read_group():
    try:
        data = getReadGroup()
        return RestApiReadGroup.ok(data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    500,
                    f"Okuma grubu listelenirken hata oluştu: {str(e)}"
                )
            )
        )


@readGroup.get('/{id}')
def get_read_group_id(id: int):
    try:
        data = getReadGroupId(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiReadGroup.error(
                        404,
                        "Okuma grubu bulunamadı"
                    )
                )
            )

        return RestApiReadGroup.ok(data)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    500,
                    f"Okuma grubu getirilirken hata oluştu: {str(e)}"
                )
            )
        )


@readGroup.post('')
def create_read_group(raw: ScadaReadGroup):
    try:
        data = ReadGroup(raw)
        return RestApiReadGroup.ok(data)

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    400,
                    "Geçersiz cihaz_id"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    500,
                    f"Okuma grubu oluşturulurken hata oluştu: {str(e)}"
                )
            )
        )


@readGroup.put('/{id}')
def update_read_group(id: int, raw: ScadaReadGroup):
    try:
        data = putReadGroup(id, raw)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiReadGroup.error(
                        404,
                        "Okuma grubu bulunamadı"
                    )
                )
            )

        return RestApiReadGroup.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    400,
                    "Geçersiz cihaz_id"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    500,
                    f"Okuma grubu güncellenirken hata oluştu: {str(e)}"
                )
            )
        )


@readGroup.delete('/{id}')
def delete_read_group(id: int):
    try:
        data = delReadGroup(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiReadGroup.error(
                        404,
                        "Okuma grubu bulunamadı"
                    )
                )
            )

        return RestApiReadGroup.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    400,
                    "Okuma grubu başka kayıtlar tarafından kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    500,
                    f"Okuma grubu silinirken hata oluştu: {str(e)}"
                )
            )
        )


@readGroup.patch('/{id}')
def patch_read_group(id: int, raw: ScadaReadGroupPatch):
    try:
        data = patchReadGroup(id, raw)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiReadGroup.error(
                        404,
                        "Okuma grubu bulunamadı"
                    )
                )
            )

        return RestApiReadGroup.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    400,
                    "Geçersiz cihaz_id"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiReadGroup.error(
                    500,
                    f"Okuma grubu güncellenirken hata oluştu: {str(e)}"
                )
            )
        )