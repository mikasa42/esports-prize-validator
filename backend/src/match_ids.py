"""Identificação consistente de partidas no CSV, cliente e API oficial."""
import re
import unicodedata


def normalizar_id_partida(value):
    value = unicodedata.normalize('NFKC', str(value))
    value = value.translate(str.maketrans({char: '-' for char in '‐‑‒–—−'}))
    value = ''.join(char for char in value if not char.isspace() and unicodedata.category(char) != 'Cf').upper()
    if not value:
        raise ValueError('ID Partida não pode estar vazio.')
    fortnite = re.fullmatch(r'FN-(\d{4})-R(\d+)-M(\d+)', value)
    if fortnite:
        year, round_number, match_number = fortnite.groups()
        value = f'FN-{year}-R{int(round_number)}-M{int(match_number)}'
    return value
