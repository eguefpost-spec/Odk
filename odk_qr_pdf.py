#!/usr/bin/env python3
"""Génère un PDF des codes QR (App Users / ODK Collect) d'un projet ODK Central.

Pour chaque utilisateur mobile (App User) actif du projet, le script construit
le code QR de configuration au format attendu par ODK Collect
(JSON -> zlib deflate -> base64), exactement comme le fait l'interface web
d'ODK Central, puis assemble le tout dans un PDF imprimable.

Exemple :
    export ODK_PASSWORD='monMotDePasse'
    python3 odk_qr_pdf.py \
        --url https://odk.adkoul.online \
        --project 6 \
        --email saminou@adkoul.org \
        --out codes_qr_projet6.pdf
"""

import argparse
import base64
import getpass
import io
import json
import os
import sys
import zlib

try:
    import requests
    import qrcode
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except ImportError as exc:  # pragma: no cover
    sys.exit(
        f"Dépendance manquante ({exc.name}). Installez-les avec :\n"
        "    pip install -r requirements.txt"
    )


# --------------------------------------------------------------------------- #
# API ODK Central
# --------------------------------------------------------------------------- #
def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def login(base, email, password):
    """Ouvre une session et renvoie le token de l'utilisateur."""
    resp = requests.post(
        f"{base}/v1/sessions",
        json={"email": email, "password": password},
        timeout=30,
    )
    if resp.status_code == 401:
        sys.exit("Identifiants refusés (401). Vérifiez l'email / le mot de passe.")
    resp.raise_for_status()
    return resp.json()["token"]


def get_project(base, token, pid):
    resp = requests.get(f"{base}/v1/projects/{pid}", headers=_auth(token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_app_users(base, token, pid):
    """Renvoie la liste des App Users (field keys) du projet."""
    resp = requests.get(
        f"{base}/v1/projects/{pid}/app-users", headers=_auth(token), timeout=30
    )
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------- #
# Construction du code QR (format ODK Collect)
# --------------------------------------------------------------------------- #
def qr_settings_payload(base, fk_token, pid, project_name, managed=True):
    """Construit la charge utile base64 du QR de configuration ODK Collect.

    Format identique à celui de l'interface ODK Central :
    base64( zlib_deflate( JSON.stringify(settings) ) ).
    """
    general = {"server_url": f"{base}/v1/key/{fk_token}/projects/{pid}"}
    if managed:
        # Réglages d'un « Managed QR Code » (valeur par défaut d'ODK Central).
        general["form_update_mode"] = "match_exactly"
        general["autosend"] = "wifi_and_cellular"

    settings = {
        "general": general,
        "project": {"name": project_name},
        "admin": {},
    }
    raw = json.dumps(settings, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(zlib.compress(raw, 9)).decode("ascii")


def make_qr_image(payload):
    """Renvoie un buffer PNG (BytesIO) du code QR, lisible par reportlab."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# --------------------------------------------------------------------------- #
# Génération du PDF
# --------------------------------------------------------------------------- #
def build_pdf(entries, out_path, project_name):
    """entries : liste de (nom, image PIL du QR)."""
    page_w, page_h = A4
    cols, rows = 2, 3
    per_page = cols * rows

    margin = 15 * mm
    header_h = 16 * mm
    grid_w = page_w - 2 * margin
    grid_h = page_h - 2 * margin - header_h
    cell_w = grid_w / cols
    cell_h = grid_h / rows
    qr_size = min(cell_w, cell_h) - 14 * mm

    pdf = canvas.Canvas(out_path, pagesize=A4)

    for index, (name, image) in enumerate(entries):
        slot = index % per_page
        if slot == 0:
            if index:
                pdf.showPage()
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, page_h - margin, f"Codes QR — {project_name}")
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawString(
                margin,
                page_h - margin - 6 * mm,
                "Scannez avec ODK Collect : « ... » → Configurer via code QR.",
            )
            pdf.setFillColorRGB(0, 0, 0)

        col = slot % cols
        row = slot // cols
        cell_x = margin + col * cell_w
        cell_y = page_h - margin - header_h - (row + 1) * cell_h

        qr_x = cell_x + (cell_w - qr_size) / 2
        qr_y = cell_y + (cell_h - qr_size) / 2 + 4 * mm
        pdf.drawImage(
            ImageReader(image),
            qr_x,
            qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            mask="auto",
        )

        pdf.setFont("Helvetica-Bold", 11)
        label = name if len(name) <= 38 else name[:37] + "…"
        pdf.drawCentredString(cell_x + cell_w / 2, qr_y - 6 * mm, label)

    pdf.showPage()
    pdf.save()


# --------------------------------------------------------------------------- #
# Programme principal
# --------------------------------------------------------------------------- #
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="URL de base, ex. https://odk.adkoul.online")
    parser.add_argument("--project", required=True, type=int, help="ID du projet (ex. 6)")
    parser.add_argument("--email", required=True, help="Email de connexion ODK Central")
    parser.add_argument("--out", default="codes_qr.pdf", help="Fichier PDF de sortie")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="QR « non managé » (sans form_update_mode / autosend)",
    )
    parser.add_argument(
        "--include-revoked",
        action="store_true",
        help="Inclure aussi les App Users dont l'accès a été révoqué (sans token)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    base = args.url.rstrip("/")

    password = os.environ.get("ODK_PASSWORD")
    if not password:
        password = getpass.getpass(f"Mot de passe ODK pour {args.email} : ")

    print(f"→ Connexion à {base} …")
    token = login(base, args.email, password)

    project = get_project(base, token, args.project)
    project_name = project.get("name", f"Projet {args.project}")
    print(f"→ Projet : {project_name}")

    app_users = get_app_users(base, token, args.project)

    entries = []
    skipped = 0
    for fk in app_users:
        fk_token = fk.get("token")
        if not fk_token:
            if not args.include_revoked:
                skipped += 1
                continue
            # Sans token impossible de générer un QR exploitable.
            skipped += 1
            continue
        payload = qr_settings_payload(
            base, fk_token, args.project, project_name, managed=not args.legacy
        )
        entries.append((fk.get("displayName", "Sans nom"), make_qr_image(payload)))

    if not entries:
        sys.exit(
            "Aucun App User actif avec un code QR exploitable n'a été trouvé "
            f"(révoqués/ignorés : {skipped})."
        )

    build_pdf(entries, args.out, project_name)
    msg = f"✓ PDF généré : {args.out}  ({len(entries)} code(s) QR"
    if skipped:
        msg += f", {skipped} utilisateur(s) révoqué(s) ignoré(s)"
    print(msg + ")")


if __name__ == "__main__":
    main()
