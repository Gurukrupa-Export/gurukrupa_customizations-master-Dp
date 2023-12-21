// Copyright (c) 2023, 8848 Digital LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on('Manual Punch', {
	refresh(frm){
		frm.set_intro("Existing Personal Out and OT records will be cancelled on save")
	},
	onload(frm){
		frm.trigger('date')
		frm.set_value({"employee":null, "shift_name": null, "start_time": null, "end_time": null, "for_od":0, "punch_id":null})
	},
	after_save: function(frm) {
		frm.trigger("search")
	},
	date: function(frm) {
		frm.set_value("new_punch", frm.doc.date)
	},
	employee: function(frm) {
		if (frm.doc.employee) {
			frappe.db.get_value("Employee",frm.doc.employee, ["attendance_device_id","default_shift"], (r) => {
				frm.set_value({"punch_id":r.attendance_device_id, "shift_name":r.default_shift})
			})
		}
	},
	search: function(frm) {
		frm.call({
			method: "search_checkin",
			doc: frm.doc,
			callback: function(r) {
				var checkins = r.message
				$.each(checkins || [], function(i,d) {
					if (!d.source) {
						d.source = "Employee Checkin"
					}
					d.type = i%2==0 ? "IN":"OUT"
					frm.add_child("details", d)
				})
				frm.refresh_field("details")
			}
		})
	},
	add_new_punch(frm) {
		if (!frm.doc.date || !frm.doc.employee) {
			frappe.throw("Filters missing")
		}
		if (frm.doc.new_punch) {
			frappe.run_serially([
				()=>frm.call("validate_punch"),
				()=>add_punch(frm, frm.doc.new_punch),
				()=>frm.refresh_field("details")
			])
		}
		frm.refresh_field("details")
	}
});

frappe.ui.form.on("Manual Punch Details", {
	before_details_remove(frm, cdt, cdn) {
		var row = locals[cdt][cdn]
		if (!row.employee_checkin) return
		var to_be_deleted = cur_frm.doc.to_be_deleted ? cur_frm.doc.to_be_deleted.split(',') : []
		to_be_deleted.push(row.employee_checkin)
		frm.set_value("to_be_deleted", to_be_deleted.join())
	}
})

function validate_dates(frm) {
        var date = frm.doc.date;
        var datetime = frm.doc.new_punch;
        
        if (date && datetime) {
            var dateObj = moment(date);
            var datetimeObj = moment(datetime);
            
            if (!datetimeObj.isSame(dateObj, 'day')) {
                frappe.throw('The New Punch must be on the same day as the date field.');
            }
        }
}

function add_punch(frm,time) {
	let new_punch = {
		"date": frm.doc.date,
		"time": time,
		"source": frm.doc.for_od ? "Outdoor Duty" : "Manual Punch"
	} 
	var checkins = frm.doc.details || []
	checkins.push(new_punch)
	checkins.sort((a,b)=>{
		return moment(a.time).diff(b.time, 'second')
	})
	frm.doc.details = []
	$.each(checkins || [], function(i,d) {
		d.type = i%2==0 ? "IN":"OUT"
		frm.add_child("details", d)
	})
}