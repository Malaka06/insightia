import base64
from pathlib import Path
import streamlit as st


# ------------------------------------------------------------
# Logo
# ------------------------------------------------------------
def _logo_data_uri() -> str | None:
    candidates = [
        Path("assets/insightia_logo.svg"),
        Path("assets/insightia_logo.png"),
    ]
    for p in candidates:
        if p.exists():
            mime = "image/svg+xml" if p.suffix.lower() == ".svg" else "image/png"
            b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
            return f"data:{mime};base64,{b64}"
    return None


# ------------------------------------------------------------
# Breadcrumb (4 étapes, cliquable) — rendu INLINE
# ------------------------------------------------------------
def render_breadcrumb(active: str) -> None:
    # Pas sur pages marketing
    if active in ("landing", "solution", "usecases", "about", "contact"):
        return

    # CSS breadcrumb (léger) : injecté ici dans le DOM principal (pas iframe)
    st.markdown(
        "<style>"
        ".crumbline{max-width:1200px;margin:14px auto 10px auto;padding:0 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;}"
        ".crumb{text-decoration:none;font-weight:800;font-size:13px;letter-spacing:0.02em;color:rgba(255,255,255,0.70);transition:color 140ms ease;}"
        ".crumb:hover{color:rgba(255,255,255,0.96);}"
        ".crumb-active{color:#fff;font-weight:900;}"
        ".crumb-sep{opacity:.38;font-weight:900;font-size:12px;color:rgba(255,255,255,0.70);}"
        "</style>",
        unsafe_allow_html=True,
    )

    steps = [
        ("start", "Importer"),
        ("analysis", "Analyser"),
        ("prioritization", "Prioriser"),
        ("reports", "Rapports"),
    ]

    items = []
    for page, label in steps:
        if page == active:
            items.append(f"<span class='crumb crumb-active'>{label}</span>")
        else:
            items.append(f"<a class='crumb' href='?page={page}'>{label}</a>")

    html = "<div class='crumbline'>" + "<span class='crumb-sep'>→</span>".join(items) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------
# Header global (dans le DOM Streamlit, donc visible + stylé)
# ------------------------------------------------------------
def render_header(active: str = "landing") -> None:
    logo_src = _logo_data_uri()
    brand_html = (
        f"<img src='{logo_src}' alt='INSIGHTIA' class='brand-logo' />"
        if logo_src
        else "<span class='brand-text'>INSIGHTIA</span>"
    )

    def nav_link(label: str, page: str) -> str:
        cls = "nav-link is-active" if active == page else "nav-link"
        return f"<a class='{cls}' href='?page={page}'>{label}</a>"

    # IMPORTANT: HTML en une seule ligne (évite l’affichage en texte / <pre>)
    header_html = (
        "<header class='topnav'>"
        "<div class='topnav-inner'>"
        "<a class='brand' href='?page=landing' aria-label='Accueil'>"
        "<span class='brand-dot'></span>"
        f"{brand_html}"
        "</a>"
        "<nav class='navlinks' aria-label='Navigation principale'>"
        f"{nav_link('Accueil','landing')}"
        f"{nav_link('Solution','solution')}"
        f"{nav_link('Cas d’usage','usecases')}"
        f"{nav_link('À propos','about')}"
        f"{nav_link('Contact','contact')}"
        "</nav>"
        "<div class='nav-cta'>"
        "<a class='btn btn-nav' href='?page=chat'>Essayez gratuitement</a>"
        "</div>"
        "</div>"
        "</header>"
        "<a class='chat-fab' href='?page=chat' aria-label='Ouvrir l’assistant'>"
        "<span class='chat-fab-ic' aria-hidden='true'>"
        "<svg viewBox='0 0 24 24' fill='none'>"
        "<path d='M20 12c0 3.866-3.582 7-8 7a9.77 9.77 0 0 1-3.1-.5L4 20l1.4-3.5A6.7 6.7 0 0 1 4 12c0-3.866 3.582-7 8-7s8 3.134 8 7z' "
        "stroke='currentColor' stroke-width='2' stroke-linejoin='round'/>"
        "</svg>"
        "</span>"
        "</a>"
    )

    st.markdown(header_html, unsafe_allow_html=True)

    # Breadcrumb juste sous le header
    render_breadcrumb(active)


# ------------------------------------------------------------
# Footer global (utilise les classes déjà définies dans theme.css)
# ------------------------------------------------------------
def render_footer() -> None:
    footer_html = (
        "<footer class='footer'>"
        "<div class='footer-inner'>"
        "<div class='footer-cta-title'>Besoin de renseignements ?</div>"
        "<div class='footer-cta-sub'>Une question, une démo, un partenariat ou un recrutement — écrivez-nous.</div>"
        "<div class='footer-email'>"
        "<a class='footer-email-link' href='mailto:recrutementmalaka@gmail.com'>recrutementmalaka@gmail.com</a>"
        "</div>"
        "<div class='footer-brand'>"
        "<strong>INSIGHTIA</strong>"
        "<span class='footer-sep'>·</span>"
        "<span>Voix du Client → décisions produit</span>"
        "</div>"
        "<div class='footer-sub'>Analyse explicable · Taxonomie métier · Exports immédiats · Sans dépendance externe</div>"
        "</div>"
        "</footer>"
    )
    st.markdown(footer_html, unsafe_allow_html=True)
