from Benny.benny import Benny
from MiGUBA.BibleAPI import BibleAPI
from MiGUBA.APIBible import APIBible
from MiGUBA.ESVBible import ESVBible

import os

bibleBenny = Benny(BibleAPI)
bibleBenny.register(APIBible('')) # os.getenv('API_APIBIBLE_KEY')))
bibleBenny.register(ESVBible('')) # os.getenv('API_ESV_KEY')))