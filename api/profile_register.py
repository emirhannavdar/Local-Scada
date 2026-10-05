from datetime import datetime
from typing import TypeVar, Generic, Optional

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection
import psycopg

profile_register = APIRouter()

T = TypeVar("T")


class RestApiProfileRegister(BaseModel, Generic[T]):
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


class ScadaProfileRegister(BaseModel):
    profile_id: int
    register_adresi: int
    function_code: int
    register_sayisi: int
    veri_tipi: str
    byte_order: str
    word_order: str
    olcek: float
    offset_degeri: float
    bit_index: int
    sinyal_sozlugu_id: int
    aciklama: str | None = None


class ScadaProfileRegisterPatch(BaseModel):
    profile_id: int | None = None
    register_adresi: int | None = None
    function_code: int | None = None
    register_sayisi: int | None = None
    veri_tipi: str | None = None
    byte_order: str | None = None
    word_order: str | None = None
    olcek: float | None = None
    offset_degeri: float | None = None
    bit_index: int | None = None
    sinyal_sozlugu_id: int | None = None
    aciklama: str | None = None


def postProfileRegister(raw: ScadaProfileRegister):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO profil_register (
                    profil_id,
                    register_adresi,
                    function_code,
                    register_sayisi,
                    veri_tipi,
                    byte_order,
                    word_order,
                    olcek,
                    offset_degeri,
                    bit_index,
                    sinyal_sozlugu_id,
                    aciklama
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    raw.profile_id,
                    raw.register_adresi,
                    raw.function_code,
                    raw.register_sayisi,
                    raw.veri_tipi,
                    raw.byte_order,
                    raw.word_order,
                    raw.olcek,
                    raw.offset_degeri,
                    raw.bit_index,
                    raw.sinyal_sozlugu_id,
                    raw.aciklama
                )
            )

            profileRegister = cursor.fetchone()[0]

            connection.commit()
            return profileRegister

        except Exception:
            connection.rollback()
            raise


def getProfileRegister():
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id,
                   profil_id,
                   register_adresi,
                   function_code,
                   register_sayisi,
                   veri_tipi,
                   byte_order,
                   word_order,
                   olcek,
                   offset_degeri,
                   bit_index,
                   sinyal_sozlugu_id,
                   aciklama
            FROM profil_register
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return result

    finally:
        connection.close()


def getProfileRegisterId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id,
                   profil_id,
                   register_adresi,
                   function_code,
                   register_sayisi,
                   veri_tipi,
                   byte_order,
                   word_order,
                   olcek,
                   offset_degeri,
                   bit_index,
                   sinyal_sozlugu_id,
                   aciklama
            FROM profil_register
            WHERE id = %s
            """,
            (id,)
        )

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return result

    finally:
        connection.close()


def putProfileRegister(id, raw):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE profil_register
            SET profil_id = %s,
                register_adresi = %s,
                function_code = %s,
                register_sayisi = %s,
                veri_tipi = %s,
                byte_order = %s,
                word_order = %s,
                olcek = %s,
                offset_degeri = %s,
                bit_index = %s,
                sinyal_sozlugu_id = %s,
                aciklama = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                raw.profile_id,
                raw.register_adresi,
                raw.function_code,
                raw.register_sayisi,
                raw.veri_tipi,
                raw.byte_order,
                raw.word_order,
                raw.olcek,
                raw.offset_degeri,
                raw.bit_index,
                raw.sinyal_sozlugu_id,
                raw.aciklama,
                id
            )
        )

        connection.commit()

        row = cursor.fetchone()

        return row[0] if row else None

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delProfileRegister(id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        kontrol = getProfileRegisterId(id)

        if not kontrol:
            error_res = RestApiProfileRegister.error(
                "Profil register silinirken hata oluştu: Profil register bulunamadı",
                404
            )
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(error_res)
            )

        cursor.execute(
            """
            DELETE
            FROM profil_register
            WHERE id = %s
            """,
            (id,)
        )

        connection.commit()

        return {
            "success": True
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def patchProfileRegister(id: int, raw: ScadaProfileRegisterPatch):
    update_data = raw.model_dump(exclude_unset=True)

    if not update_data:
        return id

    connection = get_connection()

    try:
        cursor = connection.cursor()

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())

        query = f"""
            UPDATE profil_register
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


@profile_register.get('')
def get_profile_register():
    try:
        data = getProfileRegister()

        if not data:
            return RestApiProfileRegister.error(
                message="Profil register bulunamadı",
                code=404
            )

        return RestApiProfileRegister.ok(
            data=data,
            message="BASARILI"
        )

    except Exception as e:
        error_res = RestApiProfileRegister.error(
            f"Sistem hatası: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@profile_register.get('/{id}')
def get_profile_register_id(id: int):
    try:
        data = getProfileRegisterId(id)

        if not data:
            return RestApiProfileRegister.error(
                message="Profil register bulunamadı",
                code=404
            )

        return RestApiProfileRegister.ok(
            data=data,
            message="BASARILI"
        )

    except Exception as e:
        error_res = RestApiProfileRegister.error(
            f"Sistem hatası: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@profile_register.post('')
def create_profile_register(raw: ScadaProfileRegister):
    try:
        data = postProfileRegister(raw)

        return RestApiProfileRegister.ok(
            data=data,
            message="BASARILI"
        )

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiProfileRegister.error(
            message=f"Geçersiz veri formatı veya ENUM değeri: {e.diag.message_primary}",
            code=400
        )

        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(error_res)
        )

    except Exception as e:
        error_res = RestApiProfileRegister.error(
            message=f"Profil register kaydedilirken beklenmeyen bir hata oluştu: {str(e)}",
            code=500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@profile_register.put('/{id}')
def update_profile_register(id: int, raw: ScadaProfileRegister):
    try:
        profile_register_up = putProfileRegister(id, raw)

        if not profile_register_up:
            error_res = RestApiProfileRegister.error(
                f"{id} numaralı profil register güncellenemedi veya bulunamadı.",
                404
            )

            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(error_res)
            )

        return RestApiProfileRegister.ok(
            data=profile_register_up,
            message="BASARILI"
        )

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiProfileRegister.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )

        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(error_res)
        )

    except Exception as e:
        error_res = RestApiProfileRegister.error(
            f"Profil register güncellenirken hata oluştu: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@profile_register.delete('/{id}')
def delete_profile_register(id: int):
    try:
        dele = delProfileRegister(id)

        return RestApiProfileRegister.ok(
            data=dele,
            message="BASARILI"
        )

    except HTTPException as http_ex:
        raise http_ex

    except Exception as e:
        error_res = RestApiProfileRegister.error(
            f"Profil register silinirken hata oluştu: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@profile_register.patch('/{id}')
def patch_profile_register(id: int, raw: ScadaProfileRegisterPatch):
    try:
        updated_id = patchProfileRegister(id, raw)

        if not updated_id:
            error_res = RestApiProfileRegister.error(
                message=f"{id} numaralı profil register bulunamadı veya güncellenemedi.",
                code=404
            )

            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(error_res)
            )

        return RestApiProfileRegister.ok(
            data=updated_id,
            message="BASARILI"
        )

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiProfileRegister.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )

        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(error_res)
        )

    except Exception as e:
        error_res = RestApiProfileRegister.error(
            message=f"Profil register güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
            code=500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )