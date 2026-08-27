$(document).ready(function () {

    function add_supplier_registration_button() {

        // Only run on Frappe login page
        if (window.location.hash !== "#login") {
            return;
        }

        // Prevent duplicate button
        if ($(".supplier-registration-btn").length) {
            return;
        }

        // Find login card
        const login_container = $(".for-login");

        if (!login_container.length) {
            return;
        }

        // Create button
        const button = $(`
            <a
                href="/supplier-registration"
                class="btn btn-default btn-block supplier-registration-btn"
            >
                Supplier Registration
            </a>
        `);

        // Match spacing with existing login buttons
        button.css({
            "margin-top": "12px"
        });

        // Add after Login with Email Link
        const email_link_button = login_container.find(
            ".btn-login-with-email-link"
        );

        if (email_link_button.length) {
            email_link_button.after(button);
        } else {
            login_container.append(button);
        }
    }

    // Initial load
    add_supplier_registration_button();

    // Frappe uses hash-based routing
    $(window).on("hashchange", function () {
        setTimeout(function () {
            add_supplier_registration_button();
        }, 300);
    });

    // Login page can render dynamically
    setTimeout(function () {
        add_supplier_registration_button();
    }, 1000);

    setTimeout(function () {
        add_supplier_registration_button();
    }, 2000);
});