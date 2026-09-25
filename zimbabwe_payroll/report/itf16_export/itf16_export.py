import csv
import io

import frappe

from zimbabwe_payroll.utils.statutory import report_filters, rows_for_slips


def execute(filters=None):
    filters = filters or {}
    data = []
    for row in rows_for_slips(filters):
        a = row["amounts"]
        slip = row["slip"]
        data.append(
            {
                "employee": row["employee"],
                "employee_name": row["employee_name"],
                "posting_date": row["posting_date"],
                "currency": row["currency"],
                "gross_remuneration": a.gross,
                "taxable_income": a.taxable_income,
                "paye": a.paye,
                "aids_levy": a.aids_levy,
                "employee_nssa": a.employee_nssa,
                "employee_pension": a.employee_pension,
                "medical_credit": a.medical_credit,
                "benefits": a.benefits,
                "net_pay": slip.net_pay,
            }
        )
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 170},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 95},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 70},
        {"label": "Gross Remuneration", "fieldname": "gross_remuneration", "fieldtype": "Currency", "width": 120},
        {"label": "Taxable Income", "fieldname": "taxable_income", "fieldtype": "Currency", "width": 110},
        {"label": "PAYE", "fieldname": "paye", "fieldtype": "Currency", "width": 95},
        {"label": "AIDS Levy", "fieldname": "aids_levy", "fieldtype": "Currency", "width": 95},
        {"label": "Employee NSSA", "fieldname": "employee_nssa", "fieldtype": "Currency", "width": 110},
        {"label": "Employee Pension", "fieldname": "employee_pension", "fieldtype": "Currency", "width": 115},
        {"label": "Medical Credit", "fieldname": "medical_credit", "fieldtype": "Currency", "width": 110},
        {"label": "Benefits", "fieldname": "benefits", "fieldtype": "Currency", "width": 100},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 100},
    ]
    return columns, data


def get_filters():
    return report_filters()


@frappe.whitelist()
def download_csv(filters=None):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    filters = filters or {}
    _, rows = execute(filters)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["employee"])
    writer.writeheader()
    writer.writerows(rows)
    frappe.local.response.filename = "zimbabwe_itf16_export.csv"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "download"
