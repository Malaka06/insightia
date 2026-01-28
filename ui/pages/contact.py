import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def render():
    st.title("Contactez-moi")
    st.write("Choisissez un message pré-écrit ou écrivez le vôtre.")

    with st.form("contact_form"):
        nom = st.text_input("Votre nom")
        email = st.text_input("Votre email")

        motif = st.selectbox(
            "Motif du contact",
            [
                "Remarques sur mon travail",
                "Recrutement / Opportunité",
                "Prise de contact simple",
            ],
        )

        messages_predefinis = {
            "Remarques sur mon travail": "Bonjour, j’ai découvert votre travail et je souhaite vous partager quelques remarques.",
            "Recrutement / Opportunité": "Bonjour, je vous contacte concernant une opportunité professionnelle.",
            "Prise de contact simple": "Bonjour, je souhaite simplement entrer en contact avec vous.",
        }

        choix_message = st.selectbox(
            "Choisissez un message pré-écrit (optionnel)",
            ["Aucun"] + list(messages_predefinis.keys()),
        )

        if choix_message != "Aucun":
            message = st.text_area(
                "Votre message",
                value=messages_predefinis[choix_message],
                height=160,
            )
        else:
            message = st.text_area("Votre message", height=160)

        submitted = st.form_submit_button("Envoyer")

    def envoyer_mail(nom: str, email: str, motif: str, message: str):
        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = "recrutementmalaka@gmail.com"
        msg["Subject"] = f"[Contact] {motif}"

        body = f"""Nom : {nom}
Email : {email}
Motif : {motif}

Message :
{message}

Cordialement,
{nom}
"""
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(
                st.secrets["SMTP_USER"],
                st.secrets["SMTP_PASS"],
            )
            server.sendmail(
                email,
                "recrutementmalaka@gmail.com",
                msg.as_string(),
            )

    if submitted:
        if nom and email and message.strip():
            try:
                envoyer_mail(nom, email, motif, message)
                st.success("Votre message a bien été envoyé.")
            except Exception as e:
                st.error(f"Erreur : {e}")
        else:
            st.warning("Veuillez remplir tous les champs.")
