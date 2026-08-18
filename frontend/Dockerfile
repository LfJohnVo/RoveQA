# Base image for the RoveQA frontend: build static assets, serve with nginx.
# Joined to compose in Phase 10 when the real UI exists.
FROM node:24-alpine AS build
WORKDIR /app
RUN corepack enable pnpm
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
