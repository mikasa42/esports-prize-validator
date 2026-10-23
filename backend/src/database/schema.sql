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

-- Contas da aplicação. Nunca armazenar a senha original.
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    login VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    empresa VARCHAR(150) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Apenas o hash do token de sessão fica no banco.
CREATE TABLE IF NOT EXISTS sessoes_usuario (
    token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    usuario_id INT NOT NULL,
    expira_em DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sessoes_expiracao (expira_em),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- Limite compartilhado entre processos, por endereço IP e janela de tempo.
CREATE TABLE IF NOT EXISTS tentativas_autenticacao (
    chave CHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    tentativas INT NOT NULL DEFAULT 1,
    expira_em DATETIME NOT NULL,
    INDEX idx_tentativas_expiracao (expira_em)
);


-- Entrada durável para o processamento assíncrono e resultado por usuário.
CREATE TABLE IF NOT EXISTS consultas (
    id CHAR(36) CHARACTER SET ascii PRIMARY KEY,
    usuario_id INT NOT NULL,
    nome_arquivo VARCHAR(255) NOT NULL,
    criterio VARCHAR(10) NOT NULL,
    conteudo MEDIUMBLOB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    total INT NOT NULL,
    processadas INT NOT NULL DEFAULT 0,
    tentativas INT NOT NULL DEFAULT 0,
    resultado LONGTEXT NULL,
    erro VARCHAR(255) NULL,
    criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_consultas_usuario (usuario_id, criada_em),
    INDEX idx_consultas_status (status),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);
