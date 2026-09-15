from app.modules.trial_quota.application.trial_quota_service import TrialQuotaService
from app.modules.trial_quota.application.trial_role_service import TrialRoleService


def get_trial_role_service() -> TrialRoleService:
    return TrialRoleService()


def get_trial_quota_service() -> TrialQuotaService:
    return TrialQuotaService()
