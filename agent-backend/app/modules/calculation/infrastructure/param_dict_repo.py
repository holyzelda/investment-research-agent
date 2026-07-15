"""calculation 基础设施 · 参数字典仓储。"""
from app.modules.calculation.domain.param_dictionary import ParamDictionary
from app.modules.calculation.infrastructure.data_loader import param_dict_raw


class JsonParamDictRepository:
    """从 param_dict.json 构造 ParamDictionary 聚合。"""

    def load(self) -> ParamDictionary:
        return ParamDictionary.from_raw(param_dict_raw())
