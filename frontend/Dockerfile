# Estágio 1: Build da aplicação React
FROM node:18-alpine AS builder
WORKDIR /app

# Copia os arquivos de dependência
COPY package*.json ./

# Instala as dependências fixadas no lockfile
RUN npm ci --legacy-peer-deps
# Mantém a compatibilidade do ajv-keywords 5 com o Webpack.
RUN npm install ajv@^8.12.0 --save --legacy-peer-deps

# Copia todo o restante do código do frontend
COPY . .

# Executa o build de produção
RUN npm run build

# Estágio 2: Servir os arquivos estáticos com Nginx
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
