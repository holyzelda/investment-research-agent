#!/usr/bin/env python3
"""抓取北极星栏目新闻，导出 Excel 并可写入 MySQL。"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

try:
    from .database_config import load_database_config
except ImportError:
    from database_config import load_database_config


SECTION_CONFIGS = {
    "chuneng_policy": {
        "name": "储能政策",
        "source": "北极星储能网",
        "base_url": "https://chuneng.bjx.com.cn/zc/",
        "keywords": ("虚拟电厂", "征求意见稿", "储能"),
        "file_prefix": "北极星储能政策",
    },
    "shoudian_policy": {
        "name": "电力市场政策",
        "source": "北极星售电网",
        "base_url": "https://shoudian.bjx.com.cn/zc/",
        "keywords": ("细则", "方案", "电力市场"),
        "file_prefix": "北极星电力市场政策",
    },
    "shoudian_data": {
        "name": "电力市场数据",
        "source": "北极星售电网",
        "base_url": "https://shoudian.bjx.com.cn/sj/",
        "keywords": ("全社会", "月报", "现货"),
        "file_prefix": "北极星电力市场数据",
    },
}
CREATOR = "bjx_policy_crawler"
PROVINCE_ALIASES = {
    "北京": "北京",
    "天津": "天津",
    "上海": "上海",
    "重庆": "重庆",
    "河北": "河北",
    "山西": "山西",
    "辽宁": "辽宁",
    "吉林": "吉林",
    "黑龙江": "黑龙江",
    "江苏": "江苏",
    "浙江": "浙江",
    "安徽": "安徽",
    "福建": "福建",
    "江西": "江西",
    "山东": "山东",
    "河南": "河南",
    "湖北": "湖北",
    "湖南": "湖南",
    "广东": "广东",
    "海南": "海南",
    "四川": "四川",
    "贵州": "贵州",
    "云南": "云南",
    "陕西": "陕西",
    "甘肃": "甘肃",
    "青海": "青海",
    "台湾": "台湾",
    "内蒙古": "内蒙古",
    "广西": "广西",
    "西藏": "西藏",
    "宁夏": "宁夏",
    "新疆": "新疆",
    "香港": "香港",
    "澳门": "澳门",
}
ARTICLE_PATTERN = re.compile(
    r'<li>\s*<a\s+href="(?P<url>https://news\.bjx\.com\.cn/html/\d{8}/\d+\.shtml)"'
    r'[^>]*title="(?P<title>[^"]+)"[^>]*>.*?</a>\s*'
    r'<span>(?P<date>\d{4}-\d{2}-\d{2})</span>\s*</li>',
    re.IGNORECASE | re.DOTALL,
)
DETAIL_KEYWORDS_PATTERN = re.compile(
    r'<span[^>]*id=["\']key_word["\'][^>]*>.*?关键词：(?P<body>.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)
DETAIL_KEYWORD_LINK_PATTERN = re.compile(
    r'<em[^>]*>\s*<a\b[^>]*>(?P<keyword>.*?)</a>\s*</em>',
    re.IGNORECASE | re.DOTALL,
)


def parse_args() -> argparse.Namespace:
    yesterday = date.today() - timedelta(days=1)
    parser = argparse.ArgumentParser(
        description="抓取北极星栏目新闻，按日期和标题关键词导出 Excel 或写入 MySQL。"
    )
    parser.add_argument(
        "--section",
        choices=("all", *SECTION_CONFIGS),
        default="chuneng_policy",
        help="栏目配置，默认 chuneng_policy；使用 all 一次抓取三个栏目。",
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=yesterday,
        help="目标日期，格式 YYYY-MM-DD；默认取昨日。",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=None,
        help="标题过滤关键词，任一命中即保留。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="最多导出的记录数，默认 30。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="输出文件路径；默认按栏目生成对应的 Excel 文件。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Excel 输出目录，默认使用当前目录；可与 --section all 一起使用。",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="最多检查的列表页数，默认 20。",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="将结果写入 MySQL；连接信息通过项目统一 Settings（含 Nacos）获取。",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="不生成 Excel，通常与 --write-db 一起使用。",
    )
    return parser.parse_args()


def fetch_page(base_url: str, page_number: int, retries: int = 3) -> str:
    url = base_url if page_number == 1 else f"{base_url}{page_number}/"
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/138.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == retries:
                raise RuntimeError(f"请求失败：{url}（已重试 {retries} 次）") from exc
            time.sleep(attempt)
    raise RuntimeError(f"请求失败：{url}")


def parse_articles(page_html: str) -> list[dict[str, str]]:
    articles = []
    for match in ARTICLE_PATTERN.finditer(page_html):
        articles.append(
            {
                "title": html.unescape(match.group("title")).strip(),
                "url": match.group("url"),
                "date": match.group("date"),
            }
        )
    return articles


def collect_articles(
    base_url: str,
    target_date: date,
    keywords: list[str],
    limit: int,
    max_pages: int,
) -> list[dict[str, str]]:
    target_text = target_date.isoformat()
    daily_articles: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for page_number in range(1, max_pages + 1):
        articles = parse_articles(fetch_page(base_url, page_number))
        if not articles:
            raise RuntimeError(f"第 {page_number} 页未解析到新闻，网站结构可能已变化。")

        for article in articles:
            if article["date"] != target_text or article["url"] in seen_urls:
                continue
            matched = [keyword for keyword in keywords if keyword in article["title"]]
            article["keywords"] = "、".join(matched)
            daily_articles.append(article)
            seen_urls.add(article["url"])

        page_dates = [article["date"] for article in articles]
        if target_text in page_dates and min(page_dates) < target_text:
            break
        if max(page_dates) < target_text:
            break

        time.sleep(0.3)

    if len(daily_articles) <= 10:
        return daily_articles
    filtered_articles = [article for article in daily_articles if article["keywords"]]
    return filtered_articles[:limit]


def fetch_detail_keywords(url: str, retries: int = 2) -> list[str]:
    """从详情页标题下方的关键词区域提取网站原始关键词。"""
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/138.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                page_html = response.read().decode("utf-8", errors="replace")
            match = DETAIL_KEYWORDS_PATTERN.search(page_html)
            if not match:
                return fetch_detail_keywords_via_browser(url)
            keywords = []
            for keyword_match in DETAIL_KEYWORD_LINK_PATTERN.finditer(
                match.group("body")
            ):
                keyword = re.sub(r"\s+", " ", html.unescape(keyword_match.group("keyword"))).strip()
                if keyword and keyword not in keywords:
                    keywords.append(keyword)
            return keywords
        except (HTTPError, URLError, TimeoutError):
            if attempt == retries:
                return []
            time.sleep(attempt)
    return []


def fetch_detail_keywords_via_browser(url: str) -> list[str]:
    """通过本机 web-access 浏览器代理读取被 WAF 拦截的详情页。"""
    target_id = None
    try:
        new_request = Request(
            "http://localhost:3456/new",
            data=url.encode("utf-8"),
            method="POST",
        )
        with urlopen(new_request, timeout=20) as response:
            target_id = json.loads(response.read().decode("utf-8"))["targetId"]

        javascript = (
            "JSON.stringify(Array.from(document.querySelectorAll("
            "'#key_word em a')).map(function(a) { return a.textContent.trim(); }))"
        )
        eval_url = "http://localhost:3456/eval?target=" + quote(target_id, safe="")
        eval_request = Request(
            eval_url,
            data=javascript.encode("utf-8"),
            method="POST",
        )
        with urlopen(eval_request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        keywords = json.loads(payload.get("value", "[]"))
        return list(dict.fromkeys(keyword.strip() for keyword in keywords if keyword.strip()))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return []
    finally:
        if target_id:
            try:
                close_url = "http://localhost:3456/close?target=" + quote(
                    target_id, safe=""
                )
                with urlopen(close_url, timeout=10):
                    pass
            except OSError:
                pass


def enrich_detail_keywords(records: list[dict[str, str]]) -> None:
    """补充详情页关键词；详情页受限时保留列表页过滤关键词。"""
    for record in records:
        detail_keywords = fetch_detail_keywords(record["url"])
        if detail_keywords:
            record["detail_keywords"] = "、".join(detail_keywords)
        else:
            record["detail_keywords"] = record["keywords"]
        time.sleep(0.2)


def extract_province(title: str) -> str | None:
    """从标题中识别省级行政区，无法明确识别时返回空。"""
    for alias in sorted(PROVINCE_ALIASES, key=len, reverse=True):
        if alias in title:
            return PROVINCE_ALIASES[alias]
    return None


def prepare_database_records(
    records: list[dict[str, str]], section: dict[str, object]
) -> list[dict[str, object]]:
    prepared = []
    for record in records:
        filter_keywords = [
            keyword for keyword in record["keywords"].split("、") if keyword
        ]
        detail_keywords = [
            keyword
            for keyword in record.get("detail_keywords", record["keywords"]).split("、")
            if keyword
        ]
        prepared.append(
            {
                "title": record["title"][:255],
                "summary": None,
                "link_url": record["url"],
                "province": extract_province(record["title"]),
                "publish_time": datetime.strptime(record["date"], "%Y-%m-%d"),
                "expire_time": None,
                "status": 1,
                "rating": 0.00,
                "sort_order": 0,
                "tags": ",".join(detail_keywords),
                "extra_data": json.dumps(
                    {
                        "source": section["source"],
                        "source_section": section["name"],
                        "detail_keywords": detail_keywords,
                        "filter_keywords": filter_keywords,
                        "list_date": record["date"],
                    },
                    ensure_ascii=False,
                ),
                "is_deleted": 0,
                "created_by": CREATOR,
                "updated_by": CREATOR,
            }
        )
    return prepared


def write_database(
    records: list[dict[str, str]],
    section: dict[str, object],
    database_config: dict[str, object],
) -> tuple[int, int]:
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError(
            "缺少 PyMySQL，请先执行：python -m pip install -r requirements.txt"
        ) from exc

    select_sql = (
        "SELECT id FROM policy_market_scrolling_messages "
        "WHERE link_url = %s AND is_deleted = 0 LIMIT 1"
    )
    insert_sql = """
        INSERT INTO policy_market_scrolling_messages
            (title, summary, link_url, province, publish_time, expire_time,
             tags, extra_data, created_by, updated_by)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, CAST(%s AS JSON), %s, %s)
    """
    inserted = 0
    skipped = 0
    connection = None
    try:
        connection = pymysql.connect(**database_config)
        with connection.cursor() as cursor:
            for record in prepare_database_records(records, section):
                cursor.execute(select_sql, (record["link_url"],))
                if cursor.fetchone():
                    skipped += 1
                    continue
                cursor.execute(
                    insert_sql,
                    (
                        record["title"],
                        record["summary"],
                        record["link_url"],
                        record["province"],
                        record["publish_time"],
                        record["expire_time"],
                        record["tags"],
                        record["extra_data"],
                        record["created_by"],
                        record["updated_by"],
                    ),
                )
                inserted += 1
        connection.commit()
    except Exception as exc:
        if connection is not None:
            connection.rollback()
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"数据库写入失败：{exc}") from exc
    finally:
        if connection is not None:
            connection.close()
    return inserted, skipped


def write_excel(
    records: list[dict[str, str]], output_path: Path, section: dict[str, object]
) -> None:
    database_records = prepare_database_records(records, section)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "待入库数据"
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:N{max(1, len(database_records) + 1)}"

    headers = (
        "title",
        "summary",
        "link_url",
        "province",
        "publish_time",
        "expire_time",
        "status",
        "rating",
        "sort_order",
        "tags",
        "extra_data",
        "is_deleted",
        "created_by",
        "updated_by",
    )
    worksheet.append(headers)
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for record in database_records:
        worksheet.append(tuple(record[header] for header in headers))
        row_number = worksheet.max_row
        worksheet.cell(row_number, 5).number_format = "yyyy-mm-dd hh:mm:ss"
        worksheet.cell(row_number, 8).number_format = "0.00"
        url_cell = worksheet.cell(row_number, 3)
        url_cell.hyperlink = record["link_url"]
        url_cell.style = "Hyperlink"
        for cell in worksheet[row_number]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    column_widths = {
        "A": 70,
        "B": 12,
        "C": 55,
        "D": 14,
        "E": 21,
        "F": 21,
        "G": 10,
        "H": 10,
        "I": 12,
        "J": 20,
        "K": 65,
        "L": 12,
        "M": 22,
        "N": 22,
    }
    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width
    worksheet.row_dimensions[1].height = 24

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def main() -> int:
    args = parse_args()
    if args.section == "all" and args.output:
        print("错误：--section all 时不能指定单个 --output 文件。", file=sys.stderr)
        return 2
    if args.limit < 1 or args.limit > 30:
        print("错误：--limit 必须在 1 到 30 之间。", file=sys.stderr)
        return 2
    if args.max_pages < 1:
        print("错误：--max-pages 必须大于 0。", file=sys.stderr)
        return 2
    custom_keywords = [keyword.strip() for keyword in (args.keywords or []) if keyword.strip()]
    if args.keywords is not None and not custom_keywords:
        print("错误：至少需要一个非空关键词。", file=sys.stderr)
        return 2

    section_keys = list(SECTION_CONFIGS) if args.section == "all" else [args.section]
    all_results: list[tuple[str, int, int]] = []
    try:
        database_config = load_database_config() if args.write_db else None
        for section_key in section_keys:
            section = SECTION_CONFIGS[section_key]
            keywords = custom_keywords or list(section["keywords"])
            records = collect_articles(
                section["base_url"],
                args.target_date,
                keywords,
                args.limit,
                args.max_pages,
            )
            enrich_detail_keywords(records)
            if not args.no_excel:
                output_path = args.output or args.output_dir / (
                    f"{section['file_prefix']}_{args.target_date.isoformat()}.xlsx"
                )
                write_excel(records, output_path, section)
            inserted = skipped = 0
            if args.write_db:
                assert database_config is not None
                inserted, skipped = write_database(records, section, database_config)
            all_results.append((section_key, len(records), inserted))
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"目标日期：{args.target_date.isoformat()}")
    for section_key, count, inserted in all_results:
        section = SECTION_CONFIGS[section_key]
        keywords = custom_keywords or list(section["keywords"])
        print(f"栏目：{section['name']}（{section['base_url']}）")
        print(f"过滤关键词：{'、'.join(keywords)}")
        print(f"符合条件记录数：{count}")
        if not args.no_excel:
            output_path = args.output or args.output_dir / (
                f"{section['file_prefix']}_{args.target_date.isoformat()}.xlsx"
            )
            print(f"Excel 输出文件：{output_path.resolve()}")
        if args.write_db:
            print(f"数据库新增：{inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
