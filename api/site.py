from typing import Generic, TypeVar
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from psycopg.errors import UniqueViolation, ForeignKeyViolation

from database.database import get_connection


site = APIRouter()

T = TypeVar("T")


class RestApiSite(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    dateTime: datetime = Field(default_factory=datetime.now)
    errorCode: int = 0
    message: str = ""


class ScadaSite(BaseModel):
    name: str
    kod: str | None = None
    kurulu_guc_kwp: float | None = None
    konum: str | None = None
    zaman_dilimi: str = "Europe/Istanbul"
    aktif: bool = True
    varsayilan_carpan: float = 1


class ScadaSitePatch(BaseModel):
    name: str | None = None
    kod: str | None = None
    kurulu_guc_kwp: float | None = None
    konum: str | None = None
    zaman_dilimi: str | None = None
    aktif: bool | None = None
    varsayilan_carpan: float | None = None


def row_to_dict(row):
    return {
        "id": row[0],
        "name": row[1],
        "kod": row[2],
        "kurulu_guc_kwp": (
            float(row[3])
            if row[3] is not None
            else None
        ),
        "konum": row[4],
        "zaman_dilimi": row[5],
        "aktif": row[6],
        "created_at": row[7],
        "updated_at": row[8],
        "varsayilan_carpan": (
            float(row[9])
            if row[9] is not None
            else None
        )
    }


def postSite(data: ScadaSite):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO saha
            (
                ad,
                kod,
                kurulu_guc_kwp,
                konum,
                zaman_dilimi,
                aktif,
                varsayilan_carpan
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                ad,
                kod,
                kurulu_guc_kwp,
                konum,
                zaman_dilimi,
                aktif,
                created_at,
                updated_at,
                varsayilan_carpan
            """,
            (
                data.name,
                data.kod,
                data.kurulu_guc_kwp,
                data.konum,
                data.zaman_dilimi,
                data.aktif,
                data.varsayilan_carpan
            )
        )

        row = cursor.fetchone()

        connection.commit()

        return row_to_dict(row)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def getSite():
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
                created_at,
                updated_at,
                varsayilan_carpan
            FROM saha
            ORDER BY id
            """
        )

        rows = cursor.fetchall()

        return [
            row_to_dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def getSiteId(id: int):
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
                created_at,
                updated_at,
                varsayilan_carpan
            FROM saha
            WHERE id = %s
            """,
            (id,)
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return row_to_dict(row)

    finally:
        connection.close()


def putSite(
    id: int,
    data: ScadaSite
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE saha
            SET
                ad = %s,
                kod = %s,
                kurulu_guc_kwp = %s,
                konum = %s,
                zaman_dilimi = %s,
                aktif = %s,
                varsayilan_carpan = %s,
                updated_at = now()
            WHERE id = %s
            RETURNING
                id,
                ad,
                kod,
                kurulu_guc_kwp,
                konum,
                zaman_dilimi,
                aktif,
                created_at,
                updated_at,
                varsayilan_carpan
            """,
            (
                data.name,
                data.kod,
                data.kurulu_guc_kwp,
                data.konum,
                data.zaman_dilimi,
                data.aktif,
                data.varsayilan_carpan,
                id
            )
        )

        row = cursor.fetchone()

        connection.commit()

        if row is None:
            return None

        return row_to_dict(row)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def patchSite(
    id: int,
    data: ScadaSitePatch
):
    connection = get_connection()

    try:
        current = getSiteId(id)

        if current is None:
            return None

        values = data.model_dump(
            exclude_unset=True
        )

        if not values:
            return current

        field_map = {
            "name": "ad",
            "kod": "kod",
            "kurulu_guc_kwp": "kurulu_guc_kwp",
            "konum": "konum",
            "zaman_dilimi": "zaman_dilimi",
            "aktif": "aktif",
            "varsayilan_carpan": "varsayilan_carpan"
        }

        set_parts = []
        params = []

        for field, value in values.items():
            column = field_map[field]

            set_parts.append(
                f"{column} = %s"
            )

            params.append(value)

        set_parts.append(
            "updated_at = now()"
        )

        params.append(id)

        cursor = connection.cursor()

        cursor.execute(
            f"""
            UPDATE saha
            SET {", ".join(set_parts)}
            WHERE id = %s
            RETURNING
                id,
                ad,
                kod,
                kurulu_guc_kwp,
                konum,
                zaman_dilimi,
                aktif,
                created_at,
                updated_at,
                varsayilan_carpan
            """,
            params
        )

        row = cursor.fetchone()

        connection.commit()

        if row is None:
            return None

        return row_to_dict(row)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delSite(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM saha
            WHERE id = %s
            RETURNING id
            """,
            (id,)
        )

        row = cursor.fetchone()

        connection.commit()

        if row is None:
            return None

        return {
            "id": row[0]
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


@site.get("")
def Sites():
    try:
        data = getSite()

        return RestApiSite(
            success=True,
            data=data,
            message="İşlem başarılı"
        )

    except Exception as e:
        return RestApiSite(
            success=False,
            errorCode=500,
            message=str(e)
        )


@site.get("/{id}")
def SiteId(id: int):
    try:
        data = getSiteId(id)

        if data is None:
            return RestApiSite(
                success=False,
                errorCode=404,
                message="Saha bulunamadı"
            )

        return RestApiSite(
            success=True,
            data=data,
            message="İşlem başarılı"
        )

    except Exception as e:
        return RestApiSite(
            success=False,
            errorCode=500,
            message=str(e)
        )


@site.post("")
def SitePost(data: ScadaSite):
    try:
        result = postSite(data)

        return RestApiSite(
            success=True,
            data=result,
            message="Saha oluşturuldu"
        )

    except UniqueViolation:
        return RestApiSite(
            success=False,
            errorCode=409,
            message="Bu saha zaten mevcut"
        )

    except Exception as e:
        return RestApiSite(
            success=False,
            errorCode=500,
            message=str(e)
        )


@site.put("/{id}")
def SitePut(
    id: int,
    data: ScadaSite
):
    try:
        result = putSite(
            id,
            data
        )

        if result is None:
            return RestApiSite(
                success=False,
                errorCode=404,
                message="Saha bulunamadı"
            )

        return RestApiSite(
            success=True,
            data=result,
            message="Saha güncellendi"
        )

    except Exception as e:
        return RestApiSite(
            success=False,
            errorCode=500,
            message=str(e)
        )


@site.patch("/{id}")
def SitePatch(
    id: int,
    data: ScadaSitePatch
):
    try:
        result = patchSite(
            id,
            data
        )

        if result is None:
            return RestApiSite(
                success=False,
                errorCode=404,
                message="Saha bulunamadı"
            )

        return RestApiSite(
            success=True,
            data=result,
            message="Saha güncellendi"
        )

    except Exception as e:
        return RestApiSite(
            success=False,
            errorCode=500,
            message=str(e)
        )


@site.delete("/{id}")
def SiteDelete(id: int):
    try:
        result = delSite(id)

        if result is None:
            return RestApiSite(
                success=False,
                errorCode=404,
                message="Saha bulunamadı"
            )

        return RestApiSite(
            success=True,
            data=result,
            message="Saha silindi"
        )

    except ForeignKeyViolation:
        return RestApiSite(
            success=False,
            errorCode=409,
            message="Bu sahaya bağlı kayıtlar bulunduğu için silinemiyor"
        )

    except Exception as e:
        return RestApiSite(
            success=False,
            errorCode=500,
            message=str(e)
        )