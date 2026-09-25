from zimbabwe_payroll.utils.reporting import aggregate, report_data
from zimbabwe_payroll.utils.statutory import report_filters


def execute(filters=None):
    filters = filters or {}
    _, detail = report_data(filters, "paye")
    fields = ("gross_remuneration", "taxable_income", "paye_before_credits", "tax_credits", "paye", "aids_levy", "total_paye_aids", "employee_nssa", "employee_pension")
    data = aggregate(detail, ("currency",), fields)
    columns = [
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 90},
        *[{"label": label.replace("_", " ").title(), "fieldname": label, "fieldtype": "Currency", "width": 130} for label in fields],
    ]
    return columns, data


def get_filters():
    return report_filters()
