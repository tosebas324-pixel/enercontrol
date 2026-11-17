"""Lectura de configuración: st.secrets primero, variables de entorno después."""
import os

import streamlit as st


def get_section(name: str, keys: list) -> dict:
    cfg = {}
    try:
        if name in st.secrets:
            section = st.secrets[name]
            for k in keys:
                if k in section:
                    cfg[k] = section[k]
    except Exception:  # sin secrets.toml: se usan variables de entorno
        pass
    for k in keys:
        if k not in cfg:
            v = os.getenv(f"{name.upper()}_{k.upper()}")
            if v not in (None, ""):
                cfg[k] = v
    return cfg
