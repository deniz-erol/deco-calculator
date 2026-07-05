"""About — method notes, table sources, Rev 7 note, safety disclaimer."""

from __future__ import annotations

import os as _os, sys as _sys
_root = _os.path.dirname(_os.path.abspath(__file__))
while _root != _os.path.dirname(_root) and not (
    _os.path.isdir(_os.path.join(_root, "app")) and _os.path.isdir(_os.path.join(_root, "engine"))
):
    _root = _os.path.dirname(_root)
if _root not in _sys.path:
    _sys.path.insert(0, _root)

import streamlit as st

from app._i18n import t
from app._shared import render_disclaimer, render_sidebar_toggles

st.set_page_config(page_title="About", page_icon="📖", layout="wide")

render_sidebar_toggles(st.sidebar)

st.title(t("about_page_title"))
render_disclaimer()

st.markdown(t("about_body"))
