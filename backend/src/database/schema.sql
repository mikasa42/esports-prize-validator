-- Tabelas criadas no banco configurado pela aplicação.

-- 1. Tabela de Equipes (Times)
CREATE TABLE IF NOT EXISTS equipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Jogadores (Atrelados a uma equipe)
CREATE TABLE IF NOT EXISTS jogadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipe_id INT NOT NULL,
    nick VARCHAR(100) NOT NULL,
    FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE
);

-- 3. Tabela de Partidas (Resumo geral da partida)
CREATE TABLE IF NOT EXISTS partidas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_partida_externo VARCHAR(50) NOT NULL UNIQUE, -- Ex: MATCH-101 ou FN-2026-R1-M1001
    data_partida DATE NOT NULL,
    rodada INT NOT NULL
);

-- 4. Tabela de Estatísticas da Partida por Jogador (Desempenho individual e de equipe na partida)
CREATE TABLE IF NOT EXISTS estatisticas_partida (
    id INT AUTO_INCREMENT PRIMARY KEY,
    partida_id INT NOT NULL,
    jogador_id INT NOT NULL,
    equipe_id INT NOT NULL,
    minutos INT NOT NULL,
    kills INT NOT NULL,
    venceu ENUM('Sim', 'Não') NOT NULL,
    FOREIGN KEY (partida_id) REFERENCES partidas(id) ON DELETE CASCADE,
    FOREIGN KEY (jogador_id) REFERENCES jogadores(id) ON DELETE CASCADE,
    FOREIGN KEY (equipe_id) REFERENCES equipes(id) ON DELETE CASCADE
);

-- Resposta completa para consultas posteriores sem acesso à API.
CREATE TABLE IF NOT EXISTS respostas_oficiais (
    id_partida_externo VARCHAR(50) PRIMARY KEY,
    resposta JSON NOT NULL,
    FOREIGN KEY (id_partida_externo) REFERENCES partidas(id_partida_externo) ON DELETE CASCADE
);
