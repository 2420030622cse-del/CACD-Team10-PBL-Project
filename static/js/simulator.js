// Attack Simulator orchestration logic
document.addEventListener('DOMContentLoaded', () => {
    const query = new URLSearchParams(window.location.search);
    const pathParts = window.location.pathname.split('/').filter(Boolean);
    if (window.APP_CONFIG.IS_STATIC_BUILD) {
        const pageIndex = pathParts.indexOf('simulation');
        if (pageIndex >= 0 && window.validSimulationMethods.includes(pathParts[pageIndex + 1])) {
            window.SIM_METHOD = pathParts[pageIndex + 1];
        }
    }
    const requestedType = query.get('type');
    window.SIM_TYPE = ['PIN', 'TEXT', 'MIX'].includes(requestedType) ? requestedType : window.SIM_TYPE || 'PIN';
    const requestedSpeed = Number(query.get('speed'));
    window.SIM_SPEED = [1, 10, 120, 500].includes(requestedSpeed) ? requestedSpeed : Number(window.SIM_SPEED || 120);
    const requestedAttempts = query.has('max_attempts') ? Number(query.get('max_attempts')) : NaN;
    window.SIM_MAX_ATTEMPTS = Number.isFinite(requestedAttempts)
        ? Math.max(0, Math.min(requestedAttempts, 10_000_000))
        : Math.max(0, Math.min(Number(window.SIM_MAX_ATTEMPTS) || 0, 10_000_000));
    const requestedTime = query.has('max_time') ? Number(query.get('max_time')) : NaN;
    window.SIM_MAX_TIME = Number.isFinite(requestedTime)
        ? Math.max(0, Math.min(requestedTime, 300))
        : Math.max(0, Math.min(Number(window.SIM_MAX_TIME) || 0, 300));
    window.SIM_RULES = query.has('rules')
        ? query.get('rules').split(',').filter(Boolean)
        : window.SIM_RULES || [];
    window.SIM_MAX_RULES = Number(query.get('max_rules') || window.SIM_MAX_RULES || 2);
    // State variables
    let isRunning = false;
    let isPaused = false;
    let attemptsCount = 0;
    let elapsedSeconds = 0.0;
    let currentState = {};
    let timerInterval = null;
    let stepTimeout = null;
    let startTimestamp = null;
    let pauseTimestamp = null;
    let totalPausedMs = 0;
    let simulationRunId = 0;

    // Elements
    const guessDisplayBox = document.getElementById('guess-display-box');
    const currentGuessText = document.getElementById('current-guess-text');
    const guessStatusIndicator = document.getElementById('guess-status-indicator');
    const guessStatusLabel = document.getElementById('guess-status-label');
    const statusBadge = document.getElementById('simulation-badge-status');

    // Controls
    const btnPauseResume = document.getElementById('btn-pause-resume');
    const btnStop = document.getElementById('btn-stop');
    const btnRestart = document.getElementById('btn-restart');
    const btnGoReport = document.getElementById('btn-finish-redirect');

    // Stats
    const statAttempts = document.getElementById('stat-attempts');
    const statLength = document.getElementById('stat-length');
    const statSpeed = document.getElementById('stat-speed');
    const statTime = document.getElementById('stat-time');
    const progressPercentLabel = document.getElementById('progress-percent-label');
    const progressBarFill = document.getElementById('progress-bar-fill');
    
    // Log console
    const logConsoleLines = document.getElementById('log-console-lines');
    const maxVisibleLogLines = 1500;
    const ruleBaseWord = document.getElementById('rule-base-word');
    const ruleCurrentRule = document.getElementById('rule-current-rule');
    const ruleEnabledCount = document.getElementById('rule-enabled-count');
    const ruleSearchStatus = document.getElementById('rule-search-status');
    let matchedResult = null;

    function formatRuleName(rule) {
        const labels = {
            original: 'Original',
            lowercase: 'Lowercase',
            capitalize: 'Capitalize',
            uppercase: 'Uppercase',
            reverse: 'Reverse',
            'appendNumber(1)': 'Append 1',
            'appendNumber(123)': 'Append 123',
            'prefixNumber(1)': 'Prefix 1',
            'prefixNumber(123)': 'Prefix 123',
            'appendSymbol(!)': 'Append !',
            'appendSymbol(@)': 'Append @',
            'prefixSymbol(@)': 'Prefix @',
            'replace(a,@)': 'Replace a with @',
            'replace(e,3)': 'Replace e with 3',
            'replace(i,1)': 'Replace i with 1',
            'replace(o,0)': 'Replace o with 0',
            'replace(s,$)': 'Replace s with $'
        };
        return labels[rule] || rule;
    }

    // Calculate step configs based on requested speed
    // Higher speed runs larger batches per step to prevent network lag
    function getStepConfiguration() {
        const speed = window.SIM_SPEED;
        if (speed === 1) {
            return { batchSize: 1, delay: 1000 };
        } else if (speed === 10) {
            return { batchSize: 2, delay: 200 };
        } else if (speed === 500) {
            return { batchSize: 125, delay: 250 };
        } else {
            // default 120 guesses/sec
            return { batchSize: 30, delay: 250 };
        }
    }

    const { batchSize, delay } = getStepConfiguration();

    // Start
    function startSimulation() {
        const runId = ++simulationRunId;
        isRunning = true;
        isPaused = false;
        attemptsCount = 0;
        elapsedSeconds = 0.0;
        currentState = {};
        totalPausedMs = 0;
        matchedResult = null;
        startTimestamp = Date.now();

        // UI Reset
        statusBadge.className = 'status-badge badge-running';
        statusBadge.textContent = 'RUNNING';
        btnPauseResume.className = 'btn-control btn-pause';
        btnPauseResume.querySelector('.lbl').textContent = 'PAUSE';
        btnPauseResume.querySelector('i').className = 'fa-solid fa-pause';
        
        btnStop.classList.remove('hidden');
        btnPauseResume.classList.remove('hidden');
        btnRestart.classList.remove('hidden');
        btnGoReport.classList.add('hidden');
        
        guessDisplayBox.className = 'console-box state-changing';
        currentGuessText.textContent = '------';
        guessStatusLabel.textContent = 'INITIATING SIMULATION ENGINE...';
        
        logConsoleLines.innerHTML = '';
        if (statLength) statLength.textContent = '-';
        statAttempts.textContent = '0';
        statSpeed.textContent = String(window.SIM_SPEED);
        statTime.textContent = '0.0 sec';
        progressPercentLabel.textContent = '0.00%';
        progressBarFill.style.width = '0%';
        const passwordLength = getTestPassword().length;
        const base = window.SIM_TYPE === 'PIN' ? 10 : window.SIM_TYPE === 'TEXT' ? 52 : 70;
        window.THEORETICAL_SPACE = base ** (window.SIM_TYPE === 'PIN' ? 6 : passwordLength);

        // Charts Initializations
        renderLengthGrowthChart('lengthGrowthChart', window.SIM_TYPE);
        initProgressTraceChart('progressTraceChart');

        // Start timer ticks
        startTimer();
        
        // Start steps loops
        scheduleNextStep(500, runId);
    }

    function startTimer() {
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            if (!isRunning || isPaused) return;
            const currentMs = Date.now();
            elapsedSeconds = (currentMs - startTimestamp - totalPausedMs) / 1000.0;
            
            // Limit bounds checks
            if (window.SIM_MAX_TIME > 0 && elapsedSeconds >= window.SIM_MAX_TIME) {
                elapsedSeconds = window.SIM_MAX_TIME;
                finishSimulation(false, 'limit_reached');
            }
            
            statTime.textContent = `${elapsedSeconds.toFixed(1)} sec`;
        }, 100);
    }

    function scheduleNextStep(msDelay, runId) {
        if (stepTimeout) clearTimeout(stepTimeout);
        if (!isRunning || isPaused) return;
        stepTimeout = setTimeout(() => runStep(runId), msDelay);
    }

    function runStep(runId) {
        if (!isRunning || isPaused || runId !== simulationRunId) return;

        const remainingAttempts = window.SIM_MAX_ATTEMPTS > 0
            ? window.SIM_MAX_ATTEMPTS - attemptsCount
            : batchSize;
        if (remainingAttempts <= 0) {
            finishSimulation(false, 'limit_reached');
            return;
        }
        const requestBatchSize = Math.min(batchSize, remainingAttempts);

        // Visual state update to CHANGING
        guessDisplayBox.className = 'console-box state-changing';
        guessStatusLabel.textContent = 'TRYING NEXT COMBINATION...';
        
        apiFetch('/api/simulate-step', {
            method: 'POST',
            body: {
                password: getTestPassword(),
                method: window.SIM_METHOD,
                type: window.SIM_TYPE,
                state: currentState,
                batch_size: requestBatchSize,
                charset: window.SIM_CHARSET,
                rules: window.SIM_RULES,
                max_rules: window.SIM_MAX_RULES,
                elapsed_time: elapsedSeconds
            }
        })
        .then(data => {
            if (!isRunning || runId !== simulationRunId) return;
            if (data.error) {
                console.error("Simulation step error: ", data.error);
                finishSimulation(false, 'error', data.error);
                return;
            }
            
            currentState = data.state;
            if (Array.isArray(data.candidate_details) && data.candidate_details.length) {
                const finalDetail = data.candidate_details[data.candidate_details.length - 1];
                if (ruleBaseWord) ruleBaseWord.textContent = finalDetail.base_word;
                if (ruleCurrentRule) ruleCurrentRule.textContent = finalDetail.rules.map(formatRuleName).join(' + ');
                if (ruleEnabledCount) ruleEnabledCount.textContent = String((window.SIM_RULES || []).length + 1);
            }
            if (data.result && data.result.method === 'Rule Based') matchedResult = data.result;
            const prevAttempts = attemptsCount;
            attemptsCount += data.count;
            
            // Set stats values
            statAttempts.textContent = attemptsCount.toLocaleString();

            // Display current guess (the last one checked in the batch)
            const guesses = data.guesses || [];
            if (guesses.length > 0) {
                const finalGuess = guesses[guesses.length - 1];
                currentGuessText.textContent = finalGuess;
                
                // Write log console entries
                guesses.forEach((g, idx) => {
                    const isLast = idx === guesses.length - 1;
                    const isCorrect = isLast && data.found;
                    const lineClass = isCorrect ? 'log-correct' : 'log-incorrect';
                    const resultSymbol = isCorrect ? '✓' : '✗';
                    const detail = data.candidate_details && data.candidate_details[idx];
                    const attemptNum = detail && detail.attempt ? detail.attempt : prevAttempts + idx + 1;
                    
                    const line = document.createElement('div');
                    line.className = `log-line ${lineClass}`;
                    const attemptCell = document.createElement('span');
                    attemptCell.className = 'col-attempt';
                    attemptCell.textContent = `#${attemptNum.toLocaleString()}`;
                    const guessCell = document.createElement('span');
                    guessCell.className = 'col-guess';
                    guessCell.textContent = g;
                    const resultCell = document.createElement('span');
                    resultCell.className = 'col-result res';
                    resultCell.textContent = resultSymbol;
                    line.append(attemptCell, guessCell, resultCell);
                    logConsoleLines.appendChild(line);
                });
                while (logConsoleLines.childElementCount > maxVisibleLogLines) {
                    logConsoleLines.firstElementChild.remove();
                }
                logConsoleLines.scrollTop = logConsoleLines.scrollHeight;
            }

            // Calculate progress percent
            let progressPercent = 0.0;
            if (window.THEORETICAL_SPACE > 0) {
                progressPercent = (attemptsCount / window.THEORETICAL_SPACE) * 100.0;
                if (progressPercent > 100.0) progressPercent = 100.0;
            }
            
            progressPercentLabel.textContent = `${progressPercent.toFixed(2)}%`;
            progressBarFill.style.width = `${progressPercent}%`;

            // Plot dynamic trace points
            updateProgressTraceChart(elapsedSeconds, attemptsCount);

            if (data.found) {
                finishSimulation(true, 'cracked');
            } else if (data.exhausted) {
                finishSimulation(false, 'exhausted');
            } else if (window.SIM_MAX_ATTEMPTS > 0 && attemptsCount >= window.SIM_MAX_ATTEMPTS) {
                finishSimulation(false, 'limit_reached');
                return;
            } else {
                // Animate incorrect flash briefly
                guessDisplayBox.className = 'console-box state-incorrect';
                guessStatusLabel.textContent = '✗ INCORRECT';
                
                // Loop
                scheduleNextStep(delay, runId);
            }
        })
        .catch(err => {
            if (!isRunning || runId !== simulationRunId) return;
            console.error("Simulation request failed:", err);
            finishSimulation(false, 'error', err.message);
        });
    }

    function finishSimulation(found, reason, errorMessage = '') {
        if (startTimestamp && !isPaused) {
            elapsedSeconds = (Date.now() - startTimestamp - totalPausedMs) / 1000.0;
        }
        isRunning = false;
        if (timerInterval) clearInterval(timerInterval);
        if (stepTimeout) clearTimeout(stepTimeout);

        btnPauseResume.classList.add('hidden');
        btnStop.classList.add('hidden');
        
        btnGoReport.classList.toggle('hidden', reason === 'error');
        statTime.textContent = `${elapsedSeconds.toFixed(1)} sec`;

        if (found) {
            if (statLength) statLength.textContent = String(currentGuessText.textContent.length);
            const actualSpeed = attemptsCount / (elapsedSeconds > 0 ? elapsedSeconds : 1.0);
            statSpeed.textContent = actualSpeed.toFixed(1);
            guessDisplayBox.className = 'console-box state-correct';
            guessStatusLabel.textContent = '✓ TARGET FOUND';
            statusBadge.className = 'status-badge badge-finished';
            statusBadge.textContent = 'FINISHED';
            if (ruleSearchStatus) ruleSearchStatus.textContent = 'Target found';
            if (matchedResult) {
                window.SIM_RESULT = { ...matchedResult, elapsedTime: elapsedSeconds };
            }
        } else {
            guessDisplayBox.className = 'console-box';
            guessStatusLabel.textContent = reason === 'exhausted' ? '✗ TARGET NOT FOUND' : reason === 'limit_reached' ? '✗ LIMIT REACHED' : reason === 'error' ? `✗ ${errorMessage || 'SIMULATION ERROR'}` : '✗ STOPPED';
            statusBadge.className = 'status-badge badge-stopped';
            statusBadge.textContent = reason === 'exhausted' ? 'NOT FOUND' : reason === 'limit_reached' ? 'LIMIT REACHED' : reason === 'error' ? 'ERROR' : 'STOPPED';
            if (ruleSearchStatus) ruleSearchStatus.textContent = reason === 'exhausted' ? 'Search exhausted' : 'Search stopped';
        }

        // Configure Report redirect url
        const speedVal = attemptsCount / (elapsedSeconds > 0 ? elapsedSeconds : 1.0);
        btnGoReport.onclick = () => {
            const params = {
                method: window.SIM_METHOD,
                type: window.SIM_TYPE,
                attempts: attemptsCount,
                time_taken: elapsedSeconds,
                speed: speedVal,
                found,
                reason: found ? 'cracked' : reason
            };
            window.location.href = appUrl('report', params, window.SIM_METHOD);
        };
    }

    // Bind Controls Click events
    btnPauseResume.addEventListener('click', () => {
        if (!isRunning) return;
        
        isPaused = !isPaused;
        if (isPaused) {
            pauseTimestamp = Date.now();
            statusBadge.className = 'status-badge badge-paused';
            statusBadge.textContent = 'PAUSED';
            btnPauseResume.className = 'btn-control btn-restart';
            btnPauseResume.querySelector('.lbl').textContent = 'RESUME';
            btnPauseResume.querySelector('i').className = 'fa-solid fa-play';
        } else {
            totalPausedMs += (Date.now() - pauseTimestamp);
            statusBadge.className = 'status-badge badge-running';
            statusBadge.textContent = 'RUNNING';
            btnPauseResume.className = 'btn-control btn-pause';
            btnPauseResume.querySelector('.lbl').textContent = 'PAUSE';
            btnPauseResume.querySelector('i').className = 'fa-solid fa-pause';
            
            // Resume steps and timer ticks
            startTimer();
            scheduleNextStep(50, simulationRunId);
        }
    });

    btnStop.addEventListener('click', () => {
        if (!isRunning) return;
        finishSimulation(false, 'stopped');
    });

    btnRestart.addEventListener('click', () => {
        if (timerInterval) clearInterval(timerInterval);
        if (stepTimeout) clearTimeout(stepTimeout);
        startSimulation();
    });

    // Auto-launch simulation on load
    startSimulation();
});
