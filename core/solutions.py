# solutions.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# =========================
# Types
# =========================
@dataclass
class ActionItem:
    area: str                 # "Produit", "Tech", "Ops", "Support", "Data"
    title: str                # action courte
    details: str              # ce qu'on fait concrètement
    owner: str                # équipe responsable
    effort: str               # "S", "M", "L"
    eta: str                  # "24-48h", "1-2 semaines", "1-2 sprints", etc.
    risk: str                 # risque principal
    kpi: List[str]            # KPI à suivre


@dataclass
class Playbook:
    domain: str
    theme: str
    priority: str
    exec_summary: str               # phrase comité
    rationale: List[str]            # pourquoi (règles lisibles)
    actions: List[ActionItem]       # plan d'action structuré
    guardrails: List[str]           # ce qu'on ne fait pas / pièges
    next_questions: List[str]       # questions à poser (drill-down)
    confidence_note: str            # note explicite (pas un score opaque)


# =========================
# Helpers
# =========================
def _norm(s: str) -> str:
    return str(s or "").strip()


def _prio_label(p: str) -> str:
    p = _norm(p).upper()
    return p if p in ("P0", "P1", "P2") else "P2"


def _domain_label(d: str) -> str:
    d = _norm(d).lower()
    if d in ("assurance", "assurance_auto", "auto", "assurance-auto"):
        return "assurance_auto"
    if d in ("ecommerce", "e-commerce", "shop", "retail"):
        return "ecommerce"
    if d in ("saas", "software", "b2b"):
        return "saas"
    return "generic"


def _fallback_confidence(priority: str) -> str:
    # Assumé explicite : sans evidence/citations, on reste prudent.
    if priority == "P0":
        return "Moyenne : priorité élevée mais à confirmer par verbatims exemplaires et volumes (nb, % blocking)."
    if priority == "P1":
        return "Moyenne : action recommandée, à confirmer par exemples et segments (device, canal, version)."
    return "Faible à moyenne : longue traîne, utile surtout pour identifier patterns récurrents."


# =========================
# Playbooks (riches) par domaine
# =========================

# NOTE: Tu ajusteras les thèmes exacts selon ta taxonomie finale.
# L’idée : un playbook riche par thème, décliné selon P0/P1/P2 si besoin.

ASSURANCE_AUTO: Dict[str, Dict[str, Any]] = {
    "Sinistre / Collision / Accident": {
        "exec": {
            "P0": "Réduire immédiatement les frictions de déclaration d’accident (parcours + pièces) car cela bloque la résolution sinistre.",
            "P1": "Améliorer le parcours de déclaration d’accident (guidage, pièces) pour réduire l’abandon et les contacts support.",
            "P2": "Clarifier les étapes de déclaration d’accident et renforcer l’aide contextuelle.",
        },
        "rationale": [
            "Impact direct sur parcours critique (déclaration sinistre).",
            "Les frictions (photos/pièces/étapes) créent abandon et tickets.",
        ],
        "actions": [
            ActionItem(
                area="Produit",
                title="Parcours déclaration 'Collision' en 3 étapes max",
                details="Réduire le nombre d’écrans; auto-remplissage; sauvegarde brouillon; reprise après échec.",
                owner="Produit",
                effort="M",
                eta="1-2 sprints",
                risk="Risque de non-conformité si suppression de pièces",
                kpi=["Taux d’abandon déclaration", "Temps moyen déclaration", "Tickets sinistre / 1000 users"]
            ),
            ActionItem(
                area="Tech",
                title="Upload photo robuste (réseau faible)",
                details="Retry, reprise, compression, timeout clair, file d’attente offline si mobile.",
                owner="Tech",
                effort="M",
                eta="1 sprint",
                risk="Régression mobile si non testé multi-device",
                kpi=["Taux d’échec upload", "Crash rate mobile", "Durée upload médiane"]
            ),
            ActionItem(
                area="Support",
                title="Macro + page d’aide 'pièces requises'",
                details="Liste des pièces, exemples photo acceptables, erreurs fréquentes, solution immédiate.",
                owner="Support/Ops",
                effort="S",
                eta="24-48h",
                risk="Incohérence si règles changent côté produit",
                kpi=["Taux de réouverture ticket", "Temps de résolution", "CSAT support"]
            ),
        ],
        "guardrails": [
            "Ne pas ajouter de nouvelles pièces requises sans preuve (augmente l’abandon).",
            "Ne pas déployer sans test sur Android bas de gamme (upload/photo).",
        ],
        "questions": [
            "À quelle étape les utilisateurs quittent-ils le parcours ?",
            "Quels messages d’erreur apparaissent sur upload photo ?",
            "Le problème est-il lié à Android/iOS/versions spécifiques ?",
        ],
    },

    "Sinistre / Bris de glace": {
        "exec": {
            "P0": "Fiabiliser la déclaration bris de glace (photos + guidage) car le parcours est perçu comme bloquant.",
            "P1": "Optimiser bris de glace (guidage photo + simplification) pour réduire abandon et contacts.",
            "P2": "Améliorer la clarté des instructions bris de glace (aide contextuelle).",
        },
        "rationale": [
            "Signal récurrent 'bris glace' + 'photo'.",
            "Parcours souvent similaire à collision → gains rapides par mutualisation.",
        ],
        "actions": [
            ActionItem(
                area="Produit",
                title="Guidage photo bris de glace",
                details="Écran avec exemples 'photo ok / photo refusée', validation immédiate, checklist.",
                owner="Produit",
                effort="S",
                eta="1 sprint",
                risk="Sur-contrôle → frustration",
                kpi=["Taux d’acceptation pièces", "Abandon parcours", "Tickets bris de glace"]
            ),
            ActionItem(
                area="Ops",
                title="Aligner règles d’acceptation des pièces",
                details="Documenter critères; harmoniser entre back-office et app; réduire refus arbitraires.",
                owner="Ops",
                effort="M",
                eta="1-2 semaines",
                risk="Dépendance équipes sinistre",
                kpi=["% pièces refusées", "Temps de traitement", "NPS parcours sinistre"]
            ),
        ],
        "guardrails": [
            "Ne pas complexifier le wording (éviter jargon assurance)."
        ],
        "questions": [
            "Quels refus de pièces sont les plus fréquents ?",
            "Les utilisateurs comprennent-ils 'tiers/tous risques' dans ce contexte ?",
        ],
    },

    "Sinistre / Catastrophe naturelle": {
        "exec": {
            "P0": "Rendre la déclaration 'catastrophe naturelle' compréhensible et guidée (éligibilité + pièces) pour éviter blocages et escalades.",
            "P1": "Améliorer l’orientation et l’éligibilité du parcours catastrophe naturelle.",
            "P2": "Clarifier les critères d’éligibilité et les délais (FAQ + aide).",
        },
        "rationale": [
            "Événement sensible → forte charge support si parcours flou.",
            "Les conditions d’éligibilité et délais sont source de conflit.",
        ],
        "actions": [
            ActionItem(
                area="Produit",
                title="Check éligibilité simple",
                details="Questionnaire 3-5 questions max + message clair: 'éligible / à confirmer / non éligible'.",
                owner="Produit",
                effort="M",
                eta="1-2 sprints",
                risk="Erreur d’éligibilité (risque légal) → wording prudent",
                kpi=["Tickets 'cat nat'", "Taux d’abandon", "CSAT parcours"]
            ),
            ActionItem(
                area="Support",
                title="Template de réponse + page officielle",
                details="Message standard + liens + délais + pièces; réduit escalades.",
                owner="Support",
                effort="S",
                eta="24-48h",
                risk="Infos obsolètes si règles changent",
                kpi=["Temps réponse", "Réouverture", "Escalades"]
            ),
        ],
        "guardrails": [
            "Toujours éviter les promesses de délais exacts si non garantis."
        ],
        "questions": [
            "Quels termes créent confusion (arrêté, franchise, délai) ?",
        ],
    },

    "Déclaration / Justificatifs / Parcours": {
        "exec": {
            "P0": "Simplifier et fiabiliser le parcours + justificatifs (photos, email, étapes) car c’est une source majeure d’abandon.",
            "P1": "Réduire la complexité du parcours (étapes, validation, messages) pour diminuer abandon et tickets.",
            "P2": "Renforcer l’aide contextuelle et la clarté des justificatifs demandés.",
        },
        "rationale": [
            "Mots dominants: parcours, complexité, photo, téléphone/android/email.",
            "Souvent un problème d’UX + robustesse technique (upload).",
        ],
        "actions": [
            ActionItem(
                area="Produit",
                title="Réduction étapes + brouillon",
                details="Brouillon automatique, retour arrière sans perte, progression visible.",
                owner="Produit",
                effort="M",
                eta="1-2 sprints",
                risk="Dette UX si patch partiel",
                kpi=["Abandon parcours", "Temps de complétion", "Tickets parcours"]
            ),
            ActionItem(
                area="Tech",
                title="Messages d’erreur actionnables",
                details="Au lieu de 'Erreur', dire quoi faire: 'réessayer', 'changer réseau', 'taille max', etc.",
                owner="Tech",
                effort="S",
                eta="1 semaine",
                risk="Incohérence des messages",
                kpi=["Taux d’erreur", "Retry success rate"]
            ),
        ],
        "guardrails": [
            "Ne pas ajouter de nouveaux champs sans preuve (augmenter abandon)."
        ],
        "questions": [
            "Quelle étape concentre le plus d’erreurs ?",
            "Quels devices (android versions) sont les plus touchés ?",
        ],
    },

    "Contrat / Garanties / Profil assuré": {
        "exec": {
            "P0": "Clarifier garanties (tiers/tous risques) et profils (jeune conducteur) car cela génère incompréhension et conflit.",
            "P1": "Améliorer la lisibilité des garanties/profils pour réduire incompréhension et contacts.",
            "P2": "Rendre les libellés de garanties plus pédagogiques (glossaire + exemples).",
        },
        "rationale": [
            "Signal contractuel: tiers, tous risques, jeune conducteur, niveaux faible/moyenne.",
        ],
        "actions": [
            ActionItem(
                area="Produit",
                title="Glossaire garanties in-app",
                details="Définitions courtes + exemple concret + liens 'en savoir plus'.",
                owner="Produit",
                effort="S",
                eta="1 sprint",
                risk="Surcharge d’info si mal designé",
                kpi=["Tickets contrat", "CTR aide", "CSAT compréhension"]
            ),
            ActionItem(
                area="Ops",
                title="Aligner wording contrat/app/support",
                details="Même nomenclature partout; réduire incohérences sources de litige.",
                owner="Ops",
                effort="M",
                eta="2-3 semaines",
                risk="Dépendance juridique",
                kpi=["Réclamations", "Tickets contradiction"]
            ),
        ],
        "guardrails": [
            "Ne pas promettre une couverture sans référence contractuelle."
        ],
        "questions": [
            "Quels termes exacts déclenchent plaintes (tiers, franchise, exclusions) ?",
        ],
    },
}

ECOMMERCE: Dict[str, Dict[str, Any]] = {
    "Commande / Paiement": {
        "exec": {
            "P0": "Stabiliser le paiement (refus/3DS/erreurs) car c’est un point de rupture direct sur le chiffre d’affaires.",
            "P1": "Réduire les échecs de paiement et clarifier les erreurs pour limiter les abandons.",
            "P2": "Améliorer l’UX paiement (messages, alternatives) pour réduire friction.",
        },
        "rationale": ["Le paiement impacte directement la conversion et le revenu."],
        "actions": [
            ActionItem(
                area="Tech",
                title="Instrumenter erreurs PSP + 3DS",
                details="Logs par code erreur, corrélation device/navigateur, tableau de bord quotidien.",
                owner="Tech",
                effort="M",
                eta="1-2 semaines",
                risk="Données incomplètes si tracking partiel",
                kpi=["Taux d’échec paiement", "Conversion checkout", "Taux 3DS success"]
            ),
            ActionItem(
                area="Produit",
                title="Messages d’erreur paiement actionnables",
                details="Expliquer la cause probable + alternatives (autre carte, PayPal, etc.).",
                owner="Produit",
                effort="S",
                eta="1 sprint",
                risk="Sur-promesse si cause inconnue",
                kpi=["Abandon checkout", "Retry success rate"]
            ),
        ],
        "guardrails": ["Ne pas masquer les erreurs PSP : les rendre utiles."],
        "questions": ["Quel PSP ? Quels codes erreur dominants ?", "Mobile vs desktop ?"],
    },
    "Livraison": {
        "exec": {
            "P0": "Réduire les incidents de livraison (non reçue/retard) car cela détruit la confiance et la rétention.",
            "P1": "Améliorer suivi et gestion des retards pour réduire tickets et remboursements.",
            "P2": "Clarifier les délais et notifications.",
        },
        "rationale": ["La livraison est un driver NPS majeur en e-commerce."],
        "actions": [
            ActionItem(
                area="Ops",
                title="Améliorer tracking + notifications",
                details="Notifications proactives retard, lien suivi unique, ETA réaliste.",
                owner="Ops",
                effort="M",
                eta="2-3 semaines",
                risk="Dépendance transporteurs",
                kpi=["Tickets livraison", "Taux de retard", "NPS livraison"]
            )
        ],
        "guardrails": ["Ne pas annoncer des ETA non fiables."],
        "questions": ["Quel transporteur / zone concentre le problème ?"],
    },
}

SAAS: Dict[str, Dict[str, Any]] = {
    "Connexion / Authentification": {
        "exec": {
            "P0": "Rétablir la connexion (login/session/SSO) car c’est un blocage total d’accès au service.",
            "P1": "Réduire les incidents d’authentification (SSO, reset, session) pour diminuer tickets.",
            "P2": "Clarifier messages et parcours de récupération.",
        },
        "rationale": ["Accès service = parcours critique."],
        "actions": [
            ActionItem(
                area="Tech",
                title="Monitoring auth + taux d’erreur",
                details="Dash login errors, SSO callbacks, rate limits; alerte temps réel.",
                owner="Tech",
                effort="M",
                eta="1-2 semaines",
                risk="Monitoring mal configuré",
                kpi=["Login success rate", "Auth error rate", "MTTR incidents auth"]
            ),
            ActionItem(
                area="Produit",
                title="Parcours reset mot de passe sans friction",
                details="Messages clairs, expiration liens, anti-boucle, support SSO.",
                owner="Produit",
                effort="S",
                eta="1 sprint",
                risk="Fail security si mal fait",
                kpi=["Taux réussite reset", "Tickets reset", "Time-to-login"]
            ),
        ],
        "guardrails": ["Ne pas sacrifier sécurité pour réduire friction."],
        "questions": ["SSO ou mot de passe ? navigateur/OS ? fréquence ?"],
    },
    "Bug / Crash": {
        "exec": {
            "P0": "Réduire crash/bugs bloquants via repro+hotfix car l’expérience est interrompue.",
            "P1": "Diminuer les bugs fréquents via priorisation par impact et versions.",
            "P2": "Hygiène qualité (tests, monitoring) et collecte de repro.",
        },
        "rationale": ["Crash = rupture d’usage."],
        "actions": [
            ActionItem(
                area="Tech",
                title="Top crashers + hotfix",
                details="Collect stacktraces, isoler 3 crashers, patch rapide.",
                owner="Tech",
                effort="M",
                eta="24-72h",
                risk="Hotfix régressif",
                kpi=["Crash-free sessions", "Errors per 1k sessions", "MTTR"]
            )
        ],
        "guardrails": ["Ne pas hotfix sans test minimal."],
        "questions": ["Quelle version/feature cause le crash ?"],
    },
}

PLAYBOOKS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "assurance_auto": ASSURANCE_AUTO,
    "ecommerce": ECOMMERCE,
    "saas": SAAS,
}


# =========================
# Public API
# =========================
def get_playbook(
    domain: str,
    theme: str,
    priority: str,
    *,
    nb: Optional[int] = None,
    part_blocking: Optional[float] = None,
    part_neg: Optional[float] = None,
    low_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Retourne un playbook riche (phrase comité + plan d’action).
    Paramètres stats optionnels : utilisés dans la rationale/confidence.
    """
    d = _domain_label(domain)
    t = _norm(theme)
    p = _prio_label(priority)

    entry = PLAYBOOKS.get(d, {}).get(t)

    # Fallback par domaine si thème inconnu
    if entry is None:
        # fallback "generic"
        exec_map = {
            "P0": "Traiter en priorité un blocage utilisateur sur un parcours critique (hotfix + investigation).",
            "P1": "Planifier une amélioration ciblée pour réduire la friction et les tickets.",
            "P2": "Surveiller et regrouper davantage de signal avant investissement produit.",
        }
        rationale = [
            "Thème non reconnu dans la taxonomie du domaine.",
            "Recommandation générique : à affiner en créant/ajustant la catégorie.",
        ]
        actions = [
            ActionItem(
                area="Data",
                title="Drill-down sur verbatims",
                details="Extraire 20 exemples; identifier mots-clés; proposer nouvelle catégorie/règle.",
                owner="Data/Produit",
                effort="S",
                eta="1-2 jours",
                risk="Catégorie mal définie si échantillon biaisé",
                kpi=["% 'Autre'", "Couverture taxonomie", "Taux low_conf"]
            )
        ]
        guardrails = ["Ne pas sur-prioriser un thème inconnu sans volume et exemples."]
        questions = ["Quels exemples concrets ? Quel segment (device, canal, version) ?"]
        confidence = _fallback_confidence(p)

        pb = Playbook(
            domain=d,
            theme=t,
            priority=p,
            exec_summary=exec_map[p],
            rationale=rationale + _stats_rationale(nb, part_blocking, part_neg, low_confidence),
            actions=actions,
            guardrails=guardrails,
            next_questions=questions,
            confidence_note=confidence,
        )
        return asdict(pb)

    exec_summary = entry["exec"].get(p) or entry["exec"].get("P1") or "Améliorer ce thème."
    rationale = list(entry.get("rationale", [])) + _stats_rationale(nb, part_blocking, part_neg, low_confidence)
    actions: List[ActionItem] = entry.get("actions", [])
    guardrails: List[str] = entry.get("guardrails", [])
    questions: List[str] = entry.get("questions", [])

    # Note de confiance : explicite, basée sur low_confidence si dispo
    confidence = _confidence_from_low_conf(low_confidence, p)

    pb = Playbook(
        domain=d,
        theme=t,
        priority=p,
        exec_summary=exec_summary,
        rationale=rationale,
        actions=actions,
        guardrails=guardrails,
        next_questions=questions,
        confidence_note=confidence,
    )
    return asdict(pb)


def _stats_rationale(
    nb: Optional[int],
    part_blocking: Optional[float],
    part_neg: Optional[float],
    low_confidence: Optional[float],
) -> List[str]:
    out = []
    if nb is not None:
        out.append(f"Volume (nb) = {nb}.")
    if part_blocking is not None:
        out.append(f"% bloquant ≈ {round(part_blocking * 100, 1)}%.")
    if part_neg is not None:
        out.append(f"% négatif ≈ {round(part_neg * 100, 1)}%.")
    if low_confidence is not None:
        out.append(f"Qualité classification (low_conf) ≈ {round(low_confidence * 100, 1)}%.")
    return out


def _confidence_from_low_conf(low_confidence: Optional[float], priority: str) -> str:
    # Ici low_confidence peut être "part_low_conf" (0..1) au niveau thème
    if low_confidence is None:
        return _fallback_confidence(priority)

    # plus low_conf est élevé, moins on est confiant
    if low_confidence >= 0.7:
        return "Faible : classification incertaine (beaucoup de cas ambigus). Exiger des verbatims exemplaires."
    if low_confidence >= 0.4:
        return "Moyenne : signal exploitable mais à confirmer par drill-down et segmentation."
    return "Élevée : signal stable, actions recommandées avec peu d’ambiguïté."
