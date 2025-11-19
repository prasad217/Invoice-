FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY .npmrc ./
RUN npm install --no-audit --no-fund --legacy-peer-deps
COPY . .
EXPOSE 3000
CMD ["npm","run","dev"]
