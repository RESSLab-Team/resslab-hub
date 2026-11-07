FROM node:lts-alpine AS build-stage
# pnpm links node_modules from a content-addressable store (see docs/worktree-dev-environment.md).
# Installed with npm on purpose: corepack is no longer shipped with recent Node images.
RUN npm install -g pnpm@11
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY ./ .
RUN pnpm run build

FROM nginx:mainline-alpine AS production-stage
RUN mkdir /app
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build-stage /app/dist /app
