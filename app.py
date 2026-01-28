import streamlit as st

# ------------------------------------------------------------
# UI globale
# ------------------------------------------------------------
from ui.theme import inject_css
from ui.layout import render_header, render_footer

# ------------------------------------------------------------
# Pages (toutes exposent render())
# ------------------------------------------------------------
from ui.pages.landing import render as render_landing
from ui.pages.start import render as render_start
from ui.pages.chat import render as render_chat
from ui.pages.analysis import render as render_analysis
from ui.pages.backlog import render as render_prioritization
from ui.pages.reports import render as render_reports
from ui.pages.about import render as render_about
from ui.pages.contact import render as render_contact


# ------------------------------------------------------------
# Configuration app
# ------------------------------------------------------------
st.set_page_config(
    page_title="INSIGHTIA",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

# ------------------------------------------------------------
# Routing
# ------------------------------------------------------------
page = st.query_params.get("page", "landing")

# ------------------------------------------------------------
# Layout
# ------------------------------------------------------------
render_header(active=page)

routes = {
    "landing": render_landing,
    "start": render_start,
    "chat": render_chat,
    "analysis": render_analysis,
    "prioritization": render_prioritization,
    "reports": render_reports,
    "about": render_about,  
    "contact": render_contact,  
}

# Fallback si la page n'existe pas
routes.get(page, render_landing)()

# Footer global (CTA recrutement / contact)
render_footer()
