# Copyright (c) 2023, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from frappe import _


class PersonalOutGatePass(Document):
	def validate(self):
		self.make_prsnl_out_logs()

	def make_prsnl_out_logs(self):
		if not self.checkin_details:
			return
		for log in self.checkin_details:
			create_prsnl_out_log(log)

		frappe.msgprint(_("Personal Out Records Created/Updated"))
		self.checkin_details = []

	@frappe.whitelist()
	def get_checkin_details(self, from_log=False):
		conditions = self.get_conditions(from_log)
		data = frappe.db.sql(f"""SELECT emp_det.employee, emp_det.employee_name, emp_det.at_date as date, 
								time(check_out.checkout) as out_time, time(MIN(check_in.time)) AS in_time,
								time(timediff(MIN(check_in.time),check_out.checkout)) as total_hours,
								pol.name as po_log, if(pol.name is null, 1, pol.approve) as approve, pol.total_hours as approved_hours
								FROM (
								SELECT employee, employee_name, DATE(time) AS at_date, SUM(IF(log_type = 'OUT', 1, 0)) AS cnt, shift_start
								FROM `tabEmployee Checkin`
								WHERE log_type = 'OUT'
								GROUP BY employee, shift_start
								HAVING cnt > 1
								) emp_det
								LEFT JOIN (
								SELECT time AS checkout, employee AS emp, DATE(time) AS co_date, shift_start
								FROM `tabEmployee Checkin`
								WHERE log_type = 'OUT'
								) check_out ON emp_det.employee = check_out.emp AND emp_det.at_date = check_out.co_date and emp_det.shift_start = check_out.shift_start
								LEFT JOIN (
								SELECT time, employee, DATE(time) AS ci_date
								FROM `tabEmployee Checkin`
								WHERE log_type = 'IN'
								) check_in ON emp_det.employee = check_in.employee AND emp_det.at_date = check_in.ci_date AND check_out.checkout < check_in.time
								LEFT JOIN (select name, approve, total_hours, employee, date, out_time from `tabPersonal Out Log` where is_cancelled = 0) pol on emp_det.employee = pol.employee AND emp_det.at_date = pol.date and time(check_out.checkout) = pol.out_time
								{conditions}
							GROUP BY emp_det.employee, emp_det.at_date, check_out.checkout having in_time is not null""", as_dict=1)
		self.checkin_details = []
		if not data and not from_log:
			frappe.msgprint("No Records were found for the current filters")
			return
		for row in data:
			if row.po_log:
				row["total_hours"] = row.approved_hours
			self.append("checkin_details", row)


	def get_conditions(self, from_log):
		if not (self.from_date and self.to_date):
			frappe.throw("Invalid Date Range")
		conditions = f"where (emp_det.at_date between '{getdate(self.from_date)}' and '{getdate(self.to_date)}')"
		if from_log:
			conditions += " and pol.name is not null"
		if self.employee:
			conditions += f" and emp_det.employee = '{self.employee}'"
		if self.employee_name:
			conditions += f" and emp_det.employee_name like '%{self.employee_name}%'"

		sub_query_filter = []
		if self.company:
			sub_query_filter.append(f"e.company = '{self.company}'")
		if self.department:
			sub_query_filter.append(f"e.department = '{self.department}'")
		if self.designation:
			sub_query_filter.append(f"e.designation = '{self.designation}'")
		if sub_query_filter:
			conditions += f" and emp_det.employee in (select e.name from `tabEmployee` e where {' and '.join(sub_query_filter)})"
		return conditions

def create_prsnl_out_log(ref_doc):
	if ref_doc.po_log:
		doc = frappe.get_doc("Personal Out Log",ref_doc.po_log)
		if doc.approve and not ref_doc.approve:
			doc.delete()
			return
	else:
		if not ref_doc.approve:
			return
		doc = frappe.new_doc("Personal Out Log")
	fields = ["employee","employee_name","date","out_time","in_time","total_hours","approve"]
	data = {}
	for field in fields:
		data[field] = ref_doc.get(field)

	doc.update(data)
	doc.save()
	return doc.name

@frappe.whitelist()
def create_prsnl_out_logs(from_date=None, to_date = None, employee = None):
	doc = frappe.get_doc("Personal Out Gate Pass")
	doc.from_date = getdate(from_date)
	doc.to_date = getdate(to_date)
	if employee:
		doc.employee = employee
	doc.get_checkin_details()
	doc.save()