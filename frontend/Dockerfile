# Image frontend FraudGuard : build de production React servi par Nginx.
#
# Create React App intègre les variables REACT_APP_* AU MOMENT DU BUILD :
# elles sont donc passées en arguments de build (docker compose : build.args ;
# Render : les variables d'environnement du service sont transmises comme
# build args aux ARG déclarés ci-dessous).

# ---------- Étape 1 : build ----------
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG REACT_APP_API_URL=http://localhost:8000/api
ARG REACT_APP_USE_MOCKS=false
ENV REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_USE_MOCKS=$REACT_APP_USE_MOCKS \
    GENERATE_SOURCEMAP=false

RUN npm run build

# ---------- Étape 2 : service ----------
FROM nginx:1.27-alpine

# Le modèle est converti au démarrage (envsubst) : Nginx écoute sur $PORT,
# fourni par Render (80 par défaut en local).
ENV PORT=80
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
