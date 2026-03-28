# ---- Build Stage ----
FROM node:18 AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy all source files
COPY . .

# Force clean and build
# Accept Vite environment variables at build time
ARG VITE_AUTH_API_URL
ARG VITE_DOC_API_URL
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_AUTH_API_URL=$VITE_AUTH_API_URL
ENV VITE_DOC_API_URL=$VITE_DOC_API_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

RUN npm run build

# ---- Production Stage ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf
