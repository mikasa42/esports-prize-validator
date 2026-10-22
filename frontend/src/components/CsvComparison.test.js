import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import CsvComparison from './CsvComparison';

let container, root;
const cell = (coluna, csv, oficial, status, motivo = '') => ({ coluna, csv, oficial, status, motivo });
const comparison = { somente_ids: false, resumo: { total_linhas: 2, conferente: 2, linhas_divergentes: 1, linhas_duplicadas: 1, nao_comparavel: 1, sem_referencia: 1 }, linhas: [
  { linha: 2, match_id_externo: 'MATCH-1001', jogador: 'FURIA / chelo', origem: 'banco', campos: [cell('Kills', '99', 12, 'divergente'), cell('Minutos', '24', 24, 'conferente'), cell('Rodada', '1', 1, 'conferente'), cell('Observação', '<script>teste</script>', null, 'nao_comparavel', 'Sem equivalente na API.')] },
  { linha: 3, match_id_externo: 'MATCH-404', jogador: '', duplicada_de: 2, campos: [cell('Kills', '1', null, 'sem_referencia', 'API indisponível.')] },
] };
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});
async function render(value = comparison) { await act(async () => root.render(<CsvComparison comparison={value} />)); }
async function filter(value) {
  await act(async () => {
    const select = container.querySelector('select');
    select.value = value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

test('exibe CSV e oficial lado a lado com origem e divergências', async () => {
  await render();
  const row = container.querySelector('tbody tr');
  expect(row.textContent).toContain('Kills');
  expect(row.textContent).toContain('99');
  expect(row.textContent).toContain('12');
  expect(row.textContent).toContain('Divergência');
  expect(row.textContent).toContain('Resposta oficial salva');
  expect(container.textContent).toContain('Sem referência oficial');
  expect(container.textContent).toContain('Repetida da linha 2');
});

test('filtra somente divergências sem ocultar o valor original', async () => {
  await render();
  await filter('atencao');
  expect(container.querySelectorAll('tbody tr')).toHaveLength(1);
  expect(container.querySelector('tbody').textContent).toContain('99');
  await filter('nao_comparavel');
  expect(container.querySelector('tbody').textContent).toContain('<script>teste</script>');
  expect(container.querySelector('script')).toBeNull();
});

test('busca por coluna e identificação, sem nova requisição', async () => {
  await render();
  await act(async () => {
    const input = container.querySelector('input');
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'rodada');
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  expect(container.querySelectorAll('tbody tr')).toHaveLength(1);
  expect(container.querySelector('tbody').textContent).toContain('Rodada');
});

test('paginação e mensagem de filtros vazios', async () => {
  const fields = Array.from({ length: 25 }, (_, index) => cell(`Campo${index}`, '1', 1, 'conferente'));
  await render({ ...comparison, linhas: [{ ...comparison.linhas[0], campos: fields }] });
  expect(container.querySelectorAll('tbody tr')).toHaveLength(20);
  await act(async () => container.querySelector('[aria-label="Próxima página da conferência"]').click());
  expect(container.querySelectorAll('tbody tr')).toHaveLength(5);
  await filter('atencao');
  expect(container.querySelector('.comparison-empty').textContent).toContain('Nenhum campo');
  expect(container.querySelector('[aria-current="page"]').textContent).toBe('1 / 1');
});

test('arquivo só com IDs informa que faltam estatísticas para comparação', async () => {
  await render({ ...comparison, somente_ids: true });
  expect(container.querySelector('.comparison-notice').textContent).toContain('contém apenas IDs');
});

test('sem comparação mantém compatibilidade com respostas antigas', async () => {
  await render(null);
  expect(container.textContent).toBe('');
});
