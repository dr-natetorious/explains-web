// Dr Nate Explains - Template-Based Component System

/**
 * Simple template-based component system
 * - No Shadow DOM complexity
 * - Easy property binding
 * - Centralized CSS styling
 * - Template-driven updates
 */

// Base Component Class
class TemplateComponent extends HTMLElement {
    constructor() {
        super();
        this.data = {};
        this.template = '';
        this.isConnected = false;
    }

    connectedCallback() {
        this.isConnected = true;
        this.init();
        this.render();
        this.bindEvents();
    }

    disconnectedCallback() {
        this.isConnected = false;
        this.cleanup();
    }

    // Override in subclasses
    init() {}
    bindEvents() {}
    cleanup() {}

    // Simple template system with {{}} binding
    render() {
        if (!this.template) return;
        
        let html = this.template;
        
        // Replace {{property}} with actual values
        html = html.replace(/\{\{(\w+)\}\}/g, (match, prop) => {
            return this.data[prop] || '';
        });
        
        // Replace {{#if condition}} blocks
        html = html.replace(/\{\{#if (\w+)\}\}(.*?)\{\{\/if\}\}/gs, (match, condition, content) => {
            return this.data[condition] ? content : '';
        });
        
        // Replace {{#each array}} blocks
        html = html.replace(/\{\{#each (\w+)\}\}(.*?)\{\{\/each\}\}/gs, (match, arrayName, itemTemplate) => {
            const array = this.data[arrayName] || [];
            return array.map(item => {
                let itemHtml = itemTemplate;
                Object.keys(item).forEach(key => {
                    itemHtml = itemHtml.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), item[key]);
                });
                return itemHtml;
            }).join('');
        });
        
        this.innerHTML = html;
    }

    // Update component data and re-render
    updateData(newData) {
        this.data = { ...this.data, ...newData };
        if (this.isConnected) {
            this.render();
        }
    }

    // Get property values from attributes
    getAttributeData() {
        const data = {};
        for (let attr of this.attributes) {
            data[attr.name.replace(/-/g, '_')] = attr.value;
        }
        return data;
    }

    // Dispatch custom events
    emit(eventName, detail = {}) {
        this.dispatchEvent(new CustomEvent(eventName, {
            detail,
            bubbles: true,
            composed: true
        }));
    }
}

// Lean Control Component
class LeanControl extends TemplateComponent {
    init() {
        this.data = {
            lean: parseInt(this.getAttribute('lean')) || 0,
            context: this.getAttribute('context') || 'general',
            ...this.getAttributeData()
        };
        
        this.template = `
            <div class="lean-control">
                <div class="lean-control__header">
                    <h3 class="lean-control__title">Perspective Control</h3>
                    <div class="lean-control__value">
                        <i class="bi bi-sliders"></i>
                        <span>{{displayValue}}</span>
                    </div>
                </div>
                
                <div class="lean-control__slider-container">
                    <input 
                        type="range" 
                        class="lean-control__slider" 
                        min="-2" 
                        max="2" 
                        step="1" 
                        value="{{lean}}"
                        aria-label="Perspective control slider"
                    >
                </div>
                
                <div class="lean-control__labels">
                    <span>{{leftLabel}}</span>
                    <span>Neutral</span>
                    <span>{{rightLabel}}</span>
                </div>
                
                <div class="lean-control__description">
                    {{description}}
                </div>
            </div>
        `;
        
        this.updateLabelsAndValues();
    }

    bindEvents() {
        const slider = this.querySelector('.lean-control__slider');
        if (slider) {
            slider.addEventListener('input', (e) => {
                this.data.lean = parseInt(e.target.value);
                this.updateLabelsAndValues();
                this.render();
                this.emit('lean-change', {
                    lean: this.data.lean,
                    context: this.data.context
                });
            });
        }
    }

    updateLabelsAndValues() {
        const contexts = {
            politics: { left: 'Liberal', right: 'Conservative' },
            tech: { left: 'Simple', right: 'Advanced' },
            business: { left: 'Basic', right: 'Expert' },
            science: { left: 'Popular', right: 'Technical' },
            general: { left: 'Liberal', right: 'Conservative' }
        };
        
        const labels = contexts[this.data.context] || contexts.general;
        this.data.leftLabel = labels.left;
        this.data.rightLabel = labels.right;
        
        const leanTexts = {
            '-2': { display: `Very ${labels.left}`, desc: `Articles emphasize ${labels.left.toLowerCase()} viewpoints and perspectives.` },
            '-1': { display: labels.left, desc: `Articles lean toward ${labels.left.toLowerCase()} interpretations while acknowledging other views.` },
            '0': { display: 'Neutral', desc: 'Articles present balanced perspectives with multiple viewpoints represented fairly.' },
            '1': { display: labels.right, desc: `Articles lean toward ${labels.right.toLowerCase()} interpretations while acknowledging other views.` },
            '2': { display: `Very ${labels.right}`, desc: `Articles emphasize ${labels.right.toLowerCase()} values and perspectives.` }
        };
        
        const current = leanTexts[this.data.lean.toString()] || leanTexts['0'];
        this.data.displayValue = current.display;
        this.data.description = current.desc;
    }

    // Public API
    get lean() {
        return this.data.lean;
    }

    set lean(value) {
        this.data.lean = parseInt(value) || 0;
        this.updateLabelsAndValues();
        this.render();
    }

    get context() {
        return this.data.context;
    }

    set context(value) {
        this.data.context = value;
        this.updateLabelsAndValues();
        this.render();
    }
}

// Headline Card Component
class HeadlineCard extends TemplateComponent {
    init() {
        this.data = {
            title: this.getAttribute('title') || 'Loading...',
            summary: this.getAttribute('summary') || 'Loading summary...',
            category: this.getAttribute('category') || 'general',
            timestamp: this.getAttribute('timestamp') || 'Just now',
            read_time: this.getAttribute('read-time') || '5 min read',
            complexity: parseInt(this.getAttribute('complexity')) || 1,
            url: this.getAttribute('url') || '#',
            ...this.getAttributeData()
        };
        
        this.template = `
            <article class="headline-card" style="--category-color: var(--color-${this.data.category})">
                <header class="headline-card__header">
                    <span class="headline-card__category headline-card__category--${this.data.category}">
                        {{categoryDisplay}}
                    </span>
                    <div class="headline-card__complexity">
                        {{#each complexityDots}}
                        <div class="headline-card__complexity-dot {{#if active}}headline-card__complexity-dot--active{{/if}}"></div>
                        {{/each}}
                    </div>
                </header>
                
                <h3 class="headline-card__title">{{title}}</h3>
                <p class="headline-card__summary">{{summary}}</p>
                
                <footer class="headline-card__footer">
                    <div class="headline-card__meta">
                        <i class="bi bi-clock"></i>
                        <span>{{timestamp}}</span>
                    </div>
                    <div class="headline-card__meta">
                        <i class="bi bi-book"></i>
                        <span>{{read_time}}</span>
                    </div>
                </footer>
            </article>
        `;
        
        this.updateComplexityData();
        this.updateCategoryDisplay();
    }

    bindEvents() {
        const card = this.querySelector('.headline-card');
        if (card) {
            card.addEventListener('click', () => {
                this.emit('headline-click', {
                    title: this.data.title,
                    url: this.data.url,
                    category: this.data.category
                });
                
                if (this.data.url && this.data.url !== '#') {
                    window.location.href = this.data.url;
                }
            });

            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    card.click();
                }
            });

            // Make focusable for accessibility
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            card.setAttribute('aria-label', `Read article: ${this.data.title}`);
        }
    }

    updateComplexityData() {
        this.data.complexityDots = [];
        for (let i = 1; i <= 5; i++) {
            this.data.complexityDots.push({
                active: i <= this.data.complexity
            });
        }
    }

    updateCategoryDisplay() {
        this.data.categoryDisplay = this.data.category.charAt(0).toUpperCase() + this.data.category.slice(1);
    }

    // Update specific properties
    updateTitle(title) {
        this.updateData({ title });
    }

    updateSummary(summary) {
        this.updateData({ summary });
    }

    updateCategory(category) {
        this.data.category = category;
        this.updateCategoryDisplay();
        this.render();
    }

    updateComplexity(complexity) {
        this.data.complexity = parseInt(complexity) || 1;
        this.updateComplexityData();
        this.render();
    }
}

// Headlines Grid Component
class HeadlinesGrid extends TemplateComponent {
    init() {
        this.data = {
            headlines: [],
            loading: true,
            category: this.getAttribute('category') || 'all',
            lean: parseInt(this.getAttribute('lean')) || 0
        };
        
        this.template = `
            <div class="headlines-grid">
                {{#if loading}}
                <div class="headlines-grid__loading">
                    <div class="flex flex--center p-8">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading headlines...</span>
                        </div>
                    </div>
                </div>
                {{/if}}
                
                {{#if headlines}}
                <div class="grid grid--3">
                    {{#each headlines}}
                    <headline-card
                        title="{{title}}"
                        summary="{{summary}}"
                        category="{{category}}"
                        timestamp="{{timestamp}}"
                        read-time="{{readTime}}"
                        complexity="{{complexity}}"
                        url="{{url}}">
                    </headline-card>
                    {{/each}}
                </div>
                {{/if}}
                
                {{#if showLoadMore}}
                <div class="headlines-grid__load-more">
                    <button class="btn btn-outline-primary btn-lg" id="load-more-btn">
                        Load More Headlines
                    </button>
                </div>
                {{/if}}
            </div>
        `;
    }

    bindEvents() {
        const loadMoreBtn = this.querySelector('#load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.emit('load-more');
            });
        }
    }

    // Load headlines data
    async loadHeadlines(headlines = null) {
        if (headlines) {
            this.updateData({ 
                headlines, 
                loading: false,
                showLoadMore: headlines.length >= 6
            });
        } else {
            // Simulate API call
            this.updateData({ loading: true });
            
            setTimeout(() => {
                const mockHeadlines = this.generateMockHeadlines();
                this.updateData({ 
                    headlines: mockHeadlines, 
                    loading: false,
                    showLoadMore: true
                });
            }, 1000);
        }
    }

    generateMockHeadlines() {
        return [
            {
                title: "Federal Reserve Announces Interest Rate Decision",
                summary: "The Federal Reserve's latest monetary policy decision impacts markets globally as inflation concerns continue.",
                category: "business",
                timestamp: "2 hours ago",
                readTime: "5 min read",
                complexity: 2,
                url: "/article/fed-rate-decision"
            },
            {
                title: "Breakthrough in Quantum Computing Research",
                summary: "Scientists achieve major milestone in quantum error correction, bringing practical quantum computers closer to reality.",
                category: "tech",
                timestamp: "4 hours ago",
                readTime: "7 min read",
                complexity: 4,
                url: "/article/quantum-computing-breakthrough"
            },
            {
                title: "Climate Summit Reaches Historic Agreement",
                summary: "World leaders commit to ambitious new climate targets in unprecedented global cooperation effort.",
                category: "politics",
                timestamp: "6 hours ago",
                readTime: "4 min read",
                complexity: 1,
                url: "/article/climate-summit-agreement"
            },
            {
                title: "New Archaeological Discovery Rewrites History",
                summary: "Ancient artifacts found in Peru suggest advanced civilization existed earlier than previously thought.",
                category: "science",
                timestamp: "8 hours ago",
                readTime: "6 min read",
                complexity: 3,
                url: "/article/archaeological-discovery"
            },
            {
                title: "Tech Giants Report Quarterly Earnings",
                summary: "Major technology companies exceed expectations despite economic headwinds and regulatory challenges.",
                category: "business",
                timestamp: "10 hours ago",
                readTime: "5 min read",
                complexity: 2,
                url: "/article/tech-earnings"
            },
            {
                title: "Renewable Energy Milestone Achieved",
                summary: "Solar and wind power generation hits record highs as costs continue to decline globally.",
                category: "science",
                timestamp: "12 hours ago",
                readTime: "4 min read",
                complexity: 2,
                url: "/article/renewable-energy-milestone"
            }
        ];
    }

    filterByCategory(category) {
        this.data.category = category;
        // Filter logic would be implemented here
        this.emit('category-filter', { category });
    }

    updateLean(lean) {
        this.data.lean = lean;
        // This would trigger re-fetching headlines with new perspective
        this.emit('lean-update', { lean });
    }
}

// Category Filter Component
class CategoryFilter extends TemplateComponent {
    init() {
        this.data = {
            categories: [
                { id: 'all', name: 'All', active: true },
                { id: 'politics', name: 'Politics', active: false },
                { id: 'tech', name: 'Tech', active: false },
                { id: 'business', name: 'Business', active: false },
                { id: 'science', name: 'Science', active: false }
            ],
            activeCategory: 'all'
        };
        
        this.template = `
            <div class="category-filter">
                <div class="flex gap-2">
                    {{#each categories}}
                    <button 
                        class="btn {{#if active}}btn-secondary{{/if}}{{#if active}}{{else}}btn-outline-secondary{{/if}} btn-sm" 
                        data-category="{{id}}">
                        {{name}}
                    </button>
                    {{/each}}
                </div>
            </div>
        `;
    }

    bindEvents() {
        this.addEventListener('click', (e) => {
            if (e.target.matches('[data-category]')) {
                const category = e.target.dataset.category;
                this.setActiveCategory(category);
                this.emit('category-change', { category });
            }
        });
    }

    setActiveCategory(categoryId) {
        this.data.categories.forEach(cat => {
            cat.active = cat.id === categoryId;
        });
        this.data.activeCategory = categoryId;
        this.render();
    }
}

// Simple State Management
class AppState {
    constructor() {
        this.state = {
            lean: 0,
            context: 'general',
            category: 'all',
            headlines: [],
            loading: false
        };
        this.subscribers = [];
    }

    subscribe(callback) {
        this.subscribers.push(callback);
        return () => {
            this.subscribers = this.subscribers.filter(sub => sub !== callback);
        };
    }

    setState(newState) {
        const prevState = { ...this.state };
        this.state = { ...this.state, ...newState };
        
        this.subscribers.forEach(callback => {
            callback(this.state, prevState);
        });
    }

    getState() {
        return { ...this.state };
    }
}

// Theme Manager (simplified)
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme();
        this.bindToggle();
    }

    bindToggle() {
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    toggleTheme() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme();
        localStorage.setItem('theme', this.theme);
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            const icon = toggle.querySelector('i');
            if (icon) {
                icon.className = this.theme === 'light' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
            }
        }
    }
}

// Initialize everything when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    // Register custom elements
    customElements.define('lean-control', LeanControl);
    customElements.define('headline-card', HeadlineCard);
    customElements.define('headlines-grid', HeadlinesGrid);
    customElements.define('category-filter', CategoryFilter);
    
    // Initialize app state
    const appState = new AppState();
    
    // Initialize theme manager
    const themeManager = new ThemeManager();
    
    // Global event handling
    document.addEventListener('lean-change', (e) => {
        appState.setState({ lean: e.detail.lean, context: e.detail.context });
        
        // Update headlines grid with new lean
        const headlinesGrid = document.querySelector('headlines-grid');
        if (headlinesGrid) {
            headlinesGrid.updateLean(e.detail.lean);
        }
    });
    
    document.addEventListener('category-change', (e) => {
        appState.setState({ category: e.detail.category });
        
        // Update headlines grid with new category
        const headlinesGrid = document.querySelector('headlines-grid');
        if (headlinesGrid) {
            headlinesGrid.filterByCategory(e.detail.category);
        }
    });
    
    document.addEventListener('headline-click', (e) => {
        console.log('Headline clicked:', e.detail);
        // Analytics tracking could go here
    });
    
    // Auto-load headlines on page load
    setTimeout(() => {
        const headlinesGrid = document.querySelector('headlines-grid');
        if (headlinesGrid) {
            headlinesGrid.loadHeadlines();
        }
    }, 100);
    
    // Expose for debugging
    window.appState = appState;
    window.themeManager = themeManager;
});

// Export components for external use
window.DrNateComponents = {
    LeanControl,
    HeadlineCard,
    HeadlinesGrid,
    CategoryFilter,
    AppState,
    ThemeManager
};