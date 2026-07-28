from app.modules.index_map.infrastructure.persistence.orm import (
    IndexMapPeriodORM,
    IndexMapProvinceORM,
)


def test_index_map_tables_have_period_province_unique_key_and_query_indexes():
    assert IndexMapPeriodORM.__tablename__ == "ir_index_map_period"
    assert IndexMapProvinceORM.__tablename__ == "ir_index_map_province"
    assert {column.name for column in IndexMapProvinceORM.__table__.columns} >= {
        "id", "period", "province_code", "province_name", "map_name", "index_score",
        "grade", "opened", "rank", "annualized_return", "detail_payload", "updated_at",
    }
    assert any(
        index.unique and set(index.columns.keys()) == {"period", "province_code"}
        for index in IndexMapProvinceORM.__table__.indexes
    )
    assert any(
        set(index.columns.keys()) == {"period", "rank"}
        for index in IndexMapProvinceORM.__table__.indexes
    )
