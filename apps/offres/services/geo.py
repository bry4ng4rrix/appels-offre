"""Geographie des offres : regions (filtrage) et coordonnees (carte).

Fusion des anciens modules regions.py et coordonnees.py.
"""
import re
import unicodedata
from functools import lru_cache

#: Codes de region. Madagascar est distingue de l'ocean Indien : c'est le
#: marche domestique, il merite sa propre ligne plutot que d'etre noye avec
#: La Reunion et Maurice.
MADAGASCAR = "madagascar"
OCEAN_INDIEN = "ocean-indien"
AFRIQUE = "afrique"
EUROPE = "europe"
AMERIQUES = "ameriques"
ASIE_PACIFIQUE = "asie-pacifique"
MOYEN_ORIENT = "moyen-orient"
INTERNATIONAL = "international"
INCONNUE = "inconnue"

#: Libelles affiches, dans l'ordre ou ils comptent pour Label Technology.
LIBELLES = [
    (MADAGASCAR, "Madagascar"),
    (OCEAN_INDIEN, "Océan Indien"),
    (AFRIQUE, "Afrique"),
    (EUROPE, "Europe"),
    (MOYEN_ORIENT, "Moyen-Orient"),
    (ASIE_PACIFIQUE, "Asie-Pacifique"),
    (AMERIQUES, "Amériques"),
    (INTERNATIONAL, "International"),
    (INCONNUE, "Non précisée"),
]

LIBELLE = dict(LIBELLES)


def normaliser(valeur) -> str:
    """Ramene un lieu a une cle comparable.

    Minuscules, accents retires, apostrophes droite et courbe unifiees, tirets
    et ponctuation ramenes a l'espace, espaces multiples reduits.
    """
    texte = (valeur or "").strip().lower()
    # Les deux apostrophes coexistent dans les donnees : "Cote d'Ivoire" et
    # "Cote d’Ivoire" sont le meme pays.
    for signe in ("'", "’", "ʼ", "-", "_", ",", ".", "(", ")", "/"):
        texte = texte.replace(signe, " ")
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return " ".join(texte.split())


#: Correspondance lieu -> region. Les cles sont NORMALISEES : minuscules, sans
#: accent, apostrophes et tirets ramenes a l'espace. Y ajouter une entree
#: suffit a reclasser toutes les offres concernees.
CORRESPONDANCE = {}


def _declarer(region, *lieux):
    for lieu in lieux:
        CORRESPONDANCE[normaliser(lieu)] = region


_declarer(MADAGASCAR, "Madagascar", "Antananarivo", "MDG", "Tananarive")

_declarer(OCEAN_INDIEN,
          "La Réunion (France)", "La Réunion", "Réunion", "Saint-Denis",
          "Mayotte (France)", "Mayotte", "Mamoudzou",
          "Maurice", "Mauritius", "Port-Louis", "Île Maurice",
          "Comores", "Comoros", "Moroni",
          "Seychelles", "Victoria",
          "Océan Indien (Madagascar membre)", "Océan Indien", "Indian Ocean")

_declarer(AFRIQUE,
          # Pays, graphies francaise et anglaise confondues par la normalisation.
          "Niger", "Mali", "Burundi", "Ethiopia", "Éthiopie", "Bénin", "Benin",
          "Sénégal", "Senegal", "Guinée", "Guinea", "Mozambique", "Cameroun",
          "Cameroon", "Côte d'Ivoire", "Ivory Coast", "Nigeria", "Kenya",
          "Somalia", "Somalie", "Tchad", "Chad", "Djibouti", "Tunisie",
          "Tunisia", "Burkina Faso", "Ghana", "Togo", "Rwanda",
          "Guinée-Bissau", "Guinée Bissau", "Guinea-Bissau", "Eswatini",
          "Sudan", "Soudan", "South Africa", "Afrique du Sud", "Uganda",
          "Ouganda", "Tanzania", "Tanzanie", "Malawi", "Angola", "Gabon",
          "Mauritanie", "Mauritania", "Sierra Leone", "Zambia", "Zambie",
          "South Sudan", "Soudan du Sud", "Gambia", "Gambie", "Egypt",
          "Égypte", "Eritrea", "Érythrée", "Zimbabwe", "Namibia", "Namibie",
          "Liberia", "Libéria", "Libya", "Libye", "Algérie", "Algeria",
          "Maroc", "Morocco", "Botswana", "Lesotho", "Congo",
          "République du Congo", "RDC", "RCA", "République centrafricaine",
          "Democratic Republic of the Congo", "Cabo Verde", "Cap-Vert",
          "Sao Tome", "São Tomé", "Guinée équatoriale", "Equatorial Guinea",
          # Villes, telles qu'UNjobnet les publie.
          "Nairobi", "Kinshasa", "Addis Ababa", "Cairo", "Conakry", "Abidjan",
          "Dakar", "Yaounde", "Bouake", "Monrovia", "Juba", "Bissau",
          "Bamako", "Niamey", "Ouagadougou", "Lome", "Accra", "Kampala",
          "Bujumbura", "Kigali", "Maputo", "Lusaka", "Harare", "Khartoum",
          "Mogadishu", "Tunis", "Rabat", "Alger", "Luanda", "Libreville",
          "Nouakchott", "Freetown", "Lilongwe", "Gaborone", "Windhoek",
          "Pretoria", "Johannesburg", "Cape Town", "Dar es Salaam",
          "Goma", "Bangui", "N'Djamena", "Garoua", "Zanzibar")

_declarer(EUROPE,
          "The Hague", "Geneva", "Genève", "Vienna", "Vienne", "Luxembourg",
          "Rome", "Paris", "Brussels", "Bruxelles", "London", "Londres",
          "Copenhagen", "Copenhague", "Kyiv", "Kiev", "Ukraine", "Albania",
          "Albanie", "Madrid", "Berlin", "Bonn", "Budapest", "Warsaw",
          "Varsovie", "Lisbon", "Lisbonne", "Athens", "Athènes", "Stockholm",
          "Helsinki", "Oslo", "Dublin", "Barcelona", "Milan", "Turin",
          "Bratislava", "Prague", "Bucharest", "Sarajevo", "Belgrade",
          "Pristina", "Skopje", "Chisinau", "Tbilisi", "Yerevan", "Erevan",
          "France", "Belgique", "Suisse", "Espagne", "Italie", "Allemagne",
          "Portugal", "Pologne", "Roumanie", "Serbie", "Moldova", "Géorgie",
          "Arménie", "Kosovo", "Bosnia and Herzegovina")

_declarer(MOYEN_ORIENT,
          "Damascus", "Damas", "Syria", "Syrie", "Aden", "Yemen", "Yémen",
          "Beirut", "Beyrouth", "Lebanon", "Liban", "Amman", "Jordan",
          "Jordanie", "Baghdad", "Bagdad", "Iraq", "Irak", "Iran", "Tehran",
          "Téhéran", "Ankara", "Istanbul", "Gaziantep", "Turkey", "Turquie",
          "Jerusalem", "Jérusalem", "Ramallah", "Gaza", "Riyadh", "Riyad",
          "Doha", "Kuwait", "Koweït", "Abu Dhabi", "Dubai", "Dubaï", "Sanaa",
          "Erbil", "Palestine", "Israel", "Israël")

_declarer(ASIE_PACIFIQUE,
          "Bangkok", "Manila", "Manille", "Philippines", "Dhaka", "New Delhi",
          "India", "Inde", "Colombo", "Sri Lanka", "Kyrgyzstan", "Kirghizistan",
          "Kuala Lumpur", "Malaysia", "Malaisie", "Singapore", "Singapour",
          "Yangon", "Myanmar", "Phnom Penh", "Cambodia", "Cambodge", "Kabul",
          "Kaboul", "Afghanistan", "Indonesia", "Indonésie", "Jakarta",
          "Mongolia", "Mongolie", "Suva", "Fiji", "Fidji", "Micronesia",
          "Micronésie", "Papua New Guinea", "Papouasie-Nouvelle-Guinée",
          "Samoa", "Timor-Leste", "Vanuatu", "Solomon Islands", "Tonga",
          "Kiribati", "Nepal", "Népal", "Pakistan", "Islamabad", "Hanoi",
          "Vietnam", "Viêt Nam", "Beijing", "Pékin", "China", "Chine",
          "Tokyo", "Seoul", "Séoul", "Bangladesh", "Uzbekistan", "Ouzbékistan",
          "Kazakhstan", "Tajikistan", "Tadjikistan", "Turkmenistan",
          "Vientiane", "Laos", "Bhutan", "Bhoutan", "Maldives",
          "Nouvelle-Calédonie", "New Caledonia", "Australia", "Australie")

_declarer(AMERIQUES,
          "Washington DC", "Washington", "New York", "United States",
          "États-Unis", "Etats-Unis", "Seattle", "Panama City", "Panama",
          "Caracas", "Venezuela", "Bogota", "Bogotá", "Colombia", "Colombie",
          "Bolivia", "Bolivie", "Santiago", "Chile", "Chili", "Brasilia",
          "Brazil", "Brésil", "Mexico", "Mexico City", "Mexique",
          "San Salvador", "El Salvador", "Guatemala", "Honduras", "Nicaragua",
          "Costa Rica", "Haiti", "Haïti", "Port-au-Prince", "Lima", "Peru",
          "Pérou", "Quito", "Ecuador", "Équateur", "Buenos Aires", "Argentina",
          "Argentine", "Montevideo", "Uruguay", "Paraguay", "Asuncion",
          "Guyana", "Suriname", "Kingston", "Jamaica", "Jamaïque",
          "Santo Domingo", "Cuba", "La Havane", "Canada", "Ottawa", "Toronto",
          "Barbados", "Trinidad", "Belize", "Hawai (Etats-Unis)", "Hawaii")

# Queue observee dans les donnees, relevee le 25/08/2026. Ces entrees ne sont
# pas theoriques : chacune correspond a des offres reellement presentes en
# base et qui tombaient en region inconnue.
_declarer(AFRIQUE,
          "Kisangani", "Brazzaville", "Banjul", "Abuja", "Garoowe", "Maseru",
          "Ibadan", "Algiers", "Bunia", "Kakuma", "Aweil", "Selibaby",
          "Bukavu", "Beni", "Kaduna", "Kano", "Mekelle", "Hargeisa",
          "Antsiranana", "Toamasina", "Mahajanga", "Fianarantsoa")

_declarer(EUROPE,
          "Macedonia", "Macédoine", "Sofia", "Bulgaria", "Bulgarie", "Mons",
          "Brunssum", "Spain", "Greece", "Grèce", "Lyon", "Dnipro", "Lviv",
          "Montreal", "Halifax", "Germany", "Allemagne", "Darmstadt",
          "Tallinn", "Estonia", "Estonie", "Latvia", "Lettonie", "Lithuania",
          "Lituanie", "Zagreb", "Ljubljana", "Valencia", "Seville", "Naples",
          "Frankfurt", "Munich", "Hamburg", "Zurich", "Bern", "Amsterdam",
          "Rotterdam", "Marseille", "Toulouse", "Nantes", "Bordeaux")

_declarer(MOYEN_ORIENT,
          "Türkiye", "Turkiye", "Kerman", "Izmir", "Aleppo", "Alep", "Homs",
          "Oman", "Muscat", "Mascate", "Kahramanmaras", "Malatya", "Adiyaman",
          "Palestinian Territory", "Territoire palestinien", "Bahrain",
          "Bahreïn", "Qatar", "Saudi Arabia", "Arabie saoudite",
          "United Arab Emirates", "Émirats arabes unis", "Hebron", "Nablus")

_declarer(ASIE_PACIFIQUE,
          "Mount Isa", "Kathmandu", "Katmandou", "Bhubaneshwar", "Cox's Bazar",
          "Patna", "Anand", "Bishkek", "Tarawa", "Sydney", "Patancheru",
          "South Korea", "Corée du Sud", "Thimphu", "Port Moresby", "Quetta",
          "Almaty", "Japan", "Japon", "Melbourne", "Canberra", "Auckland",
          "New Zealand", "Nouvelle-Zélande", "Karachi", "Lahore", "Mumbai",
          "Chennai", "Kolkata", "Bangalore", "Hyderabad", "Ho Chi Minh",
          "Baku", "Bakou", "Azerbaijan", "Azerbaïdjan")

_declarer(AMERIQUES,
          "San Jose", "San José", "Paramaribo", "Sao Paulo", "São Paulo",
          "Rio de Janeiro", "Quibdo", "Quibdó", "Medellin", "Medellín",
          "Cali", "Barranquilla", "Recife", "Salvador", "Brasilia",
          "Vancouver", "Chicago", "Boston", "Miami", "Los Angeles",
          "San Francisco", "Denver", "Atlanta")

_declarer(INTERNATIONAL, "Multimedia")

_declarer(INTERNATIONAL,
          "Multinational", "International", "Global", "Mondial", "Worldwide",
          "Divers", "Multiple", "Plusieurs pays", "Regional", "Régional")


# Pur, sur une centaine de libelles distincts : le cache evite de relancer
# des centaines de regex par offre (299 ms pour 3 291 offres sans lui).
@lru_cache(maxsize=2048)
def region(pays) -> str:
    """Region d'un lieu. INCONNUE si le lieu n'est pas repertorie.

    La correspondance exacte est tentee d'abord. A defaut, on cherche si une
    cle connue apparait dans la valeur : le champ porte parfois une precision
    entre parentheses -- "La Reunion (France)", "Ocean Indien (Madagascar
    membre)" -- que la normalisation aplatit sans la supprimer.
    """
    cle = normaliser(pays)
    if not cle:
        return INCONNUE
    if cle in CORRESPONDANCE:
        return CORRESPONDANCE[cle]

    # Recherche par inclusion, du lieu le plus long au plus court : sans quoi
    # "guinee" gagnerait sur "guinee bissau", et "congo" sur "republique
    # democratique du congo".
    #
    # La recherche porte sur des MOTS ENTIERS. Une inclusion brute rangerait
    # "Tirana" au Moyen-Orient, "iran" y figurant comme sous-chaine, et
    # "Romania" de meme par "oman". Le piege est discret : il ne produit pas
    # d'erreur, seulement un classement faux.
    for connu in sorted(CORRESPONDANCE, key=len, reverse=True):
        if re.search(r"\b" + re.escape(connu) + r"\b", cle):
            return CORRESPONDANCE[connu]
    return INCONNUE


def repartir(valeurs) -> dict:
    """Classe une liste de lieux : region -> liste des lieux qui en relevent.

    Sert au filtrage : la base ne connait que le champ `pays`, on lui donne
    donc la liste des valeurs a retenir plutot qu'une region qu'elle ignore.
    """
    par_region = {}
    for valeur in valeurs:
        par_region.setdefault(region(valeur), []).append(valeur)
    return par_region


# ------------------------------------------------------------ coordonnees

# Coordonnees des lieux, pour la carte.
#
# Les cles sont normalisees par regions.normaliser() : minuscules, sans accent,
# ponctuation ramenee a l'espace. "Cote d'Ivoire" et "Cote d’Ivoire" partagent
# donc la meme entree, comme pour le classement en regions.
#
# Un lieu absent de cette table n'apparait pas sur la carte. Ce n'est pas une
# perte silencieuse : la vue compte ces offres et la page le dit. Mieux vaut
# signaler qu'on ne sait pas placer une offre que la poser au hasard.
#
# Pour les PAYS, la coordonnee est le centroide approximatif -- le point doit
# designer le pays, pas une ville en particulier. Pour les VILLES, publiees
# telles quelles par UNjobnet, c'est la ville elle-meme.
#
# La precision visee est celle d'une carte du monde : un demi-degre d'ecart ne
# se voit pas a cette echelle, et chercher mieux serait du temps perdu.
#
#

_BRUT = {
    # --- Madagascar et ocean Indien ---
    "Madagascar": (-18.9, 46.9),
    "Antananarivo": (-18.9, 47.5),
    "Antsiranana": (-12.3, 49.3),
    "Toamasina": (-18.1, 49.4),
    "Mahajanga": (-15.7, 46.3),
    "Fianarantsoa": (-21.4, 47.1),
    "La Réunion (France)": (-21.1, 55.5),
    "La Réunion": (-21.1, 55.5),
    "Mayotte (France)": (-12.8, 45.2),
    "Mayotte": (-12.8, 45.2),
    "Maurice": (-20.3, 57.6),
    "Mauritius": (-20.3, 57.6),
    "Comores": (-11.7, 43.3),
    "Comoros": (-11.7, 43.3),
    "Seychelles": (-4.6, 55.5),
    # La COI siege a Maurice : le point y est pose, faute de mieux.
    "Océan Indien (Madagascar membre)": (-20.3, 57.6),

    # --- Afrique, pays ---
    "Niger": (17.6, 8.1), "Mali": (17.6, -4.0), "Burundi": (-3.4, 29.9),
    "Ethiopia": (9.1, 40.5), "Bénin": (9.3, 2.3), "Sénégal": (14.5, -14.5),
    "Guinée": (9.9, -9.7), "Mozambique": (-18.7, 35.5), "Cameroun": (7.4, 12.4),
    "Côte d'Ivoire": (7.5, -5.5), "Nigeria": (9.1, 8.7), "Kenya": (-0.02, 37.9),
    "Somalia": (5.2, 46.2), "Tchad": (15.5, 18.7), "Djibouti": (11.8, 42.6),
    "Tunisie": (33.9, 9.5), "Tunisia": (33.9, 9.5), "Burkina Faso": (12.2, -1.6),
    "Ghana": (7.9, -1.0), "Togo": (8.6, 0.8), "Rwanda": (-1.9, 29.9),
    "Guinée-Bissau": (11.8, -15.2), "Eswatini": (-26.5, 31.5),
    "Sudan": (12.9, 30.2), "South Africa": (-30.6, 22.9),
    "Uganda": (1.4, 32.3), "Tanzania": (-6.4, 34.9), "Malawi": (-13.3, 34.3),
    "Angola": (-11.2, 17.9), "Gabon": (-0.8, 11.6), "Mauritanie": (21.0, -10.9),
    "Sierra Leone": (8.5, -11.8), "Zambia": (-13.1, 27.8),
    "South Sudan": (7.9, 30.0), "Gambia": (13.4, -15.3), "Egypt": (26.8, 30.8),
    "Eritrea": (15.2, 39.8), "Zimbabwe": (-19.0, 29.9), "Namibia": (-22.6, 17.1),
    # Graphies francaises des portails nationaux branches le 14/09/2026.
    "Namibie": (-22.6, 17.1), "Afrique du Sud": (-30.6, 22.9),
    "Liberia": (6.4, -9.4), "Libya": (26.3, 17.2), "Algérie": (28.0, 1.7),
    "Maroc": (31.8, -7.1), "Botswana": (-22.3, 24.7), "Lesotho": (-29.6, 28.2),
    "RDC": (-4.0, 21.8), "Democratic Republic of the Congo": (-4.0, 21.8),
    "RCA": (6.6, 20.9), "Congo": (-0.2, 15.8),
    "Cabo Verde": (16.0, -24.0), "Sao Tome": (0.2, 6.6),

    # --- Afrique, villes ---
    "Nairobi": (-1.3, 36.8), "Kinshasa": (-4.4, 15.3),
    "Addis Ababa": (9.0, 38.7), "Cairo": (30.0, 31.2), "Conakry": (9.6, -13.6),
    "Abidjan": (5.3, -4.0), "Dakar": (14.7, -17.4), "Yaounde": (3.9, 11.5),
    "Bouake": (7.7, -5.0), "Monrovia": (6.3, -10.8), "Juba": (4.85, 31.6),
    "Bissau": (11.9, -15.6), "Bamako": (12.6, -8.0), "Niamey": (13.5, 2.1),
    "Ouagadougou": (12.4, -1.5), "Lome": (6.1, 1.2), "Accra": (5.6, -0.2),
    "Kampala": (0.3, 32.6), "Bujumbura": (-3.4, 29.4), "Kigali": (-1.9, 30.1),
    "Maputo": (-25.9, 32.6), "Lusaka": (-15.4, 28.3), "Harare": (-17.8, 31.1),
    "Khartoum": (15.5, 32.5), "Mogadishu": (2.0, 45.3), "Tunis": (36.8, 10.2),
    "Rabat": (34.0, -6.8), "Alger": (36.8, 3.1), "Algiers": (36.8, 3.1),
    "Luanda": (-8.8, 13.2), "Libreville": (0.4, 9.5),
    "Nouakchott": (18.1, -16.0), "Freetown": (8.5, -13.2),
    "Lilongwe": (-13.9, 33.8), "Gaborone": (-24.6, 25.9),
    "Windhoek": (-22.6, 17.1), "Pretoria": (-25.7, 28.2),
    "Johannesburg": (-26.2, 28.0), "Cape Town": (-33.9, 18.4),
    "Dar es Salaam": (-6.8, 39.3), "Goma": (-1.7, 29.2), "Bangui": (4.4, 18.6),
    "Garoua": (9.3, 13.4), "Zanzibar": (-6.2, 39.2), "Kisangani": (0.5, 25.2),
    "Banjul": (13.5, -16.6), "Abuja": (9.1, 7.4), "Garoowe": (8.4, 48.5),
    "Maseru": (-29.3, 27.5), "Ibadan": (7.4, 3.9), "Bunia": (1.6, 30.3),
    "Kakuma": (3.7, 34.9), "Aweil": (8.8, 27.4), "Selibaby": (15.2, -12.2),

    # --- Europe ---
    "The Hague": (52.1, 4.3), "Geneva": (46.2, 6.1), "Vienna": (48.2, 16.4),
    "Luxembourg": (49.8, 6.1), "Rome": (41.9, 12.5), "Paris": (48.9, 2.4),
    "Brussels": (50.8, 4.4), "London": (51.5, -0.1), "Copenhagen": (55.7, 12.6),
    "Kyiv": (50.5, 30.5), "Ukraine": (48.4, 31.2), "Albania": (41.2, 20.2),
    "Madrid": (40.4, -3.7), "Berlin": (52.5, 13.4), "Bonn": (50.7, 7.1),
    "Budapest": (47.5, 19.0), "Warsaw": (52.2, 21.0), "Lisbon": (38.7, -9.1),
    "Athens": (38.0, 23.7), "Stockholm": (59.3, 18.1), "Helsinki": (60.2, 24.9),
    "Oslo": (59.9, 10.8), "Dublin": (53.3, -6.3), "Barcelona": (41.4, 2.2),
    "Milan": (45.5, 9.2), "Prague": (50.1, 14.4), "Sarajevo": (43.9, 18.4),
    "Belgrade": (44.8, 20.5), "Skopje": (42.0, 21.4), "Chisinau": (47.0, 28.9),
    "Tbilisi": (41.7, 44.8), "Yerevan": (40.2, 44.5), "France": (46.6, 2.3),
    "Macedonia": (41.6, 21.7), "Sofia": (42.7, 23.3), "Mons": (50.5, 3.9),
    "Brunssum": (50.9, 5.97), "Spain": (40.2, -3.7), "Greece": (39.1, 21.8),
    "Lyon": (45.8, 4.8), "Dnipro": (48.5, 35.0), "Lviv": (49.8, 24.0),
    "Germany": (51.2, 10.4), "Darmstadt": (49.9, 8.65), "Tallinn": (59.4, 24.8),
    "Montreal": (45.5, -73.6), "Halifax": (44.6, -63.6),

    # --- Moyen-Orient ---
    "Damascus": (33.5, 36.3), "Syria": (34.8, 39.0), "Aden": (12.8, 45.0),
    "Yemen": (15.6, 48.5), "Beirut": (33.9, 35.5), "Amman": (31.9, 35.9),
    "Baghdad": (33.3, 44.4), "Iraq": (33.2, 43.7), "Iran": (32.4, 53.7),
    "Ankara": (39.9, 32.9), "Istanbul": (41.0, 29.0), "Gaziantep": (37.1, 37.4),
    "Jerusalem": (31.8, 35.2), "Gaza": (31.5, 34.5), "Sanaa": (15.4, 44.2),
    "Erbil": (36.2, 44.0), "Türkiye": (39.0, 35.2), "Kerman": (30.3, 57.1),
    "Izmir": (38.4, 27.1), "Aleppo": (36.2, 37.1), "Homs": (34.7, 36.7),
    "Oman": (21.5, 55.9), "Muscat": (23.6, 58.5),
    "Kahramanmaras": (37.6, 36.9), "Malatya": (38.4, 38.3),
    "Adiyaman": (37.8, 38.3), "Palestinian Territory": (31.9, 35.2),

    # --- Asie et Pacifique ---
    "Bangkok": (13.8, 100.5), "Manila": (14.6, 121.0),
    "Philippines": (12.9, 121.8), "Dhaka": (23.8, 90.4),
    "New Delhi": (28.6, 77.2), "India": (20.6, 79.0), "Colombo": (6.9, 79.9),
    "Kyrgyzstan": (41.2, 74.8), "Kuala Lumpur": (3.1, 101.7),
    "Singapore": (1.35, 103.8), "Yangon": (16.9, 96.2),
    "Phnom Penh": (11.6, 104.9), "Kabul": (34.5, 69.2),
    "Indonesia": (-0.8, 113.9), "Jakarta": (-6.2, 106.8),
    "Mongolia": (46.9, 103.8), "Suva": (-18.1, 178.4), "Fiji": (-17.7, 178.1),
    "Micronesia": (7.4, 150.6), "Papua New Guinea": (-6.3, 143.9),
    "Samoa": (-13.8, -172.1), "Timor-Leste": (-8.9, 125.7),
    "Nepal": (28.4, 84.1), "Pakistan": (30.4, 69.3),
    "Islamabad": (33.7, 73.1), "Hanoi": (21.0, 105.8), "Vietnam": (14.1, 108.3),
    "Beijing": (39.9, 116.4), "China": (35.9, 104.2), "Tokyo": (35.7, 139.7),
    "Seoul": (37.6, 127.0), "Bangladesh": (23.7, 90.4),
    "Uzbekistan": (41.4, 64.6), "Kazakhstan": (48.0, 66.9),
    "Mount Isa": (-20.7, 139.5), "Kathmandu": (27.7, 85.3),
    "Bhubaneshwar": (20.3, 85.8), "Cox's Bazar": (21.4, 92.0),
    "Patna": (25.6, 85.1), "Anand": (22.6, 73.0), "Bishkek": (42.9, 74.6),
    "Tarawa": (1.3, 172.98), "Sydney": (-33.9, 151.2),
    "Patancheru": (17.5, 78.3), "South Korea": (36.5, 127.9),
    "Thimphu": (27.5, 89.6), "Port Moresby": (-9.5, 147.2),
    "Quetta": (30.2, 67.0), "Almaty": (43.2, 76.9), "Japan": (36.2, 138.3),
    "Baku": (40.4, 49.9),

    # --- Ameriques ---
    "Washington DC": (38.9, -77.0), "New York": (40.7, -74.0),
    "United States": (39.8, -98.6), "Seattle": (47.6, -122.3),
    "Panama City": (9.0, -79.5), "Caracas": (10.5, -66.9),
    "Bogota": (4.7, -74.1), "Colombia": (4.6, -74.3), "Bolivia": (-16.3, -63.6),
    "Santiago": (-33.4, -70.7), "Brasilia": (-15.8, -47.9),
    "Brazil": (-14.2, -51.9), "Mexico": (23.6, -102.6),
    "Mexico City": (19.4, -99.1), "San Salvador": (13.7, -89.2),
    "Guatemala": (15.8, -90.2), "Honduras": (15.2, -86.2),
    "Nicaragua": (12.9, -85.2), "Costa Rica": (9.7, -83.8),
    "Haiti": (18.9, -72.3), "Lima": (-12.0, -77.0), "Peru": (-9.2, -75.0),
    "Quito": (-0.2, -78.5), "Buenos Aires": (-34.6, -58.4),
    "Montevideo": (-34.9, -56.2), "Guyana": (4.9, -58.9),
    "Suriname": (3.9, -56.0), "Canada": (56.1, -106.3),
    "San Jose": (9.9, -84.1), "Paramaribo": (5.9, -55.2),
    "Sao Paulo": (-23.6, -46.6), "Rio de Janeiro": (-22.9, -43.2),
    "Quibdo": (5.7, -76.7), "Hawai (Etats-Unis)": (21.3, -157.9),
    "Santo Domingo": (18.5, -69.9), "Port-au-Prince": (18.5, -72.3),
    "Valdivia": (-39.8, -73.2),

    # --- Derniers lieux releves en base, sans famille evidente ---
    "Cambodia": (12.6, 104.9), "Laos": (19.9, 102.5), "Male": (4.2, 73.5),
    "Maldives": (3.2, 73.2), "Gemena": (3.25, 19.8),
}

#: Table effective, cles normalisees.
COORDONNEES = {normaliser(lieu): point for lieu, point in _BRUT.items()}


@lru_cache(maxsize=2048)
def point(pays):
    """(latitude, longitude) du lieu, ou None s'il n'est pas repertorie.

    La correspondance exacte prime. A defaut, on cherche un lieu connu comme
    MOT ENTIER dans la valeur -- "Nigeria, Abuja" doit se placer -- du plus
    long au plus court, pour que "guinee bissau" gagne sur "guinee".
    """
    import re

    cle = normaliser(pays)
    if not cle:
        return None
    if cle in COORDONNEES:
        return COORDONNEES[cle]
    for connu in sorted(COORDONNEES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(connu) + r"\b", cle):
            return COORDONNEES[connu]
    return None
