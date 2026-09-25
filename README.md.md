# Zimbabwe Payroll for ERPNext

Installable Frappe/ERPNext v16 app for Zimbabwe payroll statutory calculations and reports.

This package is deliberately separate from the POS app found in the workspace. It reads submitted `Salary Slip` records and exposes Script Reports for:

1. PAYE and AIDS Levy register
2. PAYE monthly remittance summary
3. NSSA Pension and Other Benefits Scheme (POBS)
4. NSSA Accident Prevention and Workers Compensation Scheme (APWCS/WCIF)
5. ZIMDEF / Manpower Development Fund
6. Standards Development Levy
7. Medical Aid and Pension schedule
8. Dual-currency reconciliation
9. Annual ITF16 export
10. Company Contributions Summary

## Install

```bash
bench get-app /path/to/zimbabwe_payroll_app
bench --site <site> install-app zimbabwe_payroll
bench --site <site> migrate
```

The app is compatible with Frappe/ERPNext 16. It does not alter core ERPNext payroll calculation. It reports from submitted Salary Slips and can be extended with hooks or custom fields.

## Required payroll configuration

The report engine first uses the following optional custom fields on `Salary Slip` where present, and otherwise derives values from salary components:

- `custom_zimbabwe_paye`
- `custom_zimbabwe_paye_before_credits`
- `custom_zimbabwe_tax_credits`
- `custom_zimbabwe_taxable_income`
- `custom_zimbabwe_medical_expenses`
- `custom_zimbabwe_medical_credit`
- `custom_zimbabwe_pension_employee`
- `custom_zimbabwe_pension_employer`
- `custom_zimbabwe_nssa_basic`
- `custom_zimbabwe_zig_amount`
- `custom_zimbabwe_usd_amount`
- `custom_zimbabwe_exchange_rate`
- `custom_zimbabwe_apwcs_rate`

Employer-side values are kept separate from employee deductions. The Company
Contributions Summary reports employer NSSA, employer pension, employer medical
aid, APWCS/WCIF, ZIMDEF, Standards Development Levy and the total company
contribution cost per employee and currency.

Recommended salary-component names include `Basic`, `Pension`, `NSSA`, `Medical Aid`, `PAYE`, `AIDS Levy`, `Bonus`, `Housing Benefit`, `Motor Vehicle Benefit`, `Data and Airtime Benefit`, and `Reimbursement`. Component matching is case-insensitive and also uses abbreviations.

## Statutory controls

The default reference configuration uses:

- USD monthly PAYE bands: 0–100 at 0%; 100.01–300 at 20%; 300.01–1,000 at 25%; 1,000.01–2,000 at 30%; 2,000.01–3,000 at 35%; above 3,000 at 40%.
- ZiG/ZWG monthly PAYE bands: 0–2,800 at 0%; 2,800.01–8,400 at 20%; 8,400.01–28,000 at 25%; 28,000.01–56,000 at 30%; 56,000.01–84,000 at 35%; above 84,000 at 40%.
- AIDS Levy: 3% of PAYE after credits.
- NSSA POBS: 4.5% employee and 4.5% employer, capped by the configured insurable-earnings ceiling.
- ZIMDEF: 1% of total gross wage bill.
- Standards Development Levy: 0.5% of total remuneration.

The engine calculates employer NSSA at 4.5% of basic salary subject to the
configured ceiling when no employer NSSA component is present on the Salary
Slip. Employer pension and employer medical aid are read from earnings
components or their explicit custom fields. APWCS/WCIF, ZIMDEF and Standards
Development Levy are calculated as employer-only obligations.

Rates and thresholds are intentionally configurable. Update the reference tables when ZIMRA, NSSA or the relevant Finance Act changes. The bonus exemption is not hard-coded because current guidance can differ by effective notice.

## Report filters

Every report supports:

- Company
- From Date
- To Date
- Currency where applicable
- Employee where applicable
- Payroll Entry where applicable

## Important implementation note

This code is a statutory-reporting layer, not legal advice. Before production use, reconcile each report against the current ZIMRA, NSSA, ZIMDEF and Standards Development Levy notices and obtain a payroll test sign-off.
