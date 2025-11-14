# AI AGENT MASTER INSTRUCTIONS — Base Project Template

> **PURPOSE**: This is the single file an AI agent needs to read to create a complete project from scratch. Contains all instructions, structures, and configurations needed to generate a functional base project.

---

## 📋 EXECUTIVE SUMMARY

**WHAT THIS FILE DOES**: 
- Instructs AI agent to create complete project structure
- Defines architecture, technologies, and development patterns
- Establishes AI workflow and deployment configuration
- Generates all necessary files for a functional project

**EXPECTED RESULT**:
- FastAPI + Frontend project ready for development
- Complete CI/CD configuration with GitHub Actions
- Development environment with devcontainer
- Documentation and deployment guides
- Standardized file structure

---

## 🎯 PROJECT INITIALIZATION PROTOCOL

### STEP 1: Automatic Project Detection and Setup

**FIRST**: Check if there's a `README.md` file in the current directory:

1. **If README.md exists**:
   - Read and analyze the content
   - Extract project concept, description, and requirements
   - Use this as the project foundation
   - Auto-generate project name and codename from README content
   - Show extracted information and ask for confirmation

2. **If README.md does NOT exist**:
   - Ask user: "I don't see a README.md file. Would you like to:"
     - a) Upload/create a README.md with your project concept first
     - b) Start with basic project ideas and I'll help create the concept
   - If option (a): Wait for README.md, then proceed as above
   - If option (b): Gather project information interactively

### STEP 2: Project Information Collection

When collecting project data, **ALWAYS** ask these values:

```yaml
REQUIRED_DATA:
  project_name: "Project Name"           # Ex: "Management System"
  codename: "project-code"               # Ex: "management-system" (lowercase, hyphens)
  repository_url: "https://github.com/user/repo.git"
  domain: "domain.com"                   # OPTIONAL - only for web projects
  port: 8001                             # OPTIONAL - unique number 8000-8999
  description: "Brief description"        # OPTIONAL or extracted from README
  project_concept: "Full concept"        # Extracted from README or user input
```

**MANDATORY VALIDATIONS**:
- `project_name`: Cannot be empty
- `codename`: Only letters, numbers, and hyphens, all lowercase
- `repository_url`: Must be valid GitHub HTTPS URL
- `port`: If provided, must be integer between 8000-8999
- `domain`: If provided, valid domain format

---

## 🏗️ PROJECT ARCHITECTURE

### Standard Technology Stack
```yaml
Backend:
  - Python 3.12+
  - FastAPI + Uvicorn
  - SQLite (desarrollo) / PostgreSQL (producción)
  - Pydantic para validación
  - SQLAlchemy ORM

Frontend:
  - HTML5 + CSS3
  - Alpine.js (sin build system)
  - TailwindCSS
  - Vanilla JavaScript

Development:
  - VS Code + Devcontainer
  - GitHub Codespaces
  - Python virtual environment
  - Pre-commit hooks

Deployment:
  - VPS con Nginx
  - systemd service
  - GitHub Actions CI/CD
  - SSH automated deployment
```

### Directory Structure
```
project/
├── .devcontainer/
│   └── devcontainer.json
├── .github/
│   ├── workflows/
│   │   └── deploy.yml
│   └── copilot-instructions.md
├── .vscode/
│   └── settings.json
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── routers/
│   │       └── __init__.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── pages/                    # Páginas específicas del proyecto
│   │   ├── dashboard.html
│   │   └── admin.html
│   ├── components/              # Componentes Alpine.js reutilizables
│   │   ├── navigation/
│   │   │   ├── navbar.js
│   │   │   └── sidebar.js
│   │   ├── forms/
│   │   │   ├── input-field.js
│   │   │   ├── select-field.js
│   │   │   └── form-validation.js
│   │   ├── data/
│   │   │   ├── data-table.js
│   │   │   ├── pagination.js
│   │   │   └── search-filter.js
│   │   ├── ui/
│   │   │   ├── modal.js
│   │   │   ├── toast.js
│   │   │   ├── loading.js
│   │   │   └── card.js
│   │   └── layout/
│   │       ├── header.js
│   │       └── footer.js
│   ├── stores/                  # Alpine stores (estado global)
│   │   ├── auth.js
│   │   ├── app.js
│   │   └── notifications.js
│   ├── utils/                   # Utilidades JavaScript
│   │   ├── api.js
│   │   ├── validation.js
│   │   └── helpers.js
│   ├── static/
│   │   ├── css/
│   │   │   ├── components.css
│   │   │   └── pages.css
│   │   ├── js/
│   │   │   └── app.js
│   │   └── img/
│   └── templates/               # Fragmentos HTML reutilizables
│       ├── modals/
│       ├── forms/
│       └── cards/
├── docs/
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEVELOPMENT_GUIDE.md
│   ├── API_DOCS.md
│   └── private/              ← LOCAL ONLY (not tracked by Git)
│       ├── NOTAS_PROYECTO.md
│       ├── IDEAS_DESARROLLO.md
│       └── CONFIGURACIONES_LOCALES.md
├── scripts/
│   ├── start_dev.sh
│   └── deploy.sh
├── .env.example
├── .gitignore              ← GENERATED by AI agent
├── README.md
├── requirements.txt
└── manifest.json
```

---

## 📝 FILES TO GENERATE

### 1. Root File: `manifest.json`
```json
{
  "project_name": "{{project_name}}",
  "codename": "{{codename}}",
  "repository_url": "{{repository_url}}",
  "domain": "{{domain}}",
  "port": {{port}},
  "description": "{{description}}",
  "created_at": "{{fecha_actual}}",
  "technology_stack": {
    "backend": "FastAPI + Python 3.12+",
    "frontend": "HTML + Alpine.js + TailwindCSS",
    "database": "SQLite/PostgreSQL",
    "deployment": "VPS + Nginx + systemd"
  },
  "version": "1.0.0"
}
```

### 2. Main Backend: `backend/app/main.py`
```python
"""
{{project_name}} - FastAPI Application
Generated from AI Agent Master Template
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="{{project_name}}",
    description="{{description}}",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("../frontend/static"):
    app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/")
async def root():
    return {"message": "{{project_name}} API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "{{project_name}}"}

# API routes
@app.get("/api/v1/status")
async def api_status():
    return {"api_version": "1.0.0", "status": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={{port or 8000}})
```

### 3. Main Frontend: `frontend/index.html`
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{project_name}}</title>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div x-data="app()" class="container mx-auto px-4 py-8">
        <header class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">{{project_name}}</h1>
            <p class="text-gray-600">{{description}}</p>
        </header>
        
        <main>
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-2xl font-semibold mb-4">Estado del Sistema</h2>
                <div x-show="loading" class="text-blue-500">Cargando...</div>
                <div x-show="!loading && status" class="text-green-600">
                    ✅ API Conectada: <span x-text="status"></span>
                </div>
                <div x-show="error" class="text-red-600" x-text="error"></div>
            </div>
        </main>
    </div>

    <!-- Load Alpine.js stores and components -->
    <script src="./stores/auth.js"></script>
    <script src="./stores/app.js"></script>
    <script src="./utils/api.js"></script>
    <script src="./components/ui/toast.js"></script>

    <script>
        function app() {
            return {
                loading: true,
                status: null,
                error: null,
                
                async init() {
                    try {
                        const response = await fetch('/api/v1/status');
                        const data = await response.json();
                        this.status = data.status;
                        this.loading = false;
                    } catch (err) {
                        this.error = 'Error conectando con la API';
                        this.loading = false;
                    }
                }
            }
        }
    </script>
</body>
</html>
```

### 3.1. Core Component: `frontend/components/ui/modal.js`
```javascript
/**
 * Reusable Modal Component for {{project_name}}
 * Usage: x-data="modal({ title: 'My Modal', size: 'lg' })"
 */
function modal(config = {}) {
    return {
        open: false,
        title: config.title || 'Modal',
        size: config.size || 'md',
        closable: config.closable !== false,
        
        show() {
            this.open = true;
            document.body.style.overflow = 'hidden';
            this.$nextTick(() => {
                if (this.$refs.modal) {
                    this.$refs.modal.focus();
                }
            });
        },
        
        hide() {
            this.open = false;
            document.body.style.overflow = 'auto';
        },
        
        onEscape(event) {
            if (event.key === 'Escape' && this.closable) {
                this.hide();
            }
        },
        
        onBackdropClick(event) {
            if (event.target === event.currentTarget && this.closable) {
                this.hide();
            }
        },
        
        init() {
            // Focus management
            this.$watch('open', value => {
                if (value) {
                    document.addEventListener('keydown', this.onEscape);
                } else {
                    document.removeEventListener('keydown', this.onEscape);
                }
            });
        }
    }
}

// Make available globally
window.modal = modal;
```

### 3.2. Data Component: `frontend/components/data/data-table.js`
```javascript
/**
 * Advanced Data Table Component for {{project_name}}
 * Usage: x-data="dataTable({ apiUrl: '/api/items', itemsPerPage: 10 })"
 */
function dataTable(config = {}) {
    return {
        // Data state
        items: [],
        loading: false,
        error: null,
        
        // Search & Filter
        searchTerm: '',
        filters: config.filters || {},
        
        // Sorting
        sortBy: config.sortBy || 'id',
        sortDirection: 'asc',
        
        // Pagination
        currentPage: 1,
        itemsPerPage: config.itemsPerPage || 10,
        
        // Selection
        selectedItems: [],
        selectAll: false,
        
        // API Configuration
        apiUrl: config.apiUrl || '/api/items',
        
        // Fetch data from API
        async fetchData() {
            this.loading = true;
            this.error = null;
            
            try {
                const params = new URLSearchParams({
                    page: this.currentPage,
                    per_page: this.itemsPerPage,
                    sort_by: this.sortBy,
                    sort_direction: this.sortDirection,
                    search: this.searchTerm,
                    ...this.filters
                });
                
                const response = await fetch(`${this.apiUrl}?${params}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                this.items = data.items || data;
                
            } catch (error) {
                this.error = error.message;
                console.error('Error fetching data:', error);
            } finally {
                this.loading = false;
            }
        },
        
        // Computed properties
        get filteredItems() {
            if (!this.searchTerm) return this.items;
            
            return this.items.filter(item => 
                Object.values(item).some(value => 
                    String(value).toLowerCase().includes(this.searchTerm.toLowerCase())
                )
            );
        },
        
        get paginatedItems() {
            const start = (this.currentPage - 1) * this.itemsPerPage;
            return this.filteredItems.slice(start, start + this.itemsPerPage);
        },
        
        get totalPages() {
            return Math.ceil(this.filteredItems.length / this.itemsPerPage);
        },
        
        // Sorting methods
        sort(field) {
            if (this.sortBy === field) {
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortBy = field;
                this.sortDirection = 'asc';
            }
            
            this.items.sort((a, b) => {
                const aVal = a[field];
                const bVal = b[field];
                const modifier = this.sortDirection === 'asc' ? 1 : -1;
                
                if (aVal < bVal) return -1 * modifier;
                if (aVal > bVal) return 1 * modifier;
                return 0;
            });
        },
        
        getSortIcon(field) {
            if (this.sortBy !== field) return '↕️';
            return this.sortDirection === 'asc' ? '↑' : '↓';
        },
        
        // Pagination methods
        goToPage(page) {
            if (page >= 1 && page <= this.totalPages) {
                this.currentPage = page;
            }
        },
        
        nextPage() {
            this.goToPage(this.currentPage + 1);
        },
        
        prevPage() {
            this.goToPage(this.currentPage - 1);
        },
        
        // Selection methods
        toggleItem(item) {
            const index = this.selectedItems.findIndex(selected => selected.id === item.id);
            if (index > -1) {
                this.selectedItems.splice(index, 1);
            } else {
                this.selectedItems.push(item);
            }
            this.updateSelectAll();
        },
        
        toggleAll() {
            if (this.selectAll) {
                this.selectedItems = [...this.paginatedItems];
            } else {
                this.selectedItems = [];
            }
        },
        
        updateSelectAll() {
            this.selectAll = this.paginatedItems.length > 0 && 
                           this.paginatedItems.every(item => 
                               this.selectedItems.some(selected => selected.id === item.id)
                           );
        },
        
        isSelected(item) {
            return this.selectedItems.some(selected => selected.id === item.id);
        },
        
        // Initialize component
        init() {
            this.fetchData();
            
            // Watch for search changes with debounce
            let searchTimeout;
            this.$watch('searchTerm', () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.currentPage = 1;
                    if (config.liveSearch) {
                        this.fetchData();
                    }
                }, 300);
            });
        }
    }
}

window.dataTable = dataTable;
```

### 3.3. Navigation Component: `frontend/components/navigation/navbar.js`
```javascript
/**
 * Navigation Bar Component for {{project_name}}
 */
function navbar() {
    return {
        mobileMenuOpen: false,
        userMenuOpen: false,
        
        toggleMobileMenu() {
            this.mobileMenuOpen = !this.mobileMenuOpen;
        },
        
        toggleUserMenu() {
            this.userMenuOpen = !this.userMenuOpen;
        },
        
        closeMobileMenu() {
            this.mobileMenuOpen = false;
        },
        
        closeUserMenu() {
            this.userMenuOpen = false;
        },
        
        async logout() {
            try {
                await this.$store.auth.logout();
                window.location.href = '/login';
            } catch (error) {
                console.error('Logout error:', error);
            }
        },
        
        get user() {
            return this.$store.auth.user;
        },
        
        get isAuthenticated() {
            return this.$store.auth.isAuthenticated;
        },
        
        init() {
            // Close menus when clicking outside
            document.addEventListener('click', (event) => {
                if (!this.$el.contains(event.target)) {
                    this.mobileMenuOpen = false;
                    this.userMenuOpen = false;
                }
            });
        }
    }
}

window.navbar = navbar;
```

### 3.4. Form Component: `frontend/components/forms/form-validation.js`
```javascript
/**
 * Form Validation Component for {{project_name}}
 */
function formValidation(config = {}) {
    return {
        fields: config.fields || {},
        errors: {},
        submitted: false,
        loading: false,
        
        // Validation rules
        rules: {
            required: (value) => value !== null && value !== undefined && value !== '',
            email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
            min: (value, min) => String(value).length >= min,
            max: (value, max) => String(value).length <= max,
            numeric: (value) => !isNaN(value) && !isNaN(parseFloat(value)),
            url: (value) => {
                try {
                    new URL(value);
                    return true;
                } catch {
                    return false;
                }
            }
        },
        
        // Validate single field
        validateField(fieldName) {
            const field = this.fields[fieldName];
            const value = field.value;
            const rules = field.rules || [];
            
            this.errors[fieldName] = [];
            
            for (const rule of rules) {
                if (typeof rule === 'string') {
                    // Simple rule like 'required', 'email'
                    if (this.rules[rule] && !this.rules[rule](value)) {
                        this.errors[fieldName].push(this.getErrorMessage(rule, fieldName));
                    }
                } else if (typeof rule === 'object') {
                    // Rule with parameters like { min: 5 }
                    const [ruleName, ruleValue] = Object.entries(rule)[0];
                    if (this.rules[ruleName] && !this.rules[ruleName](value, ruleValue)) {
                        this.errors[fieldName].push(this.getErrorMessage(ruleName, fieldName, ruleValue));
                    }
                }
            }
            
            return this.errors[fieldName].length === 0;
        },
        
        // Validate all fields
        validateForm() {
            let isValid = true;
            
            for (const fieldName in this.fields) {
                if (!this.validateField(fieldName)) {
                    isValid = false;
                }
            }
            
            return isValid;
        },
        
        // Get error message
        getErrorMessage(rule, fieldName, ruleValue = null) {
            const messages = {
                required: `${fieldName} es requerido`,
                email: `${fieldName} debe ser un email válido`,
                min: `${fieldName} debe tener al menos ${ruleValue} caracteres`,
                max: `${fieldName} no debe exceder ${ruleValue} caracteres`,
                numeric: `${fieldName} debe ser un número`,
                url: `${fieldName} debe ser una URL válida`
            };
            
            return messages[rule] || `${fieldName} es inválido`;
        },
        
        // Check if field has errors
        hasError(fieldName) {
            return this.errors[fieldName] && this.errors[fieldName].length > 0;
        },
        
        // Get field error message
        getError(fieldName) {
            return this.hasError(fieldName) ? this.errors[fieldName][0] : null;
        },
        
        // Submit form
        async submitForm(submitHandler) {
            this.submitted = true;
            
            if (!this.validateForm()) {
                return false;
            }
            
            this.loading = true;
            
            try {
                const formData = {};
                for (const [fieldName, field] of Object.entries(this.fields)) {
                    formData[fieldName] = field.value;
                }
                
                await submitHandler(formData);
                return true;
            } catch (error) {
                console.error('Form submission error:', error);
                return false;
            } finally {
                this.loading = false;
            }
        },
        
        init() {
            // Watch field values for real-time validation
            for (const fieldName in this.fields) {
                this.$watch(`fields.${fieldName}.value`, () => {
                    if (this.submitted) {
                        this.validateField(fieldName);
                    }
                });
            }
        }
    }
}

window.formValidation = formValidation;
```

### 3.5. Global Store: `frontend/stores/auth.js`
```javascript
/**
 * Authentication Store for {{project_name}}
 */
document.addEventListener('alpine:init', () => {
    Alpine.store('auth', {
        user: null,
        token: localStorage.getItem('auth_token'),
        loading: false,
        
        async login(credentials) {
            this.loading = true;
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(credentials)
                });
                
                if (!response.ok) {
                    throw new Error('Login failed');
                }
                
                const data = await response.json();
                this.user = data.user;
                this.token = data.token;
                localStorage.setItem('auth_token', data.token);
                
                return true;
            } catch (error) {
                console.error('Login error:', error);
                throw error;
            } finally {
                this.loading = false;
            }
        },
        
        async logout() {
            try {
                if (this.token) {
                    await fetch('/api/auth/logout', {
                        method: 'POST',
                        headers: { 
                            'Authorization': `Bearer ${this.token}`,
                            'Content-Type': 'application/json' 
                        }
                    });
                }
            } catch (error) {
                console.error('Logout error:', error);
            } finally {
                this.user = null;
                this.token = null;
                localStorage.removeItem('auth_token');
            }
        },
        
        async checkAuth() {
            if (!this.token) return false;
            
            try {
                const response = await fetch('/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                });
                
                if (response.ok) {
                    this.user = await response.json();
                    return true;
                } else {
                    this.logout();
                    return false;
                }
            } catch (error) {
                console.error('Auth check error:', error);
                this.logout();
                return false;
            }
        },
        
        get isAuthenticated() {
            return !!this.token && !!this.user;
        }
    });
});
```

### 3.6. API Utility: `frontend/utils/api.js`
```javascript
/**
 * API Utility functions for {{project_name}}
 */
class API {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }
    
    // Get auth token from Alpine store
    getAuthToken() {
        return Alpine.store('auth').token;
    }
    
    // Build headers with auth
    getHeaders(includeAuth = true, customHeaders = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...customHeaders
        };
        
        if (includeAuth && this.getAuthToken()) {
            headers['Authorization'] = `Bearer ${this.getAuthToken()}`;
        }
        
        return headers;
    }
    
    // Handle API response
    async handleResponse(response) {
        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: response.statusText }));
            throw new Error(error.message || `HTTP ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        }
        
        return response.text();
    }
    
    // GET request
    async get(endpoint, params = {}, options = {}) {
        const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                url.searchParams.append(key, value);
            }
        });
        
        const response = await fetch(url, {
            method: 'GET',
            headers: this.getHeaders(options.auth !== false, options.headers),
            ...options
        });
        
        return this.handleResponse(response);
    }
    
    // POST request
    async post(endpoint, data = {}, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: this.getHeaders(options.auth !== false, options.headers),
            body: JSON.stringify(data),
            ...options
        });
        
        return this.handleResponse(response);
    }
    
    // PUT request
    async put(endpoint, data = {}, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: this.getHeaders(options.auth !== false, options.headers),
            body: JSON.stringify(data),
            ...options
        });
        
        return this.handleResponse(response);
    }
    
    // DELETE request
    async delete(endpoint, options = {}) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'DELETE',
            headers: this.getHeaders(options.auth !== false, options.headers),
            ...options
        });
        
        return this.handleResponse(response);
    }
}

// Create global instance
window.api = new API();
```

### 4. Development Configuration: `.devcontainer/devcontainer.json`
```json
{
  "name": "{{project_name}} DevContainer",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/github-cli:1": {},
    "ghcr.io/devcontainers/features/node:1": {"version": "18"}
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-toolsai.jupyter",
        "GitHub.copilot",
        "GitHub.copilot-chat"
      ]
    }
  },
  "postCreateCommand": "pip install -r backend/requirements.txt",
  "forwardPorts": [{{port or 8000}}],
  "portsAttributes": {
    "{{port or 8000}}": {
      "label": "{{project_name}} API",
      "onAutoForward": "notify"
    }
  }
}
```

### 5. Copilot Instructions: `.github/copilot-instructions.md`
```markdown
# GitHub Copilot Instructions - {{project_name}}

## Project Context
- **Name**: {{project_name}}
- **Technologies**: FastAPI + Alpine.js + TailwindCSS
- **Architecture**: API Backend + Frontend SPA
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Deployment**: VPS with Nginx

## Communication Style
- **Language**: **ALWAYS respond in Spanish** when communicating with the developer
- **Response Length**: **Keep responses SHORT, CONCISE and TO THE POINT** - this is CRITICAL
  - Default: Brief, direct answers (1-3 sentences maximum)
  - Only provide detailed explanations when explicitly asked ("dame más detalles", "explícame mejor")
  - After detailed explanations, return to short responses immediately
- **Code**: English for variable names, functions, classes, and comments
- **Documentation**: Spanish for user-facing docs, English for technical docs
- **Commit messages**: English
- **Error messages**: Spanish explanations with English technical details

## Code Style
- **Python**: Use type hints, docstrings, and PEP8 conventions
- **JavaScript**: ES6+, functional when possible
- **HTML/CSS**: Semantic, accessible, responsive with TailwindCSS

## Development Patterns
1. **REST API**: Use FastAPI routers, Pydantic schemas, appropriate status codes
2. **Frontend**: Alpine.js with simple components, no build process
3. **Database**: SQLAlchemy ORM, manual migrations
4. **Testing**: Pytest for backend, manual for frontend
5. **Error Handling**: Consistent JSON responses, proper logging

## Workflow
- Local development in devcontainer/Codespaces
- Feature branch → PR → merge → auto-deploy
- CI/CD with GitHub Actions
- Automated deployment via SSH

## Useful Commands
```bash
# Local development
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port {{port or 8000}}

# Testing
cd backend && python -m pytest

# Deployment (automatic via GitHub Actions)
git push origin main
```

## Developer Preferences
- **CRITICAL**: Wants SHORT, DIRECT responses by default
- Prefers explanations in Spanish
- Likes detailed context before implementation
- Values clean, maintainable code  
- Focuses on practical, working solutions
- Only wants long explanations when explicitly requested
```

### 6. GitHub Actions: `.github/workflows/deploy.yml`
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy to VPS
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.VPS_HOST }}
        username: ${{ secrets.VPS_USER }}
        key: ${{ secrets.VPS_SSH_KEY }}
        port: ${{ secrets.VPS_PORT || '22' }}
        script: |
          # Navigate to project directory
          cd /var/www/{{codename}} || exit 1
          
          # Pull latest code
          git pull origin main
          
          # Update dependencies
          source /root/.venv_{{codename}}/bin/activate
          pip install -r backend/requirements.txt
          
          # Restart service
          sudo systemctl restart {{codename}}.service
          sudo systemctl reload nginx
          
          # Check status
          sleep 5
          curl -f http://localhost:{{port or 8000}}/health || exit 1
          
          echo "✅ Deployment successful"
```

### 7. Variables de entorno: `.env.example`
```env
# {{project_name}} Environment Variables

# API Configuration
API_HOST=0.0.0.0
API_PORT={{port or 8000}}
DEBUG=true

# Database Configuration
DATABASE_URL=sqlite:///./{{codename}}.db
# DATABASE_URL=postgresql://user:password@localhost/{{codename}}

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=*

# External APIs (if needed)
# EXTERNAL_API_KEY=
# EXTERNAL_API_URL=

# Production Settings
# DOMAIN={{domain}}
# SSL_CERT_PATH=
# SSL_KEY_PATH=
```

### 8. Git Configuration: `.gitignore`
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/
.venv/
.env/

# Environment Variables
.env
.env.local
.env.production
.env.staging

# IDE
.vscode/settings.json
.vscode/launch.json
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Database
*.db
*.sqlite
*.sqlite3

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# SSH Keys
*.pem
*.key
id_rsa
id_rsa.pub

# Temporary files
tmp/
temp/
*.tmp
*.temp

# Coverage
.coverage
.coverage.*
htmlcov/
.tox/
coverage.xml
*.cover
.hypothesis/

# Jupyter Notebook
.ipynb_checkpoints

# Node.js (if used)
node_modules/
package-lock.json
yarn.lock

# LOCAL DOCUMENTATION (not tracked)
docs/private/
```

### 9. Local Documentation: `docs/private/NOTAS_PROYECTO.md`
```markdown
# Notas del Proyecto - {{project_name}}

> 📝 Este archivo es LOCAL y NO se sube a GitHub. Úsalo para tus notas personales, ideas, y configuraciones sensibles.

## 🎯 Conceptos y Ideas

### Idea Original
{{project_concept}}

### Funcionalidades Planeadas
- [ ] 
- [ ] 
- [ ] 

### Notas de Desarrollo
- 
- 
- 

## 🔧 Configuraciones Locales

### Variables de Entorno Sensibles
```env
# Agregar aquí credenciales reales (NO en .env.example)
DATABASE_URL=
SECRET_KEY=
API_KEYS=
```

### Configuraciones del Servidor
- Host: 
- Puerto: {{port}}
- Dominio: {{domain}}

## 📋 Tareas Pendientes

- [ ] 
- [ ] 
- [ ] 

## 💭 Ideas Futuras

- 
- 
- 

---
*Archivo creado automáticamente por AI Agent el {{fecha_actual}}*
```

### 10. Local Ideas File: `docs/private/IDEAS_DESARROLLO.md`
```markdown
# Ideas de Desarrollo - {{project_name}}

> 💡 Espacio para brainstorming y evolución del proyecto

## 🚀 Funcionalidades Futuras

### Corto Plazo (1-2 semanas)
- [ ] 
- [ ] 

### Mediano Plazo (1-2 meses)
- [ ] 
- [ ] 

### Largo Plazo (3+ meses)
- [ ] 
- [ ] 

## 🔄 Mejoras de la Arquitectura

- 
- 
- 

## 🎨 Mejoras de UI/UX

- 
- 
- 

## 📊 Métricas y Analytics

- 
- 
- 

## 🔌 Integraciones Posibles

- 
- 
- 

---
*Actualizar regularmente con nuevas ideas*
```

### 11. Local Config File: `docs/private/CONFIGURACIONES_LOCALES.md`
```markdown
# Configuraciones Locales - {{project_name}}

> ⚙️ Configuraciones específicas del entorno de desarrollo local

## 🔧 Configuración de Desarrollo

### VS Code Settings
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black"
}
```

### Comandos Frecuentes
```bash
# Iniciar desarrollo
cd backend && source ../venv/bin/activate && python -m uvicorn app.main:app --reload

# Ejecutar tests
cd backend && python -m pytest

# Backup base de datos
cp {{codename}}.db backups/{{codename}}_$(date +%Y%m%d).db
```

## 🔑 Credenciales de Desarrollo

### Base de Datos Local
- Host: localhost
- Puerto: 5432
- Usuario: 
- Password: 

### APIs Externas
- Servicio 1: 
- Servicio 2: 

## 📝 Notas del Servidor de Producción

### Acceso SSH
- Host: 
- Usuario: 
- Puerto: 

### Configuraciones
- Nginx config: `/etc/nginx/sites-available/{{codename}}`
- Service file: `/etc/systemd/system/{{codename}}.service`
- App directory: `/var/www/{{codename}}`

---
*Mantener actualizado con cambios de configuración*
```

### 12. README.md del proyecto
```markdown
# {{project_name}}

{{description}}

## 🚀 Inicio Rápido

### Desarrollo Local

1. **Abrir en Codespaces/DevContainer**
   ```bash
   # El devcontainer instala automáticamente las dependencias
   ```

2. **Instalar dependencias manualmente (opcional)**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port {{port or 8000}}
   ```

4. **Acceder a la aplicación**
   - Frontend: http://localhost:{{port or 8000}}/frontend/
   - API Docs: http://localhost:{{port or 8000}}/docs
   - Health Check: http://localhost:{{port or 8000}}/health

## 📁 Estructura del Proyecto

```
{{codename}}/
├── backend/           # FastAPI application
├── frontend/          # Component-based frontend architecture
│   ├── components/    # Reusable Alpine.js components
│   ├── stores/        # Global state management
│   ├── utils/         # JavaScript utilities
│   └── pages/         # Application pages
├── .devcontainer/     # VS Code devcontainer config
├── .github/           # GitHub Actions & Copilot config
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## 🛠️ Tecnologías

- **Backend**: FastAPI + Python 3.12+
- **Frontend**: Component-based architecture with Alpine.js + TailwindCSS
  - Reusable components (modals, data tables, forms, navigation)
  - Global state management with Alpine stores
  - No build process required - vanilla JavaScript
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Deployment**: VPS + Nginx + systemd
- **CI/CD**: GitHub Actions

## 🧩 Arquitectura Frontend

El frontend utiliza una arquitectura por componentes que permite:
- **Componentes Reutilizables**: Modal, DataTable, Forms, Navigation
- **Estado Global**: Alpine.js stores para auth, notificaciones, etc.
- **Modularidad**: Cada componente es independiente y configurable
- **Escalabilidad**: Fácil agregar nuevos componentes y páginas
- **Sin Build Process**: Desarrollo directo sin herramientas de compilación

## 🚀 Deployment

El deployment es automático cuando se hace push a `main`:

1. GitHub Actions ejecuta el workflow
2. Se conecta al VPS via SSH
3. Actualiza el código y dependencias
4. Reinicia los servicios
5. Verifica que la aplicación esté funcionando

### Configuración Manual del VPS

Ver `docs/DEPLOYMENT_GUIDE.md` para instrucciones detalladas.

## 📚 Documentación

- [Guía de Desarrollo](docs/DEVELOPMENT_GUIDE.md)
- [Guía de Deployment](docs/DEPLOYMENT_GUIDE.md)  
- [Documentación de API](docs/API_DOCS.md)

## 🤝 Colaboración con AI

Este proyecto está optimizado para trabajar con GitHub Copilot. Ver `.github/copilot-instructions.md` para detalles sobre el estilo de código y patrones recomendados.

## 📄 Licencia

[Especificar licencia aquí]
```

---

## 🤖 INITIALIZATION PROTOCOL

### Step 1: Automatic Project Detection
1. **Read** this file completely
2. **Check for README.md** in current directory:
   - If exists: Parse content, extract project concept, auto-generate name/codename
   - If missing: Ask user to either create README.md or provide project concept

3. **For README.md analysis**:
   - Extract project title/name from headers
   - Generate codename (lowercase, hyphens)
   - Use content as project description and concept
   - Auto-detect technology preferences if mentioned

4. **Collect remaining data** (if not in README):
   - Repository URL (current repo or ask for target)
   - Domain (optional)
   - Port (optional, suggest based on project type)

5. **Validate** all collected data according to defined rules

### Step 2: Confirmation
1. **Show project summary**:
   ```
   PROJECT SUMMARY:
   ================
   Name: [project_name]
   Codename: [codename]
   Repository: [repository_url]
   Domain: [domain or "Not specified"]
   Port: [port or "8000 (default)"]
   Concept: [extracted from README or user input]
   
   FILES TO CREATE:
   - manifest.json
   - Complete backend/ structure
   - Complete frontend/ structure
   - .devcontainer/ configuration
   - GitHub Actions and configuration
   - Complete documentation
   
   Proceed with creation? Type 'YES' to confirm.
   ```

2. **Wait for explicit user confirmation**

### Step 3: File Generation
1. **Create** `manifest.json` with collected values
2. **Generate** complete directory structure including `docs/private/`
3. **Create** all files using templates above (including .gitignore)
4. **Create** local documentation files in `docs/private/` (Spanish, not tracked)
5. **Replace** all placeholders `{{variable}}` with real values
6. **Ensure** `docs/private/` is excluded from Git tracking

### Step 4: Finalization
1. **Create branch** `scaffold/init`
2. **Commit** all generated files with message:
   ```
   feat: initialize project structure from AI template
   
   - Add complete FastAPI + Frontend structure
   - Configure devcontainer and GitHub Actions
   - Set up deployment automation
   - Include comprehensive documentation
   ```
3. **Show** summary of created files
4. **Provide** next steps instructions:
   ```
   ✅ Project initialized successfully!
   
   NEXT STEPS:
   1. Review generated files
   2. Customize .env with your values
   3. Configure GitHub secrets for deployment
   4. Merge scaffold/init branch
   5. Start development in devcontainer
   
   To run locally:
   cd backend && python -m uvicorn app.main:app --reload
   ```

### Step 5: Post-Setup Interaction
After project creation, **ALWAYS switch to Spanish** for all interactions with the developer, as configured in the generated copilot-instructions.md file.

---

## 🔒 SECURITY CONFIGURATIONS

### GitHub Secrets (for deployment)
```yaml
Secrets requeridos en GitHub:
  VPS_HOST: "IP del servidor"
  VPS_USER: "root" 
  VPS_SSH_KEY: "Clave privada SSH"
  VPS_PORT: "22" (opcional)
```

### Files that should NEVER be committed
```
.env
.env.local  
*.key
*.pem
__pycache__/
*.pyc
.vscode/settings.json (local)
```

---

## ✅ COMPLETION CHECKLIST

Upon completing initialization, verify:

- [ ] `manifest.json` created with correct values
- [ ] Complete directory structure generated (including `docs/private/`)
- [ ] Code files with functional templates
- [ ] Devcontainer configuration ready
- [ ] GitHub Actions configured
- [ ] Complete documentation included (English for repo, Spanish for local)
- [ ] `.gitignore` generated with proper exclusions
- [ ] `docs/private/` folder created with local Spanish documentation
- [ ] Branch `scaffold/init` created with commits
- [ ] Next steps instructions shown to user
- [ ] **Language switch**: After setup, communicate in Spanish with developer

**IMPORTANT!**: After generating everything, instruct user about configuring GitHub Secrets before first deployment.

---

*This file contains all necessary information for an AI agent to generate a complete and functional project. No additional files required for initialization.*