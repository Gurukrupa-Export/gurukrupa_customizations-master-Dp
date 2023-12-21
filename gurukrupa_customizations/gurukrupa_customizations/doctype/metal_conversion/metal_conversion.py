# Copyright (c) 2023, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MetalConversion(Document):
	def before_save(self):
		self.create_stock_entry()

	def create_stock_entry(self):
		crv = frappe.get_doc("Stock Entry", {"name": self.customer_received_voucher})
		company = crv.company
		for itm in crv.items:
			if itm.batch_no == self.batch_no:
				s_warehouse = itm.s_warehouse
				t_warehouse = itm.t_warehouse
				item_code = itm.item_code
				qty = itm.qty
				customer = itm.customer
				inventory_type = itm.inventory_type

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Repack"
		se.inventory_type = crv.inventory_type
		se._customer = crv._customer
		se.custom_metal_conversion_reference = self.customer_received_voucher
		se.company = company
		items = se.append("items")
		items.item_code = item_code
		items.s_warehouse = s_warehouse
		items.t_warehouse = t_warehouse
		items.qty = qty
		items.customer = customer
		items.inventory_type = inventory_type
		items.batch_no = self.batch_no

		se.submit()

		frappe.msgprint(f"Stock Entry { se.name } is created")


	@frappe.whitelist()
	def get_linked_item_details(self):
		se = frappe.get_doc("Stock Entry", self.customer_received_voucher)

		data = frappe.db.sql(f"""SELECT
					sed.item_code AS item_code,
					MAX(CASE
						WHEN va1.attribute = "Metal Purity" THEN va1.attribute_value
						ELSE NULL
					END) AS metal_purity,
					MAX(CASE
						WHEN va2.attribute = "Metal Colour" THEN va2.attribute_value
						ELSE NULL
					END) AS metal_colour,
					MAX(CASE
						WHEN va3.attribute = "Metal Touch" THEN va3.attribute_value
						ELSE NULL
					END) AS metal_touch,
					sed.qty AS qty,
					b.batch_qty - sed.qty AS remaining_qty
				FROM `tabStock Entry` se 
				JOIN `tabBatch` b on b.name = "{ self.batch_no }"
				JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
				JOIN `tabItem` itm ON itm.name = sed.item_code
				LEFT JOIN `tabItem Variant Attribute` va1 ON va1.parent = itm.name AND va1.attribute = "Metal Purity"
				LEFT JOIN `tabItem Variant Attribute` va2 ON va2.parent = itm.name AND va2.attribute = "Metal Colour"
				LEFT JOIN `tabItem Variant Attribute` va3 ON va3.parent = itm.name AND va3.attribute = "Metal Touch"
				WHERE se.name = "{ se.name }"
				GROUP BY sed.item_code;
				""", as_dict=1)

		return frappe.render_template("gurukrupa_customizations/gurukrupa_customizations/doctype/metal_conversion/item_details.html", {"data":data})
	
	@frappe.whitelist()
	def get_list_of_metal_type(self):
		attr = frappe.get_doc("Item Attribute", "Metal Type")

		attr_list = []
		for a in attr.item_attribute_values:
			attr_list.append(a.attribute_value)

		return attr_list
	
	@frappe.whitelist()
	def get_list_of_metal_purity(self):
		attr = frappe.get_doc("Item Attribute", "Metal Purity")

		attr_list = []
		for a in attr.item_attribute_values:
			attr_list.append(a.attribute_value)

		return attr_list