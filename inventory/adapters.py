from allauth.account.adapter import DefaultAccountAdapter
from .utils import get_effective_config

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return bool(get_effective_config().allow_registration)
