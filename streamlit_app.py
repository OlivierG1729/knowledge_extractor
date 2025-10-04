"""Streamlit interface for the knowledge extractor application."""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st

from app import db
from app.ingestion import IngestionError, ingest_text_input, ingest_uploaded_file, ingest_url
from app.services import KnowledgeService

BASE_DIR = Path(__file__).parent


@st.cache_resource(show_spinner=False)
def get_service() -> KnowledgeService:
    return KnowledgeService(BASE_DIR)


def corpus_management_page(service: KnowledgeService) -> None:
    st.header("Gestion du corpus")
    st.markdown(
        "Ajoutez des documents au corpus en téléchargeant un fichier, en collant un texte ou en fournissant une URL."
    )
    tab_file, tab_text, tab_url = st.tabs(["Fichier", "Texte", "URL"])

    with tab_file:
        uploaded = st.file_uploader("Téléverser un document", type=["txt", "md", "rtf", "docx", "pdf"])
        if uploaded is not None and st.button("Ajouter le fichier", key="add_file"):
            try:
                title, text, saved_path = ingest_uploaded_file(
                    BASE_DIR,
                    file_name=uploaded.name,
                    data=uploaded.getvalue(),
                    mime_type=uploaded.type,
                )
                service.add_document(
                    title=title,
                    source_type="fichier",
                    source_path=str(saved_path),
                    url=None,
                    text_content=text,
                )
                st.success(f"Document '{title}' ajouté au corpus.")
            except IngestionError as error:
                st.error(str(error))

    with tab_text:
        title = st.text_input("Titre (optionnel)")
        text_content = st.text_area("Contenu du document")
        if st.button("Ajouter le texte", key="add_text"):
            try:
                final_title, text = ingest_text_input(text_content, title=title or None)
                service.add_document(
                    title=final_title,
                    source_type="texte",
                    source_path=None,
                    url=None,
                    text_content=text,
                )
                st.success(f"Document '{final_title}' ajouté au corpus.")
            except IngestionError as error:
                st.error(str(error))

    with tab_url:
        url = st.text_input("Adresse URL")
        if st.button("Ajouter la page web", key="add_url") and url:
            try:
                title, text, saved_path = ingest_url(BASE_DIR, url)
                service.add_document(
                    title=title,
                    source_type="url",
                    source_path=str(saved_path),
                    url=url,
                    text_content=text,
                )
                st.success(f"Document '{title}' provenant de l'URL ajouté au corpus.")
            except IngestionError as error:
                st.error(str(error))

    st.subheader("Documents disponibles")
    documents = service.list_documents()
    if not documents:
        st.info("Aucun document enregistré pour le moment.")
        return
    for document in documents:
        with st.expander(document["title"], expanded=False):
            st.write(f"**Source :** {document['source_type']}")
            if document.get("url"):
                st.write(f"**URL :** {document['url']}")
            st.write(document["text_content"][:500] + ("…" if len(document["text_content"]) > 500 else ""))
            if st.button("Générer / mettre à jour le résumé", key=f"summary_{document['id']}"):
                summary = service.build_summary(document["id"])
                if summary:
                    st.success("Résumé enregistré et exporté en PDF.")
                else:
                    st.warning("Impossible de générer le résumé.")


def revision_sheet_page(service: KnowledgeService) -> None:
    st.header("Fiches de révision")
    theme = st.text_input("Thématique à réviser")
    if st.button("Générer la fiche", key="generate_sheet"):
        if not theme:
            st.warning("Veuillez saisir une thématique.")
        else:
            markdown = service.generate_revision_sheet(theme)
            if not markdown:
                st.warning("Aucun document dans le corpus pour générer une fiche.")
            else:
                st.success("Fiche générée et enregistrée en PDF.")
                st.markdown(markdown)

    st.subheader("Fiches enregistrées")
    sheets = db.fetch_revision_sheets(BASE_DIR)
    if sheets:
        for sheet in sheets:
            with st.expander(sheet["theme"], expanded=False):
                st.markdown(sheet["content"])
                st.caption(f"PDF : {sheet['pdf_path']}")
    else:
        st.info("Aucune fiche enregistrée pour le moment.")


def summaries_page(service: KnowledgeService) -> None:
    st.header("Résumés des documents")
    summaries = db.fetch_summaries(BASE_DIR)
    documents = {doc["id"]: doc for doc in service.list_documents()}
    if not summaries:
        st.info("Aucun résumé généré pour le moment.")
        return
    for summary in summaries:
        document = documents.get(summary["document_id"])
        if not document:
            continue
        with st.expander(document["title"], expanded=False):
            st.write(summary["summary"])
            st.caption(f"PDF : {summary['pdf_path']}")


def reports_page() -> None:
    st.header("Rapports de suivi")
    revision_report = BASE_DIR / "data" / "reports" / "revision_sheets_overview.csv"
    summary_report = BASE_DIR / "data" / "reports" / "document_summaries_overview.csv"

    if revision_report.exists():
        st.subheader("Fiches de révision")
        df_revision = pd.read_csv(revision_report)
        st.dataframe(df_revision)
    else:
        st.info("Aucun rapport de fiches de révision disponible.")

    if summary_report.exists():
        st.subheader("Résumés")
        df_summary = pd.read_csv(summary_report)
        st.dataframe(df_summary)
    else:
        st.info("Aucun rapport de résumés disponible.")


def main() -> None:
    st.set_page_config(page_title="Knowledge Extractor", layout="wide")
    service = get_service()

    menu = {
        "Gestion du corpus": corpus_management_page,
        "Fiches de révision": revision_sheet_page,
        "Résumés": summaries_page,
        "Rapports": lambda service: reports_page(),
    }
    choice = st.sidebar.radio("Navigation", list(menu.keys()))
    page = menu[choice]
    page(service)


if __name__ == "__main__":
    main()

