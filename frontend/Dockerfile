FROM node:26-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5 AS build-stage
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
FROM nginxinc/nginx-unprivileged:1.31-alpine@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e AS production-stage
EXPOSE 8080
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build-stage /app/dist /app
