from fastapi import Depends
from supabase import create_client, Client
from .config import Settings, get_settings

_ANON_USER = {"id": "00000000-0000-0000-0000-000000000001", "email": None, "role": "anon"}


def get_supabase(settings: Settings = Depends(get_settings)) -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_current_user() -> dict:
    return _ANON_USER
