FROM node:22-alpine AS build

WORKDIR /src
COPY package.json package-lock.json ./
RUN npx --yes npm@10.5.0 ci --no-audit --no-fund

COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src/ ./src/
COPY public/ ./public/

ENV VITE_APP_BASE_API=/gateway/ir-agent/ \
    VITE_API_TOKEN=
RUN npx --yes npm@10.5.0 run build

FROM nginxinc/nginx-unprivileged:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist/ /usr/share/nginx/html/investment/

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
