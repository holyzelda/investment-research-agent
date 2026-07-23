from sqlalchemy import DateTime, Integer, Numeric, String

from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM


def test_scrolling_message_orm_maps_table_and_query_indexes():
    table = ScrollingMessageORM.__table__

    assert table.name == "policy_market_scrolling_messages"
    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 255
    assert isinstance(table.c.publish_time.type, DateTime)
    assert isinstance(table.c.rating.type, Numeric)
    assert (table.c.rating.type.precision, table.c.rating.type.scale) == (3, 2)
    assert isinstance(table.c.status.type, Integer)

    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    assert indexes["idx_status_deleted_sort"] == (
        "is_deleted", "status", "sort_order", "rating"
    )
    assert indexes["idx_province"] == ("province",)
    assert indexes["idx_expire_time"] == ("expire_time",)
