"""Home — landing page: disclaimer, intro, navigation hint."""

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

st.set_page_config(page_title="Deco Calculator", page_icon="🤿", layout="wide")

render_sidebar_toggles(st.sidebar)

st.title(t("home_page_title"))
render_disclaimer()

st.markdown(t("home_intro"))

st.subheader(t("home_get_started"))
col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_Planner.py", label=t("home_link_planner"), icon="🧭")
with col2:
    st.page_link("pages/2_Profiles.py", label=t("home_link_profiles"), icon="👤")
with col3:
    st.page_link("pages/3_About.py", label=t("home_link_about"), icon="📖")

st.divider()
st.caption(t("home_footer_caption"))
