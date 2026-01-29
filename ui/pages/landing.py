import streamlit as st


def render_landing() -> None:
    html = """<section class="hero">
<div class="hero-inner">

<div class="hero-grid">
<div class="hero-left">
<h1>Comprenez la voix de vos clients</h1>

<p class="hero-sub">
Donnez du sens à vos retours clients, même à grande échelle.
InsightIA fait émerger thèmes, attentes et signaux clés à partir des mots.
</p>

<div class="hero-actions">
<a class="btn btn-primary" href="?page=start">Essayez gratuitement</a>
<a class="btn btn-secondary" href="?page=start">Démo</a>
</div>

<p class="hero-proof">
Analyse explicable · Lecture structurée · Sans dépendance externe
</p>

<p class="hero-proof">
<strong>Les clients parlent. InsightIA en révèle le sens.</strong>
</p>
</div>

<div class="hero-right" aria-hidden="true">
<div class="panel-wrap">
<div class="panel-blue"></div>
<div class="panel-glow"></div>
</div>
</div>
</div>

<div class="stepbar">
<a class="step-item" href="?page=start">
<span class="step-ic" aria-hidden="true">
<svg viewBox="0 0 24 24" fill="none">
<path d="M12 3v10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
<path d="M8 9l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M4 17v3h16v-3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
</span>
Charger les données
</a>

<a class="step-item" href="?page=analysis">
<span class="step-ic" aria-hidden="true">
<svg viewBox="0 0 24 24" fill="none">
<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>
<path d="M20 20l-3.2-3.2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
</span>
Analyser les verbatims
</a>

<a class="step-item" href="?page=prioritization">
<span class="step-ic" aria-hidden="true">
<svg viewBox="0 0 24 24" fill="none">
<path d="M8 6h13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
<path d="M8 12h13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
<path d="M8 18h13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
<path d="M3 6h.01M3 12h.01M3 18h.01" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
</svg>
</span>
Prioriser les actions
</a>

<a class="step-item" href="?page=reports">
<span class="step-ic" aria-hidden="true">
<svg viewBox="0 0 24 24" fill="none">
<path d="M7 3h8l4 4v14H7V3z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
<path d="M15 3v5h5" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
<path d="M9 13h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
<path d="M9 17h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
</span>
Recevoir les rapports
</a>
</div>

</div>
</section>

<section class="section">
<div class="container">
<div class="section-head">
<h2>La voix du client, rendue lisible</h2>
<p class="lead">
Centralisez des retours multi-sources et obtenez une lecture claire, fidèle et partageable.
</p>
</div>

<div class="grid-3">
<div class="card">
<span class="kicker">Compréhension</span>
<h3>Relié aux mots réels</h3>
<p>
Chaque signal reste rattaché aux verbatims d’origine pour préserver le contexte.
</p>
</div>

<div class="card">
<span class="kicker">Clarté</span>
<h3>Thèmes et usages</h3>
<p>
Les retours sont structurés par thèmes, attentes et usages, sans perdre la nuance.
</p>
</div>

<div class="card">
<span class="kicker">Partage</span>
<h3>Résultats exploitables</h3>
<p>
Une lecture simple à expliquer et à diffuser entre Produit, Support et Ops.
</p>
</div>
</div>

<div class="cta-final">
<h2>Voyez ce que vos clients expriment</h2>
<p class="lead">
Importez vos données ou lancez une démo pour obtenir une lecture claire en quelques minutes.
</p>
<div class="cta-actions">
<a class="btn btn-primary" href="?page=start">Commencer</a>
<a class="btn btn-ghost-dark" href="?page=chat">Assistant</a>
</div>
</div>
</div>
</section>"""
    st.markdown(html, unsafe_allow_html=True)


def render():
    render_landing()
