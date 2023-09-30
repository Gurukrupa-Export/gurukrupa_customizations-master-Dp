// Copyright (c) 2023, 8848 Digital LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('OT Allowance', {
	setup(frm) {
		frm.set_query("department", function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		})
	},
	onload(frm) {
		let start = frappe.datetime.month_start(frappe.datetime.get_today())
		let end = frappe.datetime.month_end(frappe.datetime.get_today())
		frm.set_value({"from_date":start,"to_date":end})
		frm.set_value("employee",null)
	},
	after_save: function(frm) {
		frm.call("get_ot_details",{"from_log":true})
	},
	employee(frm) {
		if (frm.doc.employee) {
			frappe.db.get_value("Employee", frm.doc.employee, ["company", "designation", "department", "attendance_device_id as punch_id"], (r)=>{
				frm.set_value(r)
			})
		}
		else {
			frm.set_value({
				"company": null,
				"designation": null,
				"department": null,
				"punch_id": null
			})
		}
	}
});

frappe.ui.form.on("OT Details", {
	allow(frm, cdt, cdn) {
		let d = locals[cdt][cdn]
		if (!d.allow) {
			frappe.model.set_value(cdt,cdn,"allowed_ot", d.attn_ot_hrs)
		}
	},
	allowed_ot(frm, cdt, cdn) {
		let d = locals[cdt][cdn]
		if (d.allowed_ot > d.attn_ot_hrs || !d.allow || !d.allowed_ot) {
			frappe.model.set_value(cdt,cdn,"allowed_ot", d.attn_ot_hrs)
		}
		frm.refresh_field('ot_details')
	}
})