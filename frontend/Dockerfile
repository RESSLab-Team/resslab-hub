FROM node:26-alpine AS build-stage
# pnpm links node_modules from a content-addressable store (see docs/worktree-dev-environment.md).
# Installed with npm on purpose: corepack is no longer shipped with recent Node images.
RUN npm install -g pnpm@11
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY ./ .
RUN pnpm run build

# nginx as a non-root user (uid 101), on 8080 (#456). Same image family as
# docs/Dockerfile. COPY writes the files as root: nginx reads them, it can't
# change them.
FROM nginxinc/nginx-unprivileged:1.31-alpine AS production-stage
EXPOSE 8080
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build-stage /app/dist /app
