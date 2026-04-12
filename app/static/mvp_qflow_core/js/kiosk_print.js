document.addEventListener("DOMContentLoaded", function () {
    const panel = document.getElementById("qflow-print-panel");

    if (!panel) {
        return;
    }

    const statusMessage = document.getElementById("qflow-print-status-message");
    const retryButton = document.getElementById("qflow-retry-print-button");
    const cancelButton = document.getElementById("qflow-cancel-print-button");
    const markFailedButton = document.getElementById("qflow-mark-print-failed-button");

    const printUrl = panel.dataset.printUrl;
    const internalToken = panel.dataset.internalToken;
    const printEventUrl = panel.dataset.printEventUrl;
    const autoPrint = panel.dataset.autoPrint === "true";

    let printWindow = null;
    let printFlowStarted = false;

    function getCsrfToken() {
        const cookieValue = document.cookie
            .split("; ")
            .find(row => row.startsWith("csrftoken="));

        return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : "";
    }

    async function sendPrintEvent(eventName, details = {}) {
        if (!printEventUrl || !internalToken) {
            return;
        }

        try {
            await fetch(printEventUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify({
                    internal_token: internalToken,
                    event: eventName,
                    details: details,
                }),
            });
        } catch (error) {
            console.error("Unable to log print event:", error);
        }
    }

    function setStatus(message, tone = "neutral") {
        statusMessage.textContent = message;

        statusMessage.classList.remove(
            "text-slate-600",
            "text-emerald-700",
            "text-amber-700",
            "text-red-700"
        );

        if (tone === "success") {
            statusMessage.classList.add("text-emerald-700");
        } else if (tone === "warning") {
            statusMessage.classList.add("text-amber-700");
        } else if (tone === "error") {
            statusMessage.classList.add("text-red-700");
        } else {
            statusMessage.classList.add("text-slate-600");
        }
    }

    function showRecoveryActions() {
        retryButton.classList.remove("hidden");
        retryButton.classList.add("flex");

        cancelButton.classList.remove("hidden");
        cancelButton.classList.add("flex");

        markFailedButton.classList.remove("hidden");
        markFailedButton.classList.add("flex");
    }

    function hideRecoveryActions() {
        retryButton.classList.add("hidden");
        retryButton.classList.remove("flex");

        cancelButton.classList.add("hidden");
        cancelButton.classList.remove("flex");

        markFailedButton.classList.add("hidden");
        markFailedButton.classList.remove("flex");
    }

    function openPrintWindow(isRetry = false) {
        if (!printUrl) {
            setStatus("Printing failure: print URL is missing.", "error");
            showRecoveryActions();
            sendPrintEvent("printing_failure", {
                reason: "missing_print_url",
            });
            return;
        }

        const finalPrintUrl = `${printUrl}?autoprint=1`;
        printWindow = window.open(
            finalPrintUrl,
            "_blank",
            "width=420,height=760,noopener,noreferrer"
        );

        if (!printWindow) {
            setStatus(
                "Printing failure: the browser blocked the print popup. Please retry printing.",
                "error"
            );
            showRecoveryActions();
            sendPrintEvent("print_popup_blocked", {
                is_retry: isRetry,
            });
            return;
        }

        printFlowStarted = true;
        hideRecoveryActions();
        setStatus(
            isRetry
                ? "Retry started. Complete the print action in the new window."
                : "Print window opened. Complete the print action in the new window.",
            "success"
        );

        sendPrintEvent(isRetry ? "print_retry_requested" : "print_opened", {
            print_url: finalPrintUrl,
        });

        const closeWatcher = window.setInterval(function () {
            if (!printWindow || printWindow.closed) {
                window.clearInterval(closeWatcher);

                if (printFlowStarted) {
                    setStatus(
                        "The print window was closed. If the ticket did not print correctly, use Retry Printing or Mark Printing Failure.",
                        "warning"
                    );
                    showRecoveryActions();
                    sendPrintEvent("print_window_closed", {});
                }
            }
        }, 800);
    }

    retryButton.addEventListener("click", function () {
        openPrintWindow(true);
    });

    cancelButton.addEventListener("click", async function () {
        setStatus("Printing was cancelled by the operator.", "warning");
        showRecoveryActions();
        await sendPrintEvent("print_cancelled", {});
    });

    markFailedButton.addEventListener("click", async function () {
        setStatus(
            "Printing failure recorded. You can retry printing or continue manually.",
            "error"
        );
        showRecoveryActions();
        await sendPrintEvent("printing_failure", {
            reason: "marked_manually_by_operator",
        });
    });

    if (autoPrint) {
        openPrintWindow(false);
    }
});