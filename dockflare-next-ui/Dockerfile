FROM node:18-alpine AS builder # <<< THIS LINE WAS MISSING/INCOMPLETE
LABEL stage=nextjs-builder

WORKDIR /app
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build
FROM node:18-alpine AS runner
LABEL stage=nextjs-runner # This label is optional, but good for clarity

WORKDIR /app

ENV NODE_ENV production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]