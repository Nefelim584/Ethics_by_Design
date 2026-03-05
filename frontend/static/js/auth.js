/**
 * Shared auth helpers for login.html & register.html
 */

/** Show an error message in the .alert box */
function showError(msg) {
    const el = document.getElementById("alert");
    el.textContent = msg;
    el.classList.add("visible");
}

/** Hide the error alert */
function hideError() {
    const el = document.getElementById("alert");
    el.classList.remove("visible");
}

/** POST JSON to the given path; returns the parsed response + ok flag */
async function postJSON(url, body) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
    });
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
}

