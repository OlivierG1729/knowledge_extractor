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

## Polices PDF intégrées

Les exports PDF utilisent la police Unicode **DejaVu Sans** pour éviter les erreurs
``FPDFUnicodeEncodingException`` lors de l'écriture de ponctuations ou caractères
non ASCII. Les fichiers `.ttf` ne sont plus suivis dans le dépôt : ils sont
compressés (gzip) et encodés en Base64 dans `app/assets/dejavu_sans_data.py`. Au
moment de l'exécution, `PDFDocument` extrait ces polices dans un répertoire de
cache (`/tmp/knowledge_extractor_fonts` par défaut) puis les enregistre auprès de
FPDF.

### Régénérer les polices

En cas de mise à jour des fichiers `DejaVuSans.ttf` / `DejaVuSans-Bold.ttf`,
exécuter le script suivant :

```bash
python scripts/generate_dejavu_font_data.py \
    --regular /chemin/vers/DejaVuSans.ttf \
    --bold /chemin/vers/DejaVuSans-Bold.ttf
```

Le script réécrit `app/assets/dejavu_sans_data.py` avec les nouvelles données
encodées.

