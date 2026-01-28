import streamlit as st

def render():
    st.title("À propos de moi")

    st.header("L’insight")
    st.write(
        "Un insight ne vient pas d’une accumulation de données ou de graphiques. "
        "Il naît d’un moment de clarté, lorsque les mots des utilisateurs — jusque-là dispersés, "
        "répétitifs ou confus — révèlent ce qui bloque réellement, ce qui irrite et ce qui appelle une décision."
    )

    st.header("La méthode")
    st.write(
        "Je développe InsightIA, un outil d’analyse de verbatims clients basé sur une approche "
        "de traitement du langage naturel volontairement maîtrisée et explicable. "
        "Les retours sont analysés hors ligne, structurés selon des thèmes métier explicites, puis priorisés "
        "à partir de critères simples (volume, sévérité, caractère bloquant) afin de soutenir des décisions "
        "compréhensibles et défendables."
    )

    st.header("La démarche")
    st.write(
        "Ce projet s’inscrit dans une démarche de construction et d’apprentissage continus, inspirée par "
        "l’idée de confronter rapidement les hypothèses au réel. Chaque retour, positif ou critique, "
        "devient un signal pour améliorer l’outil, affiner la méthode et rester aligné avec les besoins réels."
    )
