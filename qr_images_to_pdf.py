#!/usr/bin/env python3
"""Assemble des images de codes QR (déjà exportées) en un PDF imprimable.

- Ordonne les images par numéro de téléchargement (« ..._1.png », « ..._2.png »…).
- Détecte et retire les doublons (même contenu de QR décodé).
- Étiquette chaque QR avec un nom fourni dans --names (une ligne par QR, dans
  l'ordre), sinon « Utilisateur N ».
"""

import argparse
import base64
import glob
import io
import json
import os
import re
import sys
import zlib

import cv2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def order_key(path):
    """0 pour « ...chargement.png », N pour « ...chargement_N.png »."""
    m = re.search(r"_(\d+)\.png$", path)
    return int(m.group(1)) if m else 0


def decode_qr(path):
    img = cv2.imread(path)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return data or None


def load_images(images_dir, dedupe=True):
    files = sorted(glob.glob(os.path.join(images_dir, "*.png")), key=order_key)
    entries, seen = [], set()
    for path in files:
        payload = decode_qr(path)
        key = payload if payload else os.path.basename(path)
        if dedupe and key in seen:
            print(f"  doublon ignoré : {os.path.basename(path)}")
            continue
        seen.add(key)
        entries.append(path)
    return entries


def build_pdf(items, out_path, title):
    """items : liste de (nom, chemin image)."""
    page_w, page_h = A4
    cols, rows = 2, 3
    per_page = cols * rows
    margin = 15 * mm
    header_h = 16 * mm
    grid_w = page_w - 2 * margin
    grid_h = page_h - 2 * margin - header_h
    cell_w, cell_h = grid_w / cols, grid_h / rows
    qr_size = min(cell_w, cell_h) - 14 * mm

    pdf = canvas.Canvas(out_path, pagesize=A4)
    for index, (name, path) in enumerate(items):
        slot = index % per_page
        if slot == 0:
            if index:
                pdf.showPage()
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, page_h - margin, title)
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawString(
                margin, page_h - margin - 6 * mm,
                "ODK Collect : menu ⋮ → Configurer via code QR → scanner.",
            )
            pdf.setFillColorRGB(0, 0, 0)

        col, row = slot % cols, slot // cols
        cell_x = margin + col * cell_w
        cell_y = page_h - margin - header_h - (row + 1) * cell_h
        qr_x = cell_x + (cell_w - qr_size) / 2
        qr_y = cell_y + (cell_h - qr_size) / 2 + 4 * mm
        pdf.drawImage(ImageReader(path), qr_x, qr_y, width=qr_size, height=qr_size,
                      preserveAspectRatio=True, mask="auto")
        pdf.setFont("Helvetica-Bold", 11)
        label = name if len(name) <= 38 else name[:37] + "…"
        pdf.drawCentredString(cell_x + cell_w / 2, qr_y - 6 * mm, label)
    pdf.showPage()
    pdf.save()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images", required=True, help="Dossier contenant les .png des QR")
    p.add_argument("--names", help="Fichier texte : un nom par ligne, dans l'ordre")
    p.add_argument("--out", default="codes_qr.pdf")
    p.add_argument("--title", default="Codes QR — Utilisateurs mobiles")
    p.add_argument("--keep-duplicates", action="store_true")
    args = p.parse_args(argv)

    paths = load_images(args.images, dedupe=not args.keep_duplicates)
    if not paths:
        sys.exit("Aucune image .png trouvée.")

    names = []
    if args.names and os.path.exists(args.names):
        with open(args.names, encoding="utf-8") as fh:
            names = [ln.strip() for ln in fh if ln.strip()]

    items = []
    for i, path in enumerate(paths):
        name = names[i] if i < len(names) else f"Utilisateur {i + 1}"
        items.append((name, path))

    build_pdf(items, args.out, args.title)
    print(f"✓ PDF généré : {args.out} ({len(items)} code(s) QR)")


if __name__ == "__main__":
    main()
