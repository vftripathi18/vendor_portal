(function () {

    function add_supplier_registration_button() {

        // Only on login page
        if (window.location.hash !== "#login") {
            return;
        }

        // Already added
        if (document.getElementById("supplier-registration-button")) {
            return;
        }

        // Find the login form/card
        const login_container = document.querySelector(".for-login");

        if (!login_container) {
            return;
        }

        // Find the existing login actions area
        const actions =
            login_container.querySelector(".page-card-actions");

        if (!actions) {
            return;
        }

        // Create button
        const button = document.createElement("a");

        button.id = "supplier-registration-button";

        button.href = "/supplier-registration";

        button.className =
            "btn btn-default btn-block supplier-registration-btn";

        button.innerText = "Supplier Registration";

        button.style.marginTop = "12px";

        // Add button
        actions.appendChild(button);
    }

    // Try immediately
    add_supplier_registration_button();

    // Try after page loads
    window.addEventListener("load", function () {
        add_supplier_registration_button();
    });

    // Frappe login uses hash routing
    window.addEventListener("hashchange", function () {

        setTimeout(function () {
            add_supplier_registration_button();
        }, 100);

        setTimeout(function () {
            add_supplier_registration_button();
        }, 500);

    });

    // Watch for Frappe dynamically creating login elements
    const observer = new MutationObserver(function () {
        add_supplier_registration_button();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

})();