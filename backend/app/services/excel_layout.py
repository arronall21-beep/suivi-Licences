"""Structure des onglets métier de Suivi_Licence.xlsx (partagée entre import et export).

Chaque colonne : (libellé exporté, clé interne, type, alias acceptés à l'import).
Types : str, date, int, money, vendor, contract, criticality, computed (export uniquement).
Les alias sont comparés après normalisation (minuscules, sans accents ni ponctuation).
"""

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Col:
    label: str
    key: str
    kind: str = "str"
    aliases: list[str] = field(default_factory=list)

    @property
    def importable(self) -> bool:
        return self.kind != "computed"


@dataclass
class Sheet:
    name: str
    category: str | None  # LICENCE... ou CONTRACT / PLANNING / DASHBOARD
    columns: list[Col]
    importable: bool = True
    aliases: list[str] = field(default_factory=list)


def norm(text) -> str:
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


REF = ["reference", "ref", "id", "code", "identifiant", "n", "no", "numero"]
VENDOR = ["fournisseur", "editeur", "editeurfournisseur", "constructeur", "vendor", "editeurconstructeur"]
CONTRACT = ["contrat", "referencecontrat", "refcontrat", "contratassocie", "ncontrat"]
OWNER = ["responsable", "responsableinterne", "proprietaire", "gestionnaire", "owner", "referent"]
DEPT = ["direction", "directionutilisatrice", "departement", "service", "entite", "directionmetier"]
START = [
    "datedebut",
    "debut",
    "datededebut",
    "dateacquisition",
    "datedachat",
    "datemiseenservice",
    "dateemission",
    "datedebutcontrat",
]
END = [
    "dateexpiration",
    "datedexpiration",
    "expiration",
    "datefin",
    "datedefin",
    "echeance",
    "dateecheance",
    "datederenouvellement",
    "daterenouvellement",
    "finvalidite",
    "datefinvalidite",
]
CRIT = ["criticite", "criticity", "niveaucriticite", "priorite"]
COST = ["coutannuel", "coutannuelht", "montantannuel", "cout", "couteur", "coutannueleur", "montant"]
BUDGET = ["budgetestime", "budget", "budgetrenouvellement", "budgetprevisionnel", "budgetprevu", "coutrenouvellement"]
ACTION = ["plandaction", "planaction", "action", "actions", "actionaprevoir"]
OBS = ["observations", "observation", "commentaire", "commentaires", "remarques", "notes", "colonne1"]

COMMON_TAIL = [
    Col("Responsable interne", "internal_owner", aliases=OWNER),
    Col("Direction utilisatrice", "user_department", aliases=DEPT),
]
LIFECYCLE_COLS = [
    Col("Jours restants", "days_remaining", "computed", ["joursrestants", "nbjoursrestants"]),
    Col("Statut", "status", "computed", ["statut", "etat", "status"]),
]
MONEY_TAIL = [
    Col("Criticité", "criticality", "criticality", CRIT),
    Col("Coût annuel", "annual_cost", "money", COST),
    Col("Budget estimé", "budget_estimated", "money", BUDGET),
    Col("Plan d'action", "action_plan", aliases=ACTION),
    Col("Observations", "observation", aliases=OBS),
]

LICENCES = Sheet(
    "Licences_Logicielles",
    "LICENCE",
    [
        Col("Référence", "reference", aliases=REF + ["reflicence", "referencelicence"]),
        Col(
            "Nom du logiciel",
            "name",
            aliases=["nomdulogiciel", "logiciel", "nom", "produit", "designation", "licence", "application"],
        ),
        Col("Éditeur / Fournisseur", "vendor", "vendor", VENDOR),
        Col("Type de licence", "lic_type", aliases=["typedelicence", "typelicence", "type"]),
        Col("Clé de licence", "license_key", aliases=["cledelicence", "clelicence", "cle", "licensekey"]),
        Col(
            "Quantité totale",
            "total_quantity",
            "int",
            ["quantitetotale", "quantite", "qte", "qtetotale", "nombre", "nblicences", "nombredelicences", "totallicences"],
        ),
        Col(
            "Quantité utilisée",
            "used_quantity",
            "int",
            ["quantiteutilisee", "utilisees", "qteutilisee", "nbutilisees", "licencesutilisees", "utilise"],
        ),
        Col("Quantité disponible", "available_quantity", "computed", ["quantitedisponible", "disponibles", "qtedisponible"]),
        Col("Taux d'utilisation (%)", "usage_rate", "computed", ["tauxdutilisation", "tauxutilisation", "taux"]),
        Col("Contrat", "contract", "contract", CONTRACT),
        *COMMON_TAIL,
        Col("Date de début", "start_date", "date", START),
        Col("Date d'expiration", "end_date", "date", END),
        *LIFECYCLE_COLS,
        *MONEY_TAIL,
    ],
    aliases=["licences", "licence", "licenceslogicielles", "logiciels"],
)

CERTIFICATS = Sheet(
    "Certificats",
    "CERTIFICAT",
    [
        Col("Référence", "reference", aliases=REF + ["refcertificat"]),
        Col(
            "Nom / Domaine",
            "name",
            aliases=[
                "nomdomaine",
                "domaine",
                "servicedomaine",
                "nom",
                "cn",
                "commonname",
                "nomducertificat",
                "certificat",
                "designation",
            ],
        ),
        Col("Type de certificat", "cert_type", aliases=["typedecertificat", "typecertificat", "type"]),
        Col("Autorité de certification", "authority", aliases=["autoritedecertification", "autorite", "ac", "emetteur", "ca"]),
        Col(
            "Serveur / Application cible",
            "server_app_target",
            aliases=["serveurapplicationcible", "serveurapplication", "serveur", "applicationcible", "cible", "serveurcible"],
        ),
        Col("Environnement", "environment", aliases=["environnement", "env"]),
        Col("Fournisseur", "vendor", "vendor", VENDOR),
        Col("Contrat", "contract", "contract", CONTRACT),
        *COMMON_TAIL,
        Col("Date d'émission", "start_date", "date", START),
        Col("Date d'expiration", "end_date", "date", END),
        *LIFECYCLE_COLS,
        *MONEY_TAIL,
    ],
    aliases=["certificat", "certificats", "certificatsssl"],
)

MATERIELS = Sheet(
    "Materiels",
    "MATERIEL",
    [
        Col("Référence", "reference", aliases=REF + ["refmateriel", "inventaire", "ninventaire"]),
        Col("Désignation", "name", aliases=["designation", "nom", "equipement", "materiel", "libelle"]),
        Col("Marque", "brand", aliases=["marque", "constructeur"]),
        Col("Modèle", "model", aliases=["modele", "model"]),
        Col("Numéro de série", "serial_number", aliases=["numerodeserie", "nserie", "serie", "sn", "serialnumber", "numserie"]),
        Col("Site / Localisation", "site_location", aliases=["sitelocalisation", "site", "localisation", "emplacement"]),
        Col("Fournisseur", "vendor", "vendor", ["fournisseur", "vendor", "prestataire", "revendeur"]),
        Col("Contrat", "contract", "contract", CONTRACT),
        *COMMON_TAIL,
        Col("Date d'acquisition", "start_date", "date", START),
        Col(
            "Date de fin de contrat",
            "end_date",
            "date",
            ["datefin", "datedefin", "datefincontrat", "datedefindecontrat", "echeance"],
        ),
        Col("Fin de garantie", "warranty_end_date", "date", ["findegarantie", "fingarantie", "datefingarantie", "garantie"]),
        Col(
            "Fin de support",
            "support_end_date",
            "date",
            ["findesupport", "finsupport", "datefinsupport", "eos", "eol", "finsupportconstructeur"],
        ),
        Col(
            "Type de contrat support",
            "support_contract_type",
            aliases=["typedecontratsupport", "typecontratsupport", "contratsupport", "typesupport"],
        ),
        *LIFECYCLE_COLS,
        *MONEY_TAIL,
    ],
    aliases=["materiel", "materiels", "equipements", "hardware"],
)

APPLICATIONS = Sheet(
    "Applications",
    "APPLICATION",
    [
        Col("Référence", "reference", aliases=REF + ["refapplication"]),
        Col("Nom de l'application", "name", aliases=["nomdelapplication", "application", "nom", "nomapplication", "designation"]),
        Col("Propriétaire métier", "business_owner", aliases=["proprietairemetier", "metier", "businessowner"]),
        Col("Responsable technique", "internal_owner", aliases=["responsabletechnique"] + OWNER),
        Col("Direction utilisatrice", "user_department", aliases=DEPT),
        Col(
            "Hébergement",
            "hosting_env",
            aliases=["hebergement", "environnementdhebergement", "environnementhebergement", "hosting"],
        ),
        Col("Prestataire", "service_provider", aliases=["prestataire", "tma", "infogerant", "serviceprovider"]),
        Col("Fournisseur", "vendor", "vendor", VENDOR),
        Col("Contrat", "contract", "contract", CONTRACT),
        Col("Niveau SLA", "sla_level", aliases=["niveausla", "sla"]),
        Col("Environnement", "environment", aliases=["environnement", "env"]),
        Col("Contrat maintenance", "support_contract_type", aliases=["contratmaintenance", "typecontratmaintenance"]),
        Col("Date de mise en service", "start_date", "date", START),
        Col("Date de fin de contrat", "end_date", "date", END + ["datefincontrat", "datedefindecontrat"]),
        *LIFECYCLE_COLS,
        *MONEY_TAIL,
    ],
    aliases=["application", "applications", "applis", "applicatifs"],
)

CONTRATS = Sheet(
    "Contrats_Fournisseurs",
    "CONTRACT",
    [
        Col("Référence contrat", "reference", aliases=["referencecontrat", "refcontrat", "contrat", "ncontrat"] + REF),
        Col(
            "Référence marché",
            "market_ref",
            aliases=["referencemarche", "refmarche", "marche", "nmarche", "referencemarchebc", "refmarchebc"],
        ),
        Col("Fournisseur", "vendor", "vendor", VENDOR + ["prestataire", "titulaire"]),
        Col("Contact", "contact_person", aliases=["contact", "contactfournisseur", "interlocuteur"]),
        Col("Email support", "email_support", aliases=["emailsupport", "email", "mail", "courriel"]),
        Col("Téléphone", "phone", aliases=["telephone", "tel", "phone"]),
        Col("Site web", "website", aliases=["siteweb", "site", "web", "url", "website"]),
        Col("Type de contrat", "type", aliases=["typedecontrat", "typecontrat", "type", "nature"]),
        Col("Périmètre", "scope", aliases=["perimetre", "objet", "scope", "description"]),
        Col("Responsable interne", "internal_owner", aliases=OWNER),
        Col("Date de début", "start_date", "date", START),
        Col("Date de fin", "end_date", "date", END),
        Col(
            "Préavis (jours)",
            "notice_period_days",
            "int",
            ["preavisjours", "preavis", "delaidepreavis", "delaipreavis", "noticeperiod", "preaviscontractuel"],
        ),
        Col(
            "Date limite de dénonciation",
            "renewal_start_date",
            "computed",
            ["datelimitedenonciation", "datedenonciation", "debutrenouvellement"],
        ),
        Col("Montant annuel", "annual_amount", "money", ["montantannuel", "montant", "montantannuelht", "cout", "coutannuel"]),
        Col("Devise", "currency", aliases=["devise", "monnaie", "currency"]),
        Col("Statut contrat", "status", aliases=["statutcontrat", "statut", "etat"]),
        Col("Jours restants", "days_remaining", "computed", ["joursrestants"]),
        Col("Échéance", "lifecycle_status", "computed", ["statutecheance", "alerte"]),
        Col("Pièce jointe", "attachment_url", aliases=["piecejointe", "lien", "document", "attachment"]),
    ],
    aliases=["contrats", "contratsfournisseurs", "contrat", "fournisseurs"],
)

PLANNING = Sheet(
    "Planning_Renouvellement",
    "PLANNING",
    [
        Col("Type", "type", "computed"),
        Col("Référence", "reference", "computed"),
        Col("Actif / Contrat", "name", "computed"),
        Col("Fournisseur", "vendor_name", "computed"),
        Col("Échéance", "end_date", "computed"),
        Col("Début renouvellement", "renewal_start_date", "computed"),
        Col("Jours restants", "days_remaining", "computed"),
        Col("Priorité", "priority", "computed"),
        Col("Responsable", "owner", "computed"),
        Col("Statut", "status", "computed"),
        Col("Budget renouvellement", "budget", "computed"),
        Col("Plan d'action", "action_plan", "computed"),
    ],
    importable=False,
    aliases=["planning", "planningrenouvellement", "renouvellements"],
)

DASHBOARD = Sheet("Dashboard", "DASHBOARD", [], importable=False, aliases=["dashboard", "tableaudebord", "synthese"])

ASSET_SHEETS = [LICENCES, CERTIFICATS, MATERIELS, APPLICATIONS]
ALL_SHEETS = [LICENCES, CERTIFICATS, MATERIELS, APPLICATIONS, CONTRATS, PLANNING, DASHBOARD]


def match_sheet(sheet_title: str) -> Sheet | None:
    n = norm(sheet_title)
    for sh in ALL_SHEETS:
        if n == norm(sh.name) or n in sh.aliases:
            return sh
    return None
