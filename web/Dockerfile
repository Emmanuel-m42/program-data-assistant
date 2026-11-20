# Web image: the SvelteKit app built with adapter-static, served by nginx as a single-page app.
#
#   docker build --build-arg PUBLIC_API_URL=https://pda-api-123456789012.us-central1.run.app -t pda-web web/
#
# PUBLIC_API_URL is baked into the bundle at build time. Leave it unset (or "demo") for demo mode,
# which reads the recorded runs bundled with the app and calls no API.

FROM node:24.22.3-alpine3.24 AS build
WORKDIR /web

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG PUBLIC_API_URL=demo
ENV PUBLIC_API_URL=$PUBLIC_API_URL
RUN npm run build


# nginx-unprivileged runs as uid 101 and listens on 8080.
FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/build /usr/share/nginx/html

USER 101
EXPOSE 8080
