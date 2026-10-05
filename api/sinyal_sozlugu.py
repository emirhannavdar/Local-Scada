from datetime import datetime
from typing import TypeVar, Generic, Optional

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from database.database import get_connection
import psycopg

signalDict = APIRouter()

T = TypeVar("T")


class RestApiSignalDict(BaseModel, Generic[T]):
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


class ScadaSinyalDict(BaseModel):
    sinyal_adi: str
    aciklama: str
    cihaz_tipi: str
    veri_tipi: str
    birim: str
    min_deger: float
    max_deger: float
    alarm_sinifi: str
    arsiv_kurali: str
    okuma_sinifi: str
    deadband: float
    periyot_saniye: int
    gosterim_formati: str
    aktif: bool = True


class ScadaSinyalDictPatch(BaseModel):
    sinyal_adi: str | None = None
    aciklama: str | None = None
    cihaz_tipi: str | None = None
    veri_tipi: str | None = None
    birim: str | None = None
    min_deger: float | None = None
    max_deger: float | None = None
    alarm_sinifi: str | None = None
    arsiv_kurali: str | None = None
    okuma_sinifi: str | None = None
    deadband: float | None = None
    periyot_saniye: int | None = None
    gosterim_formati: str | None = None
    aktif: bool | None = None


def sinyalSozlugu(raw: ScadaSinyalDict):
    with get_connection() as connection:
        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO sinyal_sozlugu (
                    sinyal_adi,
                    aciklama,
                    cihaz_tipi,
                    veri_tipi,
                    birim,
                    min_deger,
                    max_deger,
                    alarm_sinifi,
                    arsiv_kurali,
                    okuma_sinifi,
                    deadband,
                    periyot_saniye,
                    gosterim_formati,
                    aktif
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
                (
                    raw.sinyal_adi,
                    raw.aciklama,
                    raw.cihaz_tipi,
                    raw.veri_tipi,
                    raw.birim,
                    raw.min_deger,
                    raw.max_deger,
                    raw.alarm_sinifi,
                    raw.arsiv_kurali,
                    raw.okuma_sinifi,
                    raw.deadband,
                    raw.periyot_saniye,
                    raw.gosterim_formati,
                    raw.aktif
                )
            )

            sinyal_sozlugu_id = cursor.fetchone()[0]

            connection.commit()
            return sinyal_sozlugu_id

        except Exception:
            connection.rollback()
            raise


def getSinyalSozlugu():
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id,
                   sinyal_adi,
                   aciklama,
                   cihaz_tipi,
                   veri_tipi,
                   birim,
                   min_deger,
                   max_deger,
                   alarm_sinifi,
                   arsiv_kurali,
                   okuma_sinifi,
                   deadband,
                   periyot_saniye,
                   gosterim_formati,
                   aktif
            FROM sinyal_sozlugu
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return result

    finally:
        connection.close()


def getSinyalSozluguId(id):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id,
                   sinyal_adi,
                   aciklama,
                   cihaz_tipi,
                   veri_tipi,
                   birim,
                   min_deger,
                   max_deger,
                   alarm_sinifi,
                   arsiv_kurali,
                   okuma_sinifi,
                   deadband,
                   periyot_saniye,
                   gosterim_formati,
                   aktif
            FROM sinyal_sozlugu
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


def putSinyalSozlugu(id, raw):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE sinyal_sozlugu
            SET sinyal_adi = %s,
                aciklama = %s,
                cihaz_tipi = %s,
                veri_tipi = %s,
                birim = %s,
                min_deger = %s,
                max_deger = %s,
                alarm_sinifi = %s,
                arsiv_kurali = %s,
                okuma_sinifi = %s,
                deadband = %s,
                periyot_saniye = %s,
                gosterim_formati = %s,
                aktif = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                raw.sinyal_adi,
                raw.aciklama,
                raw.cihaz_tipi,
                raw.veri_tipi,
                raw.birim,
                raw.min_deger,
                raw.max_deger,
                raw.alarm_sinifi,
                raw.arsiv_kurali,
                raw.okuma_sinifi,
                raw.deadband,
                raw.periyot_saniye,
                raw.gosterim_formati,
                raw.aktif,
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


def delSinyalSozlugu(id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        kontrol = getSinyalSozluguId(id)

        if not kontrol:
            error_res = RestApiSignalDict.error(
                "Sinyal sözlüğü silinirken hata oluştu: Sinyal sözlüğü bulunamadı",
                404
            )
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(error_res)
            )

        cursor.execute(
            """
            DELETE
            FROM sinyal_sozlugu
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


def patchSinyalSozlugu(id: int, raw: ScadaSinyalDictPatch):
    update_data = raw.model_dump(exclude_unset=True)

    if not update_data:
        return id

    connection = get_connection()

    try:
        cursor = connection.cursor()

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())

        query = f"""
            UPDATE sinyal_sozlugu
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


@signalDict.get('')
def get_signal_dict():
    try:
        data = getSinyalSozlugu()

        if not data:
            return RestApiSignalDict.error(
                message="Sinyal sözlüğü bulunamadı",
                code=404
            )

        return RestApiSignalDict.ok(
            data=data,
            message="BASARILI"
        )

    except Exception as e:
        error_res = RestApiSignalDict.error(
            f"Sistem hatası: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@signalDict.get('/{id}')
def get_signal_dict_id(id: int):
    try:
        data = getSinyalSozluguId(id)

        if not data:
            return RestApiSignalDict.error(
                message="Sinyal sözlüğü bulunamadı",
                code=404
            )

        return RestApiSignalDict.ok(
            data=data,
            message="BASARILI"
        )

    except Exception as e:
        error_res = RestApiSignalDict.error(
            f"Sistem hatası: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@signalDict.post('')
def create_signal_dict(raw: ScadaSinyalDict):
    try:
        data = sinyalSozlugu(raw)

        return RestApiSignalDict.ok(
            data=data,
            message="BASARILI"
        )

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiSignalDict.error(
            message=f"Geçersiz veri formatı veya ENUM değeri: {e.diag.message_primary}",
            code=400
        )

        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(error_res)
        )

    except Exception as e:
        error_res = RestApiSignalDict.error(
            message=f"Sinyal sözlüğü kaydedilirken beklenmeyen bir hata oluştu: {str(e)}",
            code=500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@signalDict.put('/{id}')
def update_signal_dict(id: int, raw: ScadaSinyalDict):
    try:
        signal_up = putSinyalSozlugu(id, raw)

        if not signal_up:
            error_res = RestApiSignalDict.error(
                f"{id} numaralı sinyal sözlüğü güncellenemedi veya bulunamadı.",
                404
            )

            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(error_res)
            )

        return RestApiSignalDict.ok(
            data=signal_up,
            message="BASARILI"
        )

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiSignalDict.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )

        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(error_res)
        )

    except Exception as e:
        error_res = RestApiSignalDict.error(
            f"Sinyal sözlüğü güncellenirken hata oluştu: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@signalDict.delete('/{id}')
def delete_signal_dict(id: int):
    try:
        dele = delSinyalSozlugu(id)

        return RestApiSignalDict.ok(
            data=dele,
            message="BASARILI"
        )

    except HTTPException as http_ex:
        raise http_ex

    except Exception as e:
        error_res = RestApiSignalDict.error(
            f"Sinyal sözlüğü silinirken hata oluştu: {str(e)}",
            500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )


@signalDict.patch('/{id}')
def patch_signal_dict(id: int, raw: ScadaSinyalDictPatch):
    try:
        updated_id = patchSinyalSozlugu(id, raw)

        if not updated_id:
            error_res = RestApiSignalDict.error(
                message=f"{id} numaralı sinyal sözlüğü bulunamadı veya güncellenemedi.",
                code=404
            )

            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(error_res)
            )

        return RestApiSignalDict.ok(
            data=updated_id,
            message="BASARILI"
        )

    except psycopg.errors.InvalidTextRepresentation as e:
        error_res = RestApiSignalDict.error(
            message=f"Güncelleme sırasında geçersiz veri formatı veya ENUM hatası: {e.diag.message_primary}",
            code=400
        )

        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(error_res)
        )

    except Exception as e:
        error_res = RestApiSignalDict.error(
            message=f"Sinyal sözlüğü güncellenirken beklenmeyen bir hata oluştu: {str(e)}",
            code=500
        )

        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(error_res)
        )