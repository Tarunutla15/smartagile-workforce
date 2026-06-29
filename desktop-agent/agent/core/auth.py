"""
Auth manager (facade).

The actual token storage / refresh lives in the top-level ``auth_store`` and
``auth_session`` modules (also used by the localhost pairing server and the uploader).
This module just re-exports them so the rest of the package has a single import surface.
"""

from __future__ import annotations

import auth_session
import auth_store

get_api_base = auth_session.get_api_base
get_valid_access_token = auth_session.get_valid_access_token
refresh_access_token = auth_session.refresh_access_token
clear_memory_cache = auth_session.clear_memory_cache

store_path = auth_store.store_path
get_refresh = auth_store.get_refresh
get_paired_user_id = auth_store.get_paired_user_id

__all__ = [
    "get_api_base",
    "get_valid_access_token",
    "refresh_access_token",
    "clear_memory_cache",
    "store_path",
    "get_refresh",
    "get_paired_user_id",
]
