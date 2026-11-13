"""Constantes des sources de collecte, reprises de l'ancien config.py.

Importees dans Offre/settings.py : elles sont donc lisibles via
django.conf.settings comme tout autre reglage.
"""

# --- Source : UNjobnet (scraping HTML) ---
UNJOBNET_BASE_URL = "https://www.unjobnet.org/jobs"
UNJOBNET_MAX_PAGES = 300  # garde-fou, la boucle s'arrete normalement bien avant
# Au tout premier lancement, aucun ID n'est connu : sans plafond on
# remonterait tout l'historique des deux sites et on enverrait des milliers
# d'items au LLM d'un seul coup. On se limite aux plus recents.
# Mettre None pour ne pas plafonner (equivaut a "manage.py veille --complet").
FIRST_RUN_MAX_ITEMS = 100

# Politesse envers unjobnet : pause entre deux pages. Sur un rattrapage
# complet (~273 pages) cela evite de marteler le site.
UNJOBNET_PAGE_DELAY = 0.4

# --- Source : Banque mondiale (API de recherche publique, sans cle) ---
BM_BASE_URL = "https://search.worldbank.org/api/v3/projects"
BM_DETAIL_URL = "https://projects.banquemondiale.org/fr/projects-operations/project-detail/{id}"
# Codes pays ISO-2. L'API ne gere PAS plusieurs codes dans une meme requete
# ("MG,MZ" renvoie 0 resultat) : le scraper interroge un pays a la fois.
# Liste vide = tous les pays (28 000 projets, a reserver a un usage cible).
BM_PAYS = ["MG"]
BM_PAGE_SIZE = 50
BM_MAX_PAGES = 100  # garde-fou, comme pour les autres sources

# --- Source : avis de passation de marches Banque mondiale ---
# C'est l'API derriere projects.banquemondiale.org/fr/projects-operations/opportunities
BM_AVIS_URL = "https://search.worldbank.org/api/v2/procnotices"
BM_AVIS_DETAIL_URL = (
    "https://projects.banquemondiale.org/fr/projects-operations/procurement-detail/{id}"
)
# Noms de pays EXACTS (champ project_ctry_name), pas des codes ISO. Le filtre
# countryname_exact/countrycode est ignore par l'API et renvoie tout.
BM_AVIS_PAYS = ["Madagascar"]
# On interroge type par type : "Contract Award" (8174 avis sur 11277 pour
# Madagascar) recense des marches deja attribues, sans interet pour une veille.
BM_AVIS_TYPES = [
    "Request for Expression of Interest",
    "Invitation for Bids",
    "General Procurement Notice",
    "Invitation for Prequalification",
]
# Ne garder que les avis dont la date limite de depot n'est pas passee.
BM_AVIS_OUVERTS_SEULEMENT = True
# Certains avis n'ont pas de date limite (les "General Procurement Notice" n'en
# ont jamais). Les garder tous ferait remonter des avis de 2011 ; les jeter tous
# ferait perdre un avis recent dont le champ manque. On se fie donc a la date de
# publication au-dela de ce delai.
BM_AVIS_SANS_DATE_MAX_JOURS = 90
BM_AVIS_PAGE_SIZE = 50
BM_AVIS_MAX_PAGES = 100

# --- Source : Banque africaine de developpement (BAD / AfDB) ---
# Page publique rendue cote serveur : https://www.afdb.org/fr/documents/project-related-procurement
# Verifie le 20/08/2026 : robots.txt autorise ce chemin. Les conditions
# n'interdisent pas la collecte, seulement "resell, redistribute or create
# derivative works for commercial purposes" sans accord ecrit -- collecte
# interne uniquement, pas de rediffusion.
BAD_BASE_URL = "https://www.afdb.org/fr/documents/project-related-procurement"
BAD_DETAIL_BASE = "https://www.afdb.org"
# robots.txt impose "Crawl-delay: 10". Ce n'est pas un reglage de confort :
# c'est une consigne du site, a respecter.
BAD_PAGE_DELAY = 10
BAD_MAX_PAGES = 50  # 20 avis par page ; garde-fou comme les autres sources
# Marches deja attribues : sans interet pour une veille d'opportunites.
# On cible le radical "bution de ..." et non l'orthographe complete : le site
# publie "Attribution", mais aussi "Attruibution" et "Atribution" -- des fautes
# de frappe reelles, relevees sur 802 avis. Une liste d'orthographes exactes
# laisserait passer ces avis.
BAD_TYPES_EXCLUS = ["contract award", "bution de marche", "bution de contrat"]

# --- Source : ARMP Madagascar (marches publics nationaux) ---
# Autorite de Regulation des Marches Publics. Verifie le 21/08/2026 : aucun
# robots.txt, aucune mention legale, aucun copyright -- les avis sont publies
# pour etre lus par les candidats.
# Le site ne repond qu'en HTTP : pas de HTTPS disponible.
ARMP_BASE_URL = "http://www.armp.mg/marches_publics/"
# Toute la page tient en une requete (~800 Ko, 424 avis) : ni pagination ni
# delai de politesse a prevoir.
ARMP_OUVERTS_SEULEMENT = True

# --- Source : FID Madagascar (Fonds d'Intervention pour le Developpement) ---
# Le site est sous WordPress et expose son API REST publiquement : on
# l'interroge plutot que de scraper /appels-doffres/. La page HTML n'affiche
# une date de cloture que pour 8 avis sur 100 et melange appels d'offres,
# resultats et attributions -- l'API donne une date fiable et des categories.
# Verifie le 21/08/2026 : robots.txt autorise tout ("Disallow:" vide).
FID_API_URL = "https://www.fid.mg/wp-json/wp/v2/posts"
# Categories pertinentes. Volontairement exclues : 15 "Resultats des appels
# d'offre" et 80 "Avis d'attribution des marches" (marches deja attribues),
# ainsi que 17 "Emplois" (postes salaries, pas des prestations).
FID_CATEGORIES = [
    14,   # Appel d'offre                     (740 articles)
    16,   # Appel a manifestation d'interet   (207)
    49,   # Avis de consultation              (385)
    50,   # Demande de cotations              (2)
]
FID_PAGE_SIZE = 100      # maximum autorise par l'API WordPress
FID_PAGE_DELAY = 0.5     # aucune consigne dans robots.txt, simple politesse
FID_MAX_PAGES = 20       # garde-fou : 20 x 100 couvre largement chaque categorie
# Un avis sans date de cloture lisible est retenu s'il a ete publie recemment.
# Sans ce plafond, les 740 appels d'offres archives depuis 2018 remonteraient.
FID_MAX_JOURS = 45

# --- Source : WWF Madagascar ---
# Page unique melangeant appels d'offres et postes salaries : le tri par le
# LLM fait le depart, son prompt ecartant deja les postes sans prestation.
# Verifie le 21/08/2026 : robots.txt autorise ce chemin et impose
# "Crawl-delay: 10" -- sans effet ici, la source ne fait qu'une requete.
WWF_BASE_URL = "https://www.wwf.mg/rejoignez_nous3/emploi/"
# La liste ne porte pas de date limite, seulement une date de publication.
# Au-dela de ce delai, une annonce est consideree close.
WWF_MAX_JOURS = 60
# Delai entre deux requetes, impose par le robots.txt du site
# ("Crawl-delay: 10"). Il ne jouait pas tant qu'on ne lisait que la page de
# liste ; il joue desormais, l'echeance de depot n'etant lisible que sur la
# fiche de chaque annonce. Compter ~10 s par annonce nouvelle.
WWF_PAGE_DELAY = 10

# --- Source : Madagascar National Parks ---
# Gestionnaire des aires protegees malgaches. WordPress, type de contenu dedie
# `appel_offre`. Verifie le 21/08/2026 : robots.txt n'interdit rien et impose
# "Crawl-delay: 10". L'API REST N'EXPOSE PAS ce type (le plugin Advanced
# Access Manager la restreint) : on passe par le HTML, contrairement au FID.
MNP_BASE_URL = "https://parcs-madagascar.com/appel-doffre/"
MNP_PAGE_DELAY = 10   # consigne du site, pas un reglage de confort
MNP_MAX_PAGES = 10    # garde-fou ; le site en compte 4 au 21/08/2026
MNP_OUVERTS_SEULEMENT = True

# --- Source : TED (Journal officiel des marches europeens) ---
# API publique, sans authentification, en POST (un GET repond 405).
# Cadre le plus favorable du pipeline : la notice legale de TED autorise
# explicitement la reutilisation "for commercial or non-commercial purposes".
TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"
# Codes pays ISO-3. Volontairement restreint : le filtre CPV 72 (services
# informatiques) donne 2929 avis ouverts a l'echelle de l'UE, majoritairement
# reserves aux entreprises etablies dans l'Union.
TED_PAYS = ["MDG"]
TED_PAGE_SIZE = 100
TED_MAX_PAGES = 10

# --- Source : BOAMP (marches publics francais, ocean Indien) ---
# Bulletin officiel des annonces des marches publics, via l'API Opendatasoft
# ouverte : 1 699 819 avis au total. Filtre sur les departements de l'ocean
# Indien, marche francophone proche d'Antananarivo dont les prestations
# numeriques sont realisables a distance.
# RESERVE : le jeu de donnees n'expose pas de champ `license`. La Licence
# Ouverte s'applique vraisemblablement (open data administratif francais),
# mais cela reste A CONFIRMER avant toute rediffusion.
BOAMP_API_URL = ("https://boamp-datadila.opendatasoft.com"
                 "/api/explore/v2.1/catalog/datasets/boamp")
# 974 = La Reunion (21483 avis, 143 ouverts), 976 = Mayotte (8047 avis).
BOAMP_DEPARTEMENTS = ["974", "976"]
BOAMP_PAGE_SIZE = 100
BOAMP_MAX_PAGES = 20

# --- Source : Commission de l'ocean Indien (COI) ---
# Organisation intergouvernementale : Comores, France (La Reunion), Madagascar,
# Maurice, Seychelles. Ses marches sont ouverts aux prestataires des cinq Etats.
# WordPress avec API REST publique. Verifie le 24/08/2026 : robots.txt
# autorise tout ("Disallow:" vide).
COI_API_URL = "https://www.commissionoceanindien.org/wp-json/wp/v2/posts"
# Categories "Opportunites" par annee. ATTENTION : elles ne cloisonnent pas --
# "Opportunites 2025" renvoie aussi les articles de 2026. Le dedoublonnage par
# ID dans le scraper est donc indispensable.
COI_CATEGORIES = [
    1297,   # Opportunites 2026 (20 articles)
    1242,   # Opportunites 2025 (57)
]
COI_PAGE_SIZE = 100
COI_PAGE_DELAY = 0.5
COI_MAX_PAGES = 5
# La COI ne publie pas de date limite : la fraicheur est le seul critere.
COI_MAX_JOURS = 60

# --- Source : Maurice (Public Procurement Portal) ---
# Portail officiel des marches publics mauriciens. WordPress 6.9.4, sans
# pare-feu. Le site ne sert aucun robots.txt -- la requete redirige vers
# l'accueil -- donc aucune restriction n'est declaree. Verifie le 25/08/2026.
#
# La page n'affiche que les avis en cours, une vingtaine, sans pagination :
# une seule requete suffit, et un avis disparait a sa cloture. Il n'y a donc
# pas d'archive a remonter, et le plafond de premier lancement ne mord jamais.
#
# ELIGIBILITE : le Public Procurement Act mauricien prevoit l'International
# Bidding, une societe malgache peut donc soumissionner. Les fournisseurs
# locaux beneficient d'une marge de preference de 30 a 40 % selon leur statut
# (SME, certification "Made in Moris", part d'intrants locaux) : c'est un
# handicap, pas une barriere.
MAURICE_URL = ("https://publicprocurement.govmu.org"
               "/publicprocurement/?page_id=720")
MAURICE_BASE = "https://publicprocurement.govmu.org"

# --- Source : Conservation International ---
# ONG environnementale presente a Madagascar. Publie ses appels d'offres pour
# prestataires et consultants externes. Verifie le 25/08/2026 :
#
#   - robots.txt : "Allow: /", autorisation explicite.
#   - Conditions d'utilisation lues en entier (16 835 caracteres) : aucune
#     interdiction de collecte automatisee, de robot ni d'extraction. Cadre
#     juridique le plus net du pipeline apres TED.
#   - Aucune restriction de nationalite dans les appels d'offres examines :
#     l'avis "Biodiversity Hotspots Global Platform" sollicite un "web
#     development firm or consortium", sans clause d'implantation.
#
# La page ne liste que les avis OUVERTS, sans pagination : une requete suffit.
# Volume constate : 6 avis, parus sur un mois, soit environ 80 par an.
#
# RESERVE : les fiches ne portent aucune description, meme en HTML -- la
# substance est dans un PDF. Le tri juge donc sur le seul titre. Cela passe
# ici, les intitules etant descriptifs, la ou les "Avis d'Appel d'Offres
# (AAO)" generiques des Comores avaient fait ecarter cette source.
CONSERVATION_URL = "https://www.conservation.org/procurement-opportunities"
CONSERVATION_BASE = "https://www.conservation.org"

# --- Source : Cameroun, ARMP (Journal des Marches) ---
# Portail de l'Agence de Regulation des Marches Publics, qui republie le
# Journal des Marches : la publication y est une obligation legale du Code
# des marches publics. Sonde le 14/09/2026 :
#
#   - robots.txt : "Disallow:" vide, tout est autorise.
#   - Aucune page de conditions d'utilisation (mentions-legales, cgu, terms :
#     tous 404). Le site ne pose donc aucune restriction a la lecture.
#   - Le catalogue est classe par TYPE d'avis, et chaque liste est paginee
#     par 10, la plus recente en tete. Il n'existe pas de liste "tous types" :
#     filtres?type=avis&val=0 rend la page sans aucun avis.
#
# ELIGIBILITE : chaque fiche porte une rubrique "Participation et origine"
# qui dit si les entreprises etrangeres sont admises ; elle est reprise dans
# la description pour que le tri en tienne compte.
CM_BASE = "https://www.armp.cm"
CM_LISTE = CM_BASE + "/filtres"
CM_DETAIL = CM_BASE + "/details"
#: Valeur du filtre -> libelle. L'ordre est celui du parcours : les avis
#: ouverts aux etrangers d'abord, puisque le plafond de premier lancement
#: peut mordre avant la fin.
CM_TYPES = [
    (4, "Appel d'offres international"),
    (12, "Manifestation d'interet"),
    (1, "Appel d'offres national"),
    (5, "Demande de cotation"),
    (7, "Demande de proposition"),
    (21, "Appel d'offres restreint"),
]
#: Les communiques et additifs modifient un avis existant ; ils n'ont ni
#: objet propre ni echeance (le portail y met 01-01-1970).
CM_TYPES_EXCLUS = {"COMM", "ADDITIF"}
CM_PAGE_DELAY = 1        # aucune consigne dans robots.txt, simple politesse
CM_MAX_PAGES = 20        # par type ; 10 avis par page

# --- Source : Mali, DGMP (Direction Generale des Marches Publics) ---
# Site Drupal de la direction qui publie les dossiers d'appel d'offres et
# les avis de manifestation d'interet. Sonde le 14/09/2026 :
#
#   - robots.txt : le standard Drupal, qui n'interdit que l'administration
#     et la recherche. Les pages d'avis (?q=node/N) sont autorisees, avec
#     "Crawl-delay: 10" -- respecte entre les deux requetes.
#   - Deux tableaux rendus cote serveur, SANS pagination : 1 837 lignes pour
#     les appels d'offres, 1 082 pour les manifestations d'interet, depuis
#     decembre 2020. Deux requetes suffisent a tout lire.
#   - Aucune date limite : la ligne porte l'autorite contractante, le
#     service, le libelle, la date du dossier et le dossier lui-meme (.docx
#     ou .pdf). L'echeance est dans le dossier, non telecharge.
#
# RYTHME : lent et irregulier. 123 dossiers en 2026 contre 421 en 2024, et
# le plus recent date de sept semaines au moment du sondage. Sans echeance,
# un dossier de plus de 30 jours est presume clos au chargement : on ne
# collecte donc que les dossiers recents, pour ne pas depenser le tri sur
# des avis deja perimes.
ML_BASE = "https://www.dgmp.gouv.ml"
ML_LISTES = [
    (ML_BASE + "/?q=node/71", "Appel d'offres"),
    (ML_BASE + "/?q=node/66", "Manifestation d'interet"),
]
ML_PAGE_DELAY = 10       # consigne du robots.txt
ML_MAX_JOURS = 45

# --- Source : Ghana, GHANEPS (Ghana Electronic Procurement System) ---
# Plateforme e-PPS (European Dynamics) de la Public Procurement Authority.
# Sonde le 14/09/2026 :
#
#   - Pas de robots.txt. La page "About" (361 caracteres) ne pose aucune
#     condition ; termsOfUse.do et disclaimer.do repondent 500 : il n'y a
#     pas de conditions d'utilisation publiees.
#   - La recherche rapide "Current Tenders" (searchSelect=6) liste les avis
#     en phase de depot, 10 par page, avec une pagination DisplayTag dont le
#     parametre porte un identifiant de tableau (d-3680175-p=N) constant
#     d'une requete a l'autre.
#   - Chaque fiche (prepareViewCfTWS.do?resourceId=N) est un formulaire
#     "libelle : valeur" : description, type (Goods/Works/Services), methode,
#     code UNSPSC, echeance. resourceId est l'identifiant technique.
#
# Volume constate : 72 avis en cours, dont 67 en "National Competitive
# Tendering" et 5 selections de consultants sur manifestation d'interet.
# La methode est reprise dans la description : le tri peut ecarter ce qui
# est de toute evidence hors de portee.
GH_BASE = "https://www.ghaneps.gov.gh"
GH_LISTE = GH_BASE + "/epps/quickSearchAction.do"
GH_DETAIL = GH_BASE + "/epps/cft/prepareViewCfTWS.do"
GH_PARAM_PAGE = "d-3680175-p"
GH_PAGE_DELAY = 1
GH_MAX_PAGES = 30        # 10 avis par page

# --- Source : Malawi, PPDA (Public Procurement and Disposal of Assets) ---
# Page "Procurement Notices" de l'autorite de regulation. Sonde le
# 14/09/2026 : robots.txt "Disallow:" vide, aucune page de conditions.
#
# Un seul tableau (id="tenderstable"), sans pagination, qui ne liste que
# les avis en cours : 29 lignes au sondage, toutes a echeance future. Six
# colonnes : titre, institution, reference, publication, cloture (les deux
# en ISO), piece jointe PDF. Le titre est souvent laconique ("MEDICAL
# EQUIPMENT1") la ou le nom du PDF est parlant ("RFQ Health RCDF - Supply
# of CSSD and Emergency Treatment Equipment") : il est repris dans la
# description.
#
# Volume et portee : surtout des demandes de cotation a une semaine pour
# des conseils de district, avec quelques appels d'offres nationaux et
# internationaux. Peu de marches par mois, mais la source ne coute qu'une
# requete.
MW_URL = "https://www.ppda.mw/tenders"

# --- Source : Namibie, CPBN (Central Procurement Board of Namibia) ---
# L'office central passe les marches au-dessus des seuils des entites
# publiques : peu d'avis, mais des marches importants (gardiennage d'une
# capitale sur deux ans, fourniture de carburant...). Sonde le 14/09/2026 :
# pas de robots.txt (le chemin rend la page d'accueil), et "Legal Framework"
# est le droit des marches publics, pas des conditions d'utilisation.
#
# La page "Open Bids" (index/external/2) ne liste que les avis ouverts, en
# cartes dans un tableau id="activeBidsTable" : titre suivi de la reference,
# reference, cloture ("14th October, 2026 11:00"), lien vers la fiche
# index/bid/<N>. La fiche ajoute la categorie (Goods, Works, Consultancy,
# Non-Consultancy), l'institution beneficiaire et la date d'emission.
#
# La reference porte la methode : G/ONB = Open National Bidding,
# NCS/OAB = Open Advertised Bidding, OIB = Open International Bidding.
NA_URL = "https://www.cpbn.com.na/index/external/2"
NA_DETAIL_DELAY = 1

# --- Source : Afrique du Sud, eTenders (National Treasury) ---
# Portail national ou TOUTES les entites publiques sud-africaines doivent
# publier leurs avis. Sonde le 14/09/2026 :
#
#   - LICENCE EXPLICITE, la plus nette du pipeline. "Learn More", section 8,
#     data.etenders.gov.za/Home/LearnMore : "National Treasury has licensed
#     the data which allows a user of the data to: Use this data for any
#     purpose including commercial and non-commercial use ; Publish content
#     based on the use of this data ; Re-publish this data providing a link
#     to the original source remains intact." Le lien vers la source est
#     conserve dans chaque offre.
#   - Pas de robots.txt.
#   - Le tableau des opportunites est un DataTables "serverSide" : la page
#     HTML est vide, les donnees viennent de
#     GET /Home/PaginatedTenderOpportunities?status=1&start=N&length=M, qui
#     repond en JSON avec recordsTotal (2 247 avis actifs au sondage) et une
#     ligne complete par avis : numero, description, categorie, type de
#     procedure, entite, province, dates de publication et de cloture, et les
#     documents joints. Il n'y a pas de page de fiche : le detail se deplie
#     dans le tableau. Le lien conserve est celui du document d'avis.
#   - L'API OCDS notee en aout (ocds-api.etenders.gov.za) repond 404.
ZA_LISTE = "https://www.etenders.gov.za/Home/PaginatedTenderOpportunities"
ZA_PAGE = "https://www.etenders.gov.za/Home/opportunities?id=1"
ZA_DOCUMENT = "https://www.etenders.gov.za/home/Download/"
ZA_PAGE_SIZE = 100
ZA_PAGE_DELAY = 1
ZA_MAX_PAGES = 30        # 30 x 100 couvre les 2 247 avis actifs

# --- Source : Maroc, PMMP (Portail Marocain des Marches Publics) ---
# Le portail unique ou la publication est obligatoire (decret 2-12-349). Le
# plus gros gisement francophone du continent : 323 consultations publiees
# en trois jours au sondage du 14/09/2026, une centaine par jour.
#
#   - Conditions d'utilisation lues (10 036 caracteres) : ce sont des
#     prerequis techniques (navigateur, signature electronique), sans aucune
#     clause sur la lecture ou la collecte. robots.txt repond 403.
#   - Application PRADO (PHP) : toute action est un POST qui renvoie l'etat
#     de la page (PRADO_PAGESTATE) et nomme la commande (PRADO_POSTBACK_
#     TARGET). Le scraper enchaine trois postbacks : la recherche avancee
#     bornee sur la date de mise en ligne, le passage a 100 resultats par
#     page, puis la page suivante.
#   - 500 par page fait couper la connexion par le serveur (la page
#     depasserait 15 Mo) ; 100 par page pese 1,9 Mo et met 30 s.
#   - Les champs du formulaire portent des noms trompeurs : c'est
#     "dateMiseEnLigneCalculeStart/End" qui borne la date de mise en ligne,
#     "dateMiseEnLigneStart/End" bornant la date limite de remise des plis.
#
# La fenetre de trois jours couvre largement un passage quotidien, meme
# apres un week-end.
MA_BASE = "https://www.marchespublics.gov.ma"
MA_FORMULAIRE = (MA_BASE + "/index.php?page=entreprise.EntrepriseAdvancedSearch"
                 "&AllCons&EnCours&searchAnnCons")
MA_FENETRE_JOURS = 3
MA_PAGE_SIZE = 100
MA_MAX_PAGES = 10
MA_PAGE_DELAY = 2

# --- Source : Benin, SIGMAP (Portail des Marches Publics) ---
# Application Angular dont la page rend "0 avis" sans JavaScript. L'API
# qu'elle appelle a ete lue dans son code : GET api.marches-publics.bj
# /v2/api/portail/appelsoffres?status=1&page=0&size=100, qui repond en JSON
# (format Spring "content / totalElements"). Sonde le 14/09/2026 : 52 avis
# ouverts, tous avec leur dossier ; ni robots.txt (le chemin rend
# l'application) ni page de conditions dans les menus du portail.
#
# Chaque entree porte l'objet, la reference, le type de marche (Travaux,
# Fournitures, Services, Prestations intellectuelles), l'autorite
# contractante, la date de publication, la date limite de depot, le PDF de
# l'avis et un drapeau "expired". La fiche du portail est
# marches-publics.bj/appels-doffres/<dosID>.
BJ_API = "https://api.marches-publics.bj/v2/api/portail/appelsoffres"
BJ_FICHE = "https://marches-publics.bj/appels-doffres/"
BJ_PAGE_SIZE = 100
BJ_MAX_PAGES = 5

# --- Source : Kenya, PPIP (Public Procurement Information Portal) ---
# Portail de la Public Procurement Regulatory Authority, ou les entites
# publiques kenyanes publient leurs avis. Application Vue dont l'API a ete
# lue dans le code : GET tenders.go.ke/api/active-tenders?page=N (10 par
# page, format Laravel "data / last_page / total"). Sonde le 14/09/2026 :
# 289 avis actifs sur 29 pages.
#
#   - robots.txt : "Disallow:" vide. Pas de conditions d'utilisation : le
#     lien "Disclaimer" du pied de page ne mene nulle part. Les donnees sont
#     celles que le portail expose en OCDS (chaque avis porte un ocid), que
#     le registre d'aout notait sous licence CC BY 4.0.
#   - LIMITE DE DEBIT : 60 requetes par minute (X-RateLimit-Limit), au-dela
#     l'API repond 429 "Too Many Attempts". Le delai entre pages tient le
#     parcours complet sous cette limite.
#   - Trie par echeance CROISSANTE : les nouveautes sont n'importe ou, il
#     faut lire toutes les pages a chaque passage. 29 requetes.
#   - Un parametre per_page provoque une erreur 500 : on se contente de 10.
#
# ELIGIBILITE : les avis "is_reservation" sont reserves aux entreprises
# kenyanes de jeunes, de femmes ou de personnes handicapees (AGPO) ; les
# procedures restreintes et directes ne sont pas ouvertes. Ces trois cas
# sont ecartes a la collecte.
KE_API = "https://tenders.go.ke/api/active-tenders"
KE_FICHE = "https://tenders.go.ke/tenders/"
KE_PAGE_DELAY = 1.5
KE_MAX_PAGES = 60
KE_METHODES_EXCLUES = ("restricted", "direct")
KE_ATTENTE_429 = 65     # la limite est par minute ; on laisse la minute passer

