// Global State Management
class AppState extends EventTarget {
    constructor() {
        super();
        this.state = {
            currentLevel: 3,
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

    get level() { return this.state.currentLevel; }
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
        this.levelLabels = ['Basic', 'Intermediate', 'Advanced', 'Expert', 'Master'];
    }

    connectedCallback() {
        // Initialize from attributes
        const level = parseInt(this.getAttribute('current-level')) || 3;
        const topic = this.getAttribute('topic') || 'Dashboard';
        const brandTop = this.getAttribute('brand-top') || 'DR★NATE';
        const brandBottom = this.getAttribute('brand-bottom') || 'EXPLAINS';

        // Update global state
        appState.setState({
            currentLevel: level,
            currentTopic: topic,
            brandTop,
            brandBottom
        });

        this.render();

        // Listen for global state changes
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLevel || e.detail.updates.currentTopic) {
                this.render();
            }
        });

        // Handle clicks and keyboard navigation
        this.addEventListener('click', this.handleClick.bind(this));
        this.addEventListener('keydown', this.handleKeydown.bind(this));
    }

    handleClick(e) {
        if (e.target.matches('.level-line')) {
            const newLevel = parseInt(e.target.dataset.level);
            appState.setState({ currentLevel: newLevel });

            // Update focus and ARIA attributes
            this.querySelectorAll('.level-line').forEach(line => {
                line.setAttribute('aria-checked', 'false');
                line.setAttribute('tabindex', '-1');
            });

            e.target.setAttribute('aria-checked', 'true');
            e.target.setAttribute('tabindex', '0');
            e.target.focus();

            // Update aria-activedescendant
            const radioGroup = this.querySelector('[role="radiogroup"]');
            radioGroup.setAttribute('aria-activedescendant', `level-${newLevel}`);

            // Animation feedback
            e.target.style.transform = 'scaleY(1.2)';
            setTimeout(() => {
                e.target.style.transform = '';
            }, 150);
        }
    }

    handleKeydown(e) {
        if (e.target.matches('.level-line')) {
            const currentLevel = parseInt(e.target.dataset.level);
            let newLevel = currentLevel;

            switch (e.key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    newLevel = Math.max(1, currentLevel - 1);
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    newLevel = Math.min(5, currentLevel + 1);
                    break;
                case 'Home':
                    e.preventDefault();
                    newLevel = 1;
                    break;
                case 'End':
                    e.preventDefault();
                    newLevel = 5;
                    break;
                case ' ':
                case 'Enter':
                    e.preventDefault();
                    // Level is already selected, just announce it
                    break;
                default:
                    return;
            }

            if (newLevel !== currentLevel) {
                appState.setState({ currentLevel: newLevel });
                // Focus will be set in the next render cycle
                setTimeout(() => {
                    const newElement = this.querySelector(`[data-level="${newLevel}"]`);
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
                        
                        <div class="level-slider" role="group" aria-labelledby="level-slider-label">
                            <div id="level-slider-label" class="sr-only">Difficulty level selector</div>
                            <div class="slider-track" role="radiogroup" aria-label="Select difficulty level" aria-activedescendant="level-${state.currentLevel}">
                                ${this.renderLevelLines()}
                            </div>
                            <div class="slider-info" aria-live="polite" aria-atomic="true">Level ${state.currentLevel}/5</div>
                        </div>
                    </div>
                `;
    }

    renderLevelLines() {
        return Array.from({ length: 5 }, (_, index) => {
            const level = index + 1;
            const isActive = level === appState.level;
            return `
                        <div class="level-line ${isActive ? 'active' : ''}" 
                             data-level="${level}"
                             role="radio"
                             aria-checked="${isActive}"
                             aria-label="Level ${level}: ${this.levelLabels[index]}"
                             id="level-${level}"
                             tabindex="${isActive ? '0' : '-1'}">
                            <div class="level-label" aria-hidden="true">${this.levelLabels[index]}</div>
                        </div>
                    `;
        }).join('');
    }
}

// Content Area Component
class ContentArea extends HTMLElement {
    connectedCallback() {
        this.render();

        // Listen for state changes
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLevel || e.detail.updates.currentTopic) {
                this.render();
            }
        });
    }

    render() {
        const state = appState.state;
        const difficultyNames = ['Basic', 'Intermediate', 'Advanced', 'Expert', 'Master'];

        this.innerHTML = `
                    <div class="content-card">
                        <div class="content-header">
                            <h2 id="content-title">${state.currentTopic}</h2>
                            <span class="difficulty-badge difficulty-${state.currentLevel}" 
                                  aria-label="Difficulty level: ${difficultyNames[state.currentLevel - 1]}">
                                ${difficultyNames[state.currentLevel - 1]}
                            </span>
                        </div>
                        
                        <div class="content-body" aria-labelledby="content-title">
                            <p>This content adapts to <strong>Level ${state.currentLevel}</strong> complexity.</p>
                            
                            ${this.getContentForLevel(state.currentLevel)}
                        </div>
                    </div>
                `;
    }

    getContentForLevel(level) {
        const content = {
            1: '<p>🟢 <strong>Basic:</strong> Simple explanations and step-by-step guides.</p>',
            2: '<p>🔵 <strong>Intermediate:</strong> More detailed information with examples.</p>',
            3: '<p>🟠 <strong>Advanced:</strong> In-depth analysis and technical details.</p>',
            4: '<p>🔴 <strong>Expert:</strong> Complex concepts and advanced techniques.</p>',
            5: '<p>🟣 <strong>Master:</strong> Cutting-edge research and theoretical frameworks.</p>'
        };

        return content[level] || content[3];
    }
}

// Sidebar Widget Component
class SidebarWidget extends HTMLElement {
    connectedCallback() {
        this.render();

        // Listen for state changes
        appState.addEventListener('statechange', (e) => {
            if (e.detail.updates.currentLevel) {
                this.render();
            }
        });
    }

    render() {
        const state = appState.state;
        const progress = (state.currentLevel / 5) * 100;

        this.innerHTML = `
                    <div class="widget-card">
                        <h3 id="progress-title">Progress Tracker</h3>
                        <p>Current Level: <strong>${state.currentLevel}/5</strong></p>
                        
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