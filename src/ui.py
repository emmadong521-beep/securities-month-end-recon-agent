from __future__ import annotations

from html import escape

import streamlit as st


PLOTLY_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#1F2937", "family": "Arial, sans-serif"},
    "title": {"font": {"size": 18, "color": "#163b5c"}},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    "margin": {"l": 20, "r": 20, "t": 60, "b": 35},
}


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
            max-width: 1440px;
        }
        .stApp {
            background: #F7F9FC;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] label {
            color: #163b5c;
            font-weight: 700;
        }
        .finance-header {
            padding: 1.35rem 1.5rem;
            border-radius: 12px;
            background: linear-gradient(135deg, #ffffff 0%, #eef5fb 100%);
            border: 1px solid #e5edf5;
            border-left: 6px solid #1F4E79;
            box-shadow: 0 10px 28px rgba(31, 78, 121, 0.08);
            margin-bottom: 1rem;
        }
        .finance-header h1 {
            margin: 0;
            color: #163b5c;
            font-size: 1.9rem;
            letter-spacing: 0;
        }
        .finance-header p {
            margin: 0.45rem 0 0 0;
            color: #4b5563;
            font-size: 0.98rem;
        }
        .kpi-card {
            min-height: 112px;
            padding: 1rem 1rem 0.9rem 1rem;
            border-radius: 12px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-left: 5px solid #1F4E79;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
        }
        .kpi-label {
            color: #6b7280;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .kpi-value {
            color: #111827;
            font-size: 1.65rem;
            font-weight: 760;
            margin-top: 0.25rem;
            line-height: 1.18;
        }
        .kpi-delta {
            color: #4b5563;
            margin-top: 0.22rem;
            font-size: 0.82rem;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .section-title {
            margin-top: 1.25rem;
            margin-bottom: 0.65rem;
            color: #163b5c;
            font-size: 1.16rem;
            font-weight: 760;
        }
        .info-card {
            padding: 1rem 1.1rem;
            border-radius: 12px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-left: 5px solid var(--card-border, #1F4E79);
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
            margin-bottom: 0.8rem;
        }
        .info-card h4 {
            margin: 0 0 0.38rem 0;
            color: #111827;
            font-size: 1rem;
        }
        .info-card p {
            margin: 0;
            color: #374151;
            line-height: 1.55;
        }
        .agent-step-card {
            padding: 0.85rem 1rem;
            border-radius: 10px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-left: 4px solid #1F4E79;
            margin-bottom: 0.6rem;
        }
        .agent-step-card h4,
        .timeline-step h4 {
            margin: 0 0 0.3rem 0;
            color: #163b5c;
            font-size: 0.98rem;
        }
        .agent-step-card p,
        .timeline-step p {
            margin: 0;
            color: #374151;
            line-height: 1.5;
        }
        .timeline-step {
            padding: 0.85rem 1rem;
            border-radius: 10px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-left: 5px solid #9ca3af;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.6rem;
        }
        .timeline-step.breakpoint {
            border-left-color: #dc2626;
            background: #fff7f7;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 0.8rem 1rem;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stExpander"] {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            background: #ffffff;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 10px;
            border: 1px solid #1F4E79;
            box-shadow: 0 6px 16px rgba(31, 78, 121, 0.12);
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="finance-header"><h1>{escape(title)}</h1>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


def severity_color(severity: str | None) -> str:
    return {
        "HIGH": "#dc2626",
        "MEDIUM": "#d97706",
        "LOW": "#059669",
        "PASS": "#059669",
        "WARNING": "#d97706",
        "FAIL": "#dc2626",
    }.get(str(severity or "").upper(), "#1F4E79")


def reason_tag_color(tag: str | None) -> str:
    tag_text = str(tag or "").upper()
    if "HIGH" in tag_text or "LOW_MARGIN" in tag_text:
        return "#dc2626"
    if "RATE" in tag_text or "COST" in tag_text:
        return "#d97706"
    return "#1F4E79"


def render_status_badge(label: str, status: str) -> None:
    color = severity_color(status)
    st.markdown(
        (
            f'<span class="status-badge" style="color:{color};'
            f'background:{color}14;border-color:{color}33;">{escape(label)} · {escape(str(status))}</span>'
        ),
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    status: str | None = None,
    help_text: str | None = None,
) -> None:
    color = severity_color(status)
    delta_html = f'<div class="kpi-delta">{escape(delta)}</div>' if delta else ""
    help_html = f'<div class="kpi-delta">{escape(help_text)}</div>' if help_text else ""
    st.markdown(
        (
            f'<div class="kpi-card" style="border-left-color:{color};">'
            f'<div class="kpi-label">{escape(label)}</div>'
            f'<div class="kpi-value">{escape(str(value))}</div>'
            f'{delta_html}{help_html}</div>'
        ),
        unsafe_allow_html=True,
    )


def render_section_title(title: str, icon: str | None = None) -> None:
    prefix = f"{icon} " if icon else ""
    st.markdown(f'<div class="section-title">{escape(prefix + title)}</div>', unsafe_allow_html=True)


def render_info_card(title: str, body: str, icon: str | None = None, border_color: str = "#1F4E79") -> None:
    prefix = f"{icon} " if icon else ""
    st.markdown(
        (
            f'<div class="info-card" style="--card-border:{border_color};">'
            f"<h4>{escape(prefix + title)}</h4><p>{escape(body)}</p></div>"
        ),
        unsafe_allow_html=True,
    )


def render_agent_step_card(title: str, body: str, icon: str | None = None, border_color: str = "#1F4E79") -> None:
    prefix = f"{icon} " if icon else ""
    st.markdown(
        (
            f'<div class="agent-step-card" style="border-left-color:{border_color};">'
            f"<h4>{escape(prefix + title)}</h4><p>{escape(body)}</p></div>"
        ),
        unsafe_allow_html=True,
    )


def render_timeline_step(
    title: str,
    body: str,
    is_breakpoint: bool = False,
    icon: str | None = None,
) -> None:
    prefix = f"{icon} " if icon else ""
    class_name = "timeline-step breakpoint" if is_breakpoint else "timeline-step"
    st.markdown(
        f'<div class="{class_name}"><h4>{escape(prefix + title)}</h4><p>{escape(body)}</p></div>',
        unsafe_allow_html=True,
    )


def apply_plotly_theme(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_xaxes(showgrid=True, gridcolor="#E5E7EB", zerolinecolor="#CBD5E1")
    fig.update_yaxes(showgrid=True, gridcolor="#E5E7EB", zerolinecolor="#CBD5E1")
    return fig


def format_wan(amount) -> str:
    try:
        return f"{float(amount) / 10000:,.2f} 万元"
    except (TypeError, ValueError):
        return "N/A"


def format_pct(value) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "N/A"
