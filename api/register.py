from datetime import datetime
from typing import Generic, TypeVar

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from database.database import get_connection

register = APIRouter()

T = TypeVar("T")


class RestApiRegister(BaseModel, Generic[T]):
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


class ScadaRegister(BaseModel):
    cihaz_id: int
    profil_register_id: int
    sinyal_sozlugu_id: int
    name: str
    baslangic_adresi: int
    register_sayisi: int
    function_code: int
    veri_tipi: str
    word_order: str
    byte_order: str
    birim: str
    carpan: float
    min_deger: float
    max_deger: float
    aktif: bool = True
    aciklama: str | None = None
    okuma_grubu_id: int


class ScadaRegisterPatch(BaseModel):
    cihaz_id: int | None = None
    profil_register_id: int | None = None
    sinyal_sozlugu_id: int | None = None
    name: str | None = None
    baslangic_adresi: int | None = None
    register_sayisi: int | None = None
    function_code: int | None = None
    veri_tipi: str | None = None
    word_order: str | None = None
    byte_order: str | None = None
    birim: str | None = None
    carpan: float | None = None
    min_deger: float | None = None
    max_deger: float | None = None
    aktif: bool | None = None
    aciklama: str | None = None
    okuma_grubu_id: int | None = None


def postRegister(raw: ScadaRegister):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO register (
                    cihaz_id,
                    profil_register_id,
                    sinyal_sozlugu_id,
                    ad,
                    baslangic_adresi,
                    register_sayisi,
                    function_code,
                    veri_tipi,
                    word_order,
                    byte_order,
                    birim,
                    carpan,
                    min_deger,
                    max_deger,
                    aktif,
                    aciklama,
                    okuma_grubu_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    raw.cihaz_id,
                    raw.profil_register_id,
                    raw.sinyal_sozlugu_id,
                    raw.name,
                    raw.baslangic_adresi,
                    raw.register_sayisi,
                    raw.function_code,
                    raw.veri_tipi,
                    raw.word_order,
                    raw.byte_order,
                    raw.birim,
                    raw.carpan,
                    raw.min_deger,
                    raw.max_deger,
                    raw.aktif,
                    raw.aciklama,
                    raw.okuma_grubu_id
                )
            )

            register_id = cursor.fetchone()[0]

            connection.commit()
            return register_id

        except Exception:
            connection.rollback()
            raise


def getRegister():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                cihaz_id,
                profil_register_id,
                sinyal_sozlugu_id,
                ad,
                baslangic_adresi,
                register_sayisi,
                function_code,
                veri_tipi,
                word_order,
                byte_order,
                birim,
                carpan,
                min_deger,
                max_deger,
                aktif,
                aciklama,
                okuma_grubu_id
            FROM register
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "cihaz_id": row[1],
                "profil_register_id": row[2],
                "sinyal_sozlugu_id": row[3],
                "name": row[4],
                "baslangic_adresi": row[5],
                "register_sayisi": row[6],
                "function_code": row[7],
                "veri_tipi": row[8],
                "word_order": row[9],
                "byte_order": row[10],
                "birim": row[11],
                "carpan": row[12],
                "min_deger": row[13],
                "max_deger": row[14],
                "aktif": row[15],
                "aciklama": row[16],
                "okuma_grubu_id": row[17]
            }
            for row in rows
        ]

    finally:
        connection.close()


def getRegisterId(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                cihaz_id,
                profil_register_id,
                sinyal_sozlugu_id,
                ad,
                baslangic_adresi,
                register_sayisi,
                function_code,
                veri_tipi,
                word_order,
                byte_order,
                birim,
                carpan,
                min_deger,
                max_deger,
                aktif,
                aciklama,
                okuma_grubu_id
            FROM register
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
            "profil_register_id": row[2],
            "sinyal_sozlugu_id": row[3],
            "name": row[4],
            "baslangic_adresi": row[5],
            "register_sayisi": row[6],
            "function_code": row[7],
            "veri_tipi": row[8],
            "word_order": row[9],
            "byte_order": row[10],
            "birim": row[11],
            "carpan": row[12],
            "min_deger": row[13],
            "max_deger": row[14],
            "aktif": row[15],
            "aciklama": row[16],
            "okuma_grubu_id": row[17]
        }

    finally:
        connection.close()


def putRegister(id: int, raw: ScadaRegister):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE register
            SET
                cihaz_id = %s,
                profil_register_id = %s,
                sinyal_sozlugu_id = %s,
                ad = %s,
                baslangic_adresi = %s,
                register_sayisi = %s,
                function_code = %s,
                veri_tipi = %s,
                word_order = %s,
                byte_order = %s,
                birim = %s,
                carpan = %s,
                min_deger = %s,
                max_deger = %s,
                aktif = %s,
                aciklama = %s,
                okuma_grubu_id = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                raw.cihaz_id,
                raw.profil_register_id,
                raw.sinyal_sozlugu_id,
                raw.name,
                raw.baslangic_adresi,
                raw.register_sayisi,
                raw.function_code,
                raw.veri_tipi,
                raw.word_order,
                raw.byte_order,
                raw.birim,
                raw.carpan,
                raw.min_deger,
                raw.max_deger,
                raw.aktif,
                raw.aciklama,
                raw.okuma_grubu_id,
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


def delRegister(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM register
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


def patchRegister(id: int, raw: ScadaRegisterPatch):
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
            UPDATE register
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


@register.get('')
def get_register():
    try:
        data = getRegister()
        return RestApiRegister.ok(data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    500,
                    f"Register listelenirken hata oluştu: {str(e)}"
                )
            )
        )


@register.get('/{id}')
def get_register_id(id: int):
    try:
        data = getRegisterId(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiRegister.error(
                        404,
                        "Register bulunamadı"
                    )
                )
            )

        return RestApiRegister.ok(data)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    500,
                    f"Register getirilirken hata oluştu: {str(e)}"
                )
            )
        )


@register.post('')
def create_register(raw: ScadaRegister):
    try:
        data = postRegister(raw)
        return RestApiRegister.ok(data)

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Geçersiz cihaz, profil register, sinyal sözlüğü veya okuma grubu bilgisi"
                )
            )
        )

    except psycopg.errors.InvalidTextRepresentation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Geçersiz veri formatı veya ENUM değeri"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    500,
                    f"Register oluşturulurken hata oluştu: {str(e)}"
                )
            )
        )


@register.put('/{id}')
def update_register(id: int, raw: ScadaRegister):
    try:
        data = putRegister(id, raw)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiRegister.error(
                        404,
                        "Register bulunamadı"
                    )
                )
            )

        return RestApiRegister.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Geçersiz cihaz, profil register, sinyal sözlüğü veya okuma grubu bilgisi"
                )
            )
        )

    except psycopg.errors.InvalidTextRepresentation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Güncelleme sırasında geçersiz veri formatı veya ENUM hatası"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    500,
                    f"Register güncellenirken hata oluştu: {str(e)}"
                )
            )
        )


@register.delete('/{id}')
def delete_register(id: int):
    try:
        data = delRegister(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiRegister.error(
                        404,
                        "Register bulunamadı"
                    )
                )
            )

        return RestApiRegister.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Register başka kayıtlar tarafından kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    500,
                    f"Register silinirken hata oluştu: {str(e)}"
                )
            )
        )


@register.patch('/{id}')
def patch_register(id: int, raw: ScadaRegisterPatch):
    try:
        data = patchRegister(id, raw)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiRegister.error(
                        404,
                        "Register bulunamadı"
                    )
                )
            )

        return RestApiRegister.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Geçersiz cihaz, profil register, sinyal sözlüğü veya okuma grubu bilgisi"
                )
            )
        )

    except psycopg.errors.InvalidTextRepresentation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    400,
                    "Güncelleme sırasında geçersiz veri formatı veya ENUM hatası"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiRegister.error(
                    500,
                    f"Register güncellenirken hata oluştu: {str(e)}"
                )
            )
        )