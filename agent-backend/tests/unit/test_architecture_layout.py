"""Architecture layout guards for the approved practical DDD structure."""

import importlib


EXPECTED_IMPORTS = [
    "app.core.config.settings",
    "app.core.constants",
    "app.core.exceptions",
    "app.core.response",
    "app.infrastructure.database.base",
    "app.infrastructure.database.session",
    "app.modules.platform_access.domain.models",
    "app.modules.platform_access.interface.deps",
    "app.modules.platform_access.interface.middleware",
    "app.modules.platform_access.interface.router",
    "app.modules.calculation.domain.models",
    "app.modules.calculation.domain.services",
    "app.modules.calculation.domain.ports",
    "app.modules.calculation.domain.param_dictionary",
    "app.modules.calculation.domain.result",
    "app.modules.calculation.domain.execution",
    "app.modules.calculation.application.param_assembler",
    "app.modules.calculation.application.output_mapper",
    "app.modules.calculation.application.calculation_service",
    "app.modules.calculation.application.feishu_calc_engine",
    "app.modules.calculation.application.retry_policy",
    "app.modules.calculation.application.snapshot_service",
    "app.modules.calculation.application.result_view",
    "app.modules.calculation.application.task_service",
    "app.modules.calculation.application.factory",
    "app.modules.calculation.infrastructure.param_dict_repo",
    "app.modules.calculation.infrastructure.revenue_structure_reader",
    "app.modules.calculation.infrastructure.spot_precompute",
    "app.modules.calculation.infrastructure.spot_daily_scheduler",
    "app.modules.calculation.infrastructure.providers",
    "app.modules.calculation.infrastructure.feishu_client",
    "app.modules.calculation.infrastructure.feishu_http_client",
    "app.modules.calculation.infrastructure.feishu_sample",
    "app.modules.calculation.infrastructure.persistence.orm",
    "app.modules.calculation.interface.router",
    "app.modules.calculation.interface.serializers",
    "app.modules.tie_line_map.infrastructure.persistence.orm",
]


def test_approved_architecture_import_paths_exist():
    for module_name in EXPECTED_IMPORTS:
        importlib.import_module(module_name)
