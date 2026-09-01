"""FastAPI 启动入口必须实际挂载测算台账路由。"""
from app.main import app


def test_calculation_ledger_routes_are_registered_on_the_running_app():
    routes = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}

    assert ("/ir/calc/ledger", "GET") in routes
    assert ("/ir/calc/ledger/bootstrap", "GET") in routes
    assert ("/ir/calc/ledger/provinces", "GET") in routes
    assert ("/ir/calc/ledger/users", "GET") in routes
