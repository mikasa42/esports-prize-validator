import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import usePublicResults from './usePublicResults';
function Harness({ year }) {
  const state = usePublicResults(year, '', 0);
  return <p>{state.status}:{state.data?.torneio}</p>;
}
test('resposta antiga não substitui seleção mais recente', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const container = document.createElement('div');
  const root = createRoot(container);
  let oldResolve;
  global.fetch = jest.fn().mockImplementationOnce(() => new Promise(resolve => { oldResolve = resolve; }))
    .mockResolvedValueOnce({ ok: true, json: async () => ({ torneio: 'novo' }) });
  try {
    await act(async () => root.render(<Harness year="2025" />));
    const oldSignal = fetch.mock.calls[0][1].signal;
    await act(async () => root.render(<Harness year="2026" />));
    expect(oldSignal.aborted).toBe(true);
    await act(async () => oldResolve({ ok: true, json: async () => ({ torneio: 'antigo' }) }));
    expect(container.textContent).toBe('success:novo');
  } finally {
    await act(async () => root.unmount());
    delete global.fetch;
  }
});
