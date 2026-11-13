"""Classement d'une page source : encore en ligne, ou terminee ?

Le risque n'est pas symetrique. Une offre close qui traine dans la liste se
voit et s'ignore ; une offre OUVERTE marquee close disparait de l'ecran sans
que personne ne s'en apercoive. Ces tests portent donc surtout sur ce qui ne
doit PAS declencher une cloture.

Les textes sont releves sur les pages reelles des sources.
"""



from apps.offres.services.lien_checker import (CLOSE, ILLISIBLE, INTROUVABLE, OUVERTE,
                            classer, texte_utile)


class FausseReponse:
    def __init__(self, code):
        self.status_code = code


def _classer(code, texte=""):
    return classer(FausseReponse(code), texte)[0]


def test_un_404_signale_une_offre_retiree():
    assert _classer(404) == INTROUVABLE
    assert _classer(410) == INTROUVABLE


def test_un_refus_ou_une_panne_ne_valent_pas_cloture():
    # 403 et 500 disent que le SITE va mal, pas que l'offre est close. Les
    # confondre masquerait des offres valides au premier hoquet du serveur.
    for code in (403, 429, 500, 502, 503):
        assert _classer(code) == ILLISIBLE, code


def test_une_page_normale_reste_ouverte():
    texte = ("Avis d'appel d'offres pour la fourniture de materiels "
             "informatiques. Les offres sont attendues au plus tard le "
             "30 septembre 2026 a l'adresse suivante.")
    assert _classer(200, texte) == OUVERTE


def test_les_phrases_de_cloture_relevees_sur_les_sources():
    for phrase in [
        "This position is no longer open. Before you go, browse similar jobs",
        "This vacancy is closed and no longer accepting applications",
        "Applications are now closed for this position",
        "Cette offre n'est plus disponible",
        "Avis clôturé — le marché a été attribué",
        "Appel d'offres annulé par l'autorité contractante",
        "L'offre est pourvue",
    ]:
        assert _classer(200, phrase) == CLOSE, phrase


def test_l_avertissement_permanent_d_unjobnet_ne_ferme_rien():
    """Le faux ami le plus dangereux.

    UNjobnet affiche cet avertissement sur CHACUNE de ses pages, y compris
    les offres ouvertes. Le lire comme une cloture fermerait toute la source.
    """
    texte = ("Employers may deactivate or amend a posting at any time, so "
             "confirm the role and closing date on the organization's "
             "official site before applying. No genuine employer will ask "
             "you for money.")
    assert _classer(200, texte) == OUVERTE


def test_un_avertissement_anti_fraude_ne_ferme_rien():
    texte = ("Beware of scam: applications are collected only through our "
             "official portal. Recruitment fraud is a crime.")
    assert _classer(200, texte) == OUVERTE


def test_une_offre_ouverte_qui_parle_de_dates_de_cloture():
    # Une annonce decrit souvent sa propre procedure de cloture sans etre
    # close pour autant.
    texte = ("La date de clôture des candidatures est fixée au 30/09/2026. "
             "Les plis seront ouverts en séance publique.")
    assert _classer(200, texte) == OUVERTE


def test_la_justification_accompagne_une_cloture():
    # Sans extrait, impossible de verifier un verdict a posteriori.
    etat, pourquoi = classer(FausseReponse(200),
                             "Nous informons les candidats que cette offre "
                             "n'est plus disponible depuis le 1er septembre.")
    assert etat == CLOSE
    assert "plus disponible" in pourquoi


def test_une_page_vide_reste_ouverte():
    # Rien lu n'est pas une preuve de cloture.
    assert _classer(200, "") == OUVERTE


def test_un_gabarit_non_rendu_ne_ferme_rien():
    """Le faux positif qui a ferme 136 offres a tort.

    UNjobnet est une application JavaScript : son HTML statique porte LES
    DEUX branches de chaque condition. "This position is no longer open"
    figure donc sur toute page, y compris une offre dont l'echeance annoncee
    etait encore a venir. Le marqueur "{{waiting}}" juste avant trahit le
    gabarit -- texte releve tel quel sur la page.
    """
    texte = ("un monde qui preserve et defend ces cinq grands biens communs "
             "que sont la planete, le lien social, la paix, les partenariats "
             "et la prosperite economique. {{waiting}} This position is no "
             "longer open. Before you apply We review listings for quality")
    assert _classer(200, texte) == OUVERTE


def test_une_cloture_reelle_passe_encore_malgre_un_gabarit_ailleurs():
    # Le garde-fou ne doit pas desarmer la detection sur toute la page : il
    # ne disqualifie que les phrases VOISINES d'un gabarit.
    texte = ("Menu {{nav.items}} Accueil Contact. "
             + "x" * 200 +
             " Nous informons les candidats que cette offre n'est plus "
             "disponible depuis le 1er septembre.")
    assert _classer(200, texte) == CLOSE


def test_le_formulaire_de_signalement_ne_ferme_rien():
    """Le second faux positif, de nature differente du gabarit.

    Les pages UNjobnet portent un formulaire "What's the issue?" dont le menu
    deroulant propose "No longer available". Lu comme du contenu, il fermait
    les 136 offres de la source.
    """
    html = ("<html><body><article>Avis d'appel d'offres, remise des plis le "
            "30 septembre 2026.</article>"
            "<form><label>What's the issue?</label><select>"
            "<option>No longer available</option>"
            "<option>Duplicate listing</option></select></form>"
            "</body></html>")
    assert _classer(200, texte_utile(html)) == OUVERTE


def test_l_interface_est_retiree_mais_pas_le_contenu():
    html = ("<html><head><style>.x{}</style></head><body>"
            "<nav>Accueil Contact</nav>"
            "<main>Le contenu qui compte.</main>"
            "<footer>Mentions legales</footer></body></html>")
    lu = texte_utile(html)
    assert "Le contenu qui compte." in lu
    assert "Accueil" not in lu
    assert "Mentions" not in lu


def test_une_cloture_dans_le_corps_reste_detectee():
    # Le retrait de l'interface ne doit pas desarmer la detection.
    html = ("<html><body><nav>Menu</nav><main>Nous informons les candidats "
            "que cette offre n'est plus disponible.</main></body></html>")
    assert _classer(200, texte_utile(html)) == CLOSE


def test_le_fichier_ne_porte_aucun_caractere_de_controle():
    from pathlib import Path
    octets = Path(__file__).parents[1] / "services" / "lien_checker.py".read_bytes()
    for interdit in (7, 8, 11, 12):
        assert bytes([interdit]) not in octets, f"0x{interdit:02x} present"


from apps.offres.tests.outils import en_cas_de_test  # noqa: E402

Essais = en_cas_de_test(globals())
