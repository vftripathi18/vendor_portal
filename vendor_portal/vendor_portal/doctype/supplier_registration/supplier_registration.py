import frappe
from frappe.model.document import Document


class SupplierRegistration(Document):

    def on_update(self):
        # Only execute after workflow reaches Supplier Created
        if self.workflow_state != "Supplier Created":
            return

        # Prevent duplicate processing
        if self.supplier:
            return

        self.create_supplier_records()

    def create_supplier_records(self):

        # =========================================================
        # 1. BASIC VALIDATION
        # =========================================================

        if not self.name_of_the_company:
            frappe.throw("Name of the Company is required.")

        if not self.contact_person_name:
            frappe.throw("Contact Person Name is required.")

        if not self.email_id:
            frappe.throw("Contact Email ID is required to create the login.")

        # =========================================================
        # 2. CHECK DUPLICATE SUPPLIER
        # =========================================================

        existing_supplier = None

        if self.gstin_no:
            existing_supplier = frappe.db.get_value(
                "Supplier",
                {"gstin": self.gstin_no},
                "name"
            )

        if not existing_supplier:
            existing_supplier = frappe.db.get_value(
                "Supplier",
                {"supplier_name": self.name_of_the_company},
                "name"
            )

        if existing_supplier:
            frappe.throw(
                f"Supplier already exists: {existing_supplier}"
            )

        # =========================================================
        # 3. VALIDATE SUPPLIER CUSTOM FIELDS
        # =========================================================

        supplier_meta = frappe.get_meta("Supplier")

        required_supplier_fields = [
            "gstin",
            "pan",
            "custom_tan_no",
            "custom_gst_register_mail",
            "custom_gst_register_mobile_no",
            "custom_whatsapp_no",
            "custom_msme_no",
            "tax_category",
            "gst_category",
        ]

        for fieldname in required_supplier_fields:
            if not supplier_meta.has_field(fieldname):
                frappe.throw(
                    f"Supplier field '{fieldname}' does not exist."
                )

        # =========================================================
        # 4. CREATE SUPPLIER
        # =========================================================

        supplier = frappe.get_doc({
            "doctype": "Supplier",

            "supplier_name": self.name_of_the_company,
            "supplier_type": "Company",
            "supplier_group": "All Supplier Groups",

            "gstin": self.gstin_no or "",
            "pan": self.pan_no or "",

            "custom_tan_no": self.tan_no or "",
            "custom_gst_register_mail": self.gst_register_mail_id or "",
            "custom_gst_register_mobile_no": self.gst_register_mobile_no or "",
            "custom_whatsapp_no": self.whatsapp_no or "",
            "custom_msme_no": self.msme_no or "",

            "tax_category": self.tax_category or "",
            "gst_category": self.gst_category or "",
        })

        supplier.insert(ignore_permissions=True)

        # =========================================================
        # 5. CREATE CONTACT
        # =========================================================

        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": self.contact_person_name,
            "designation": self.designation or "",
            "department": self.department or "",
        })

        # Primary Email
        contact.append("email_ids", {
            "email_id": self.email_id,
            "is_primary": 1
        })

        # Mobile
        if self.mobile_no:
            contact.append("phone_nos", {
                "phone": self.mobile_no,
                "is_primary_mobile_no": 1
            })

        # Landline
        if self.landline_no:
            contact.append("phone_nos", {
                "phone": self.landline_no
            })

        # WhatsApp
        if self.whatsapp_no:
            contact.append("phone_nos", {
                "phone": self.whatsapp_no
            })

        # Link Contact to Supplier
        contact.append("links", {
            "link_doctype": "Supplier",
            "link_name": supplier.name
        })

        contact.insert(ignore_permissions=True)

        # =========================================================
        # 6. CREATE ADDRESS
        # =========================================================

        address = frappe.get_doc({
            "doctype": "Address",

            "address_title": self.name_of_the_company,
            "address_type": "Billing",

            "address_line1": self.address_line_1 or "",
            "address_line2": self.address_line_2 or "",

            "city": self.citytown or "",
            "state": self.stateprovince or "",
            "country": self.country or "India",

            "pincode": self.postal_code or "",

            "email_id": self.email_address or self.email_id,
            "phone": self.phone_no or self.mobile_no,
        })

        # Link Address to Supplier
        address.append("links", {
            "link_doctype": "Supplier",
            "link_name": supplier.name
        })

        address.insert(ignore_permissions=True)

        # =========================================================
        # 7. CREATE BANK ACCOUNT
        # =========================================================

        bank_account = None

        if self.bank_name or self.account_number:

            bank_account = frappe.get_doc({
                "doctype": "Bank Account",

                "account_name":
                    self.account_holder_name
                    or self.name_of_the_company,

                "account_type": self.account_type or "",
                "bank": self.bank_name or "",
                "bank_account_no": self.account_number or "",
                "branch_code": self.ifsc_code or "",

                "party_type": "Supplier",
                "party": supplier.name,
            })

            bank_account.insert(ignore_permissions=True)

        # =========================================================
        # 8. CREATE USER
        # =========================================================

        user = self.create_supplier_user(
            supplier=supplier,
            contact=contact
        )

        # =========================================================
        # 9. UPDATE SUPPLIER REGISTRATION
        # =========================================================

        update_values = {
            "supplier": supplier.name,
            "contact": contact.name,
            "address": address.name,
        }

        if bank_account:
            update_values["bank_account"] = bank_account.name

        registration_meta = frappe.get_meta("Supplier Registration")

        if registration_meta.has_field("user"):
            update_values["user"] = user.name

        if registration_meta.has_field("registrationstatus"):
            update_values["registrationstatus"] = "Supplier Created"

        elif registration_meta.has_field("registration_status"):
            update_values["registration_status"] = "Supplier Created"

        frappe.db.set_value(
            "Supplier Registration",
            self.name,
            update_values,
            update_modified=False
        )

        frappe.msgprint(
            f"""
            <b>Supplier Registration Completed</b><br><br>

            Supplier: <b>{supplier.name}</b><br>
            Contact: <b>{contact.name}</b><br>
            Address: <b>{address.name}</b><br>
            User: <b>{user.name}</b><br>
            """
        )

    # =============================================================
    # CREATE SUPPLIER USER
    # =============================================================

    def create_supplier_user(self, supplier, contact):

        email = self.email_id.strip().lower()

        # ---------------------------------------------------------
        # Check whether User already exists
        # ---------------------------------------------------------

        existing_user = frappe.db.exists(
            "User",
            {"name": email}
        )

        if existing_user:
            user = frappe.get_doc("User", existing_user)

            # Make sure account is enabled
            user.enabled = 1

            # Add Supplier role if missing
            if not any(role.role == "Supplier" for role in user.roles):
                user.append("roles", {
                    "role": "Supplier"
                })

            user.save(ignore_permissions=True)

            return user

        # ---------------------------------------------------------
        # Create new User
        # ---------------------------------------------------------

        user = frappe.get_doc({
            "doctype": "User",

            "email": email,
            "first_name": self.contact_person_name
                or self.name_of_the_company,

            "send_welcome_email": 1,
            "enabled": 1,

            "roles": [
                {
                    "role": "Supplier"
                }
            ]
        })

        user.insert(ignore_permissions=True)

        # ---------------------------------------------------------
        # Link User to Contact
        # ---------------------------------------------------------

        if contact:
            contact.user = user.name
            contact.save(ignore_permissions=True)

        # ---------------------------------------------------------
        # Send password setup / welcome email
        # ---------------------------------------------------------

        try:
            user.send_welcome_mail_to_user()
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Supplier User Welcome Email Failed"
            )

        return user