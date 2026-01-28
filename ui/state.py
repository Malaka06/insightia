import streamlit as st


def get_page(default: str = "landing") -> str:
    page = st.query_params.get("page", default)
    if not page:
        return default
    return str(page)


def set_page(page: str) -> None:
    st.query_params["page"] = page
    st.rerun()
