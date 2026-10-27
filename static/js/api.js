(() => {
    const config = window.APP_CONFIG;
    const methods = ['brute_force', 'dictionary', 'rule_based', 'hybrid', 'password_safety'];
    const simulationMethods = methods.filter(method => method !== 'password_safety');

    window.appUrl = (page, params = {}, method = '') => {
        let path;
        if (config.IS_STATIC_BUILD) {
            path = page === 'configure' || page === 'simulation'
                ? `${page}/${method || 'brute_force'}/`
                : `${page}/`;
            path = `${config.APP_BASE_PATH}${path}`;
        } else {
            path = `/${page}`;
            if ((page === 'configure' || page === 'simulation') && method) params.method = method;
        }
        const query = new URLSearchParams(params).toString();
        return query ? `${path}?${query}` : path;
    };

    window.apiFetch = (path, options = {}) => {
        if (config.IS_STATIC_BUILD && !config.API_BASE_URL) {
            return Promise.reject(new Error('Backend URL is not configured. Set the repository Actions variable API_BASE_URL and redeploy.'));
        }
        const base = config.API_BASE_URL.replace(/\/+$/, '');
        const headers = new Headers(options.headers || {});
        const requestOptions = { ...options, headers };
        if (requestOptions.body && typeof requestOptions.body !== 'string') {
            headers.set('Content-Type', 'application/json');
            requestOptions.body = JSON.stringify(requestOptions.body);
        }
        return fetch(`${base}${path}`, requestOptions).then(async response => {
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || `API request failed (${response.status}).`);
            return data;
        });
    };

    window.getTestPassword = () => sessionStorage.getItem('testPassword') || '';
    window.clearTestPassword = () => sessionStorage.removeItem('testPassword');
    window.validAttackMethods = methods;
    window.validSimulationMethods = simulationMethods;
})();
