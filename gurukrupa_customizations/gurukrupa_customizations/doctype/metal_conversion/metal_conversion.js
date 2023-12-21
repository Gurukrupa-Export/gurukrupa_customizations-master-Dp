// Copyright (c) 2023, 8848 Digital LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Metal Conversion', {
	refresh: function(frm) {
		set_html(frm)
		frm.set_query("customer_received_voucher", function() {
			return {
				filters: {
					"stock_entry_type": "Customer Goods Received"
				}
			};
		})
		frm.set_query("batch_no", function() {
			return {
				filters: {
					"reference_doctype": "Stock Entry",
					"reference_name": frm.doc.customer_received_voucher
				}
			};
		})
		frm.set_query("metal_shape", function() {
			return {
				filters: {
					"name": ["in", ["Metal Type", "Metal Touch","Metal Colour", "Metal Purity"]]
				}
			};
		})

		frappe.call({ 
			method: "get_list_of_metal_type",
			doc: frm.doc,
			callback: function (r) {
				frm.set_df_property("metal_type", "options", r.message)
			} 
		})

		frappe.call({ 
			method: "get_list_of_metal_purity",
			doc: frm.doc,
			callback: function (r) {
				frm.set_df_property("base_purity", "options", r.message)
				frm.set_df_property("to_purity", "options", r.message)
			} 
		})
	},
	batch_no: function(frm) {
		frappe.db.get_value("Batch", frm.doc.batch_no, ["batch_qty"]).then((r) => {
			console.log("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", r.message.batch_qty)
			frm.set_value("base_metal_wt", r.message.batch_qty)
			frm.set_value("total_weight", r.message.batch_qty)
			frm.refresh_fields('base_metal_wt')
			frm.refresh_fields('total_weight')
		})
	}

});

function set_html(frm) {
	if (frm.doc.customer_received_voucher) {
		frappe.call({ 
			method: "get_linked_item_details",
			doc: frm.doc,
			callback: function (r) { 
				frm.get_field("item_details").$wrapper.html(r.message) 
			} 
		})
	}
	else {
		frm.get_field("item_details").$wrapper.html("")
	}
}
