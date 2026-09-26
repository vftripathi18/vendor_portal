import frappe
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime


class SupplierRegistration(Document):

    def on_update(self):
        old_doc = self.get_doc_before_save()
        old_state = old_doc.workflow_state if old_doc else None
        current_state = self.workflow_state

        # FINAL STAGE ONLY: create actual Supplier records.
        # Nothing is created before Supplier Created.
        if current_state == "Supplier Created":
            if self.supplier:
                return

            self.create_supplier_records()
            return

        # Send the terms email exactly when the workflow enters
        # Terms Pending. This is intentionally before Supplier Created.
        if current_state == "Terms Pending" and old_state != "Terms Pending":
            self.send_terms_email()

    # =============================================================
    # SEND TERMS EMAIL
    # =============================================================

    def send_terms_email(self):

        if not self.email_id:
            frappe.throw("Contact Email ID is required to send the terms.")

        if not self.terms_pdf:
            frappe.throw(
                "Terms & Conditions PDF is required before sending the terms."
            )

        # New token every time terms are sent/resend.
        token = frappe.generate_hash(length=40)

        frappe.db.set_value(
            "Supplier Registration",
            self.name,
            {
                "terms_token": token,
                "terms_email_sent": 1,
                "terms_version": self.terms_version or "Current",
            },
            update_modified=False
        )

        terms_url = (
            get_url("/supplier-terms")
            + "?token="
            + token
        )

        company_name = frappe.utils.escape_html(
            self.name_of_the_company or "Supplier"
        )
        contact_name = frappe.utils.escape_html(
            self.contact_person_name or "Supplier"
        )
        registration_name = frappe.utils.escape_html(
            self.name
        )

        logo_url = get_url("/files/company%20logo.png")

        email_subject = (
            f"Vone8 Infotech | Terms & Conditions Review - {self.name_of_the_company}"
        )

        email_message = f"""
        <div style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,Helvetica,sans-serif;color:#172033;">
          <div style="max-width:680px;margin:0 auto;padding:32px 18px;">

            <div style="background:#ffffff;border:1px solid #e7ebf2;border-radius:18px;overflow:hidden;box-shadow:0 8px 30px rgba(15,23,42,.06);">

              <div style="padding:28px 32px;border-bottom:1px solid #edf0f5;">
                <img src="{logo_url}" alt="Vone8 Infotech" style="height:48px;width:auto;display:block;">
              </div>

              <div style="padding:34px 32px 12px;">
                <div style="font-size:12px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#2563eb;margin-bottom:12px;">Supplier Onboarding</div>
                <h1 style="margin:0 0 14px;font-size:28px;line-height:1.25;color:#101828;">Terms &amp; Conditions Review</h1>
                <p style="margin:0;color:#667085;font-size:15px;line-height:1.7;">
                  Dear {contact_name},<br><br>
                  Your supplier registration for <strong>{company_name}</strong> has reached the Terms &amp; Conditions review stage.
                  Please review the attached PDF carefully and confirm your decision using the secure button below.
                </p>
              </div>

              <div style="padding:20px 32px;">
                <div style="background:#f8fafc;border:1px solid #e6eaf0;border-radius:14px;padding:18px 20px;">
                  <div style="font-size:12px;color:#667085;margin-bottom:5px;">Registration</div>
                  <div style="font-size:15px;font-weight:700;color:#101828;">{registration_name}</div>
                  <div style="font-size:13px;color:#667085;margin-top:5px;">Terms &amp; Conditions PDF is attached to this email.</div>
                </div>
              </div>

              <div style="padding:8px 32px 34px;text-align:center;">
                <a href="{terms_url}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;padding:14px 26px;border-radius:10px;">Review &amp; Accept Terms</a>
                <p style="margin:16px 0 0;font-size:12px;line-height:1.6;color:#98a2b3;">
                  This secure review link is unique to this supplier registration.
                </p>
              </div>

              <div style="padding:20px 32px;background:#f8fafc;border-top:1px solid #edf0f5;">
                <p style="margin:0;font-size:12px;line-height:1.7;color:#98a2b3;">
                  Regards,<br>
                  <strong style="color:#667085;">Vone8 Infotech</strong><br>
                  Supplier Onboarding Team
                </p>
              </div>

            </div>

            <p style="text-align:center;margin:18px 0 0;font-size:11px;color:#98a2b3;">
              © 2026 Vone8 Infotech. All rights reserved.
            </p>
          </div>
        </div>
        """

        frappe.sendmail(
            recipients=[self.email_id],
            subject=email_subject,
            message=email_message,
            now=True,
            reference_doctype="Supplier Registration",
            reference_name=self.name
        )

        frappe.db.commit()

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