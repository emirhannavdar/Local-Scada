from datetime import datetime
from typing import Generic, TypeVar

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from database.database import get_connection

tag = APIRouter()

T = TypeVar("T")


class RestApiTag(BaseModel, Generic[T]):
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


class ScadaTag(BaseModel):
    cihaz_id: int
    sinyal_sozlugu_id: int
    profil_register_id: int
    sinyal_adi: str
    tag_adi: str
    tip: str
    birim: str
    olcek: float
    okuma_sinifi: str
    arsiv_kurali: str
    alarm_sinifi: str
    deadband: float
    aktif: bool = True
    register_id: int


class ScadaTagPatch(BaseModel):
    cihaz_id: int | None = None
    sinyal_sozlugu_id: int | None = None
    profil_register_id: int | None = None
    sinyal_adi: str | None = None
    tag_adi: str | None = None
    tip: str | None = None
    birim: str | None = None
    olcek: float | None = None
    okuma_sinifi: str | None = None
    arsiv_kurali: str | None = None
    alarm_sinifi: str | None = None
    deadband: float | None = None
    aktif: bool | None = None
    register_id: int | None = None


def postTag(raw: ScadaTag):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id, register_id, aktif
                FROM tag
                WHERE cihaz_id = %s
                  AND tag_adi = %s
                LIMIT 1;
                """,
                (raw.cihaz_id, raw.tag_adi)
            )

            existing = cursor.fetchone()

            if existing:
                existing_id = existing[0]
                existing_register_id = existing[1]

                if (
                    existing_register_id is None
                    or existing_register_id == raw.register_id
                ):
                    cursor.execute(
                        """
                        UPDATE tag
                        SET
                            sinyal_sozlugu_id = %s,
                            profil_register_id = %s,
                            sinyal_adi = %s,
                            tip = %s,
                            birim = %s,
                            olcek = %s,
                            okuma_sinifi = %s,
                            arsiv_kurali = %s,
                            alarm_sinifi = %s,
                            deadband = %s,
                            aktif = %s,
                            register_id = %s
                        WHERE id = %s
                        RETURNING id;
                        """,
                        (
                            raw.sinyal_sozlugu_id,
                            raw.profil_register_id,
                            raw.sinyal_adi,
                            raw.tip,
                            raw.birim,
                            raw.olcek,
                            raw.okuma_sinifi,
                            raw.arsiv_kurali,
                            raw.alarm_sinifi,
                            raw.deadband,
                            raw.aktif,
                            raw.register_id,
                            existing_id
                        )
                    )
                    tag_id = cursor.fetchone()[0]
                    connection.commit()
                    return tag_id

                raise ValueError(
                    f"Tag '{raw.tag_adi}' cihaz {raw.cihaz_id} üzerinde "
                    f"register {existing_register_id} ile zaten bağlı"
                )

            cursor.execute(
                """
                INSERT INTO tag (
                    cihaz_id,
                    sinyal_sozlugu_id,
                    profil_register_id,
                    sinyal_adi,
                    tag_adi,
                    tip,
                    birim,
                    olcek,
                    okuma_sinifi,
                    arsiv_kurali,
                    alarm_sinifi,
                    deadband,
                    aktif,
                    register_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    raw.cihaz_id,
                    raw.sinyal_sozlugu_id,
                    raw.profil_register_id,
                    raw.sinyal_adi,
                    raw.tag_adi,
                    raw.tip,
                    raw.birim,
                    raw.olcek,
                    raw.okuma_sinifi,
                    raw.arsiv_kurali,
                    raw.alarm_sinifi,
                    raw.deadband,
                    raw.aktif,
                    raw.register_id
                )
            )

            tag_id = cursor.fetchone()[0]
            connection.commit()
            return tag_id

        except Exception:
            connection.rollback()
            raise


def getTag():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                cihaz_id,
                sinyal_sozlugu_id,
                profil_register_id,
                sinyal_adi,
                tag_adi,
                tip,
                birim,
                olcek,
                okuma_sinifi,
                arsiv_kurali,
                alarm_sinifi,
                deadband,
                aktif,
                register_id
            FROM tag
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "cihaz_id": row[1],
                "sinyal_sozlugu_id": row[2],
                "profil_register_id": row[3],
                "sinyal_adi": row[4],
                "tag_adi": row[5],
                "tip": row[6],
                "birim": row[7],
                "olcek": row[8],
                "okuma_sinifi": row[9],
                "arsiv_kurali": row[10],
                "alarm_sinifi": row[11],
                "deadband": row[12],
                "aktif": row[13],
                "register_id": row[14]
            }
            for row in rows
        ]

    finally:
        connection.close()


def getTagId(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                cihaz_id,
                sinyal_sozlugu_id,
                profil_register_id,
                sinyal_adi,
                tag_adi,
                tip,
                birim,
                olcek,
                okuma_sinifi,
                arsiv_kurali,
                alarm_sinifi,
                deadband,
                aktif,
                register_id
            FROM tag
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
            "sinyal_sozlugu_id": row[2],
            "profil_register_id": row[3],
            "sinyal_adi": row[4],
            "tag_adi": row[5],
            "tip": row[6],
            "birim": row[7],
            "olcek": row[8],
            "okuma_sinifi": row[9],
            "arsiv_kurali": row[10],
            "alarm_sinifi": row[11],
            "deadband": row[12],
            "aktif": row[13],
            "register_id": row[14]
        }

    finally:
        connection.close()


def putTag(id: int, raw: ScadaTag):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE tag
            SET
                cihaz_id = %s,
                sinyal_sozlugu_id = %s,
                profil_register_id = %s,
                sinyal_adi = %s,
                tag_adi = %s,
                tip = %s,
                birim = %s,
                olcek = %s,
                okuma_sinifi = %s,
                arsiv_kurali = %s,
                alarm_sinifi = %s,
                deadband = %s,
                aktif = %s,
                register_id = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                raw.cihaz_id,
                raw.sinyal_sozlugu_id,
                raw.profil_register_id,
                raw.sinyal_adi,
                raw.tag_adi,
                raw.tip,
                raw.birim,
                raw.olcek,
                raw.okuma_sinifi,
                raw.arsiv_kurali,
                raw.alarm_sinifi,
                raw.deadband,
                raw.aktif,
                raw.register_id,
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


def delTag(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM tag
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


def patchTag(id: int, raw: ScadaTagPatch):
    update_data = raw.model_dump(exclude_unset=True)

    if not update_data:
        return id

    connection = get_connection()

    try:
        cursor = connection.cursor()

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())

        query = f"""
            UPDATE tag
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


@tag.get('')
def get_tag():
    try:
        data = getTag()
        return RestApiTag.ok(data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiTag.error(
                    500,
                    f"Tag listelenirken hata oluştu: {str(e)}"
                )
            )
        )


@tag.get('/{id}')
def get_tag_id(id: int):
    try:
        data = getTagId(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiTag.error(
                        404,
                        "Tag bulunamadı"
                    )
                )
            )

        return RestApiTag.ok(data)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiTag.error(
                    500,
                    f"Tag getirilirken hata oluştu: {str(e)}"
                )
            )
        )


@tag.post('')
def create_tag(raw: ScadaTag):
    try:
        data = postTag(raw)
        return RestApiTag.ok(data)

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Geçersiz cihaz, sinyal sözlüğü, profil register veya register bilgisi"
                )
            )
        )

    except psycopg.errors.InvalidTextRepresentation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Geçersiz veri formatı veya ENUM değeri"
                )
            )
        )

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=jsonable_encoder(
                RestApiTag.error(409, str(e))
            )
        )

    except psycopg.errors.UniqueViolation as e:
        raise HTTPException(
            status_code=409,
            detail=jsonable_encoder(
                RestApiTag.error(
                    409,
                    f"Tag benzersizlik çakışması: {str(e)}"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiTag.error(
                    500,
                    f"Tag oluşturulurken hata oluştu: {str(e)}"
                )
            )
        )


@tag.put('/{id}')
def update_tag(id: int, raw: ScadaTag):
    try:
        data = putTag(id, raw)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiTag.error(
                        404,
                        "Tag bulunamadı"
                    )
                )
            )

        return RestApiTag.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Geçersiz cihaz, sinyal sözlüğü, profil register veya register bilgisi"
                )
            )
        )

    except psycopg.errors.InvalidTextRepresentation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Güncelleme sırasında geçersiz veri formatı veya ENUM hatası"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiTag.error(
                    500,
                    f"Tag güncellenirken hata oluştu: {str(e)}"
                )
            )
        )


@tag.delete('/{id}')
def delete_tag(id: int):
    try:
        data = delTag(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiTag.error(
                        404,
                        "Tag bulunamadı"
                    )
                )
            )

        return RestApiTag.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Tag başka kayıtlar tarafından kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiTag.error(
                    500,
                    f"Tag silinirken hata oluştu: {str(e)}"
                )
            )
        )


@tag.patch('/{id}')
def patch_tag(id: int, raw: ScadaTagPatch):
    try:
        data = patchTag(id, raw)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiTag.error(
                        404,
                        "Tag bulunamadı"
                    )
                )
            )

        return RestApiTag.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Geçersiz cihaz, sinyal sözlüğü, profil register veya register bilgisi"
                )
            )
        )

    except psycopg.errors.InvalidTextRepresentation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiTag.error(
                    400,
                    "Güncelleme sırasında geçersiz veri formatı veya ENUM hatası"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiTag.error(
                    500,
                    f"Tag güncellenirken hata oluştu: {str(e)}"
                )
            )
        )