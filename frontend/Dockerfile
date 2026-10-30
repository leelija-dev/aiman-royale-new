FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG INTERNAL_API_URL=http://backend:8000
ARG NEXT_PUBLIC_SITE_URL=http://localhost:8080
ARG MEDIA_CDN_DOMAIN=
ENV INTERNAL_API_URL=$INTERNAL_API_URL NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL MEDIA_CDN_DOMAIN=$MEDIA_CDN_DOMAIN NEXT_TELEMETRY_DISABLED=1
RUN npm run build
FROM node:24-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000 NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node","server.js"]
