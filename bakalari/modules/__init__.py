""" """
import os
__all__ = [ x[:-3] for x in os.listdir(os.path.dirname(__file__)) if x.endswith(".py") and not x.startswith("_") ]

#BTW je tohle vůbec potřeba? Jak tak nad tím přemýšlím, tak ne... eShrug Protože generuji