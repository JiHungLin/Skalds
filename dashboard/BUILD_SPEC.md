# Skald Dashboard Build and Deployment Specification

## Project Setup

### Directory Structure
```
dashboard/
├── .github/            # GitHub Actions workflows
├── src/               # Source code
├── public/            # Static assets
├── dist/              # Build output
├── vite.config.ts     # Vite configuration
├── tailwind.config.js # Tailwind CSS configuration
├── package.json       # Project dependencies
└── tsconfig.json      # TypeScript configuration
```

## Build Configuration

### Vite Configuration (vite.config.ts)
```typescript
export default defineConfig({
  base: '/dashboard/', // Serves under /dashboard path
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          table: ['@tanstack/react-table'],
          query: ['@tanstack/react-query']
        }
      }
    }
  }
})
```

### TypeScript Configuration (tsconfig.json)
```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "react-jsx",
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    }
  }
}
```

## Development Environment

### Prerequisites
- Node.js >= 18.0.0
- npm >= 9.0.0

### Development Commands
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Unit testing
npm run test

# Build for production
npm run build
```

## Production Build Process

1. **Pre-build Steps**
   - Lint check
   - Type check
   - Unit tests
   - Clean dist directory

2. **Build Process**
   - Compile TypeScript
   - Bundle modules
   - Optimize assets
   - Generate sourcemaps

3. **Post-build Steps**
   - Validate bundle size
   - Generate build report
   - Copy static assets

## FastAPI Integration

### Build Output Location
The dashboard build output should be configured to generate files in the FastAPI static files directory:

```
skald/system_controller/static/dashboard/
├── index.html
├── assets/
│   ├── js/
│   ├── css/
│   └── images/
```

### FastAPI Static Files Configuration
```python
from fastapi.staticfiles import StaticFiles

app.mount("/dashboard", StaticFiles(directory="static/dashboard", html=True), name="dashboard")
```

## Deployment Strategy

### Local Development
1. Run FastAPI server
2. Run Vite dev server with proxy to FastAPI
3. Access dashboard at http://localhost:5173/dashboard

### Production Deployment
1. Build dashboard
2. Copy build output to FastAPI static directory
3. Deploy FastAPI application
4. Access dashboard through FastAPI server

### CI/CD Workflow

```yaml
name: Dashboard CI/CD

on:
  push:
    paths:
      - 'dashboard/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
        working-directory: ./dashboard
      
      - name: Type check
        run: npm run type-check
        working-directory: ./dashboard
      
      - name: Build
        run: npm run build
        working-directory: ./dashboard
      
      - name: Copy to FastAPI directory
        run: |
          mkdir -p skald/system_controller/static/dashboard
          cp -r dashboard/dist/* skald/system_controller/static/dashboard/
```

## Performance Optimization

### Bundle Size Optimization
- Code splitting
- Tree shaking
- Lazy loading of routes
- Image optimization

### Caching Strategy
- Static assets cached with long TTL
- API responses cached with React Query
- SSE connection management with retry logic

### Monitoring
- Bundle size tracking
- Performance metrics
- Error tracking

## Security Considerations

1. **Content Security Policy**
   - Restrict source of scripts and styles
   - Configure CSP headers in FastAPI

2. **API Security**
   - CSRF protection
   - Rate limiting
   - Input validation

3. **Static File Security**
   - Cache control headers
   - Security headers
   - File permissions

## Documentation Requirements

1. **Build Documentation**
   - Setup instructions
   - Build commands
   - Environment variables

2. **Deployment Guide**
   - Step-by-step deployment process
   - Configuration options
   - Troubleshooting guide

3. **Development Guide**
   - Code style guide
   - Git workflow
   - Testing requirements