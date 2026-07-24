from calendar import monthrange
from collections import Counter
from datetime import datetime

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
        period: str = "all",
        topic: str = "all",
        now: datetime | None = None,
    ) -> list[ScrollingMessage]:
        query_time = now or datetime.now()
        current_start, current_end = self._period_window(period, query_time)
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
        period: str = "all",
        topic: str = "all",
        now: datetime | None = None,
    ) -> MarketOverview:
        query_time = now or datetime.now()
        current_start, current_end = self._period_window(period, query_time)
        base_conditions = self._active_conditions(query_time, province=province)

        topic_rows = await self._query_rows(
            session,
            [*base_conditions, *self._window_conditions(current_start, current_end)],
        )
        topic_options = self._top_topics(topic_rows)
        current_rows = self._filter_topic(topic_rows, topic)

        trend_percent = None
        if period != "all":
            previous_start, previous_end = self._previous_window(period, current_start)
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
            range_label=self._range_label(province, period),
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
    def _period_window(period: str, now: datetime) -> tuple[datetime | None, datetime | None]:
        if period == "all":
            return None, None
        if period == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now
        return ScrollingMessageService._shift_months(now, -3), now

    @staticmethod
    def _previous_window(period: str, current_start: datetime | None) -> tuple[datetime, datetime]:
        if period == "month":
            previous_start = ScrollingMessageService._shift_months(current_start, -1)
            return previous_start, current_start
        previous_start = ScrollingMessageService._shift_months(current_start, -3)
        return previous_start, current_start

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
    def _shift_months(value: datetime, months: int) -> datetime:
        target_month = value.month + months
        target_year = value.year + (target_month - 1) // 12
        target_month = (target_month - 1) % 12 + 1
        target_day = min(value.day, monthrange(target_year, target_month)[1])
        return value.replace(year=target_year, month=target_month, day=target_day)

    @staticmethod
    def _range_label(province: str, period: str) -> str:
        province_label = "全部省份" if province == "all" else province
        period_label = {"all": "全部时间", "month": "本月", "quarter": "近三个月"}[period]
        return f"{province_label} · {period_label}"
