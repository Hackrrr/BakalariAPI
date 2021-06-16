"""Modul obsahující jednotlivé moduly pro BakalářiAPI.

Umožňuje přístup k low-level záležitostem BakalářiAPI.
Použij na vlastní riziko.

Obsahuje následující submoduly:
    grades - Práce se známkami
    homeworks - Práce s domácími úkoly
    komens - Práce s komens zprávami
    meetings - Práce se schůzkami
"""
from . import grades, homeworks, komens, meetings
