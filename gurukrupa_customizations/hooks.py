from . import __version__ as app_version

app_name = "gurukrupa_customizations"
app_title = "Gurukrupa Customizations"
app_publisher = "8848 Digital LLP"
app_description = "Gurukrupa Customizations"
app_email = "deepak@8848digital.com"
app_license = "MIT"

doctype_js = {
    "Cost Center": "client_script/cost_center.js"
}

doc_events = {
	"Payment Entry": {
		"validate": "gurukrupa_customizations.overrides.payment_entry.validate"
	},
    
    # "Shift Type": {
    #     "before_save": "gurukrupa_customizations.overrides.shift_type.before_save"
	# },
    # "Attendance": {
    #     "before_save": "gurukrupa_customizations.overrides.attendance.before_save"
	# },
    # "Stock Ledger Entry": {
    #     "after_submit": "gurukrupa_customizations.overrides.stock_ledger_entry.after_submit"
	# }
}

scheduler_events = {
 	"cron": {
		"0 23 * * *": [
			"gurukrupa_customizations.gurukrupa_customizations.doctype.personal_out_gate_pass.personal_out_gate_pass.create_prsnl_out_logs",
		]
	},
}

fixtures = [
	{
		"dt": "Custom Field", 
		"filters": [["dt", "in", ["Employee", "Company", "Employee Referral", "Job Requisition", "Salary Slip", "Shift Type", "Attendance", "Item"]], ["is_system_generated",'=',0]]
	},
    {
		"dt": "Property Setter", 
		"filters": [["doc_type", "in", ["Employee", "Employee Referral", "Interview"]], ["is_system_generated",'=',0]]
	}
]

from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from gurukrupa_customizations.overrides.payment_entry import add_party_gl_entries
PaymentEntry.add_party_gl_entries = add_party_gl_entries

from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from gurukrupa_customizations.overrides.salary_slip import get_holidays_for_employee
SalarySlip.get_holidays_for_employee = get_holidays_for_employee