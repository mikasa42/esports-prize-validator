-- Criação das tabelas para o desafio da PowerRev

CREATE TABLE IF NOT EXISTS torneios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    premio_total DECIMAL(10, 2) NOT NULL DEFAULT 10000.00,
    criterio_rateio ENUM('minutos', 'kills') DEFAULT 'minutos',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS partidas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    torneio_id INT NOT NULL,
    match_id_externo VARCHAR(100) NOT NULL UNIQUE,
    data_partida DATE NOT NULL,
    rodada INT NOT NULL,
    confronto VARCHAR(255) NOT NULL,
    status_verificacao ENUM('pendente', 'verificado', 'divergente', 'erro_api') DEFAULT 'pendente',
    detalhes_verificacao TEXT,
    FOREIGN KEY (torneio_id) REFERENCES torneios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS participantes_partida (
    id INT AUTO_INCREMENT PRIMARY KEY,
    partida_id INT NOT NULL,
    time_nome VARCHAR(100) NOT NULL,
    jogador_nick VARCHAR(100) NOT NULL,
    minutos INT NOT NULL,
    kills INT NOT NULL,
    venceu BOOLEAN NOT NULL,
    FOREIGN KEY (partida_id) REFERENCES partidas(id) ON DELETE CASCADE
);