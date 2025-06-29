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
            if (e.detail.updates.currentLean || e.detail.updates.currentTopic) {
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
            if (e.detail.updates.currentLean || e.detail.updates.currentTopic) {
                this.render();
            }
        });
    }

    render() {
        const state = appState.state;
        const leanNames = ['Liberal', 'Center-Left', 'Neutral', 'Center-Right', 'Conservative'];
        const leanIdx = [ -2, -1, 0, 1, 2 ].indexOf(state.currentLean);
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
            if (e.detail.updates.currentLean) {
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

// Register all components
customElements.define('top-panel', TopPanel);
customElements.define('content-area', ContentArea);
customElements.define('sidebar-widget', SidebarWidget);

// Make appState globally available for demo buttons
window.appState = appState;

// Demo: Log all state changes
appState.addEventListener('statechange', (e) => {
    console.log('🔄 State Change:', e.detail.updates);
});

console.log('✅ All components loaded and registered!');