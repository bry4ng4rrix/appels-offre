"""Registre des sources. L'ordre est celui de la collecte.

UNGM n'y figure plus : acces API refuse le 25/08/2026 (reserve aux agences
onusiennes et organisations intergouvernementales).
"""

from .afriquedusud import AfriqueDuSudScraper
from .armp_madagascar import ArmpScraper
from .bad import BadScraper
from .banquemondiale import BanqueMondialeScraper
from .benin import BeninScraper
from .bm_avis import BanqueMondialeAvisScraper
from .boamp import BoampScraper
from .cameroun import CamerounScraper
from .coi import CoiScraper
from .conservation import ConservationScraper
from .fid import FidScraper
from .ghana import GhanaScraper
from .kenya import KenyaScraper
from .malawi import MalawiScraper
from .mali import MaliScraper
from .maroc import MarocScraper
from .maurice import MauriceScraper
from .mnp import MnpScraper
from .namibie import NamibieScraper
from .ted import TedScraper
from .unjobnet import UnjobnetScraper
from .wwf import WwfScraper

REGISTRE_SCRAPERS = [
    UnjobnetScraper,
    BanqueMondialeScraper,
    BanqueMondialeAvisScraper,
    BadScraper,
    ArmpScraper,
    FidScraper,
    WwfScraper,
    MnpScraper,
    TedScraper,
    BoampScraper,
    CoiScraper,
    MauriceScraper,
    ConservationScraper,
    # Portails nationaux africains, ajoutes le 14/09/2026.
    CamerounScraper,
    MaliScraper,
    GhanaScraper,
    MalawiScraper,
    NamibieScraper,
    AfriqueDuSudScraper,
    MarocScraper,
    BeninScraper,
    KenyaScraper,
]
