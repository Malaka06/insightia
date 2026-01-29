import streamlit as st


def render():
    st.title("Cas d’usage")

    st.write(
        "Dans un SaaS B2B, les signaux clients existent déjà. "
        "Ils sont présents dans les tickets, les emails, les réponses aux enquêtes, "
        "les messages laissés après une interaction. "
        "Le problème n’est pas leur absence, mais leur dispersion."
    )

    st.write(
        "Les indicateurs classiques donnent une vue partielle. "
        "Les mots, eux, racontent ce qui se passe réellement sur le terrain."
    )

    # ------------------------------------------------------------
    # Cas 1
    # ------------------------------------------------------------
    st.header("Le churn silencieux")

    st.write(
        "La majorité des clients insatisfaits ne se plaignent pas ouvertement. "
        "Ils continuent d’utiliser le produit, répondent de manière neutre, "
        "puis ne renouvellent pas."
    )

    st.write(
        "Les retours sont courts, polis, sans alerte explicite : "
        "« Fonctionnel », « Ça fait le job », « Pas de souci particulier »."
    )

    st.write(
        "Pris individuellement, ces messages semblent anodins. "
        "Pris ensemble, ils révèlent une absence de valeur perçue, "
        "souvent visible plusieurs semaines avant la résiliation."
    )

    st.write(
        "L’analyse des verbatims permet d’identifier ces signaux faibles à temps "
        "et d’agir sur l’onboarding, la clarté d’usage et les moments clés "
        "avant que le churn ne devienne mesurable."
    )

    # ------------------------------------------------------------
    # Cas 2
    # ------------------------------------------------------------
    st.header("Le support qui traite sans apprendre")

    st.write(
        "Dans beaucoup de SaaS B2B, une part importante des tickets concerne "
        "des problèmes récurrents. Pourtant, ils n’apparaissent jamais comme tels."
    )

    st.write(
        "Un utilisateur parle d’un export compliqué. "
        "Un autre évoque une lenteur. "
        "Un troisième décrit une manipulation manuelle."
    )

    st.write(
        "Chaque message est traité séparément. "
        "Le problème de fond reste inchangé."
    )

    st.write(
        "L’analyse permet de regrouper ces retours dispersés en thèmes clairs "
        "et exploitables, transformant un flux de support en signal produit."
    )

    # ------------------------------------------------------------
    # Conclusion
    # ------------------------------------------------------------
    st.header("Pourquoi ces cas sont décisifs")

    st.write(
        "Les situations décrites ici ne sont pas exceptionnelles. "
        "Elles représentent le quotidien de nombreux SaaS B2B."
    )

    st.write(
        "Les signaux clients ne manquent pas. "
        "Ce qui manque, c’est une lecture structurée, partageable "
        "et orientée décision."
    )

    st.write(
        "Ce produit ne remplace pas l’humain. "
        "Il l’aide à voir ce qu’il ne peut pas agréger seul, "
        "et à décider plus justement."
    )
