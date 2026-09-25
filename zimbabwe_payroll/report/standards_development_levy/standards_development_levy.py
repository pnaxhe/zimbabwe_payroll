from zimbabwe_payroll.utils.reporting import report_data
from zimbabwe_payroll.utils.statutory import report_filters


def execute(filters=None):
    return report_data(filters or {}, "standards")


def get_filters():
    return report_filters()
