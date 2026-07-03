#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copie un formulaire d'un projet ODK Central source vers tous les autres projets.

Cas d'usage : le formulaire « F4 - Retour communautaire (feedback et plaintes) »
existe dans le projet DDC et doit être publié dans tous les autres projets.

Le script :
  1. se connecte à ODK Central ;
  2. localise le formulaire source (par identifiant ou nom, ex. « F4 ») dans le
     projet source (ex. « DDC ») ;
  3. télécharge sa définition (XLSForm si disponible, sinon XML) et ses
     fichiers joints (médias, CSV…) ;
  4. le publie dans chaque autre projet non archivé (création, ou nouvelle
     version avec --update si le formulaire y existe déjà) ;
  5. avec --grant-app-users, donne l'accès au nouveau formulaire à tous les
     App Users actifs de chaque projet (sinon ils ne le verront pas dans
     ODK Collect).

Par défaut le script fait un ESSAI À BLANC (dry-run) : il montre ce qu'il
ferait sans rien modifier. Ajoutez --apply pour exécuter réellement.

Exemple :
    export ODK_PASSWORD='monMotDePasse'
    python3 deploy_form_all_projects.py \
        --url https://odk.adkoul.online \
        --email saminou@adkoul.org \
        --source-project DDC \
        --form F4 \
        --grant-app-users \
        --apply
"""

import argparse
import getpass
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Dépendance manquante : pip install requests")

XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class Central:
    def __init__(self, base, email, password):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        r = self.s.post(f"{self.base}/v1/sessions",
                        json={"email": email, "password": password}, timeout=30)
        if r.status_code == 401:
            sys.exit("Identifiants refusés (401).")
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['token']}"

    def get(self, path, **kw):
        r = self.s.get(f"{self.base}/v1{path}", timeout=60, **kw)
        r.raise_for_status()
        return r

    def projects(self):
        return self.get("/projects").json()

    def forms(self, pid):
        return self.get(f"/projects/{pid}/forms").json()

    def app_users(self, pid):
        return self.get(f"/projects/{pid}/app-users").json()


def find_project(projects, needle):
    needle_l = str(needle).lower()
    for p in projects:
        if str(p["id"]) == str(needle) or needle_l in p["name"].lower():
            return p
    sys.exit(f"Projet source « {needle} » introuvable. Projets disponibles : "
             + ", ".join(f"{p['id']}:{p['name']}" for p in projects))


def find_form(forms, needle):
    needle_l = needle.lower()
    matches = [f for f in forms
               if needle_l in f["xmlFormId"].lower()
               or needle_l in (f.get("name") or "").lower()]
    if not matches:
        sys.exit(f"Formulaire « {needle} » introuvable dans le projet source. "
                 "Formulaires : " + ", ".join(f["xmlFormId"] for f in forms))
    if len(matches) > 1:
        sys.exit("Plusieurs formulaires correspondent : "
                 + ", ".join(f["xmlFormId"] for f in matches)
                 + " — précisez avec --form.")
    return matches[0]


def download_definition(api, pid, fid):
    """Renvoie (bytes, content_type). XLSForm de préférence, sinon XML."""
    r = api.s.get(f"{api.base}/v1/projects/{pid}/forms/{fid}.xlsx", timeout=120)
    if r.status_code == 200:
        return r.content, XLSX_CT
    r = api.get(f"/projects/{pid}/forms/{fid}.xml")
    return r.content, "application/xml"


def download_attachments(api, pid, fid):
    """Renvoie [(nom, bytes|None)] ; None = lié à une entity list (auto)."""
    atts = api.get(f"/projects/{pid}/forms/{fid}/attachments").json()
    out = []
    for a in atts:
        if a.get("datasetExists"):
            out.append((a["name"], None))       # lié à une entity list
            continue
        if not a.get("exists") and not a.get("blobExists"):
            out.append((a["name"], b""))         # attendu mais absent à la source
            continue
        r = api.get(f"/projects/{pid}/forms/{fid}/attachments/{a['name']}")
        out.append((a["name"], r.content))
    return out


def publish_to_project(api, pid, fid, definition, ct, attachments, update, apply):
    existing = {f["xmlFormId"] for f in api.forms(pid)}
    exists = fid in existing

    if exists and not update:
        return "déjà présent (ignoré — utilisez --update pour une nouvelle version)"
    if not apply:
        return ("mettrait à jour (nouvelle version)" if exists
                else "publierait le formulaire")

    headers = {"Content-Type": ct}
    if ct == XLSX_CT:
        headers["X-XlsForm-FormId-Fallback"] = fid

    if exists:  # nouvelle version via draft
        r = api.s.post(f"{api.base}/v1/projects/{pid}/forms/{fid}/draft"
                       "?ignoreWarnings=true",
                       data=definition, headers=headers, timeout=120)
        r.raise_for_status()
    else:
        r = api.s.post(f"{api.base}/v1/projects/{pid}/forms"
                       "?ignoreWarnings=true&publish=false",
                       data=definition, headers=headers, timeout=120)
        r.raise_for_status()

    for name, blob in attachments:
        if blob is None or blob == b"":
            continue  # entity list (liée automatiquement) ou absent à la source
        r = api.s.post(
            f"{api.base}/v1/projects/{pid}/forms/{fid}/draft/attachments/{name}",
            data=blob, headers={"Content-Type": "application/octet-stream"},
            timeout=120)
        r.raise_for_status()

    r = api.s.post(f"{api.base}/v1/projects/{pid}/forms/{fid}/draft/publish",
                   timeout=60)
    if r.status_code == 409:  # même numéro de version déjà publié
        stamp = time.strftime("%Y%m%d%H%M%S")
        r = api.s.post(f"{api.base}/v1/projects/{pid}/forms/{fid}/draft/publish"
                       f"?version={stamp}", timeout=60)
    r.raise_for_status()
    return "nouvelle version publiée" if exists else "publié"


def grant_app_users(api, pid, fid, apply):
    users = [u for u in api.app_users(pid) if u.get("token")]
    if not apply:
        return f"donnerait l'accès à {len(users)} App User(s)"
    done = 0
    for u in users:
        r = api.s.post(
            f"{api.base}/v1/projects/{pid}/forms/{fid}/assignments/app-user/{u['id']}",
            timeout=30)
        if r.status_code in (200, 409):   # 409 = déjà assigné
            done += 1
        else:
            r.raise_for_status()
    return f"accès donné à {done}/{len(users)} App User(s)"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--source-project", required=True,
                   help="Projet source : id ou partie du nom (ex. DDC)")
    p.add_argument("--form", required=True,
                   help="Formulaire à copier : partie de l'id ou du nom (ex. F4)")
    p.add_argument("--projects", nargs="*",
                   help="Limiter aux projets cibles donnés (ids ou noms). "
                        "Par défaut : tous les projets non archivés sauf la source.")
    p.add_argument("--update", action="store_true",
                   help="Publier une nouvelle version là où le formulaire existe déjà")
    p.add_argument("--grant-app-users", action="store_true",
                   help="Donner l'accès au formulaire à tous les App Users actifs")
    p.add_argument("--apply", action="store_true",
                   help="Exécuter réellement (sinon : essai à blanc)")
    args = p.parse_args(argv)

    password = os.environ.get("ODK_PASSWORD") or getpass.getpass(
        f"Mot de passe ODK pour {args.email} : ")
    api = Central(args.url, args.email, password)

    projects = api.projects()
    source = find_project(projects, args.source_project)
    form = find_form(api.forms(source["id"]), args.form)
    fid = form["xmlFormId"]
    print(f"Source : projet {source['id']} « {source['name']} », "
          f"formulaire « {form.get('name') or fid} » ({fid})")

    definition, ct = download_definition(api, source["id"], fid)
    attachments = download_attachments(api, source["id"], fid)
    kind = "XLSForm" if ct == XLSX_CT else "XML"
    print(f"Définition téléchargée ({kind}, {len(definition)} octets), "
          f"{len(attachments)} pièce(s) jointe(s)")
    for name, blob in attachments:
        note = ("liée à une entity list" if blob is None
                else "absente à la source !" if blob == b"" else f"{len(blob)} octets")
        print(f"   - {name} ({note})")

    targets = [pr for pr in projects
               if pr["id"] != source["id"] and not pr.get("archived")]
    if args.projects:
        wanted = [w.lower() for w in args.projects]
        targets = [pr for pr in targets
                   if str(pr["id"]) in args.projects
                   or any(w in pr["name"].lower() for w in wanted)]
    if not targets:
        sys.exit("Aucun projet cible.")

    mode = "APPLICATION RÉELLE" if args.apply else "ESSAI À BLANC (ajoutez --apply)"
    print(f"\n{mode} — {len(targets)} projet(s) cible(s) :\n")

    failures = 0
    for pr in targets:
        try:
            status = publish_to_project(api, pr["id"], fid, definition, ct,
                                        attachments, args.update, args.apply)
            extra = ""
            if args.grant_app_users and "ignoré" not in status:
                extra = " ; " + grant_app_users(api, pr["id"], fid, args.apply)
            print(f"  [{pr['id']:>3}] {pr['name']:35} → {status}{extra}")
        except requests.HTTPError as e:
            failures += 1
            body = e.response.text[:200] if e.response is not None else str(e)
            print(f"  [{pr['id']:>3}] {pr['name']:35} → ERREUR : {body}")

    print(f"\nTerminé. {len(targets) - failures}/{len(targets)} projet(s) OK.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
