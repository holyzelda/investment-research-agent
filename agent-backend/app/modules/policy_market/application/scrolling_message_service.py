from collections import Counter
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.policy_market.domain.models import (
    MarketOverview,
    ScrollingMessage,
    TopicOption,
    parse_tags,
)
from app.modules.policy_market.infrastructure.persistence.orm import ScrollingMessageORM


class ScrollingMessageService:
    async def list_messages(
        self,
        session: AsyncSession,
        *,
        province: str = "all",
        start_date: date | None = None,
        end_date: date | None = None,
        topic: str = "all",
        now: datetime | None = None,
    ) -> list[ScrollingMessage]:
        query_time = now or datetime.now()
        current_start, current_end = self._date_window(start_date, end_date)
        statement = (
            select(ScrollingMessageORM)
            .where(
                *self._active_conditions(query_time, province=province),
                *self._window_conditions(current_start, current_end),
            )
            .order_by(
                ScrollingMessageORM.sort_order.desc(),
                ScrollingMessageORM.rating.desc(),
                ScrollingMessageORM.publish_time.desc(),
                ScrollingMessageORM.id.desc(),
            )
        )
        rows = (await session.execute(statement)).scalars().all()
        if topic != "all":
            rows = [row for row in rows if topic in parse_tags(row.tags)]
        return [
            ScrollingMessage(
                id=row.id,
                title=row.title,
                summary=row.summary,
                link_url=row.link_url,
                province=row.province,
                publish_time=row.publish_time,
                tags=row.tags,
            )
            for row in rows
        ]

    async def get_overview(
        self,
        session: AsyncSession,
        *,
        province: str = "all",
        start_date: date | None = None,
        end_date: date | None = None,
        topic: str = "all",
        now: datetime | None = None,
    ) -> MarketOverview:
        query_time = now or datetime.now()
        current_start, current_end = self._date_window(start_date, end_date)
        base_conditions = self._active_conditions(query_time, province=province)

        topic_rows = await self._query_rows(
            session,
            [*base_conditions, *self._window_conditions(current_start, current_end)],
        )
        topic_options = self._top_topics(topic_rows)
        current_rows = self._filter_topic(topic_rows, topic)

        trend_percent = None
        if current_start is not None and current_end is not None:
            previous_start, previous_end = self._previous_window(current_start, current_end)
            previous_rows = await self._query_rows(
                session,
                [
                    *base_conditions,
                    *self._window_conditions(previous_start, previous_end),
                ],
            )
            previous_count = len(self._filter_topic(previous_rows, topic))
            if previous_count:
                trend_percent = round((len(current_rows) - previous_count) / previous_count * 100, 1)

        return MarketOverview(
            total=len(current_rows),
            trend_percent=trend_percent,
            range_label=self._range_label(province, start_date, end_date),
            topic_options=topic_options,
        )

    @staticmethod
    def _active_conditions(query_time: datetime, *, province: str = "all") -> list:
        conditions = [
            ScrollingMessageORM.is_deleted == 0,
            ScrollingMessageORM.status == 1,
            or_(
                ScrollingMessageORM.expire_time.is_(None),
                ScrollingMessageORM.expire_time > query_time,
            ),
        ]
        if province != "all":
            conditions.append(ScrollingMessageORM.province == province)
        return conditions

    @staticmethod
    async def _query_rows(session: AsyncSession, conditions: list) -> list[ScrollingMessageORM]:
        statement = select(ScrollingMessageORM).where(and_(*conditions))
        return (await session.execute(statement)).scalars().all()

    @staticmethod
    def _filter_topic(rows: list[ScrollingMessageORM], topic: str) -> list[ScrollingMessageORM]:
        if topic == "all":
            return rows
        return [row for row in rows if topic in parse_tags(row.tags)]

    @staticmethod
    def _top_topics(rows: list[ScrollingMessageORM]) -> list[TopicOption]:
        counts = Counter(tag for row in rows for tag in parse_tags(row.tags))
        return [
            TopicOption(value=value, count=count)
            for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        ]

    @staticmethod
    def _date_window(start_date: date | None, end_date: date | None) -> tuple[datetime | None, datetime | None]:
        if start_date is None or end_date is None:
            return None, None
        return datetime.combine(start_date, time.min), datetime.combine(end_date + timedelta(days=1), time.min)

    @staticmethod
    def _previous_window(current_start: datetime, current_end: datetime) -> tuple[datetime, datetime]:
        duration = current_end - current_start
        return current_start - duration, current_start

    @staticmethod
    def _window_conditions(start: datetime | None, end: datetime | None) -> list:
        if start is None or end is None:
            return []
        return [
            ScrollingMessageORM.publish_time.is_not(None),
            ScrollingMessageORM.publish_time >= start,
            ScrollingMessageORM.publish_time < end,
        ]

    @staticmethod
    def _range_label(province: str, start_date: date | None, end_date: date | None) -> str:
        province_label = "全部省份" if province == "all" else province
        period_label = "全部时间" if start_date is None or end_date is None else f"{start_date:%Y/%m/%d} 至 {end_date:%Y/%m/%d}"
        return f"{province_label} · {period_label}"
