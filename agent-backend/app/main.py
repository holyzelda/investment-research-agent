"""应用入口。

`app` 由基础设施层的应用工厂组装（app.infrastructure.web.app_factory）。
本文件保持轻薄：仅暴露 ASGI 应用对象 + 本地直跑入口。
"""
from app.core.config.settings import get_settings
from app.infrastructure.web.app_factory import create_app

app = create_app()


if __name__ == "__main__":
    # 直接运行本文件即可启动服务（IDE 右键运行 / F5 调试也走这里），
    # 无需在终端手敲 uvicorn 命令。
    # 注意：
    #   1) 必须以模块方式从 agent-backend 目录运行：python -m app.main
    #      （或在 IDE 里把工作目录设为 agent-backend），否则绝对导入 `app.*` 会失败。
    #   2) 热更新（reload）要求传入导入字符串 "app.main:app" 而非 app 对象。
    #   3) log_config=None：交给项目自己的 loguru，避免 uvicorn 默认彩色日志在
    #      无 tty（如输出被重定向）时报 isatty 错误。
    import uvicorn

    _settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=_settings.app.host,
        port=_settings.app.port,
        reload=_settings.app.debug,  # debug=true 时开启热更新
        reload_dirs=["app"],
        log_config=None,
    )
