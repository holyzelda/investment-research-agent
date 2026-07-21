"""应用启动入口。"""
import os

import uvicorn
from dotenv import load_dotenv

# 加载环境变量
env_file = os.getenv("ENV_FILE", ".env.test")
load_dotenv(env_file)

from app.main import create_app  # noqa: E402

# 创建应用实例
app = create_app()


if __name__ == "__main__":
    # 获取配置
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "9089"))
    debug = os.getenv("APP_DEBUG", "false").lower() == "true"

    # 启动服务
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
    )
