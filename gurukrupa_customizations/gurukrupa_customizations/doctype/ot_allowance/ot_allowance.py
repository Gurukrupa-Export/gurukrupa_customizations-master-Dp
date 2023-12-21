# Copyright (c) 2023, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_to_date, get_datetime, get_datetime_str, time_diff, getdate, get_timedelta, get_time
from frappe import _
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift_timings
from datetime import timedelta, datetime


class OTAllowance(Document):
	def validate(self):
		self.make_ot_logs()

	def make_ot_logs(self):
		for log in self.ot_details:
			if get_timedelta(log.allowed_ot) > get_timedelta(log.attn_ot_hrs):
				frappe.throw("Allowed OT cannot be greater than Attendance OT Hours")
			create_ot_log(log)
		self.ot_details=[]
		frappe.msgprint(_("Records Updated"))

	@frappe.whitelist()
	def get_ot_details(self, from_log=False):
		conditions = self.get_conditions(from_log)
		data = frappe.db.sql(f"""select at.name as attendance, at.employee, at.employee_name, emp.company, emp.designation,
		 	emp.department, emp.branch, sec_to_time(
		       	time_to_sec(
		       		timediff(
		       			at.out_time, timestamp(date(at.in_time),st.end_time)
		       		)
		       	)
		       	+ if(timestamp(date(at.in_time),st.start_time) > at.in_time, time_to_sec(
		       		timediff(
		       			timestamp(date(at.in_time),st.start_time), at.in_time
		       		)
		       	),0)
				- (select ifnull(sum(time_to_sec(pl.total_hours)),0) from `tabPersonal Out Log` pl 
							where pl.is_cancelled = 0 and pl.employee = at.employee and pl.date = at.attendance_date and pl.out_time >= st.end_time))  as attn_ot_hrs,
			at.shift, at.attendance_date, TIME(at.in_time) as first_in, TIME(at.out_time) as last_out, otl.name as ot_log, 
			otl.allow, otl.allowed_ot, otl.remarks
			from `tabAttendance` at 
			left join `tabShift Type` st on at.shift = st.name 
			left join (select * from `tabOT Log` where is_cancelled=0) otl on otl.attendance = at.name 
			left join `tabEmployee` emp on at.employee = emp.name
			where at.docstatus = 1 and time_to_sec(timediff(at.out_time,timestamp(date(at.in_time),st.end_time))) > 0 {conditions}""", as_dict=1)
		self.ot_details = []
		data = data + self.get_weekoffs_ot(from_log)
		if not data:
			frappe.msgprint("No Records were found for the current filters")
			return
		data = sorted(data, key=lambda x:x.get("attendance_date"))
		for row in data:
			if not row.get("allowed_ot"):
				row["allowed_ot"] = row.get("attn_ot_hrs")
			if row.get("allowed_ot") <= timedelta(minutes=30):	# for excluding OT that are less than 30 min
				continue 
			self.append("ot_details", row)

	def get_weekoffs_ot(self, from_log=False):
		holidays = self.get_emp_list()
		res = []
		
		for holiday_list, emp_list in holidays.items():
			holidays_list = frappe.get_all("Holiday", {"parent": holiday_list,
					"holiday_date":["between",[self.from_date, self.to_date]], "weekly_off": 1}, ["holiday_date","weekly_off"])
			for emp in emp_list:
				res += self.get_weekoffs_ot_per_employee(from_log, emp, holidays_list)
		return res

	def get_weekoffs_ot_per_employee(self, from_log=False, emp = None, holidays = []):
		res = []
		for holiday in holidays:
			shift = get_shift(emp.name, holiday.holiday_date, emp.default_shift)
			date_time = datetime.combine(getdate(holiday.holiday_date), get_time(shift.start_time))
			shift_timings = get_employee_shift_timings(emp.name, get_datetime(date_time), True)[1]
			filters = {
					"time":["between",[get_datetime_str(shift_timings.actual_start), get_datetime_str(shift_timings.actual_end)]],
					"employee": emp.name
			}
			fields = ["date(time) as date", "log_type as type", "time(time) as time", "time as date_time", "source", "name as employee_checkin", f"date('{holiday.holiday_date}') as holiday", "employee", "employee_name"]

			data = frappe.get_list("Employee Checkin", filters= filters, fields=fields, order_by='date_time')
			
			checkin = {}
			for row in data:
				if not checkin and row.type == "IN":
					checkin = {
						"attendance_date": row.holiday,
						"date_time": row.date_time,
						"first_in": row.time,
						"employee": row.employee,
						"employee_name": row.employee_name,
						"shift": row.shift,
						"weekly_off": holiday.weekly_off,
						"company": emp.company,
						"department": emp.department,
						"designation": emp.designation,
						"branch": emp.branch
					}
				elif checkin and row.type == "OUT":
					ot_log = {}
					ot_log = frappe.db.get_value("OT Log",{"attendance_date": row.holiday, "employee": row.employee, "is_cancelled":0, "first_in": checkin.get("first_in")},
												["name as ot_log", "allow", "allowed_ot", "remarks","attendance_date"], as_dict=1) or {}
					checkin.update(ot_log)
					checkin["last_out"] = row.time
					checkin["attn_ot_hrs"] = time_diff(row.date_time, checkin.get("date_time"))
					if not checkin.get("allowed_ot"):
						checkin["allowed_ot"] = time_diff(row.date_time, checkin.get("date_time"))
					if from_log:
						if checkin.get("ot_log"):
							res.append(checkin)
						checkin = {}
						continue
					res.append(checkin)
					checkin = {}
		return res
	
	def get_emp_list(self):
		emp_list = []
		filters = {}
		if self.employee:
			filters["employee"] = self.employee
		if self.designation:
			filters["designation"] = self.designation
		if self.department:
			filters["department"] = self.department
		if self.company:
			filters["company"] = self.company

		emp_list = frappe.get_list("Employee", filters = filters, fields = ["default_shift","holiday_list","name","company", "designation", "department", "branch"])
		holidays = {}
		for emp in emp_list:
			if shift:=emp.get("default_shift") and not emp.get("holiday_list"):
				emp.holiday_list = frappe.db.get_value("Shift Type",shift,"holiday_list")

			if emp.holiday_list not in holidays:
				holidays[emp.holiday_list] = [emp]
			else:
				holidays[emp.holiday_list].append(emp)
		return holidays

	def get_conditions(self, from_log):
		if not (self.from_date and self.to_date):
			frappe.throw("Invalid Date Range")
		conditions = f" and (at.attendance_date between '{getdate(self.from_date)}' and '{getdate(self.to_date)}')"
		if from_log:
			conditions += " and otl.name is not null"
		if self.punch_id or self.employee:
			if not self.employee:
				self.employee = frappe.db.get_value("Employee",{"attendance_device_id":self.punch_id},'name')
			conditions += f" and at.employee = '{self.employee}'"
		if self.employee_name:
			conditions += f" and at.employee_name like '%{self.employee_name}%'"
		sub_query_filter = ["e.product_incentive_applicable = 1"]
		if self.company:
			sub_query_filter.append(f"e.company = '{self.company}'")
		else:
			frappe.throw(_("Company is mandatory"))
		if self.department:
			sub_query_filter.append(f"e.department = '{self.department}'")
		if self.designation:
			sub_query_filter.append(f"e.designation = '{self.designation}'")
		
		conditions += f" and at.employee in (select e.name from `tabEmployee` e where {' and '.join(sub_query_filter)})"

		return conditions

def create_ot_log(ref_doc):
	if ref_doc.ot_log:
		doc = frappe.get_doc("OT Log",ref_doc.ot_log)
		if doc.allow and not ref_doc.allow:
			doc.delete()
			return
	else:
		if not ref_doc.allow:
			return
		doc = frappe.new_doc("OT Log")
	fields = ["employee","employee_name","attendance_date","attn_ot_hrs","allow","allowed_ot","first_in","last_out","attendance","remarks", "weekly_off"]
	data = {}
	for field in fields:
		data[field] = ref_doc.get(field)

	doc.update(data)
	doc.save()
	return doc.name


def get_shift(employee, date, default_shift):
	shift = frappe.db.get_value("Shift Assignment", {"employee": employee, "start_date": ["<=", date], "end_date": [">=",date], "status": "Active", "docstatus": 1})
	if not shift:
		shift = default_shift
	det = frappe.db.get_value("Shift Type", shift, ["name", "start_time", "end_time", "shift_hours", "begin_check_in_before_shift_start_time", "allow_check_out_after_shift_end_time"], as_dict=1)
	return det