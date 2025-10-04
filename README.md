# Knowledge Extractor

Application Streamlit permettant de centraliser un corpus documentaire et de générer des fiches de révision et des résumés au format PDF.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run streamlit_app.py
```

## Fonctionnalités principales

- Ingestion de documents depuis des fichiers (`.txt`, `.md`, `.rtf`, `.docx`, `.pdf`), du texte libre ou des pages web.
- Stockage des documents dans une base SQLite locale.
- Génération automatique de résumés et export en PDF.
- Création de fiches de révision structurées en quatre sections, exportées en PDF et mises à jour lorsque le corpus évolue.
- Génération de rapports CSV listant les fiches de révision et les résumés disponibles.

