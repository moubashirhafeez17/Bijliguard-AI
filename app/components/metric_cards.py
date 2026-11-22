import streamlit as st


def metric_row(items):
    """items: list of (label, value, help_text_or_None)."""
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        with col:
            with st.container(border=True):
                st.metric(label, value, help=help_text)


def disclaimer():
    st.caption(
        "Exhibition prototype using simulated data. A 'Suspicious' result is a signal for "
        "inspection, not proof of theft. Transformer risk is an estimate, not a certainty.")
