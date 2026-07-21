"""联络线地图 HTTP 接口。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from json import JSONDecodeError

from fastapi import APIRouter, Depends, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.core.response import ok
from app.infrastructure.database.session import get_db_session
from app.modules.tie_line_map.application.power_import_service import (
    PowerImportRecord,
    PowerImportService,
)
from app.modules.tie_line_map.application.tie_line_service import TieLineService
from app.modules.tie_line_map.interface.power_import_parser import parse_excel_import
from app.modules.tie_line_map.interface.serializers import (
    serialize_line_detail,
    serialize_lines,
)

router = APIRouter(prefix="/ir/tie-lines", tags=["tie-line-map"])
_service = TieLineService()
_power_import_service = PowerImportService()


class PowerJsonRecordReq(BaseModel):
    """JSON 宽表单条功率记录。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    data_date: date = Field(alias="dataDate")
    line_name: str = Field(alias="lineName", min_length=1, max_length=128)
    voltage_text: str = Field(alias="voltageText", min_length=1, max_length=64)
    powers: dict[str, Decimal | None]

    @field_validator("powers")
    @classmethod
    def validate_finite_powers(cls, values: dict[str, Decimal | None]):
        for time_column, value in values.items():
            if value is not None and not value.is_finite():
                raise ValueError(f"{time_column} 功率必须为有限数值")
        return values


class PowerJsonImportReq(BaseModel):
    """JSON 宽表导入请求。"""

    model_config = ConfigDict(extra="forbid")

    records: list[PowerJsonRecordReq] = Field(min_length=1)


@router.get("")
async def list_tie_lines(session: AsyncSession = Depends(get_db_session)):
    lines = await _service.list_lines(session)
    return ok(serialize_lines(lines))


@router.post("/power/import")
async def import_tie_line_power(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """按 JSON 或 Excel 文件导入功率宽表，并覆盖同业务键的旧记录。"""

    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type == "application/json":
        try:
            payload = PowerJsonImportReq.model_validate(await request.json())
        except JSONDecodeError as error:
            raise ValidationException("JSON 请求体格式无效") from error
        except ValidationError as error:
            details = "; ".join(
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            )
            raise ValidationException(details or "JSON 参数验证失败") from error
        records = [
            PowerImportRecord(
                data_date=item.data_date,
                line_name=item.line_name.strip(),
                voltage_text=item.voltage_text.strip(),
                powers=item.powers,
            )
            for item in payload.records
        ]
    elif content_type == "multipart/form-data":
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile) and not (
            hasattr(upload, "filename") and hasattr(upload, "read")
        ):
            raise ValidationException("请使用 file 字段上传 Excel 文件")
        records = await parse_excel_import(upload)
    else:
        raise ValidationException("仅支持 application/json 或 multipart/form-data")

    try:
        result = await _power_import_service.import_records(session, records)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return ok({
        "receivedCount": result.received_count,
        "deletedCount": result.deleted_count,
        "insertedCount": result.inserted_count,
        "matchedLineCount": result.matched_line_count,
    })


@router.get("/{line_id}")
async def get_tie_line(line_id: int, session: AsyncSession = Depends(get_db_session)):
    line = await _service.get_line(session, line_id=line_id)
    return ok(serialize_line_detail(line))
