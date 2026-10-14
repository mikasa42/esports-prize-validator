import React from 'react';
import Icon from './Icon';

export default function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange, disabled = false }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <div className="pagination">
    <div className="pagination-meta">
      <span>{total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} de ${total} partidas` : '0 partidas'}</span>
      <label>Por página <select value={pageSize} disabled={disabled} onChange={e => onPageSizeChange(Number(e.target.value))}>{[5, 10, 20].map(size => <option key={size} value={size}>{size}</option>)}</select></label>
    </div>
    <div className="page-controls" aria-label="Paginação das partidas">
      <button className="icon-button previous" aria-label="Página anterior" disabled={disabled || page <= 1} onClick={() => onPageChange(page - 1)}><Icon name="chevron" size={16} /></button>
      <span aria-live="polite">Página <strong>{page}</strong> de {pages}</span>
      <button className="icon-button" aria-label="Próxima página" disabled={disabled || page >= pages} onClick={() => onPageChange(page + 1)}><Icon name="chevron" size={16} /></button>
    </div>
  </div>;
}
