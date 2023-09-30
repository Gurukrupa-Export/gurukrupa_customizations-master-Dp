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
	}
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
		"filters": [["dt", "in", ["Employee", "Company"]], ["is_system_generated",'=',0]]
	}
]

from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from gurukrupa_customizations.overrides.payment_entry import add_party_gl_entries
PaymentEntry.add_party_gl_entries = add_party_gl_entries