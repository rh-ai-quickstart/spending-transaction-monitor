# Multi-stage build for React application
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy root package files for workspace setup (context is root)
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./

# Copy workspace packages
COPY packages/ui/ ./packages/ui/
COPY packages/configs/ ./packages/configs/

# Set working directory to UI package
WORKDIR /app/packages/ui

# Install dependencies using workspace
RUN pnpm install --no-frozen-lockfile

# Build the application
RUN pnpm run build:vite

# Production stage - use Node.js to serve static files
FROM node:20-alpine

WORKDIR /app

# Install serve package globally to serve static files
RUN npm install -g serve

# Copy built assets from builder stage
COPY --from=builder /app/packages/ui/dist ./dist

# Create non-root user for OpenShift compatibility
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001 -G nodejs

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

EXPOSE 8080

# Use serve to host the SPA with proper routing
CMD ["serve", "-s", "dist", "-l", "8080"]