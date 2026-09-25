from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from .statutory import (
    calculate_aids_levy,
    money,
    nssa_pobs,
    nssa_ceiling,
    report_filters,
    rows_for_slips,
    setting,
)


def columns(names: list[tuple[str, str, str, int]]) -> list[dict[str, Any]]:
    return [
        {"label": label, "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
        for label, fieldname, fieldtype, width in names
    ]


def base_columns() -> list[dict[str, Any]]:
    return columns(
        [
            ("Employee", "employee", "Link", 120),
            ("Employee Name", "employee_name", "Data", 170),
            ("Posting Date", "posting_date", "Date", 95),
            ("Currency", "currency", "Data", 70),
        ]
    )


def report_data(filters: dict[str, Any], kind: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = rows_for_slips(filters)
    out: list[dict[str, Any]] = []
    for row in rows:
        a = row["amounts"]
        if kind == "paye":
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "gross_remuneration": a.gross,
                    "taxable_income": a.taxable_income,
                    "paye_before_credits": a.paye_before_credits,
                    "tax_credits": a.credits,
                    "paye": a.paye,
                    "aids_levy": a.aids_levy,
                    "total_paye_aids": a.paye + a.aids_levy,
                    "employee_nssa": a.employee_nssa,
                    "employee_pension": a.employee_pension,
                    "net_pay": getattr(row["slip"], "net_pay", 0),
                }
            )
        elif kind == "nssa_pobs":
            exchange_rate = getattr(row["slip"], "custom_zimbabwe_exchange_rate", None)
            ceiling = nssa_ceiling(row["currency"], exchange_rate)
            employee, employer = nssa_pobs(a.basic, ceiling)
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "basic_salary": a.basic,
                    "insurable_earnings": min(a.basic, money(ceiling)),
                    "employee_contribution": a.employee_nssa or employee,
                    "employer_contribution": a.employer_nssa or employer,
                    "total_contribution": (a.employee_nssa or employee) + (a.employer_nssa or employer),
                }
            )
        elif kind == "apwcs":
            premium = (a.apwcs_base * a.apwcs_rate / Decimal("100")).quantize(Decimal("0.01"))
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "insurable_wage": a.apwcs_base,
                    "apwcs_rate": a.apwcs_rate,
                    "premium": premium,
                }
            )
        elif kind == "zimdef":
            levy = (a.zimdef_base * Decimal("0.01")).quantize(Decimal("0.01"))
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "gross_wage_bill": a.zimdef_base,
                    "zimdef_rate": Decimal("1.00"),
                    "zimdef_levy": levy,
                }
            )
        elif kind == "standards":
            levy = (a.standards_base * Decimal("0.005")).quantize(Decimal("0.01"))
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "gross_remuneration": a.standards_base,
                    "standards_rate": Decimal("0.50"),
                    "standards_levy": levy,
                }
            )
        elif kind == "medical":
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "employee_medical": a.medical_employee,
                    "employer_medical": a.medical_employer,
                    "employee_pension": a.employee_pension,
                    "employer_pension": a.employer_pension,
                    "medical_credit": a.medical_credit,
                }
            )
        elif kind == "company":
            apwcs = (a.apwcs_base * a.apwcs_rate / Decimal("100")).quantize(Decimal("0.01"))
            zimdef = (a.zimdef_base * Decimal("0.01")).quantize(Decimal("0.01"))
            standards = (a.standards_base * Decimal("0.005")).quantize(Decimal("0.01"))
            total_company = (
                a.employer_nssa
                + a.employer_pension
                + a.medical_employer
                + apwcs
                + zimdef
                + standards
            )
            out.append(
                {
                    "employee": row["employee"],
                    "employee_name": row["employee_name"],
                    "posting_date": row["posting_date"],
                    "currency": row["currency"],
                    "employer_nssa": a.employer_nssa,
                    "employer_pension": a.employer_pension,
                    "employer_medical": a.medical_employer,
                    "apwcs_wcif": apwcs,
                    "zimdef_levy": zimdef,
                    "standards_levy": standards,
                    "total_company_contributions": total_company,
                }
            )
    if kind == "paye":
        cols = base_columns() + columns(
            [
                ("Gross Remuneration", "gross_remuneration", "Currency", 120),
                ("Taxable Income", "taxable_income", "Currency", 110),
                ("PAYE Before Credits", "paye_before_credits", "Currency", 120),
                ("Tax Credits", "tax_credits", "Currency", 100),
                ("PAYE", "paye", "Currency", 95),
                ("AIDS Levy", "aids_levy", "Currency", 95),
                ("PAYE + AIDS", "total_paye_aids", "Currency", 110),
                ("Employee NSSA", "employee_nssa", "Currency", 110),
                ("Employee Pension", "employee_pension", "Currency", 115),
                ("Net Pay", "net_pay", "Currency", 110),
            ]
        )
    elif kind == "nssa_pobs":
        cols = base_columns() + columns(
            [
                ("Basic Salary", "basic_salary", "Currency", 110),
                ("Insurable Earnings", "insurable_earnings", "Currency", 120),
                ("Employee 4.5%", "employee_contribution", "Currency", 115),
                ("Employer 4.5%", "employer_contribution", "Currency", 115),
                ("Total NSSA", "total_contribution", "Currency", 105),
            ]
        )
    elif kind == "apwcs":
        cols = base_columns() + columns(
            [
                ("Insurable Wage", "insurable_wage", "Currency", 115),
                ("APWCS Rate %", "apwcs_rate", "Percent", 90),
                ("Premium", "premium", "Currency", 100),
            ]
        )
    elif kind == "zimdef":
        cols = base_columns() + columns(
            [
                ("Gross Wage Bill", "gross_wage_bill", "Currency", 120),
                ("ZIMDEF Rate %", "zimdef_rate", "Percent", 100),
                ("ZIMDEF Levy", "zimdef_levy", "Currency", 105),
            ]
        )
    elif kind == "standards":
        cols = base_columns() + columns(
            [
                ("Gross Remuneration", "gross_remuneration", "Currency", 120),
                ("Standards Rate %", "standards_rate", "Percent", 110),
                ("Standards Levy", "standards_levy", "Currency", 110),
            ]
        )
    else:
        cols = base_columns() + columns(
            [
                ("Employee Medical", "employee_medical", "Currency", 115),
                ("Employer Medical", "employer_medical", "Currency", 115),
                ("Employee Pension", "employee_pension", "Currency", 115),
                ("Employer Pension", "employer_pension", "Currency", 115),
                ("Medical Credit", "medical_credit", "Currency", 110),
            ]
        )
    if kind == "company":
        cols = base_columns() + columns(
            [
                ("Employer NSSA", "employer_nssa", "Currency", 110),
                ("Employer Pension", "employer_pension", "Currency", 115),
                ("Employer Medical", "employer_medical", "Currency", 115),
                ("APWCS/WCIF", "apwcs_wcif", "Currency", 105),
                ("ZIMDEF", "zimdef_levy", "Currency", 95),
                ("Standards Levy", "standards_levy", "Currency", 110),
                ("Total Company Contributions", "total_company_contributions", "Currency", 155),
            ]
        )
    return cols, out


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...], numeric_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        if key not in grouped:
            grouped[key] = {k: row.get(k) for k in keys}
            for field in numeric_fields:
                grouped[key][field] = Decimal("0")
        for field in numeric_fields:
            grouped[key][field] += money(row.get(field))
    return list(grouped.values())
