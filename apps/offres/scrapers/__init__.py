"""Registre des sources. L'ordre est celui de la collecte.

UNGM : API refusee le 25/08/2026, collecte par la page publique. Ses
conditions d'utilisation demandent un accord ecrit (voir Offre/sources.py).
"""

from .afriquedusud import AfriqueDuSudScraper
from .africacdc import AfricaCdcScraper
from .armp_madagascar import ArmpScraper
from .bad import BadScraper
from .berd import BerdScraper
from .banquemondiale import BanqueMondialeScraper
from .benin import BeninScraper
from .bm_avis import BanqueMondialeAvisScraper
from .boamp import BoampScraper
from .cameroun import CamerounScraper
from .canada import CanadaScraper
from .coi import CoiScraper
from .conservation import ConservationScraper
from .cote_ivoire import CoteIvoireScraper
from .enabel import EnabelScraper
from .fid import FidScraper
from .grants_gov import GrantsGovScraper
from .ghana import GhanaScraper
from .isdb import IsdbScraper
from .jirama import JiramaScraper
from .kenya import KenyaScraper
from .luxdev import LuxdevScraper
from .malawi import MalawiScraper
from .mali import MaliScraper
from .maroc import MarocScraper
from .maurice import MauriceScraper
from .mnp import MnpScraper
from .namibie import NamibieScraper
from .nouvelle_zelande import NouvelleZelandeScraper
from .ouganda import OugandaScraper
from .rwanda import RwandaScraper
from .seychelles import SeychellesScraper
from .ted import TedScraper
from .ue_ft import UeFundingTendersScraper
from .undp import UndpScraper
from .ungm import UngmScraper
from .unjobnet import UnjobnetScraper
from .wwf import WwfScraper
from .wordpress import CemacScraper, GretScraper, MeddMadagascarScraper

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
    UngmScraper,
    # Ajoutees le 19/11/2026 apres recherche web (ecartees : voir Offre/sources.py).
    UeFundingTendersScraper,
    GrantsGovScraper,
    OugandaScraper,
    CoteIvoireScraper,
    # Deuxieme vague du 19/11/2026 : cooperations europeennes, BERD, Rwanda, Canada, Nouvelle-Zelande.
    EnabelScraper,
    LuxdevScraper,
    BerdScraper,
    RwandaScraper,
    CanadaScraper,
    NouvelleZelandeScraper,
    # Troisieme vague du 19/11/2026 : sites WordPress (scrapers/wordpress.py).
    MeddMadagascarScraper,
    CemacScraper,
    GretScraper,
]
