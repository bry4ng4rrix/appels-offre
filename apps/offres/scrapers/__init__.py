"""Registre des sources. L'ordre est celui de la collecte.

UNGM n'y entre que si UNGM_ENABLED est vrai : API refusee le 25/08/2026, et
ses conditions interdisent de stocker les avis sans accord ecrit (voir
Offre/sources.py).
"""

from django.conf import settings

from .afriquedusud import AfriqueDuSudScraper
from .africacdc import AfricaCdcScraper
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
from .isdb import IsdbScraper
from .jirama import JiramaScraper
from .kenya import KenyaScraper
from .malawi import MalawiScraper
from .mali import MaliScraper
from .maroc import MarocScraper
from .maurice import MauriceScraper
from .mnp import MnpScraper
from .namibie import NamibieScraper
from .seychelles import SeychellesScraper
from .ted import TedScraper
from .undp import UndpScraper
from .ungm import UngmScraper
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
    AfricaCdcScraper,
    # Ajoutees le 17/11/2026 apres verification des listes Gemini / Perplexity.
    UndpScraper,
    IsdbScraper,
    JiramaScraper,
    SeychellesScraper,
    *([UngmScraper] if settings.UNGM_ENABLED else []),
]
