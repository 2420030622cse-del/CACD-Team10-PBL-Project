document.addEventListener('DOMContentLoaded', async () => {
    const query = new URLSearchParams(window.location.search);
    const method = query.get('method') || 'brute_force';
    const type = query.get('type') || 'PIN';
    const params = {
        method,
        type,
        attempts: Number(query.get('attempts') || 0),
        time_taken: Number(query.get('time_taken') || 0),
        speed: Number(query.get('speed') || 0),
        found: query.get('found') === 'true',
        reason: query.get('reason') || (query.get('found') === 'true' ? 'cracked' : 'limit_reached')
    };
    const methodLabels = {
        brute_force: 'Brute Force',
        dictionary: 'Dictionary',
        rule_based: 'Rule-Based',
        hybrid: 'Hybrid'
    };
    const ratingsFromPage = () => Object.fromEntries(
        [...document.querySelectorAll('[data-rating]')]
            .map(element => [element.dataset.rating, Number(element.textContent)])
    );
    const renderReport = data => {
        const outcome = params.found ? 'PASSWORD CRACKED'
            : params.reason === 'stopped' ? 'SIMULATION STOPPED'
                : params.reason === 'exhausted' ? 'SEARCH EXHAUSTED' : 'SIMULATION LIMIT REACHED';
        document.getElementById('report-outcome').textContent = outcome;
        document.getElementById('report-summary').textContent = params.found
            ? 'The simulator successfully recovered the test password.'
            : params.reason === 'stopped' ? 'The simulation was stopped before it found the test password.'
                : params.reason === 'exhausted' ? 'The selected candidate list was exhausted without finding the test password.'
                : 'No match was found within the configured simulation limits. This does not prove the password is safe.';
        document.getElementById('report-banner').className = `report-banner ${params.found ? 'banner-cracked' : 'banner-limit'}`;
        const outcomeIcon = document.getElementById('report-outcome-icon');
        outcomeIcon.className = params.found
            ? 'fa-solid fa-lock-open pulsing-glow'
            : 'fa-solid fa-user-shield';
        document.getElementById('report-method-name').textContent = methodLabels[method] || method;
        document.getElementById('report-type').textContent = type;
        document.getElementById('report-attempts').textContent = params.attempts.toLocaleString();
        document.getElementById('report-time').textContent = `${params.time_taken.toFixed(3)} sec`;
        document.getElementById('report-speed').textContent = `${params.speed.toLocaleString(undefined, { maximumFractionDigits: 0 })} guesses/sec`;
        document.getElementById('report-space').textContent = data.formatted_space;
        document.getElementById('report-overall-rating').textContent = data.ratings.overall_rating;
        for (const [name, value] of Object.entries(data.ratings)) {
            const score = document.querySelector(`[data-rating="${name}"]`);
            if (score) score.textContent = value;
            const bar = document.querySelector(`.${{
                security_strength: 'strength-fill',
                memorability: 'memorability-fill',
                randomness: 'randomness-fill',
                pattern_safety: 'pattern-fill',
                typing_usability: 'typing-fill'
            }[name]}`);
            if (bar) bar.style.width = `${value * 10}%`;
        }
        document.getElementById('report-strongest-name').textContent = data.aspects.strongest.name;
        document.getElementById('report-strongest-description').textContent = data.aspects.strongest.description;
        document.getElementById('report-weakest-name').textContent = data.aspects.weakest.name;
        document.getElementById('report-weakest-description').textContent = data.aspects.weakest.description;
        document.getElementById('report-recommendation').textContent = data.recommendation;
        window.AI_RATINGS = data.ratings;
        renderRadarProfileChart(data.ratings);
    };

    const reportError = message => {
        const summary = document.getElementById('report-summary');
        summary.textContent = message;
        document.getElementById('report-outcome').textContent = 'REPORT UNAVAILABLE';
    };
    const tryAnother = document.getElementById('report-try-another');
    tryAnother.href = appUrl('configure', {}, method);

    try {
        if (window.APP_CONFIG.IS_STATIC_BUILD) {
            const data = await apiFetch('/api/report', {
                method: 'POST',
                body: { ...params, password: getTestPassword() }
            });
            renderReport(data);
        } else {
            renderRadarProfileChart(ratingsFromPage());
        }
    } catch (error) {
        console.error('Report generation failed:', error);
        reportError(error.message);
    }

    try {
        const comparison = await apiFetch('/api/compare-methods', {
            method: 'POST',
            body: { password: getTestPassword(), type }
        });
        renderMethodComparisonChart(comparison);
    } catch (error) {
        console.error('Method comparison failed:', error);
        document.querySelector('.report-chart-card .chart-desc').textContent = error.message;
    }

    try {
        const history = await apiFetch('/api/history');
        const tbody = document.getElementById('history-table-body');
        tbody.replaceChildren();
        if (!history.length) {
            const row = tbody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 7;
            cell.className = 'text-center text-dim';
            cell.textContent = 'No simulation history found.';
            return;
        }
        history.forEach(run => {
            const row = tbody.insertRow();
            const values = [
                new Date(run.timestamp).toLocaleString(),
                run.password_type,
                (run.attack_method || '').replace('_', ' ').replace(/\b\w/g, char => char.toUpperCase()),
                Number(run.attempts).toLocaleString(),
                `${Number(run.time_taken).toFixed(3)}s`,
                run.result,
                Number(run.ai_rating).toFixed(1)
            ];
            values.forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value;
            });
        });
    } catch (error) {
        console.error('History request failed:', error);
        const tbody = document.getElementById('history-table-body');
        tbody.replaceChildren();
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.className = 'text-center text-dim';
        cell.textContent = error.message;
    }
});
