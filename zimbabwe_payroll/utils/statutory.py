"""Zimbabwe payroll statutory helpers.

The helpers are intentionally small and side-effect free where possible so they
can be tested outside a Frappe site. Site-specific Salary Slip access is kept in
the report adapter below.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import frappe


ZERO = Decimal("0")
CENT = Decimal("0.01")


def money(value: Any) -> Decimal:
    if value in (None, ""):
        return ZERO
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def rate(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def normalise(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").split())


USD_MONTHLY_TABLE = (
    (Decimal("100"), Decimal("0"), Decimal("0")),
    (Decimal("300"), Decimal("0.20"), Decimal("20")),
    (Decimal("1000"), Decimal("0.25"), Decimal("35")),
    (Decimal("2000"), Decimal("0.30"), Decimal("85")),
    (Decimal("3000"), Decimal("0.35"), Decimal("185")),
    (None, Decimal("0.40"), Decimal("335")),
)

ZIG_MONTHLY_TABLE = (
    (Decimal("2800"), Decimal("0"), Decimal("0")),
    (Decimal("8400"), Decimal("0.20"), Decimal("560")),
    (Decimal("28000"), Decimal("0.25"), Decimal("980")),
    (Decimal("56000"), Decimal("0.30"), Decimal("2380")),
    (Decimal("84000"), Decimal("0.35"), Decimal("5180")),
    (None, Decimal("0.40"), Decimal("9380")),
)


@dataclass
class SlipAmounts:
    gross: Decimal = ZERO
    taxable_income: Decimal = ZERO
    paye_before_credits: Decimal = ZERO
    credits: Decimal = ZERO
    paye: Decimal = ZERO
    aids_levy: Decimal = ZERO
    basic: Decimal = ZERO
    employee_pension: Decimal = ZERO
    employer_pension: Decimal = ZERO
    employee_nssa: Decimal = ZERO
    employer_nssa: Decimal = ZERO
    medical_employee: Decimal = ZERO
    medical_employer: Decimal = ZERO
    medical_credit: Decimal = ZERO
    bonus: Decimal = ZERO
    benefits: Decimal = ZERO
    reimbursements: Decimal = ZERO
    zimdef_base: Decimal = ZERO
    standards_base: Decimal = ZERO
    apwcs_base: Decimal = ZERO
    apwcs_rate: Decimal = ZERO


def calculate_tax(taxable_income: Any, currency: str) -> Decimal:
    """Apply the monthly reference table for the supplied currency."""
    taxable = max(money(taxable_income), ZERO)
    table = USD_MONTHLY_TABLE if normalise(currency) in {"usd", "us dollar", "us dollars"} else ZIG_MONTHLY_TABLE
    for upper, bracket_rate, deduction in table:
        if upper is None or taxable <= upper:
            return max((taxable * bracket_rate - deduction).quantize(CENT, rounding=ROUND_HALF_UP), ZERO)
    return ZERO


def calculate_aids_levy(paye_after_credits: Any) -> Decimal:
    return (max(money(paye_after_credits), ZERO) * Decimal("0.03")).quantize(CENT, rounding=ROUND_HALF_UP)


def nssa_pobs(basic_salary: Any, ceiling: Any = Decimal("700")) -> tuple[Decimal, Decimal]:
    insurable = min(max(money(basic_salary), ZERO), max(money(ceiling), ZERO))
    contribution = (insurable * Decimal("0.045")).quantize(CENT, rounding=ROUND_HALF_UP)
    return contribution, contribution


def component_matches(name: Any, *terms: str) -> bool:
    text = normalise(name)
    return any(normalise(term) in text for term in terms)


def setting(name: str, default: Any = None) -> Any:
    if not frappe.db.exists("DocType", "Zimbabwe Payroll Settings"):
        return default
    value = frappe.db.get_single_value("Zimbabwe Payroll Settings", name)
    return default if value in (None, "") else value


def nssa_ceiling(currency: str, exchange_rate: Any = None) -> Decimal:
    configured = setting("nssa_insurable_ceiling_usd", "700")
    ceiling_usd = money(configured)
    if normalise(currency) in {"usd", "us dollar", "us dollars"}:
        return ceiling_usd
    # The ceiling is maintained in USD by default. For local-currency payroll,
    # convert the USD ceiling using the approved payment-date local/USD rate.
    # A custom local-currency ceiling can still be supplied directly on the
    # Salary Slip through custom_zimbabwe_nssa_ceiling.
    local_rate = money(exchange_rate)
    return (ceiling_usd * local_rate).quantize(CENT, rounding=ROUND_HALF_UP) if local_rate else ceiling_usd


def _custom(slip: Any, fieldname: str, default: Any = ZERO) -> Decimal:
    value = getattr(slip, fieldname, None)
    return money(default if value in (None, "") else value)


def read_components(slip_name: str) -> list[Any]:
    """Return Salary Detail rows for both earnings and deductions."""
    return frappe.get_all(
        "Salary Detail",
        filters={"parent": slip_name, "parenttype": "Salary Slip"},
        fields=["salary_component", "abbr", "amount", "parentfield", "idx"],
        order_by="idx asc",
    )


def component_total(rows: list[Any], *terms: str, parentfield: str | None = None) -> Decimal:
    total = ZERO
    for row in rows:
        if parentfield and row.parentfield != parentfield:
            continue
        if component_matches(row.salary_component, *terms) or component_matches(row.abbr, *terms):
            total += money(row.amount)
    return total


def derive_slip_amounts(slip: Any) -> SlipAmounts:
    rows = read_components(slip.name)
    currency = getattr(slip, "currency", None) or getattr(slip, "custom_payroll_currency", None) or "ZWG"
    exchange_rate = getattr(slip, "custom_zimbabwe_exchange_rate", None)
    gross = _custom(slip, "custom_zimbabwe_gross_remuneration", getattr(slip, "gross_pay", ZERO))
    basic = _custom(slip, "custom_zimbabwe_nssa_basic", component_total(rows, "basic", parentfield="earnings"))
    employee_pension = _custom(
        slip,
        "custom_zimbabwe_pension_employee",
        component_total(rows, "employee pension", "pension", "retirement annuity", parentfield="deductions"),
    )
    employer_pension = _custom(
        slip,
        "custom_zimbabwe_pension_employer",
        component_total(rows, "employer pension", "pension employer", parentfield="earnings"),
    )
    employee_nssa = _custom(slip, "custom_zimbabwe_nssa_employee", component_total(rows, "nssa", parentfield="deductions"))
    employer_nssa = _custom(slip, "custom_zimbabwe_nssa_employer", component_total(rows, "nssa", parentfield="earnings"))
    if basic and (not employee_nssa or not employer_nssa):
        ceiling = _custom(slip, "custom_zimbabwe_nssa_ceiling", nssa_ceiling(currency, exchange_rate))
        calculated_employee_nssa, calculated_employer_nssa = nssa_pobs(basic, ceiling)
        employee_nssa = employee_nssa or calculated_employee_nssa
        employer_nssa = employer_nssa or calculated_employer_nssa
    medical_employee = _custom(
        slip,
        "custom_zimbabwe_medical_employee",
        component_total(rows, "medical aid", "medical scheme", parentfield="deductions"),
    )
    medical_employer = _custom(
        slip,
        "custom_zimbabwe_medical_employer",
        component_total(rows, "medical aid", "medical scheme", parentfield="earnings"),
    )
    bonus = component_total(rows, "bonus", "performance award", parentfield="earnings")
    benefits = component_total(
        rows,
        "housing benefit",
        "motor vehicle benefit",
        "furniture benefit",
        "school fees benefit",
        "loan benefit",
        "data and airtime benefit",
        "benefit in kind",
        parentfield="earnings",
    )
    reimbursements = component_total(rows, "reimbursement", "expense reimbursement", parentfield="earnings")
    taxable_income = _custom(
        slip,
        "custom_zimbabwe_taxable_income",
        gross - reimbursements - employee_pension,
    )
    paye_before = _custom(slip, "custom_zimbabwe_paye_before_credits", calculate_tax(taxable_income, currency))
    credits = _custom(
        slip,
        "custom_zimbabwe_tax_credits",
        _custom(slip, "custom_zimbabwe_medical_credit", medical_employee * Decimal("0.50")),
    )
    paye = _custom(slip, "custom_zimbabwe_paye", max(paye_before - credits, ZERO))
    aids = _custom(slip, "custom_zimbabwe_aids_levy", calculate_aids_levy(paye))
    total_wage_base = gross + employer_pension + medical_employer + benefits
    apwcs_base = _custom(slip, "custom_zimbabwe_apwcs_base", total_wage_base)
    apwcs_rate = _custom(slip, "custom_zimbabwe_apwcs_rate", setting("default_apwcs_rate", ZERO))
    apwcs_premium = (apwcs_base * apwcs_rate / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
    zimdef_base = _custom(slip, "custom_zimbabwe_zimdef_base", total_wage_base)
    zimdef_levy = (zimdef_base * Decimal("0.01")).quantize(CENT, rounding=ROUND_HALF_UP)
    standards_base = _custom(slip, "custom_zimbabwe_standards_base", total_wage_base)
    standards_levy = (standards_base * Decimal("0.005")).quantize(CENT, rounding=ROUND_HALF_UP)
    return SlipAmounts(
        gross=gross,
        taxable_income=taxable_income,
        paye_before_credits=paye_before,
        credits=credits,
        paye=paye,
        aids_levy=aids,
        basic=basic,
        employee_pension=employee_pension,
        employer_pension=employer_pension,
        employee_nssa=employee_nssa,
        employer_nssa=employer_nssa,
        medical_employee=medical_employee,
        medical_employer=medical_employer,
        medical_credit=_custom(slip, "custom_zimbabwe_medical_credit", medical_employee * Decimal("0.50")),
        bonus=bonus,
        benefits=benefits,
        reimbursements=reimbursements,
        zimdef_base=zimdef_base,
        standards_base=standards_base,
        apwcs_base=apwcs_base,
        apwcs_rate=apwcs_rate,
    )


def get_slips(filters: dict[str, Any]) -> list[Any]:
    conditions: dict[str, Any] = {"docstatus": 1}
    if filters.get("company"):
        conditions["company"] = filters["company"]
    if filters.get("employee"):
        conditions["employee"] = filters["employee"]
    if filters.get("payroll_entry"):
        conditions["payroll_entry"] = filters["payroll_entry"]
    if filters.get("from_date") and filters.get("to_date"):
        conditions["posting_date"] = ["between", [filters["from_date"], filters["to_date"]]]
    return frappe.get_all(
        "Salary Slip",
        filters=conditions,
        fields=[
            "name",
            "employee",
            "employee_name",
            "company",
            "posting_date",
            "start_date",
            "end_date",
            "currency",
            "gross_pay",
            "net_pay",
            "total_deduction",
            "payroll_entry",
        ],
        order_by="posting_date asc, employee asc",
    )


def rows_for_slips(filters: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for slip in get_slips(filters):
        amounts = derive_slip_amounts(slip)
        currency = getattr(slip, "currency", None) or "ZWG"
        if filters.get("currency") and currency != filters["currency"]:
            continue
        result.append(
            {
                "slip": slip,
                "amounts": amounts,
                "currency": currency,
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "posting_date": slip.posting_date,
            }
        )
    return result


def report_filters() -> list[dict[str, Any]]:
    return [
        {"fieldname": "company", "label": "Company", "fieldtype": "Link", "options": "Company", "reqd": 1},
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "reqd": 1},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "reqd": 1},
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee"},
        {"fieldname": "payroll_entry", "label": "Payroll Entry", "fieldtype": "Link", "options": "Payroll Entry"},
        {"fieldname": "currency", "label": "Currency", "fieldtype": "Select", "options": "\nZWG\nUSD"},
    ]
