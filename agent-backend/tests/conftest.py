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
os.environ.setdefault("IR_HEADER_USER_ID", "X-User-Id")
os.environ.setdefault("IR_HEADER_USERNAME", "X-User-Name")
os.environ.setdefault("IR_ALLOW_ANONYMOUS", "true")
# 强制关飞书：即便 application.yml 里 enabled=true（联调/PoC 用），
# 自动化测试也不连真飞书（各飞书用例自建 FeishuConfig(enabled=True) 走 MockTransport，不受此影响）。
os.environ.setdefault("IR_FEISHU_ENABLED", "false")
# 同理关现货电价库：测试不连真 MySQL（电价库算法自身用合成数据单测）。
os.environ.setdefault("IR_SPOT_ENABLED", "false")

from app.core.config.settings import reload_settings  # noqa: E402

reload_settings()
