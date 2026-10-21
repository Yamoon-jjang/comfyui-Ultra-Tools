// Ultra Tools request token helper (pairs with request_guard.py).
//
// Routes that change state or browse the disk only accept requests that carry
// the per-process token ComfyUI's Python side created at startup. This module
// fetches that token once from the same-origin route, sends it with every
// Ultra Tools request, and, if ComfyUI was restarted meanwhile (new token),
// fetches the new one and retries the request once. Nothing else changes in
// how the calling code builds or handles its requests.
import { api } from "../../scripts/api.js";

const TOKEN_ROUTE = "/ultra_tools/security/token";
const TOKEN_ERROR_CODE = "ultra_tools_token";
export const ULTRA_TOKEN_HEADER = "X-Ultra-Tools-Token";
export const ULTRA_TOKEN_QUERY = "ut_token";

let cachedToken = "";
let pendingToken = null;

function loadToken(force = false) {
    if (!force && cachedToken) return Promise.resolve(cachedToken);
    if (!force && pendingToken) return pendingToken;
    const request = (async () => {
        try {
            const response = await api.fetchApi(TOKEN_ROUTE, { cache: "no-store" });
            const data = await response.json().catch(() => null);
            if (response.ok && data && typeof data.token === "string" && data.token) {
                cachedToken = data.token;
            } else if (force) {
                cachedToken = "";
            }
        } catch (_) {
            if (force) cachedToken = "";
        }
        return cachedToken;
    })();
    pendingToken = request;
    request.finally(() => {
        if (pendingToken === request) pendingToken = null;
    });
    return request;
}

// Token already loaded (for URLs that must be built synchronously, e.g. <img>).
export function getUltraToken() {
    return cachedToken;
}

export function ensureUltraToken() {
    return loadToken(false);
}

function plainHeaders(headers) {
    if (!headers) return {};
    if (typeof Headers !== "undefined" && headers instanceof Headers) {
        return Object.fromEntries(headers.entries());
    }
    if (Array.isArray(headers)) return Object.fromEntries(headers);
    return { ...headers };
}

function withToken(options, token) {
    const next = { ...(options || {}) };
    const headers = plainHeaders(next.headers);
    if (token) headers[ULTRA_TOKEN_HEADER] = token;
    next.headers = headers;
    return next;
}

async function isTokenRejection(response) {
    if (!response || response.status !== 403) return false;
    try {
        const data = await response.clone().json();
        return data?.code === TOKEN_ERROR_CODE;
    } catch (_) {
        return false;
    }
}

// Drop-in replacement for api.fetchApi() for Ultra Tools routes.
export async function ultraFetchApi(route, options = {}) {
    const token = await loadToken(false);
    let response = await api.fetchApi(route, withToken(options, token));
    if (await isTokenRejection(response)) {
        const fresh = await loadToken(true);
        if (fresh) response = await api.fetchApi(route, withToken(options, fresh));
    }
    return response;
}

// Start loading the token as soon as the frontend loads this module.
loadToken(false);
