"""Env-driven application config (pydantic-settings).

Centralizes the hashids salt, Postgres/Redis credentials, and public host so all
services read the same settings. Implemented in Epic 5.
"""
