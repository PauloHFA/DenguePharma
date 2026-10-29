"""Refresh the active curation fragment; support standalone forms and tests."""
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


def rerun_curation():
    context = get_script_run_ctx(suppress_warning=True)
    # Fragment scope is invalid during a full app run, even inside a fragment.
    # The installed, locked Streamlit runtime exposes this queue on its context.
    scope = 'fragment' if context and context.fragment_ids_this_run else 'app'
    st.rerun(scope=scope)
