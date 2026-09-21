frappe.after_ajax(() => {
    setTimeout(() => {
        add_vendor_tutorial();
    }, 1000);
});

function add_vendor_tutorial() {
    const help_menu = $('.dropdown-help');

    if (!help_menu.length) {
        return;
    }

    const menu = help_menu.find('.dropdown-menu');

    if (!menu.length || menu.find('.vendor-tutorial-link').length) {
        return;
    }

    menu.prepend(`
        <a class="dropdown-item vendor-tutorial-link"
           href="#"
           onclick="open_vendor_tutorial(); return false;">
            <span class="mr-2">
                <svg class="icon icon-sm">
                    <use href="#icon-youtube"></use>
                </svg>
            </span>
            Tutorial
        </a>
    `);
}

window.open_vendor_tutorial = function () {

    const video_url = "/private/files/vendor_tutorial.mp4";

    const dialog = new frappe.ui.Dialog({
        title: "Vendor Portal Tutorial",
        size: "extra-large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "tutorial_video"
            }
        ]
    });

    dialog.fields_dict.tutorial_video.$wrapper.html(`
        <div style="
            width: 100%;
            background: #000;
            border-radius: 8px;
            overflow: hidden;
        ">
            <video
                controls
                autoplay
                style="
                    width: 100%;
                    max-height: 75vh;
                    display: block;
                "
            >
                <source src="${video_url}" type="video/mp4">
                Your browser does not support video playback.
            </video>
        </div>
    `);

    dialog.show();
};

