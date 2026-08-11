import asyncio

from app.modules.policy_market.infrastructure.policy_ask_loader import get_policy_ask_module

from app.modules.policy_market.domain.models import ConsultationAnswer, SourceFile


class PolicyAskExecutorAdapter:
    """将政策知识库脚本的返回值转换为应用领域结果。"""

    async def ask(self, question: str) -> ConsultationAnswer:
        policy_ask = await get_policy_ask_module()
        result = await asyncio.to_thread(policy_ask.ask, question)
        return ConsultationAnswer(
            answer=str(result.get("answer") or ""),
            # 咨询结果只对外暴露结论与源文件：省份、时效、核验状态属于检索元信息，
            # 仍在 tools 层落飞书评估表，不再随快照返回给前端。
            province_code=None,
            source_data={"references": list(result.get("references") or [])},
        )


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
