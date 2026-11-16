FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# npm ci falla con lockfiles generados en Windows (faltan dependencias opcionales de Linux);
# npm install respeta las versiones del lock y completa las de la plataforma.
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
