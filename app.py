import streamlit as st

# Import tab renderer functions from dedicated modules
from tabs import (
    render_share_tab,  # Function rendering the share overview tab content
    render_probability_tab,  # Function rendering probability metrics tab content
    render_classification_tab,  # Function rendering classification report tab content
)

# Helper callbacks to ensure at least one signal checkbox stays selected
def _global_up_changed():
    if not st.session_state.get('global_include_up') and not st.session_state.get('global_include_down'):
        st.session_state['global_include_down'] = True
def _global_down_changed():
    if not st.session_state.get('global_include_down') and not st.session_state.get('global_include_up'):
        st.session_state['global_include_up'] = True

st.set_page_config(page_title="Share Analytic Dashboard", page_icon="📈", layout="wide")
st.title("📈 Share Analytic Dashboard")
st.write("Welcome to the prototypical stock analysis dashboard. Our goal is to provide insights into stock market trends and model predictions.")

# Main app function for the layout and tab rendering
def main():
    # Global sidebar filters
    st.sidebar.header("Filters")

    sort_option = st.sidebar.selectbox(
        "Sort order",
        options=["ProbUp descending", "ProbUp ascending", "Alphabetical (Ticker)"],
        index=0,
        key="global_sort_order",
        help="Choose how to sort.",
    )

    limit_option = st.sidebar.selectbox(
        "Results to show",
        options=[10, 20, 30, "All"],
        index=0,
        key="global_limit",
        help="Limit how many items are displayed after sorting.",
    )

    up = st.sidebar.checkbox("Include UP", True, key="global_include_up", on_change=_global_up_changed)

    down = st.sidebar.checkbox("Include DOWN", True, key="global_include_down", on_change=_global_down_changed)

    prob_range = st.sidebar.slider(
        "ProbUp range",
        min_value=0.0,
        max_value=1.0,
        value=(0.0, 1.0),
        step=0.01,
        key="global_prob_range",
        help="Show predictions whose ProbUp falls within this range.",
    )

    share_tab, probability_tab, classification_tab = st.tabs([
        "Share Information", "Probability Information", "Classification Area"
    ])

    with share_tab:
        render_share_tab(
            include_up=up,
            include_down=down,
            prob_range=prob_range,
            limit_option=limit_option,
            sort_option=sort_option,
        )

    with probability_tab:
        render_probability_tab(
            include_up=up,
            include_down=down,
            prob_range=prob_range,
            limit_option=limit_option,
            sort_option=sort_option,
        )

    with classification_tab:
        render_classification_tab()


if __name__ == "__main__":
    main()

st.markdown("---")
st.caption("This web app is a students project created for the Master Information Technology at the Ferdinand Porsche FernFH in Wiener Neustadt, Austria. This site is not for commercial use and is intended for educational and demonstration purposes only.")