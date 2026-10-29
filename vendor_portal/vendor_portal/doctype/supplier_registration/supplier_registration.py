import frappe
from frappe.model.document import Document


class SupplierRegistration(Document):
    """One form-filler User can own multiple separate Supplier registrations."""

    def on_update(self):
        # Terms workflow/email functionality has been removed.
        if self.workflow_state != "Supplier Created" or self.supplier:
            return
        self.create_supplier_records()

    @staticmethod
    def _supported_fields(doctype, values):
        meta = frappe.get_meta(doctype)
        return {
            key: value for key, value in values.items()
            if key == "doctype" or meta.has_field(key)
        }

    @staticmethod
    def _find_user(email):
        found = frappe.db.get_value("User", {"name": email}, "name")
        if found:
            return found
        users = frappe.get_all(
            "User", filters={"email": email}, fields=["name"], limit=1
        )
        return users[0].name if users else None

    def _validate_registration(self):
        if not (self.name_of_the_company or "").strip():
            frappe.throw("Name of the Company is required.")
        if not (self.contact_person_name or "").strip():
            frappe.throw("Contact Person Name is required.")
        if not (self.email_id or "").strip():
            frappe.throw("Contact Email ID is required.")

    def _check_duplicate_supplier(self):
        # Different companies can be registered under one User.
        # Prevent accidental duplicate Supplier masters for the same GSTIN/name.
        existing = None
        gstin = (self.gstin_no or "").strip()
        company_name = (self.name_of_the_company or "").strip()

        if gstin:
            existing = frappe.db.get_value("Supplier", {"gstin": gstin}, "name")
        if not existing and company_name:
            existing = frappe.db.get_value(
                "Supplier", {"supplier_name": company_name}, "name"
            )
        if existing:
            frappe.throw(
                f"Supplier already exists: {frappe.utils.escape_html(existing)}. "
                "Check the existing Supplier record before submitting again."
            )

    def create_supplier_records(self):
        self._validate_registration()
        self._check_duplicate_supplier()
        email = self.email_id.strip().lower()

        # 1. Supplier. Optional/custom fields are passed only if installed
        # on this site, which avoids failures when Cloud has a different schema.
        supplier_values = self._supported_fields("Supplier", {
            "doctype": "Supplier",
            "supplier_name": self.name_of_the_company.strip(),
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

        group = supplier_values.get("supplier_group")
        if group and not frappe.db.exists("Supplier Group", group):
            fallback = frappe.db.get_value(
                "Supplier Group", {"is_group": 0}, "name"
            )
            if fallback:
                supplier_values["supplier_group"] = fallback
            else:
                frappe.throw(
                    "No Supplier Group exists. Create a Supplier Group in ERPNext."
                )

        supplier = frappe.get_doc(supplier_values)
        supplier.insert(ignore_permissions=True)

        # 2. Contact, linked to this Supplier.
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": self.contact_person_name.strip(),
            "designation": self.designation or "",
            "department": self.department or "",
        })
        contact.append("email_ids", {"email_id": email, "is_primary": 1})

        if self.mobile_no:
            contact.append("phone_nos", {
                "phone": self.mobile_no, "is_primary_mobile_no": 1
            })
        if self.landline_no:
            contact.append("phone_nos", {"phone": self.landline_no})
        if self.whatsapp_no:
            contact.append("phone_nos", {"phone": self.whatsapp_no})

        contact.append("links", {
            "link_doctype": "Supplier", "link_name": supplier.name
        })
        contact.insert(ignore_permissions=True)

        # 3. Billing Address, linked to this Supplier.
        address_values = self._supported_fields("Address", {
            "doctype": "Address",
            "address_title": self.name_of_the_company.strip(),
            "address_type": "Billing",
            "address_line1": self.address_line_1 or "",
            "address_line2": self.address_line_2 or "",
            "city": self.citytown or "",
            "state": self.stateprovince or "",
            "country": self.country or "India",
            "pincode": self.postal_code or "",
            "email_id": self.email_address or email,
            "phone": self.phone_no or self.mobile_no or "",
        })
        address = frappe.get_doc(address_values)
        address.append("links", {
            "link_doctype": "Supplier", "link_name": supplier.name
        })
        address.insert(ignore_permissions=True)

        # 4. Optional Bank Account.
        bank_account = None
        if (self.bank_name or "").strip() or (self.account_number or "").strip():
            bank_values = self._supported_fields("Bank Account", {
                "doctype": "Bank Account",
                "account_name": (
                    self.account_holder_name or self.name_of_the_company
                ),
                "account_type": self.account_type or "",
                "bank": self.bank_name or "",
                "bank_account_no": self.account_number or "",
                "branch_code": self.ifsc_code or "",
                "party_type": "Supplier",
                "party": supplier.name,
            })
            bank_account = frappe.get_doc(bank_values)
            bank_account.insert(ignore_permissions=True)

        # 5. Reuse the User by email, or create it once.
        user = self.create_or_reuse_user(email, contact)

        # 6. Link the created records to this registration.
        registration_meta = frappe.get_meta("Supplier Registration")
        links = {
            "supplier": supplier.name,
            "contact": contact.name,
            "address": address.name,
            "bank_account": bank_account.name if bank_account else None,
            "user": user.name,
        }
        update_values = {
            field: value for field, value in links.items()
            if value and registration_meta.has_field(field)
        }

        if registration_meta.has_field("registrationstatus"):
            update_values["registrationstatus"] = "Supplier Created"
        elif registration_meta.has_field("registration_status"):
            update_values["registration_status"] = "Supplier Created"

        if update_values:
            frappe.db.set_value(
                "Supplier Registration", self.name, update_values,
                update_modified=False,
            )

        frappe.msgprint(
            "<b>Supplier Registration Completed</b><br><br>"
            f"Supplier: <b>{frappe.utils.escape_html(supplier.name)}</b><br>"
            f"Contact: <b>{frappe.utils.escape_html(contact.name)}</b><br>"
            f"Address: <b>{frappe.utils.escape_html(address.name)}</b><br>"
            f"User: <b>{frappe.utils.escape_html(user.name)}</b><br><br>"
            "This login can be reused for future supplier registrations."
        )

    def create_or_reuse_user(self, email, contact):
        existing_name = self._find_user(email)

        if existing_name:
            user = frappe.get_doc("User", existing_name)
            user.enabled = 1

            if frappe.db.exists("Role", "Supplier"):
                if not any(row.role == "Supplier" for row in user.roles):
                    user.append("roles", {"role": "Supplier"})

            user.save(ignore_permissions=True)

            if contact and contact.user != user.name:
                contact.user = user.name
                contact.save(ignore_permissions=True)
            return user

        roles = []
        if frappe.db.exists("Role", "Supplier"):
            roles.append({"role": "Supplier"})

        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": (
                self.contact_person_name or self.name_of_the_company
            ),
            "send_welcome_email": 1,
            "enabled": 1,
            "roles": roles,
        })
        user.insert(ignore_permissions=True)

        if contact:
            contact.user = user.name
            contact.save(ignore_permissions=True)
        return user
