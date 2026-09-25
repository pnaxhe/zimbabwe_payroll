from zimbabwe_payroll.utils.reporting import columns
from zimbabwe_payroll.utils.statutory import money, report_filters, rows_for_slips, setting


def execute(filters=None):
    filters = filters or {}
    data = []
    for row in rows_for_slips(filters):
        slip = row["slip"]
        zig_amount = money(getattr(slip, "custom_zimbabwe_zig_amount", 0))
        usd_amount = money(getattr(slip, "custom_zimbabwe_usd_amount", 0))
        exchange_rate = money(getattr(slip, "custom_zimbabwe_exchange_rate", 0))
        zig_usd = (zig_amount / exchange_rate) if exchange_rate else money(0)
        combined = zig_usd + usd_amount
        data.append(
            {
                "employee": row["employee"],
                "employee_name": row["employee_name"],
                "posting_date": row["posting_date"],
                "zig_amount": zig_amount,
                "exchange_rate": exchange_rate,
                "zig_usd_equivalent": zig_usd,
                "usd_amount": usd_amount,
                "combined_usd_taxable": combined,
                "paye": row["amounts"].paye,
                "aids_levy": row["amounts"].aids_levy,
                "total_tax": row["amounts"].paye + row["amounts"].aids_levy,
            }
        )
    return (
        columns(
            [
                ("Employee", "employee", "Link", 120),
                ("Employee Name", "employee_name", "Data", 170),
                ("Posting Date", "posting_date", "Date", 95),
                ("ZiG/ZWG Amount", "zig_amount", "Currency", 110),
                ("Rate (ZiG/USD)", "exchange_rate", "Float", 100),
                ("ZiG/ZWG in USD", "zig_usd_equivalent", "Currency", 110),
                ("USD Amount", "usd_amount", "Currency", 100),
                ("Combined USD Taxable", "combined_usd_taxable", "Currency", 125),
                ("PAYE", "paye", "Currency", 95),
                ("AIDS Levy", "aids_levy", "Currency", 95),
                ("Total Tax", "total_tax", "Currency", 100),
            ]
        ),
        data,
    )


def get_filters():
    return report_filters()
