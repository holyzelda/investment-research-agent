#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
DATA_DIR="${POLICY_DATA_DIR:-$PROJECT_DIR/data/policy_materials}"
PENDING_DIR="$DATA_DIR/pending"
IMPORTED_DIR="$DATA_DIR/imported"
FAILED_DIR="$DATA_DIR/failed"
LOCK_FILE="$DATA_DIR/policy-material-sync.lock"
TARGET_DATE="${POLICY_TARGET_DATE:-$(date -d yesterday +%F)}"
PENDING_RETENTION_DAYS="${POLICY_PENDING_RETENTION_DAYS:-3}"
IMPORTED_RETENTION_DAYS="${POLICY_IMPORTED_RETENTION_DAYS:-30}"
FAILED_RETENTION_DAYS="${POLICY_FAILED_RETENTION_DAYS:-90}"

mkdir -p "$PENDING_DIR" "$IMPORTED_DIR" "$FAILED_DIR"

validate_retention_days() {
    local name="$1"
    local value="$2"
    if [[ ! "$value" =~ ^[0-9]+$ ]]; then
        echo "错误：$name 必须是大于或等于 0 的整数，当前值：$value" >&2
        exit 1
    fi
}

validate_retention_days "POLICY_PENDING_RETENTION_DAYS" "$PENDING_RETENTION_DAYS"
validate_retention_days "POLICY_IMPORTED_RETENTION_DAYS" "$IMPORTED_RETENTION_DAYS"
validate_retention_days "POLICY_FAILED_RETENTION_DAYS" "$FAILED_RETENTION_DAYS"

if [[ ! -x "$PYTHON" ]]; then
    echo "错误：Python 不存在或不可执行：$PYTHON" >&2
    exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "已有政策材料同步任务正在执行，本次跳过。"
    exit 0
fi

mapfile -t EXCEL_FILES < <(
    printf '%s\n' \
        "$PENDING_DIR/北极星储能政策_${TARGET_DATE}.xlsx" \
        "$PENDING_DIR/北极星电力市场政策_${TARGET_DATE}.xlsx" \
        "$PENDING_DIR/北极星电力市场数据_${TARGET_DATE}.xlsx"
)

move_failed_files() {
    local status=$?
    if [[ "$status" -ne 0 ]]; then
        local failure_dir="$FAILED_DIR/${TARGET_DATE}_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$failure_dir"
        for file in "${EXCEL_FILES[@]}"; do
            [[ -f "$file" ]] && mv -- "$file" "$failure_dir/"
        done
        echo "政策材料同步失败，现场文件已保存至：$failure_dir" >&2
    fi
    exit "$status"
}
trap move_failed_files EXIT

cleanup_old_data() {
    local pending_minutes=$((PENDING_RETENTION_DAYS * 1440))
    local imported_minutes=$((IMPORTED_RETENTION_DAYS * 1440))
    local failed_minutes=$((FAILED_RETENTION_DAYS * 1440))

    echo "[$(date '+%F %T')] 开始清理历史 Excel"

    find "$PENDING_DIR" -maxdepth 1 -type f -name '*.xlsx' \
        -mmin "+$pending_minutes" -print -delete

    find "$IMPORTED_DIR" -type f -name '*.xlsx' \
        -mmin "+$imported_minutes" -print -delete
    find "$IMPORTED_DIR" -mindepth 1 -depth -type d -empty -print -delete

    while IFS= read -r -d '' failure_dir; do
        case "$failure_dir" in
            "$FAILED_DIR"/*) find "$failure_dir" -depth -print -delete ;;
            *)
                echo "错误：拒绝清理失败目录之外的路径：$failure_dir" >&2
                return 1
                ;;
        esac
    done < <(
        find "$FAILED_DIR" -mindepth 1 -maxdepth 1 -type d \
            -mmin "+$failed_minutes" -print0
    )

    echo "[$(date '+%F %T')] 历史数据清理完成：pending=${PENDING_RETENTION_DAYS}天，imported=${IMPORTED_RETENTION_DAYS}天，failed=${FAILED_RETENTION_DAYS}天"
}

echo "[$(date '+%F %T')] 开始抓取政策材料，目标日期：$TARGET_DATE"
"$PYTHON" "$SCRIPT_DIR/bjx_policy_news.py" \
    --section all \
    --date "$TARGET_DATE" \
    --output-dir "$PENDING_DIR"

for file in "${EXCEL_FILES[@]}"; do
    if [[ ! -s "$file" ]]; then
        echo "错误：未生成有效 Excel：$file" >&2
        exit 1
    fi
done

echo "[$(date '+%F %T')] 开始导入数据库"
"$PYTHON" "$SCRIPT_DIR/import_excel_to_db.py" --input "${EXCEL_FILES[@]}"

archive_dir="$IMPORTED_DIR/$TARGET_DATE"
mkdir -p "$archive_dir"
for file in "${EXCEL_FILES[@]}"; do
    mv -f -- "$file" "$archive_dir/"
done

trap - EXIT
cleanup_old_data

echo "[$(date '+%F %T')] 政策材料同步完成，Excel 已归档至：$archive_dir"
