"""About — method notes, table sources, Rev 7 note, safety disclaimer."""

from __future__ import annotations

import streamlit as st

from app._i18n import t
from app._shared import render_disclaimer, render_sidebar_toggles

st.set_page_config(page_title="About", page_icon="📖", layout="wide")

render_sidebar_toggles(st.sidebar)

st.title(t("about_page_title"))
render_disclaimer()

st.markdown(t("about_body"))
