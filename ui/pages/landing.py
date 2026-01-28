import streamlit as st


def render_landing() -> None:
    html = """<section class="hero">
<div class="hero-inner">

<div class="hero-grid">
<div class="hero-left">
  <h1>Transformez les verbatims clients en décisions stratégiques</h1>

  <p class="hero-sub">
    Décidez rapidement quoi corriger, quoi prioriser et quoi ignorer à partir des preuves, pas des impressions.
  </p>

  <div class="hero-actions">
    <a class="btn btn-primary" href="?page=chat">Essayez gratuitement</a>
    <a class="btn btn-secondary" href="?page=chat">Voir une démo</a>
  </div>

  <p class="hero-proof">
    Analyse explicable · Taxonomie métier · Sans dépendance externe
  </p>

  <!-- 👇 LES 4 MENUS JUSTE APRÈS LE TEXTE -->
  <div class="stepbar">
    ...
  </div>
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
Importez les données
</a>

<a class="step-item" href="?page=analysis">
<span class="step-ic" aria-hidden="true">
<svg viewBox="0 0 24 24" fill="none">
<circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/>
<path d="M20 20l-3.2-3.2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
</span>
Analysez les verbatims
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
Priorisez les actions
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
Recevez des rapports
</a>
</div>

</div>
</section>

<section class="section">
<div class="container">
<div class="section-head">
<h2>Décisions produit basées sur des preuves</h2>
<p class="lead">Centralisez, filtrez et interprétez des retours multi-sources pour obtenir un backlog actionnable.</p>
</div>

<div class="grid-3">
<div class="card">
<span class="kicker">Preuves</span>
<h3>Analyse reliée aux sources</h3>
<p>Chaque signal reste rattaché aux verbatims d’origine pour des décisions justifiables et partageables.</p>
</div>

<div class="card">
<span class="kicker">Arbitrage</span>
<h3>Priorisation prête à exécuter</h3>
<p>Un backlog P0 / P1 / P2 exploitable pour trancher rapidement entre Produit, Ops et Support.</p>
</div>

<div class="card">
<span class="kicker">Partage</span>
<h3>Rapports immédiatement utilisables</h3>
<p>Synthèse claire, exports et formats de diffusion prêts, sans retraitement manuel.</p>
</div>
</div>

<div class="cta-final">
<h2>Optimisez votre stratégie grâce<br/>à l’analyse des retours clients</h2>
<p class="lead">Importez un CSV ou démarrez avec une démo en quelques minutes.</p>
<div class="cta-actions">
<a class="btn btn-primary" href="?page=chat">Commencer maintenant</a>
<a class="btn btn-ghost-dark" href="?page=chat">Parler à l’assistant</a>
</div>
</div>
</div>
</section>"""
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# Entrée publique standard
# ============================================================

def render():
    render_landing()
