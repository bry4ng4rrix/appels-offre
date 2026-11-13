"""Extraction de l'echeance sur une fiche WWF.

Le WWF ne publie pas la date de remise dans sa liste : elle vit dans le texte
de l'annonce, et son scraper le disait sans aller la chercher. Les 9 offres
WWF retenues n'avaient donc aucune echeance et restaient affichees
indefiniment.

La difficulte n'est pas de trouver une date, c'est de trouver LA BONNE. Une
annonce en porte couramment quatre : questions, reponses, visite de site,
livraison. Une date fausse serait pire que pas de date -- elle ferait passer
une offre ouverte pour close, ou l'inverse. En cas de doute, on ne rend rien.

Les textes ci-dessous sont releves sur de vraies annonces.
"""



from apps.offres.scrapers.wwf import date_limite_depuis_fiche as extraire


def test_la_bonne_date_parmi_trois_au_plus_tard():
    # Releve tel quel : questions le 13, reponses le 16, offres le 23.
    texte = ("Les demandes d'eclaircissement doivent etre envoyees a l'adresse "
             "e-mail, au plus tard le 13/09/26. Les reponses seront communiquees "
             "a l'ensemble des entreprises interessees au plus tard le "
             "16/09/2026. Les soumissionnaires interesses a concourir doivent "
             "faire parvenir leurs offres anonymes et sous pli ferme au plus "
             "tard le 23/09/2026 a 17 heures 00 aux adresses suivantes")
    assert extraire(texte) == "2026-09-23"


def test_le_mois_en_toutes_lettres():
    # Et la LIVRAISON est POSTERIEURE au depot : prendre la date la plus
    # tardive donnerait la mauvaise.
    texte = ("Les offres doivent etre deposees pour le marche MDV achat de "
             "consommables au plus tard le 03 septembre 2026. LIVRAISON Les "
             "marchandises devront etre livrees avant le 10 septembre 2026.")
    assert extraire(texte) == "2026-09-03"


def test_le_format_court_a_deux_chiffres():
    texte = "Les dossiers de candidature doivent parvenir au plus tard le 14/09/26 a 17 heures"
    assert extraire(texte) == "2026-09-14"


def test_aucune_echeance_de_depot_ne_rend_rien():
    # Visite de site et livraison ne sont pas des dates de remise.
    texte = ("Les visites de lieux se tiendront le 09/09/2026. Les marchandises "
             "seront livrees avant le 10/09/2026.")
    assert extraire(texte) == ""


def test_une_date_impossible_est_ignoree():
    assert extraire("Les offres sont attendues au plus tard le 31/02/2026") == ""


def test_un_texte_vide_ne_rend_rien():
    assert extraire("") == ""
    assert extraire(None) == ""


def test_le_rappel_de_fin_d_annonce_ne_devance_pas_l_echeance():
    # Une annonce repete souvent la date : la plus tardive fait foi, un
    # rappel ne precede jamais l'echeance qu'il rappelle.
    texte = ("Les offres sont attendues au plus tard le 20/09/2026. "
             "Rappel : depot des dossiers au plus tard le 20/09/2026 a 16h.")
    assert extraire(texte) == "2026-09-20"


def test_l_annonce_qui_ne_nomme_pas_ce_qu_on_depose():
    # Relevee telle quelle : ni "offre" ni "dossier", seulement "envoyes".
    texte = ("Ou envoyes a l'adresse recrutement@wwf.mg avec en objet "
             "AO 31/TNR/26 AMI - N et Titre de la prestation "
             "Au plus tard le 14/09/26 a 17 heures")
    assert extraire(texte) == "2026-09-14"


def test_la_phrase_des_questions_reste_ecartee():
    # Elle dit aussi "envoyees ... au plus tard" : c'est le mot
    # "eclaircissement" qui doit l'emporter, avec ou sans accent.
    for mot in ("eclaircissement", "éclaircissement"):
        texte = (f"Les demandes d'{mot} doivent etre envoyees a l'adresse "
                 "e-mail, au plus tard le 13/09/26.")
        assert extraire(texte) == "", mot


def test_le_scraper_ne_porte_aucun_caractere_de_controle():
    """Un \b avale en retour arriere (0x08) casse silencieusement un motif.

    Deja arrive quatre fois sur ce projet : la regex ne leve rien, elle ne
    correspond simplement plus jamais.
    """
    from pathlib import Path
    octets = Path(__file__).parents[1] / "scrapers" / "wwf.py".read_bytes()
    for interdit in (8, 7, 11, 12):
        assert bytes([interdit]) not in octets, f"caractere 0x{interdit:02x} present"


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
