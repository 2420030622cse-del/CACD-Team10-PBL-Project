// Password validation and AI preview logic
document.addEventListener('DOMContentLoaded', () => {
    let currentType = 'PIN'; // Default selection
    let previewRequestSequence = 0;
    let securityRequestSequence = 0;
    window.SELECTED_TYPE = currentType;
    const passwordInput = document.getElementById('test-password');
    const togglePasswordBtn = document.getElementById('toggle-password');
    const requirementsList = document.getElementById('requirements-list');
    const validationStatus = document.getElementById('validation-status');
    const startAttackBtn = document.getElementById('btn-start-attack');
    const analyzePasswordBtn = document.getElementById('btn-analyze-password');
    const clearDataBtn = document.getElementById('btn-clear-data');
    if (window.SELECTED_METHOD === 'password_safety') {
        startAttackBtn.classList.add('hidden');
    }

    // Security Analysis Elements
    const strengthStatus = document.getElementById('strength-status');
    const strengthScore = document.getElementById('security-score');
    const strengthLabel = document.getElementById('security-label');
    const strengthGuesses = document.getElementById('security-guesses');
    const strengthCrackTime = document.getElementById('security-crack-time');
    const strengthOfflineTime = document.getElementById('security-offline-time');
    const strengthWarning = document.getElementById('strength-warning');
    const strengthSuggestions = document.getElementById('strength-suggestions');
    const hibpStatusPill = document.getElementById('hibp-status-pill');
    const hibpStatus = document.getElementById('hibp-status');
    const hibpCount = document.getElementById('hibp-count');
    const hibpMessage = document.getElementById('hibp-message');
    
    // AI Preview Elements
    const aiPlaceholder = document.getElementById('ai-preview-placeholder');
    const aiPlaceholderMessage = aiPlaceholder.querySelector('p');
    const defaultPlaceholderMessage = aiPlaceholderMessage.textContent;
    const aiLoader = document.getElementById('ai-preview-loader');
    const aiContent = document.getElementById('ai-preview-content');
    const previewStrength = document.getElementById('preview-strength');
    const previewMemorability = document.getElementById('preview-memorability');
    const previewRandomness = document.getElementById('preview-randomness');
    const previewPattern = document.getElementById('preview-pattern');
    const previewTyping = document.getElementById('preview-typing');
    const previewEntropy = document.getElementById('preview-entropy');

    // Requirements definitions
    const reqsConfig = {
        'PIN': [
            { id: 'pin-len', desc: 'Exactly 6 characters', check: (val) => val.length === 6 },
            { id: 'pin-num', desc: 'Numbers 0–9 only', check: (val) => /^\d+$/.test(val) && val.length > 0 }
        ],
        'TEXT': [
            { id: 'text-len', desc: '8–20 characters', check: (val) => val.length >= 8 && val.length <= 20 },
            { id: 'text-chars', desc: 'At least one letter', check: (val) => /[a-zA-Z]/.test(val) },
            { id: 'text-ascii', desc: 'Printable ASCII only (no spaces)', check: (val) => /^[\x21-\x7E]+$/.test(val) }
        ],
        'MIX': [
            { id: 'mix-len', desc: '8–20 characters', check: (val) => val.length >= 8 && val.length <= 20 },
            { id: 'mix-letter', desc: 'At least 1 letter', check: (val) => /[a-zA-Z]/.test(val) },
            { id: 'mix-num', desc: 'At least 1 number', check: (val) => (val.match(/\d/g) || []).length >= 1 },
            { id: 'mix-sym', desc: 'At least 1 symbol', check: (val) => /[^a-zA-Z0-9]/.test(val) },
            { id: 'mix-ascii', desc: 'Printable ASCII only (no spaces)', check: (val) => /^[\x21-\x7E]+$/.test(val) }
        ]
    };

    // Toggle password visibility
    togglePasswordBtn.addEventListener('click', () => {
        const isPassword = passwordInput.getAttribute('type') === 'password';
        passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
        togglePasswordBtn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        togglePasswordBtn.innerHTML = isPassword 
            ? '<i class="fa-solid fa-eye-slash"></i>' 
            : '<i class="fa-solid fa-eye"></i>';
    });

    // Handle Type Card selections
    const typeCards = document.querySelectorAll('.type-card');
    function setCurrentType(type, focusCard = false) {
        const typeChanged = currentType !== type;
        currentType = type;
        window.SELECTED_TYPE = type;
        typeCards.forEach(c => {
            c.classList.toggle('active', c.getAttribute('data-type') === type);
            const isSelected = c.getAttribute('data-type') === type;
            c.setAttribute('aria-checked', String(isSelected));
            c.setAttribute('tabindex', isSelected ? '0' : '-1');
            if (focusCard && isSelected) c.focus();
        });

        if (!typeChanged) return;
        renderRequirements();
        updateRuleCategory();
        securityRequestSequence += 1;
        resetSecurityPanel();
        passwordInput.value = '';
        runValidation();
    }

    function updateRuleCategory() {
        document.querySelectorAll('.rule-category').forEach(category => {
            category.classList.toggle('hidden', category.dataset.ruleType !== currentType);
        });
    }

    document.querySelectorAll('.rule-order-controls button').forEach(button => {
        button.addEventListener('click', () => {
            const item = button.closest('li');
            const list = item.parentElement;
            if (button.dataset.move === 'up' && item.previousElementSibling) {
                list.insertBefore(item, item.previousElementSibling);
            } else if (button.dataset.move === 'down' && item.nextElementSibling) {
                list.insertBefore(item.nextElementSibling, item);
            }
        });
    });

    typeCards.forEach((card, index) => {
        card.addEventListener('click', () => {
            setCurrentType(card.getAttribute('data-type'));
        });
        card.addEventListener('keydown', event => {
            const nextIndex = event.key === 'ArrowRight' || event.key === 'ArrowDown'
                ? (index + 1) % typeCards.length
                : event.key === 'ArrowLeft' || event.key === 'ArrowUp'
                    ? (index - 1 + typeCards.length) % typeCards.length
                    : -1;
            if (nextIndex >= 0) {
                event.preventDefault();
                setCurrentType(typeCards[nextIndex].getAttribute('data-type'), true);
            } else if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                setCurrentType(card.getAttribute('data-type'));
            }
        });
    });

    // Render initial requirements
    function renderRequirements() {
        requirementsList.innerHTML = '';
        const configs = reqsConfig[currentType];
        configs.forEach(req => {
            const li = document.createElement('li');
            li.id = req.id;
            li.innerHTML = `<span class="req-status-icon req-invalid"><i class="fa-solid fa-circle-xmark"></i></span> ${req.desc}`;
            requirementsList.appendChild(li);
        });
    }

    // Run active checks
    let debounceTimer;
    function runValidation() {
        const val = passwordInput.value;
        const configs = reqsConfig[currentType];
        let isValid = true;

        configs.forEach(req => {
            const li = document.getElementById(req.id);
            if (!li) return;
            
            const reqPassed = req.check(val);
            if (!reqPassed) isValid = false;

            const iconSpan = li.querySelector('.req-status-icon');
            if (reqPassed) {
                iconSpan.className = 'req-status-icon req-valid';
                iconSpan.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
            } else {
                iconSpan.className = 'req-status-icon req-invalid';
                iconSpan.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
            }
        });

        // Update status badge & button
        if (val.length === 0) {
            clearTimeout(debounceTimer);
            previewRequestSequence += 1;
            clearTestPassword();
            validationStatus.className = 'validation-status status-invalid';
            validationStatus.textContent = 'STATUS: ENTER PASSWORD';
            startAttackBtn.classList.add('disabled');
            startAttackBtn.disabled = true;
            resetAiPreview();
        } else if (isValid) {
            clearTestPassword();
            startAttackBtn.classList.add('disabled');
            startAttackBtn.disabled = true;
            validationStatus.className = 'validation-status status-valid';
            validationStatus.textContent = 'STATUS: VALID PASSWORD';
            
            // Trigger AI Preview fetching with a slight debounce to avoid API spamming
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                fetchAiPreview(val);
            }, 300);
        } else {
            clearTimeout(debounceTimer);
            previewRequestSequence += 1;
            clearTestPassword();
            validationStatus.className = 'validation-status status-invalid';
            validationStatus.textContent = 'STATUS: INVALID PASSWORD';
            startAttackBtn.classList.add('disabled');
            startAttackBtn.disabled = true;
            resetAiPreview();
        }
    }

    function resetAiPreview() {
        aiContent.classList.add('hidden');
        aiLoader.classList.add('hidden');
        aiPlaceholder.classList.remove('hidden');
    }

    function setStatusPill(element, label, variant = 'neutral') {
        if (!element) return;
        element.className = `status-pill ${variant}`;
        element.textContent = label;
    }

    function resetSecurityPanel() {
        setStatusPill(strengthStatus, 'Analyzing password...', 'neutral');
        setStatusPill(hibpStatusPill, 'Checking breach exposure...', 'neutral');
        strengthScore.textContent = '—';
        strengthLabel.textContent = '—';
        strengthGuesses.textContent = '—';
        strengthCrackTime.textContent = '—';
        strengthOfflineTime.textContent = '—';
        strengthWarning.textContent = 'No analysis yet.';
        strengthSuggestions.innerHTML = '';
        hibpStatus.textContent = '—';
        hibpCount.textContent = '0';
        hibpMessage.textContent = 'Waiting for password analysis.';
    }

    function renderSecurityResults(data) {
        const strength = data && data.strength ? data.strength : {};
        const hibp = data && data.hibp ? data.hibp : {};

        const scoreValue = typeof strength.score === 'number' ? strength.score : 0;
        const humanStrength = strength.strength_label || (typeof strength.label === 'string' ? strength.label.replace(/^Strength:\s*/i, '') : 'Very Weak');
        strengthScore.textContent = `${scoreValue} / 4`;
        strengthLabel.textContent = humanStrength || 'Very Weak';
        strengthGuesses.textContent = new Intl.NumberFormat().format(Number(strength.guesses || 0));
        strengthCrackTime.textContent = strength.crack_time || '—';
        strengthOfflineTime.textContent = strength.offline_crack_time || '—';
        strengthWarning.textContent = strength.warning || 'No obvious pattern detected.';

        const warnings = Array.isArray(strength.suggestions) && strength.suggestions.length ? strength.suggestions : ['No additional suggestions available.'];
        strengthSuggestions.replaceChildren(...warnings.map(item => {
            const suggestion = document.createElement('li');
            suggestion.textContent = item;
            return suggestion;
        }));

        if (hibp.compromised) {
            setStatusPill(hibpStatusPill, '⚠ FOUND', 'warning');
            hibpStatus.textContent = '⚠ Found';
            hibpCount.textContent = new Intl.NumberFormat().format(Number(hibp.count || 0));
            hibpMessage.textContent = hibp.message || 'This password has appeared in known breach datasets.';
        } else if (hibp.status && /unable|error|unavailable/i.test(hibp.status)) {
            setStatusPill(hibpStatusPill, 'Unable to determine', 'warning');
            hibpStatus.textContent = 'Unable to determine';
            hibpCount.textContent = '0';
            hibpMessage.textContent = hibp.message || 'The HIBP service could not be reached.';
        } else if (hibp.status && /not found/i.test(hibp.status)) {
            setStatusPill(hibpStatusPill, '✓ NOT FOUND', 'success');
            hibpStatus.textContent = '✓ Not Found';
            hibpCount.textContent = '0';
            hibpMessage.textContent = hibp.message || 'Password not found in pwned password datasets.';
        } else {
            setStatusPill(hibpStatusPill, 'Checking breach exposure...', 'neutral');
            hibpStatus.textContent = '—';
            hibpCount.textContent = '0';
            hibpMessage.textContent = 'Waiting for password analysis.';
        }

        setStatusPill(strengthStatus, `Score ${scoreValue} / 4`, scoreValue >= 3 ? 'success' : scoreValue >= 2 ? 'neutral' : 'warning');
    }

    function analyzePasswordSecurity() {
        const value = passwordInput.value || '';
        const requestSequence = ++securityRequestSequence;
        const requestedType = currentType;
        if (!value) {
            resetSecurityPanel();
            return;
        }

        resetSecurityPanel();
        setStatusPill(strengthStatus, 'Analyzing password...', 'neutral');
        setStatusPill(hibpStatusPill, 'Checking breach exposure...', 'neutral');
        strengthWarning.textContent = 'Analyzing password...';
        hibpMessage.textContent = 'Checking breach exposure...';

        apiFetch('/api/security-analysis', {
            method: 'POST',
            body: { password: value, type: currentType }
        })
        .then(data => {
            if (requestSequence !== securityRequestSequence ||
                value !== passwordInput.value ||
                requestedType !== currentType) return;
            renderSecurityResults(data);
        })
        .catch(error => {
            console.error('Security analysis failed:', error);
            if (requestSequence !== securityRequestSequence ||
                value !== passwordInput.value ||
                requestedType !== currentType) return;
            setStatusPill(strengthStatus, 'Analysis unavailable', 'warning');
            setStatusPill(hibpStatusPill, 'Unable to determine', 'warning');
            strengthWarning.textContent = 'The password analysis service could not be reached.';
            hibpMessage.textContent = 'The configured backend could not complete this analysis.';
        });
    }

    // Badge styling helper
    function getBadgeClass(level) {
        const cleanLevel = level.toLowerCase().replace(' ', '');
        return `preview-badge badge-${cleanLevel}`;
    }

    function fetchAiPreview(password) {
        aiPlaceholderMessage.textContent = defaultPlaceholderMessage;
        aiPlaceholder.classList.add('hidden');
        aiContent.classList.add('hidden');
        aiLoader.classList.remove('hidden');

        const requestSequence = ++previewRequestSequence;
        apiFetch('/api/validate', {
            method: 'POST',
            body: { password, type: currentType }
        })
        .then(data => {
            if (requestSequence !== previewRequestSequence || password !== passwordInput.value) return;
            if (data.is_valid && data.analysis) {
                sessionStorage.setItem('testPassword', password);
                // Populate elements
                const preview = data.analysis.preview;
                
                previewStrength.className = getBadgeClass(preview.security_strength);
                previewStrength.textContent = preview.security_strength.toUpperCase();

                previewMemorability.className = getBadgeClass(preview.memorability);
                previewMemorability.textContent = preview.memorability.toUpperCase();

                previewRandomness.className = getBadgeClass(preview.randomness);
                previewRandomness.textContent = preview.randomness.toUpperCase();

                previewPattern.className = getBadgeClass(preview.pattern_safety);
                previewPattern.textContent = preview.pattern_safety.toUpperCase();

                previewTyping.className = getBadgeClass(preview.typing_usability);
                previewTyping.textContent = preview.typing_usability.toUpperCase();

                previewEntropy.textContent = `${data.analysis.features.entropy.toFixed(2)} bits`;

                // Unhide Content
                aiLoader.classList.add('hidden');
                aiContent.classList.remove('hidden');
                
                // Enable button
                startAttackBtn.classList.remove('disabled');
                startAttackBtn.disabled = false;
            } else {
                resetAiPreview();
            }
        })
        .catch(err => {
            console.error("Error fetching AI Preview: ", err);
            if (requestSequence !== previewRequestSequence) return;
            resetAiPreview();
            aiPlaceholderMessage.textContent = err.message;
        });
    }

    // Input listeners
    passwordInput.addEventListener('input', () => {
        securityRequestSequence += 1;
        resetSecurityPanel();
        runValidation();
    });

    analyzePasswordBtn.addEventListener('click', () => {
        analyzePasswordSecurity();
    });

    clearDataBtn.addEventListener('click', () => {
        clearDataBtn.disabled = true;
        apiFetch('/api/reset-password', { method: 'POST' })
            .then(() => {
                clearTestPassword();
                passwordInput.value = '';
                runValidation();
                resetSecurityPanel();
            })
            .catch(error => {
                console.error('Sensitive data reset failed:', error);
                clearTestPassword();
                passwordInput.value = '';
                runValidation();
                resetSecurityPanel();
                validationStatus.className = 'validation-status status-invalid';
                validationStatus.textContent = `STATUS: LOCAL DATA CLEARED; BACKEND RESET FAILED: ${error.message}`;
            })
            .finally(() => {
                clearDataBtn.disabled = false;
            });
    });
    
    // Redirect to simulator page when click start
    startAttackBtn.addEventListener('click', () => {
        if (startAttackBtn.disabled) return;

        const selectedType = window.SELECTED_TYPE || currentType;
        const maxAttempts = document.getElementById('max-attempts').value;
        const maxTime = document.getElementById('max-time').value;
        const speed = document.getElementById('simulation-speed').value;
        const ruleList = document.querySelector(`#${selectedType.toLowerCase()}-rule-list`);
        const selectedRules = ruleList
            ? [...ruleList.querySelectorAll('li')]
                .filter(item => item.querySelector('input').checked)
                .map(item => item.querySelector('input').value)
            : [];
        const maxRules = document.getElementById('max-rules')?.value || 2;

        const params = {
            type: selectedType,
            max_attempts: maxAttempts,
            max_time: maxTime,
            speed,
            rules: selectedRules.join(','),
            max_rules: maxRules
        };
        window.location.href = appUrl('simulation', params, window.SELECTED_METHOD);
    });

    // Initialize requirements layout
    renderRequirements();
    updateRuleCategory();
    resetSecurityPanel();
});
