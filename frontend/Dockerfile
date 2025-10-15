# S.O.S Cidadão Frontend - Development Dockerfile
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs \
    && adduser -S app -u 1001 -G nodejs \
    && chown -R app:nodejs /app
USER app

# Expose port
EXPOSE 3000

# Health check is configured in docker-compose.yml

# Run the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]