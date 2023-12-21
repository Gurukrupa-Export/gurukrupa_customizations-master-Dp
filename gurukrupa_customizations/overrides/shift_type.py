import frappe

"""
Provided by sourav, navin
"""

def before_save(doc, method=None):
    doc.shift_hours = frappe.utils.time_diff_in_hours(doc.end_time, doc.start_time)

    # shift spanning over 2 days
    # eg: 09:00 to 01:00 = -8
    # -8 + 12 = 4 hour shift

    if doc.shift_hours < 0:
        doc.shift_hours = doc.shift_hours + 12
