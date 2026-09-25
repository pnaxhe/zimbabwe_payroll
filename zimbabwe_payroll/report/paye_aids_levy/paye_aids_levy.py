from zimbabwe_payroll.utils.reporting import report_data
from zimbabwe_payroll.utils.statutory import report_filters


def execute(filters=None):
    filters = filters or {}
    columns, data = report_data(filters, "paye")
    return columns, data


def get_filters():
    return report_filters()
