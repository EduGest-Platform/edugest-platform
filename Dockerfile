# Frontend (React 19 + Vite 8): compila a estáticos y los sirve con nginx.
# Contexto de build: la raíz del repositorio (ver infra/compose.yaml).
FROM node:22-alpine AS build
WORKDIR /app
# Misma versión de pnpm que .mise.toml y el CI.
RUN npm install -g pnpm@10.34.3
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# La URL de la API se incrusta al compilar (ADR-0004). Sin ella, la web arranca en modo local.
ARG VITE_GISTAR_API_URL=""
ENV VITE_GISTAR_API_URL=${VITE_GISTAR_API_URL}
RUN pnpm build

FROM nginx:1.27-alpine
COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
