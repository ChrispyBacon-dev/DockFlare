# dockflare-next-ui/Dockerfile

# Stage 1: Install dependencies and build the Next.js application
FROM node:18-alpine AS builder
LABEL stage=nextjs-builder

WORKDIR /app

# Copy package.json and lock file(s) FIRST
# This allows Docker to cache the npm install layer if these files haven't changed
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./

# Install dependencies
# tsconfig.json isn't strictly needed for `npm install` itself usually,
# but some packages might have postinstall scripts that could peek at it.
# However, the build step definitely needs it.
RUN npm install --legacy-peer-deps

# Now copy ALL the application code, including tsconfig.json, src/, public/, etc.
COPY . .

# Add a debug step to verify tsconfig.json and src contents
RUN echo "--- Contents of /app before build ---" && \
    ls -l /app && \
    echo "--- Contents of /app/src/lib ---" && \
    ls -l /app/src/lib && \
    echo "--- Contents of /app/src/components/features/logs ---" && \
    ls -l /app/src/components/features/logs && \
    echo "--- tsconfig.json content ---" && \
    cat /app/tsconfig.json && \
    echo "------------------------------------"

# Build the Next.js application
# The build step needs tsconfig.json and all source files from the COPY . . above
RUN npm run build

# Stage 2: Create the final production image for the standalone Next.js server
FROM node:18-alpine AS runner
LABEL stage=nextjs-runner

WORKDIR /app

ENV NODE_ENV production
# ENV PORT 3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]