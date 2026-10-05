from datetime import datetime
from typing import Generic, TypeVar

import psycopg
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from database.database import get_connection


serialLine = APIRouter()

T = TypeVar("T")


class RestApiSerialLine(BaseModel, Generic[T]):
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


class ScadaSerialLine(BaseModel):
    name: str
    port: str
    baudrate: int | None = None
    databits: int = 8
    stopbits: int = 1
    parity: str = "NONE"
    aktif: bool = True


class ScadaSerialLinePatch(BaseModel):
    name: str | None = None
    port: str | None = None
    baudrate: int | None = None
    databits: int | None = None
    stopbits: int | None = None
    parity: str | None = None
    aktif: bool | None = None


def postSerialLine(raw: ScadaSerialLine):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO seri_hat (
                ad,
                port,
                baudrate,
                databits,
                stopbits,
                parity,
                aktif
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id;
            """,
            (
                raw.name,
                raw.port,
                raw.baudrate,
                raw.databits,
                raw.stopbits,
                raw.parity,
                raw.aktif
            )
        )

        row = cursor.fetchone()

        connection.commit()

        return row[0]

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def getSerialLine():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                ad,
                port,
                baudrate,
                databits,
                stopbits,
                parity,
                aktif
            FROM seri_hat
            ORDER BY id;
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "name": row[1],
                "port": row[2],
                "baudrate": row[3],
                "databits": row[4],
                "stopbits": row[5],
                "parity": row[6],
                "aktif": row[7]
            }
            for row in rows
        ]

    finally:
        connection.close()


def getSerialLineId(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                ad,
                port,
                baudrate,
                databits,
                stopbits,
                parity,
                aktif
            FROM seri_hat
            WHERE id = %s;
            """,
            (id,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "port": row[2],
            "baudrate": row[3],
            "databits": row[4],
            "stopbits": row[5],
            "parity": row[6],
            "aktif": row[7]
        }

    finally:
        connection.close()


def putSerialLine(
    id: int,
    raw: ScadaSerialLine
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE seri_hat
            SET
                ad = %s,
                port = %s,
                baudrate = %s,
                databits = %s,
                stopbits = %s,
                parity = %s,
                aktif = %s
            WHERE id = %s
            RETURNING id;
            """,
            (
                raw.name,
                raw.port,
                raw.baudrate,
                raw.databits,
                raw.stopbits,
                raw.parity,
                raw.aktif,
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


def delSerialLine(id: int):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM seri_hat
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


def patchSerialLine(
    id: int,
    raw: ScadaSerialLinePatch
):
    update_data = raw.model_dump(
        exclude_unset=True
    )

    if "name" in update_data:
        update_data["ad"] = update_data.pop(
            "name"
        )

    if not update_data:
        return id

    connection = get_connection()

    try:
        cursor = connection.cursor()

        set_clauses = [
            f"{key} = %s"
            for key in update_data.keys()
        ]

        values = list(
            update_data.values()
        )

        query = f"""
            UPDATE seri_hat
            SET {', '.join(set_clauses)}
            WHERE id = %s
            RETURNING id;
        """

        values.append(id)

        cursor.execute(
            query,
            tuple(values)
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


@serialLine.get('')
def get_serial_line():
    try:
        data = getSerialLine()

        return RestApiSerialLine.ok(data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    500,
                    f"Seri hat listelenirken hata oluştu: {str(e)}"
                )
            )
        )


@serialLine.get('/{id}')
def get_serial_line_id(id: int):
    try:
        data = getSerialLineId(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiSerialLine.error(
                        404,
                        "Seri hat bulunamadı"
                    )
                )
            )

        return RestApiSerialLine.ok(data)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    500,
                    f"Seri hat getirilirken hata oluştu: {str(e)}"
                )
            )
        )


@serialLine.post('')
def create_serial_line(
    raw: ScadaSerialLine
):
    try:
        data = postSerialLine(raw)

        return RestApiSerialLine.ok(data)

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    400,
                    "Bu seri hat adı zaten kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    500,
                    f"Seri hat oluşturulurken hata oluştu: {str(e)}"
                )
            )
        )


@serialLine.put('/{id}')
def update_serial_line(
    id: int,
    raw: ScadaSerialLine
):
    try:
        data = putSerialLine(
            id,
            raw
        )

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiSerialLine.error(
                        404,
                        "Seri hat bulunamadı"
                    )
                )
            )

        return RestApiSerialLine.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    400,
                    "Bu seri hat adı zaten kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    500,
                    f"Seri hat güncellenirken hata oluştu: {str(e)}"
                )
            )
        )


@serialLine.delete('/{id}')
def delete_serial_line(id: int):
    try:
        data = delSerialLine(id)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiSerialLine.error(
                        404,
                        "Seri hat bulunamadı"
                    )
                )
            )

        return RestApiSerialLine.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    400,
                    "Seri hat bir cihaz tarafından kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    500,
                    f"Seri hat silinirken hata oluştu: {str(e)}"
                )
            )
        )


@serialLine.patch('/{id}')
def patch_serial_line(
    id: int,
    raw: ScadaSerialLinePatch
):
    try:
        data = patchSerialLine(
            id,
            raw
        )

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=jsonable_encoder(
                    RestApiSerialLine.error(
                        404,
                        "Seri hat bulunamadı"
                    )
                )
            )

        return RestApiSerialLine.ok(data)

    except HTTPException:
        raise

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    400,
                    "Bu seri hat adı zaten kullanılıyor"
                )
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=jsonable_encoder(
                RestApiSerialLine.error(
                    500,
                    f"Seri hat güncellenirken hata oluştu: {str(e)}"
                )
            )
        )