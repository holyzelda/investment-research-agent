import asyncio
import logging

from app.modules.policy_market.infrastructure.policy_ask_loader import get_policy_ask_module

from app.modules.policy_market.domain.models import ConsultationAnswer, SourceFile

logger = logging.getLogger(__name__)

# 在途预取任务。asyncio.create_task 的返回值没人持引用就可能被 GC 提前回收，
# 必须在这里存住；完成后由 done callback 移除。
_prefetch_tasks: set[asyncio.Task] = set()


class PolicyAskExecutorAdapter:
    """将政策知识库脚本的返回值转换为应用领域结果。"""

    async def ask(self, question: str) -> ConsultationAnswer:
        policy_ask = await get_policy_ask_module()
        result = await asyncio.to_thread(policy_ask.ask, question)
        references = list(result.get("references") or [])
        _schedule_source_prefetch(policy_ask, references)
        return ConsultationAnswer(
            answer=str(result.get("answer") or ""),
            # 咨询结果只对外暴露结论与源文件：省份、时效、核验状态属于检索元信息，
            # 仍在 tools 层落飞书评估表，不再随快照返回给前端。
            province_code=None,
            source_data={"references": references},
        )


def _schedule_source_prefetch(policy_ask, references) -> None:
    """答案返回后台下载本次引用到的源文件，把它们焐进磁盘缓存。

    用户读完一段答案要几十秒，这段时间足够把 2~4 份 PDF 下完；等他点"信息来源"
    时就是本地命中，1~2 秒打开，而不是干等飞书下载 5~8 秒。

    只取 ``wiki`` 类型且带 token 的来源——``web`` 是公网链接，前端直跳不走代理，
    预取它毫无意义。
    """
    tokens = [
        str(item.get("token") or "").strip()
        for item in references
        if isinstance(item, dict) and str(item.get("type") or "") == "wiki"
    ]
    tokens = list(dict.fromkeys(token for token in tokens if token))  # 去重保序
    if not tokens:
        return
    try:
        task = asyncio.create_task(_prefetch_source_files(policy_ask, tokens))
    except RuntimeError:
        # 没有运行中的事件循环（同步调用场景）。预取只是加速，静默放弃。
        return
    _prefetch_tasks.add(task)
    task.add_done_callback(_prefetch_tasks.discard)


async def _prefetch_source_files(policy_ask, tokens) -> None:
    """串行预取。一次答案最多 8 条来源，串行足够，也避开飞书 drive 的 QPS 风险。"""
    for token in tokens:
        try:
            await asyncio.to_thread(policy_ask.fetch_source_file, token)
        except asyncio.CancelledError:
            raise
        except Exception:
            # 预取失败只是没加速，绝不能影响已经生成好的答案。
            logger.debug("政策源文件预取失败: token=%s", token[:12], exc_info=True)


async def stop_source_prefetch() -> None:
    """应用关闭时取消在途预取，避免事件循环退出时留下未完成任务。"""
    tasks = list(_prefetch_tasks)
    if not tasks:
        return
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


class PolicySourceFileAdapter:
    """代理下载飞书知识库里的政策源文件。

    白名单校验在 tools 层（fetch_source_file 只认省页解析出的源文件 token），
    这里只做同步转异步与结构映射。
    """

    async def fetch(self, token: str) -> SourceFile | None:
        policy_ask = await get_policy_ask_module()
        result = await asyncio.to_thread(policy_ask.fetch_source_file, token)
        if not result:
            return None
        content, filename, content_type = result
        return SourceFile(
            content=content,
            filename=str(filename or ""),
            content_type=str(content_type or "application/octet-stream"),
        )
