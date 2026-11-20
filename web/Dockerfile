# Web image: the SvelteKit app built with adapter-static, served by nginx as a single-page app.
#
# Build from the repo root, because the app bundles ../demo/recorded_runs.json for demo mode:
#
#   docker build -f web/Dockerfile --build-arg PUBLIC_API_URL=https://pda-api-123456789012.us-central1.run.app -t pda-web .
#
# PUBLIC_API_URL is baked into the bundle at build time. Leave it unset (or "demo") for demo mode,
# which reads the recorded runs and calls no API. web/Dockerfile.dockerignore limits the context.

FROM node:24.22.3-alpine3.24 AS build
WORKDIR /repo/web

COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci

COPY demo/recorded_runs.json /repo/demo/recorded_runs.json
COPY web/ ./
ARG PUBLIC_API_URL=demo
ENV PUBLIC_API_URL=$PUBLIC_API_URL
RUN npm run build


# nginx-unprivileged runs as uid 101 and listens on 8080.
FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/web/build /usr/share/nginx/html

USER 101
EXPOSE 8080
