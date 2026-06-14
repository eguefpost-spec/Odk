---
description: Vérifie les mises à jour disponibles pour Power BI Desktop et les plugins associés
---

Vérifie les mises à jour disponibles pour Power BI Desktop et les extensions installées.

## Ce que ce skill fait

1. Liste la version actuelle de Power BI Desktop détectée dans le projet
2. Identifie les connecteurs de données et visuels personnalisés utilisés
3. Signale les mises à jour disponibles ou les versions recommandées
4. Propose les actions de mise à jour à effectuer

## Instructions

Analyse les fichiers du projet (`.pbix`, `pbixproj`, manifests de visuels) pour identifier :
- La version de Power BI utilisée pour créer les rapports
- Les visuels personnalisés (`.pbiviz`) et leur version
- Les connecteurs de données tiers référencés

Dresse un rapport clair avec : version actuelle → version recommandée, et les impacts éventuels.
