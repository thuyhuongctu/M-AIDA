FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Build-time API base URL. Default "" = same-origin: the nginx layer below
# proxies /api/ to the backend, so no absolute URL is needed on a single host.
# For split hosting, pass --build-arg VITE_API_URL=https://api.your-domain.example
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
