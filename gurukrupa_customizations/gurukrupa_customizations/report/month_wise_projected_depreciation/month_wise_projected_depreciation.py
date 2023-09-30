# Copyright (c) 2023, 8848 Digital LLP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, flt
from frappe import _
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_data(filters):
	conditions = get_conditions(filters)
	year_start_date, year_end_date = frappe.get_cached_value(
			"Fiscal Year", filters.get("fiscal_year"), ["year_start_date", "year_end_date"]
		)
	to_date = filters.get("to_date") or year_end_date
	child_cond = ""
	if fb:=filters.get("finance_book"):
		child_cond = f"and finance_book = '{fb}'"
	schedules = frappe.db.sql(
		f"""select a.name as asset, a.asset_category, afb.rate_of_depreciation , a.available_for_use_date, a.purchase_date, 
			a.location, a.gross_purchase_amount as purchase_value,(
				select sum(ds.depreciation_amount) from `tabDepreciation Schedule` ds where ds.parent = a.name 
				and ds.schedule_date <= "{to_date}" {child_cond}) as acc_depreciation, 
				a.opening_accumulated_depreciation as op_acc_depreciation,
			ds.current_schedule_date, ds.depreciation_amount, ds.previous_schedule_date from `tabAsset` a left join 
			(select parent, rate_of_depreciation from `tabAsset Finance Book` group by parent) as afb on a.name = afb.parent
			right join (
				SELECT ds.parent, ds.schedule_date AS current_schedule_date, 
				sum(ds.depreciation_amount) as depreciation_amount, 
				(
					SELECT MAX(schedule_date) FROM `tabDepreciation Schedule` WHERE 
					parent = ds.parent AND schedule_date < '{to_date}' {child_cond}
				) AS previous_schedule_date 
				FROM 
				`tabDepreciation Schedule` ds 
				WHERE 
				ds.schedule_date >= '{to_date}' {child_cond}
				AND (
					SELECT MIN(schedule_date) FROM `tabDepreciation Schedule` WHERE 
					parent = ds.parent AND schedule_date >= '{to_date}' {child_cond}
				) = ds.schedule_date and ds.docstatus = 1 
				GROUP BY ds.parent, ds.schedule_date
			) as ds on ds.parent = a.name where a.docstatus = 1 {conditions}""",
		as_dict=1)


	for row in schedules:
		if getdate(to_date) != row["current_schedule_date"]:
			start_date = max(year_start_date, row["purchase_date"])
			try:
				days = get_no_of_days(row["current_schedule_date"], (row["previous_schedule_date"] or start_date))
			except:
				frappe.msgprint(str(row))
			per_day = row['depreciation_amount'] / days
			row["total_days"] = days
			row["extra_days"] = get_no_of_days(getdate(to_date), (row["previous_schedule_date"] or start_date))
			row["depreciation"] = per_day*row["extra_days"]
		row["accumulated_depreciation"] = flt(row["op_acc_depreciation"]) + flt(row["acc_depreciation"])
		row["gross_block"] = row["purchase_value"] - flt(row["accumulated_depreciation"])
		row["net_block"] = row["gross_block"] - flt(row.get("depreciation"))
	return schedules


def get_columns(filters):
	columns = [
		{
			"label": _("Purchase Date"),
			"fieldname": "purchase_date",
			"fieldtype": "Date",
		},
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Link",
			"options": "Asset Category",
		},
		{
			"label": _("Asset"),
			"fieldname": "asset",
			"fieldtype": "Link",
			"options": "Asset",
		},
		{
			"label": _("Rate of Depreciation"),
			"fieldname": "rate_of_depreciation",
			"fieldtype": "Percentage"
		},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Link",
			"options": "Location",
		},
		{
			"label": _("Purchase Value"),
			"fieldname": "purchase_value",
			"fieldtype": "Currency",
		},
		{
			"label": _("Accumulated Depreciation"),
			"fieldname": "accumulated_depreciation",
			"fieldtype": "Currency",
		},
		{
			"label": _("Gross Block"),
			"fieldname": "gross_block",
			"fieldtype": "Currency",
		},
		{
			"label": _("Depreciation"),
			"fieldname": "depreciation",
			"fieldtype": "Currency",
		},
		{"label": _("Net Block"), "fieldname": "net_block", "fieldtype": "Currency"},
	]
	return columns


def get_conditions(filters):
	condition = ""
	if asset_category := filters.get("asset_category"):
		condition += f"and asset_category = '{asset_category}'"
	if date := filters.get("to_date"):
		condition += f"""and purchase_date <= '{date}'"""
	if fy:=filters.get("fiscal_year"):
		if date:=filters.get("to_date"):
			fy_date = get_fiscal_year(date)
		else:
			year_end_date = frappe.get_cached_value("Fiscal Year", filters.get("fiscal_year"),"year_end_date")
			condition += f"""and purchase_date <= '{year_end_date}'"""
	if location:=filters.get("location"):
		filters.location = frappe.parse_json(filters.get("location"))
		condition += f"""and location in ('{"', '".join(filters.location)}')"""
	return condition

def get_no_of_days(end_date, start_date):
	return abs((end_date-start_date).days)