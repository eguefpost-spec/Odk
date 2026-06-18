#!/usr/bin/env bash
#
# Rapport de synthèse des soumissions — Projet "Mission conjointe RRM"
# Serveur ODK Central : odk.adkoul.online
#
# Prérequis : curl, jq, python3, bc
# Usage : ./rapport_soumissions_rrm.sh
#
set -euo pipefail

BASE="https://odk.adkoul.online"
EMAIL="saminou@adkoul.org"
PROJET="Mission conjointe RRM"

read -rsp "Mot de passe ODK pour $EMAIL : " PASSWORD; echo

# 1) Ouverture de session ----------------------------------------------------
TOKEN=$(curl -s -X POST "$BASE/v1/sessions" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r .token)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "ERREUR : authentification échouée." >&2
  exit 1
fi
AUTH=(-H "Authorization: Bearer $TOKEN")

# 2) Identification du projet ------------------------------------------------
PID=$(curl -s "$BASE/v1/projects" "${AUTH[@]}" \
  | jq -r --arg n "$PROJET" '.[] | select(.name==$n) | .id')

if [ -z "$PID" ]; then
  echo "ERREUR : projet \"$PROJET\" introuvable. Projets disponibles :" >&2
  curl -s "$BASE/v1/projects" "${AUTH[@]}" | jq -r '.[] | "  - \(.name) (id \(.id))"' >&2
  exit 1
fi

echo "=================================================================="
echo " RAPPORT DE SYNTHESE — $PROJET (projet #$PID)"
echo " Genere le : $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================================="

# 3) Parcours des formulaires ------------------------------------------------
FORMS_JSON=$(curl -s "$BASE/v1/projects/$PID/forms" "${AUTH[@]}")

echo "$FORMS_JSON" | jq -c '.[]' | while read -r form; do
  XMLID=$(echo "$form" | jq -r '.xmlFormId')
  NAME=$(echo "$form" | jq -r '.name')

  SUBS=$(curl -s "$BASE/v1/projects/$PID/forms/$XMLID/submissions" "${AUTH[@]}")
  N=$(echo "$SUBS" | jq 'length')

  echo
  echo "------------------------------------------------------------------"
  echo "Formulaire : $NAME  [$XMLID]"
  echo "  Nombre de soumissions : $N"

  if [ "$N" -gt 0 ]; then
    echo "  Repartition par date de soumission :"
    echo "$SUBS" | jq -r '.[].createdAt[0:10]' | sort | uniq -c \
      | awk '{printf "    %s : %s soumission(s)\n", $2, $1}'

    echo "  Repartition par auteur (submitter) :"
    echo "$SUBS" | jq -r '.[].submitter.displayName // "inconnu"' | sort | uniq -c \
      | sort -rn | awk '{c=$1; $1=""; printf "    %s : %s soumission(s)\n", substr($0,2), c}'

    echo "  Statut de revue :"
    echo "$SUBS" | jq -r '.[].reviewState // "aucun"' | sort | uniq -c \
      | awk '{printf "    %s : %s\n", $2, $1}'
  fi
done

# 4) Total global ------------------------------------------------------------
echo
echo "=================================================================="
GRAND_TOTAL=$(echo "$FORMS_JSON" | jq -r '.[].xmlFormId' | while read -r XMLID; do
  curl -s "$BASE/v1/projects/$PID/forms/$XMLID/submissions" "${AUTH[@]}" | jq 'length'
done | paste -sd+ - | bc)
echo " TOTAL GENERAL des soumissions du projet : ${GRAND_TOTAL:-0}"
echo "=================================================================="

# 5) (Optionnel) export brut CSV de chaque formulaire ------------------------
read -rp "Exporter aussi les donnees brutes en CSV (zip) ? [o/N] " EXPORT
if [[ "${EXPORT:-N}" =~ ^[oO]$ ]]; then
  mkdir -p export_rrm
  echo "$FORMS_JSON" | jq -r '.[].xmlFormId' | while read -r XMLID; do
    echo "  -> export_rrm/${XMLID}.csv.zip"
    curl -s "$BASE/v1/projects/$PID/forms/$XMLID/submissions.csv.zip" \
      "${AUTH[@]}" -o "export_rrm/${XMLID}.csv.zip"
  done
  echo "Exports CSV dans ./export_rrm/"
fi
