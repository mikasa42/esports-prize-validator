"""Leitura sem perda de linhas e comparação dos campos enviados com a fonte oficial."""
import csv
import io
import re
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from src.match_ids import normalizar_id_partida


def chave(value):
    value = unicodedata.normalize('NFKD', str(value))
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in value if not unicodedata.combining(c)).lower())


ALIASES = {
    'match_id_externo': ('id_partida', 'ID Partida', 'matchId', 'match_id_externo', 'id da partida'),
    'data_partida': ('Data', 'data_partida', 'matchDate', 'data da partida'),
    'rodada': ('Rodada', 'round'),
    'confronto': ('Partida', 'confronto', 'match'),
    'tournamentId': ('torneio', 'tournamentId', 'id_torneio'),
    'time': ('time', 'equipe', 'team'),
    'jogador': ('jogador', 'nick', 'nickname', 'player'),
    'time_nick': ('time_nick', 'time / jogador', 'time / nick'),
    'minutos': ('Minutos', 'minutesPlayed', 'tempo jogado', 'minutos jogados', 'tempo de jogo', 'tempo', 'minutes'),
    'kills': ('Kills', 'Kill', 'Abates'),
    'deaths': ('Deaths', 'Mortes'),
    'assists': ('Assists', 'Assistências'),
    'venceu': ('Venceu?', 'venceu', 'resultado', 'vitória', 'win'),
    'vencedor': ('winnerTeam', 'time vencedor', 'vencedor'),
}
CAMPOS = {chave(alias): field for field, aliases in ALIASES.items() for alias in aliases}
STATS = {'minutos', 'kills', 'deaths', 'assists', 'venceu'}


def ler_csv(content):
    text = content.decode('utf-8-sig')
    if '\n' not in text.rstrip('\n') and '\\r\\n' in text:
        text = text.replace('\\r\\n', '\n')
    try:
        header = text.splitlines()[0] if text.splitlines() else ''
        delimiter = csv.Sniffer().sniff(header, delimiters=',;\t').delimiter if any(c in header for c in ',;\t') else ','
        reader = csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True)
        columns = [name.strip() for name in next(reader)]
        if not columns or any(not name for name in columns) or len(set(columns)) != len(columns):
            raise ValueError('O CSV contém nomes de colunas vazios ou repetidos.')
        id_columns = [name for name in columns if CAMPOS.get(chave(name)) == 'match_id_externo']
        if len(id_columns) != 1:
            raise ValueError('O CSV deve conter uma única coluna id_partida ou ID Partida, com IDs preenchidos.')
        rows = []
        while True:
            line = reader.line_num + 1
            try:
                values = next(reader)
            except StopIteration:
                break
            if not values or (len(values) == 1 and not values[0].strip()):
                continue
            if len(values) != len(columns):
                raise ValueError(f'Linha {line}: quantidade de valores diferente do cabeçalho. Confira o separador e as aspas.')
            imported = dict(zip(columns, values))
            match_id = normalizar_id_partida(imported[id_columns[0]])
            if len(match_id) > 100:
                raise ValueError(f'Linha {line}: ID de partida maior que 100 caracteres.')
            rows.append({'linha': line, 'match_id_externo': match_id, 'valores': imported})
        if not rows:
            raise ValueError('O CSV deve conter ao menos uma linha com ID preenchido.')
        return columns, rows
    except (csv.Error, StopIteration) as err:
        raise ValueError('CSV inválido. Confira o cabeçalho, o separador e as aspas.') from err


def texto(value):
    return unicodedata.normalize('NFKC', str(value)).strip().casefold()


def numero(value):
    try:
        value = Decimal(str(value).strip().replace(',', '.'))
    except InvalidOperation:
        raise ValueError('Informe um número inteiro não negativo.') from None
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise ValueError('Informe um número inteiro não negativo.')
    return value


def booleano(value):
    if texto(value) in {'sim', 'true', '1', 'vitoria', 'vitória', 'venceu', 'win'}:
        return True
    if texto(value) in {'não', 'nao', 'false', '0', 'derrota', 'perdeu', 'loss'}:
        return False
    raise ValueError('Use Sim/Não, Vitória/Derrota, true/false ou 1/0.')


def data_normalizada(value):
    value = str(value).strip()
    if re.fullmatch(r'\d{2}/\d{2}/\d{4}', value):
        return datetime.strptime(value, '%d/%m/%Y').date()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return date.fromisoformat(value)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed


def iguais(field, imported, official):
    if field == 'match_id_externo':
        return normalizar_id_partida(imported) == normalizar_id_partida(official)
    if field in {'rodada', 'minutos', 'kills', 'deaths', 'assists'}:
        return numero(imported) == numero(official)
    if field == 'venceu':
        return booleano(imported) == official
    if field == 'data_partida':
        actual, expected = data_normalizada(imported), data_normalizada(official)
        # Se o CSV fornece somente a data, não exigir um horário que não foi enviado.
        if isinstance(actual, date) and not isinstance(actual, datetime):
            return actual == (expected.date() if isinstance(expected, datetime) else expected)
        return actual == expected
    return texto(imported) == texto(official)


def identificar(imported, players):
    identities = {}
    for column, value in imported.items():
        field = CAMPOS.get(chave(column))
        if field in {'time', 'jogador', 'time_nick'} and value.strip():
            identities.setdefault(field, []).append(value)
    candidates = players
    for field, values in identities.items():
        for value in values:
            def matches(player):
                team, nick = player['time_nick'].split(' / ', 1)
                expected = {'time': team, 'jogador': nick, 'time_nick': player['time_nick']}[field]
                return texto(value) == texto(expected)
            candidates = [player for player in candidates if matches(player)]
    # Só o time não identifica um jogador, mesmo se o elenco for parcial.
    has_player = bool(identities.get('jogador') or identities.get('time_nick'))
    return (candidates[0] if len(candidates) == 1 and has_player else None), identities, candidates


def comparar_linha(row, official, columns):
    fields = []
    available = official is not None and 'erro' not in official
    players = official.get('participantes', []) if available else []
    player, identities, candidates = identificar(row['valores'], players)
    winners = sorted({p['time_nick'].split(' / ', 1)[0] for p in players if p['venceu']})
    for column in columns:
        value = row['valores'][column]
        field = CAMPOS.get(chave(column))
        cell = {'coluna': column, 'campo': field, 'csv': value, 'oficial': None,
                'status': 'nao_comparavel', 'motivo': ''}
        if field is None:
            cell['motivo'] = 'Coluna sem correspondência conhecida na API oficial.'
        elif not available:
            cell.update(status='sem_referencia', motivo=(official or {}).get('erro', 'Resposta oficial indisponível.'))
        else:
            expected = None
            if field in {'match_id_externo', 'rodada', 'data_partida', 'confronto', 'tournamentId'}:
                expected = official.get(field)
            elif field == 'vencedor':
                expected = winners[0] if len(winners) == 1 else None
            elif field in {'time', 'jogador', 'time_nick'}:
                if player:
                    team, nick = player['time_nick'].split(' / ', 1)
                    expected = {'time': team, 'jogador': nick, 'time_nick': player['time_nick']}[field]
                elif field == 'time' and any(texto(p['time_nick'].split(' / ', 1)[0]) == texto(value) for p in players):
                    expected = next(p['time_nick'].split(' / ', 1)[0] for p in players if texto(p['time_nick'].split(' / ', 1)[0]) == texto(value))
                elif value.strip() and identities and not candidates:
                    cell.update(status='divergente', motivo='Time/jogador informado não corresponde a um participante desta partida.')
                else:
                    cell['motivo'] = 'Identificação ausente ou ambígua. Informe time e jogador.'
            elif field in STATS:
                if player:
                    expected = player.get(field)
                else:
                    cell['motivo'] = 'Não é possível atribuir a estatística. Informe time e jogador correspondentes à API.'
            if cell['status'] != 'divergente' and expected is not None:
                cell['oficial'] = expected
                if not value.strip():
                    cell.update(status='ausente_csv', motivo='Campo presente no cabeçalho, mas sem valor nesta linha.')
                else:
                    try:
                        cell['status'] = 'conferente' if iguais(field, value, expected) else 'divergente'
                    except (ValueError, TypeError, OverflowError) as err:
                        cell.update(status='invalido_csv', motivo=str(err) if str(err) else 'Formato inválido no CSV.')
            elif not cell['motivo']:
                cell['motivo'] = 'Campo não disponível na resposta oficial desta partida.'
        if available and field and not value.strip():
            cell.update(status='ausente_csv', motivo='Campo presente no cabeçalho, mas sem valor nesta linha.')
        elif available and cell['status'] == 'nao_comparavel':
            # Validar o formato mesmo quando falta identificação do participante.
            try:
                if field in {'rodada', 'minutos', 'kills', 'deaths', 'assists'}:
                    numero(value)
                elif field == 'venceu':
                    booleano(value)
                elif field == 'data_partida':
                    data_normalizada(value)
            except (ValueError, TypeError, OverflowError) as err:
                cell.update(status='invalido_csv', motivo=str(err) or 'Formato inválido no CSV.')
        fields.append(cell)
    statuses = {cell['status'] for cell in fields}
    status = 'divergente' if statuses & {'divergente', 'invalido_csv', 'ausente_csv'} else ('parcial' if statuses - {'conferente'} else 'conferente')
    if not available:
        status = 'sem_referencia'
    return {'linha': row['linha'], 'match_id_externo': row['match_id_externo'],
            'jogador': player['time_nick'] if player else ' / '.join(identities.get('time', []) + identities.get('jogador', []) + identities.get('time_nick', [])),
            'origem': official.get('origem') if available else None, 'status': status, 'campos': fields}


def comparar_csv(columns, rows, results):
    references = {item['match_id_externo']: item for item in results}
    compared = []
    seen = {}
    for row in rows:
        compared_row = comparar_linha(row, references.get(row['match_id_externo']), columns)
        signature = (row['match_id_externo'], tuple(row['valores'].items()))
        compared_row['duplicada_de'] = seen.get(signature)
        seen.setdefault(signature, row['linha'])
        compared.append(compared_row)
    counts = {status: 0 for status in ('conferente', 'divergente', 'ausente_csv', 'invalido_csv', 'nao_comparavel', 'sem_referencia')}
    for row in compared:
        for cell in row['campos']:
            counts[cell['status']] += 1
    return {'colunas': columns, 'linhas': compared,
            'somente_ids': all(CAMPOS.get(chave(column)) == 'match_id_externo' for column in columns),
            'resumo': {'total_linhas': len(rows), 'linhas_divergentes': sum(row['status'] == 'divergente' for row in compared),
                       'linhas_duplicadas': sum(row['duplicada_de'] is not None for row in compared), **counts}}
