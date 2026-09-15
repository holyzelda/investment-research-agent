"""测试公共夹具：强制本地/内存配置，避免依赖 Nacos/MySQL。"""
import os

# 必须在导入 app 配置之前设置环境变量
os.environ.setdefault("NACOS_ENABLED", "false")
os.environ.setdefault("APP_NAME", "ir-agent")
os.environ.setdefault("APP_VERSION", "0.1.0")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("APP_HOST", "0.0.0.0")
os.environ.setdefault("APP_PORT", "9089")
os.environ.setdefault("IR_DB_URL", "sqlite+aiosqlite:///:memory:")
# 强制关飞书：即便 application.yml 里 enabled=true（联调/PoC 用），
# 自动化测试也不连真飞书（各飞书用例自建 FeishuConfig(enabled=True) 走 MockTransport，不受此影响）。
os.environ.setdefault("IR_FEISHU_ENABLED", "false")
# 同理关现货电价库：测试不连真 MySQL（电价库算法自身用合成数据单测）。
os.environ.setdefault("IR_SPOT_ENABLED", "false")

from app.core.config.settings import reload_settings  # noqa: E402

reload_settings()

class FakeTrialRole:
    """试用角色判定桩：is_trial 可固定为 True/False，或抛出 TrialRoleUnavailable。

    业务写接口的 POST 端点都会注入 get_trial_role_service（生产实现会调统一平台），
    存量测试不关心试用额度，统一用 (result=False) 走"正常账号完全绕过额度"路径。
    """

    def __init__(self, result: bool = False):
        self._result = result

    async def is_trial(self, user_id: str) -> bool:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result
