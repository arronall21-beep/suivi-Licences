# Scénario de démonstration (≈ 10 minutes)

Pré-requis : `docker compose up --build`, puis ouvrir http://localhost:8080 et se connecter avec `admin@example.com` / `admin123`.

| # | Action | Ce qu'il faut montrer |
|---|---|---|
| 1 | Ouvrir l'application | Base vide, invitation à importer |
| 2 | **Import / Export** → déposer `data/Suivi_Licence.xlsx` → *Lancer l'import* | Rapport : lignes analysées, importées, ignorées ; anomalies détectées (doublon, date invalide, référence générée, sur-allocation Excel, contrat manquant) |
| 3 | *Voir le dashboard* | KPIs, utilisation des licences, coûts, graphiques, prochains renouvellements |
| 4 | Cliquer sur la barre « ≤ 30 jours » | Redirection vers la liste filtrée des actifs critiques |
| 5 | **Actifs → Licences**, filtre Statut = Critique | Recherche, tri par colonne, badges de statut et de criticité, barre d'utilisation |
| 6 | Ouvrir une licence (ex. *Adobe Creative Cloud*) | Fiche : dates, coûts, contrat, quantités totale / affectée / disponible, taux |
| 7 | *Modifier* → saisir un plan d'action → Enregistrer | Mise à jour immédiate |
| 8 | *Affecter* → utilisateur + poste, quantité 1 | Quantité disponible −1, taux recalculé |
| 9 | *Affecter* avec une quantité de 9999 | Refus : « Sur-allocation refusée » |
| 10 | **Contrats** | Préavis, date de début de renouvellement, « préavis atteint » |
| 11 | **Renouvellements** | Planning par mois, retards en tête, priorité P1/P2/P3, budget |
| 12 | **Alertes** → *Lancer le contrôle maintenant* | Alertes J-90 / J-60 / J-30 / J-7 / expirés et historique ; un second lancement ne crée aucun doublon |
| 13 | **Import / Export** → *Télécharger l'export Excel* | Les 7 onglets, statuts colorés, planning et dashboard générés depuis la base |
| 14 | (option) Se reconnecter avec `viewer@example.com` | Consultation seule : aucun bouton de modification |
