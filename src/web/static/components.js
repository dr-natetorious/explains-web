// Global State Management
class AppState extends EventTarget {
    constructor() {
        super();
        this.state = {
            currentLean: 0,
            currentTopic: 'Dashboard',
            brandTop: 'DR★NATE',
            brandBottom: 'EXPLAINS'
        };
    }

    setState(updates) {
        const oldState = { ...this.state };
        this.state = { ...this.state, ...updates };

        console.log('State updated:', updates);

        this.dispatchEvent(new CustomEvent('statechange', {
            detail: { oldState, newState: this.state, updates }
        }));
    }

    get lean() { return this.state.currentLean; }
    get topic() { return this.state.currentTopic; }
    get brandTop() { return this.state.brandTop; }
    get brandBottom() { return this.state.brandBottom; }
}

// Global state instance
const appState = new AppState();

// Top Panel Component
class TopPanel extends HTMLElement {
    constructor() {
        super();
        this.leanLabels = ['Liberal', 'Center-Left', 'Neutral', 'Center-Right', 'Conservative'];
        this.leanValues = [-2, -1, 0, 1, 2];
    }

    connectedCallback() {
        // Initialize from attributes
        const lean = parseInt(this.getAttribute('current-lean')) ?? 0;
        const topic = this.getAttribute('topic') || 'Dashboard';
        const brandTop = this.getAttribute('brand-top') || 'DR★NATE';
        const brandBottom = this.getAttribute('brand-bottom') || 'EXPLAINS';

        // Update global state
        appState.setState({
            currentLean: lean,
            currentTopic: topic,
            brandTop,
            brandBottom
        });

        this.render();

        // Listen for global state changes
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLean !== undefined || e.detail.updates.currentTopic) {
                this.render();
            }
        });

        // Handle clicks and keyboard navigation
        this.addEventListener('click', this.handleClick.bind(this));
        this.addEventListener('keydown', this.handleKeydown.bind(this));
    }

    handleClick(e) {
        if (e.target.matches('.lean-line')) {
            const newLean = parseInt(e.target.dataset.lean);
            appState.setState({ currentLean: newLean });

            // Update focus and ARIA attributes
            this.querySelectorAll('.lean-line').forEach(line => {
                line.setAttribute('aria-checked', 'false');
                line.setAttribute('tabindex', '-1');
            });

            e.target.setAttribute('aria-checked', 'true');
            e.target.setAttribute('tabindex', '0');
            e.target.focus();

            // Update aria-activedescendant
            const radioGroup = this.querySelector('[role="radiogroup"]');
            radioGroup.setAttribute('aria-activedescendant', `lean-${newLean}`);

            // Animation feedback
            e.target.style.transform = 'scaleY(1.2)';
            setTimeout(() => {
                e.target.style.transform = '';
            }, 150);
        }
    }

    handleKeydown(e) {
        if (e.target.matches('.lean-line')) {
            const currentLean = parseInt(e.target.dataset.lean);
            let newLean = currentLean;
            const leans = this.leanValues;
            const idx = leans.indexOf(currentLean);

            switch (e.key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    newLean = leans[Math.max(0, idx - 1)];
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    newLean = leans[Math.min(leans.length - 1, idx + 1)];
                    break;
                case 'Home':
                    e.preventDefault();
                    newLean = leans[0];
                    break;
                case 'End':
                    e.preventDefault();
                    newLean = leans[leans.length - 1];
                    break;
                case ' ':
                case 'Enter':
                    e.preventDefault();
                    // Lean is already selected, just announce it
                    break;
                default:
                    return;
            }

            if (newLean !== currentLean) {
                appState.setState({ currentLean: newLean });
                // Focus will be set in the next render cycle
                setTimeout(() => {
                    const newElement = this.querySelector(`[data-lean="${newLean}"]`);
                    if (newElement) newElement.focus();
                }, 0);
            }
        }
    }

    render() {
        const state = appState.state;
        this.innerHTML = `
            <div class="panel-container">
                <div class="brand-icon" role="img" aria-label="${state.brandTop} ${state.brandBottom} logo">
                    <div class="brand-top">${state.brandTop}</div>
                    <div class="brand-bottom">${state.brandBottom}</div>
                </div>
                <div class="divider" role="separator" aria-hidden="true"></div>
                <h1 class="topic-title" id="current-topic">${state.currentTopic}</h1>
                <div class="lean-slider" role="group" aria-labelledby="lean-slider-label">
                    <div id="lean-slider-label" class="sr-only">Lean (style) selector</div>
                    <div class="slider-track" role="radiogroup" aria-label="Select lean (style)" aria-activedescendant="lean-${state.currentLean}">
                        ${this.renderLeanLines()}
                    </div>
                    <div class="slider-info" aria-live="polite" aria-atomic="true">Lean ${state.currentLean}/2</div>
                </div>
            </div>
        `;
    }

    renderLeanLines() {
        return this.leanValues.map((lean, idx) => {
            const isActive = lean === appState.lean;
            return `
                <div class="lean-line ${isActive ? 'active' : ''}"
                     data-lean="${lean}"
                     role="radio"
                     aria-checked="${isActive}"
                     aria-label="Lean ${lean}: ${this.leanLabels[idx]}"
                     id="lean-${lean}"
                     tabindex="${isActive ? '0' : '-1'}">
                    <div class="lean-label" aria-hidden="true">${this.leanLabels[idx]}</div>
                </div>
            `;
        }).join('');
    }
}

// Content Area Component
class ContentArea extends HTMLElement {
    connectedCallback() {
        this.render();
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLean !== undefined || e.detail.updates.currentTopic) {
                this.render();
            }
        });
    }

    render() {
        const state = appState.state;
        const leanNames = ['Liberal', 'Center-Left', 'Neutral', 'Center-Right', 'Conservative'];
        const leanIdx = [-2, -1, 0, 1, 2].indexOf(state.currentLean);
        this.innerHTML = `
            <div class="content-card">
                <div class="content-header">
                    <h2 id="content-title">${state.currentTopic}</h2>
                    <span class="lean-badge lean-${state.currentLean}" 
                          aria-label="Lean: ${leanNames[leanIdx >= 0 ? leanIdx : 2]}">
                        ${leanNames[leanIdx >= 0 ? leanIdx : 2]}
                    </span>
                </div>
                <div class="content-body" aria-labelledby="content-title">
                    <p>This content adapts to <strong>Lean ${state.currentLean}</strong> style.</p>
                    ${this.getContentForLean(state.currentLean)}
                </div>
            </div>
        `;
    }

    getContentForLean(lean) {
        const content = {
            '-2': '<p>🟢 <strong>Liberal:</strong> Progressive, inclusive, and open-minded tone.</p>',
            '-1': '<p>🔵 <strong>Center-Left:</strong> Moderately progressive, balanced with tradition.</p>',
            '0': '<p>🟠 <strong>Neutral:</strong> Objective, fact-based, and impartial style.</p>',
            '1': '<p>🔴 <strong>Center-Right:</strong> Moderately conservative, pragmatic approach.</p>',
            '2': '<p>🟣 <strong>Conservative:</strong> Traditional, cautious, and value-driven style.</p>'
        };
        return content[lean] || content['0'];
    }
}

// Sidebar Widget Component
class SidebarWidget extends HTMLElement {
    connectedCallback() {
        this.render();
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLean !== undefined) {
                this.render();
            }
        });
    }

    render() {
        const state = appState.state;
        const progress = ((state.currentLean + 2) / 4) * 100;
        this.innerHTML = `
            <div class="widget-card">
                <h3 id="progress-title">Progress Tracker</h3>
                <p>Current Lean: <strong>${state.currentLean}/2</strong></p>
                <div class="progress-bar" role="progressbar" 
                     aria-valuenow="${progress}" 
                     aria-valuemin="0" 
                     aria-valuemax="100"
                     aria-labelledby="progress-title"
                     aria-describedby="progress-description">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <p id="progress-description"><small>${Math.round(progress)}% Complete</small></p>
                <div style="margin-top: 20px;">
                    <h4>Quick Actions</h4>
                    <button onclick="appState.setState({currentTopic: 'Settings'})" 
                            aria-label="Navigate to Settings page">
                        Go to Settings
                    </button>
                    <button onclick="appState.setState({currentTopic: 'Profile'})" 
                            aria-label="Navigate to Profile page">
                        View Profile
                    </button>
                </div>
            </div>
        `;
    }
}

// News Story Component
class NewsStory extends HTMLElement {
    constructor() {
        super();
        this.leanLabels = ['Liberal', 'Center-Left', 'Neutral', 'Center-Right', 'Conservative'];
        this.leanAdjectives = {
            '-2': ['progressive', 'inclusive', 'forward-thinking', 'justice-oriented', 'empathetic'],
            '-1': ['balanced', 'thoughtful', 'pragmatic', 'reform-minded', 'collaborative'],
            '0': ['objective', 'factual', 'impartial', 'analytical', 'straightforward'],
            '1': ['prudent', 'measured', 'practical', 'traditional', 'responsible'],
            '2': ['principled', 'steadfast', 'time-tested', 'value-driven', 'disciplined']
        };
    }

    connectedCallback() {
        this.updateLeanAttribute();
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLean !== undefined) {
                this.updateLeanAttribute();
                this.updateLeanTexts();
            }
        });
        this.updateLeanTexts();
        this.setupSegmentInteractions();
    }

    updateLeanAttribute() {
        this.setAttribute('lean', appState.lean.toString());
    }

    updateLeanTexts() {
        const leanTexts = this.querySelectorAll('.lean-text[data-lean-variants]');
        const currentLean = appState.lean;

        leanTexts.forEach(element => {
            // Remove all lean classes
            element.className = element.className.replace(/active-lean-[-\d]+/g, '').trim();
            
            // Add current lean class
            element.classList.add(`active-lean-${currentLean}`);

            const variants = element.getAttribute('data-lean-variants');
            if (variants) {
                const variantMap = {};
                variants.split('|').forEach(variant => {
                    const [lean, text] = variant.split(':');
                    variantMap[lean] = text;
                });

                if (variantMap[currentLean]) {
                    element.textContent = variantMap[currentLean];
                }
            }
        });
    }

    setupSegmentInteractions() {
        const segments = this.querySelectorAll('segment');
        segments.forEach(segment => {
            segment.setAttribute('tabindex', '0');
            segment.setAttribute('role', 'button');
            segment.setAttribute('aria-label', 'Interactive news segment');
            
            segment.addEventListener('click', (e) => {
                this.handleSegmentClick(e, segment);
            });
            
            segment.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.handleSegmentClick(e, segment);
                }
            });
        });
    }

    handleSegmentClick(e, segment) {
        // Add click animation
        segment.style.transform = 'translateX(8px) scale(1.02)';
        setTimeout(() => {
            segment.style.transform = '';
        }, 200);

        // Log analytics or show sources
        const axis = this.getAttribute('axis') || 'general';
        const currentLean = appState.lean;
        
        console.log('📊 Segment clicked:', {
            axis,
            lean: currentLean,
            content: segment.textContent.trim().substring(0, 50) + '...'
        });

        // Show sources if available
        this.showSources(segment);
    }

    showSources(segment) {
        const sourcesElement = this.querySelector('sources');
        if (sourcesElement) {
            const sources = Array.from(sourcesElement.querySelectorAll('source')).map(source => ({
                name: source.getAttribute('name') || 'Unknown Source',
                url: source.getAttribute('url') || '#'
            }));

            if (sources.length > 0) {
                const sourceNames = sources.map(s => s.name).join(', ');
                console.log('📰 Sources for this segment:', sourceNames);
                
                // Could trigger a modal or tooltip here
                // For now, just log to console
            }
        }
    }

    // Method to get content adapted for current lean
    getAdaptedContent(originalContent, targetLean) {
        // This method could be used to dynamically adapt content
        // based on lean when the component is created programmatically
        
        const adjustments = {
            '-2': content => content
                .replace(/apparently/g, 'evidently')
                .replace(/simply/g, 'systematically')
                .replace(/vanishing/g, 'being eliminated'),
            '-1': content => content
                .replace(/apparently/g, 'clearly')
                .replace(/simply/g, 'systematically'),
            '0': content => content, // Keep neutral
            '1': content => content
                .replace(/apparently/g, 'predictably')
                .replace(/systematically/g, 'methodically'),
            '2': content => content
                .replace(/apparently/g, 'unsurprisingly')
                .replace(/systematically/g, 'methodically')
                .replace(/being eliminated/g, 'vanishing')
        };

        return adjustments[targetLean.toString()] ? 
               adjustments[targetLean.toString()](originalContent) : 
               originalContent;
    }

    // Utility method to create news story programmatically
    static create(config) {
        const newsStory = document.createElement('news-story');
        newsStory.setAttribute('lean', config.lean || '0');
        newsStory.setAttribute('axis', config.axis || 'general');

        const segment = document.createElement('segment');
        segment.textContent = config.content || '';

        const sources = document.createElement('sources');
        if (config.sources && config.sources.length > 0) {
            config.sources.forEach(sourceData => {
                const source = document.createElement('source');
                source.setAttribute('name', sourceData.name || '');
                source.setAttribute('url', sourceData.url || '');
                if (sourceData.urlToImage) {
                    source.setAttribute('urlToImage', sourceData.urlToImage);
                }
                sources.appendChild(source);
            });
        }

        newsStory.appendChild(segment);
        newsStory.appendChild(sources);

        return newsStory;
    }
}

// Utility Functions
const NewsUtils = {
    // Create lean-text spans programmatically
    createLeanText(variants, defaultText) {
        const span = document.createElement('span');
        span.className = 'lean-text';
        span.setAttribute('data-lean-variants', variants);
        span.textContent = defaultText;
        return span;
    },

    // Parse lean variants string into object
    parseLeanVariants(variantsString) {
        const variants = {};
        variantsString.split('|').forEach(variant => {
            const [lean, text] = variant.split(':');
            variants[lean] = text;
        });
        return variants;
    },

    // Get text for specific lean
    getTextForLean(variantsString, lean) {
        const variants = this.parseLeanVariants(variantsString);
        return variants[lean.toString()] || variants['0'] || '';
    },

    // Analytics helper
    trackSegmentInteraction(axis, lean, content) {
        // This could send data to analytics service
        console.log('📈 Analytics:', {
            event: 'segment_interaction',
            axis,
            lean,
            content_preview: content.substring(0, 100),
            timestamp: new Date().toISOString()
        });
    }
};

// Register all components
customElements.define('top-panel', TopPanel);
customElements.define('content-area', ContentArea);
customElements.define('sidebar-widget', SidebarWidget);
customElements.define('news-story', NewsStory);

// Make globals available
window.appState = appState;
window.NewsStory = NewsStory;
window.NewsUtils = NewsUtils;

// Demo: Log all state changes
appState.addEventListener('statechange', (e) => {
    console.log('🔄 State Change:', e.detail.updates);
});

// Initialize analytics tracking
appState.addEventListener('statechange', (e) => {
    if (e.detail.updates.currentLean !== undefined) {
        NewsUtils.trackSegmentInteraction('lean_change', e.detail.newState.currentLean, 'Global lean slider');
    }
});

console.log('✅ All components loaded and registered!');