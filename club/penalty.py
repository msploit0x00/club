"""Late payment penalty on subscription invoices (shop rent, electricity ...), added on submit.

Moved from the Client Script "Sales Invoice-Form" (now disabled), where it never reached the
saved invoice: the Submit was sent before its five chained lookups finished. Running on the
server it works however the invoice is submitted (form, API, a subscription that submits).

Settings are on the customer's Subscription (custom fields of this app):
    gross_period        grace days after the posting date
    recursive_period    the penalty grows every N days after the grace
    penality_ratio      percent added per period
    penality_account    account of the penalty row
    penalty_tax_account optional: 14% on the penalty
Base of the penalty: the invoice rows whose item is a penalty item (is_penalty_item).
Formula (unchanged): ceil((today - (posting date + grace)) / every) x ratio, when the invoice is
submitted more than `grace` days after its posting date.
"""

import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

PENALTY_TAX_RATE = 14


def add_penalty_on_submit(doc, method=None):
	"""Sales Invoice before_validate: on submit only, before ERPNext computes the totals."""
	if doc.get("_action") != "submit" or doc.is_return or not doc.get("from_date") or not doc.customer:
		return
	sub = _subscription(doc.customer)
	if not sub:
		return
	grace = flt(sub.gross_period)
	every = flt(sub.recursive_period)
	if every <= 0 or not sub.penality_account:
		return

	# rows copied from an amended invoice are dropped first, so the penalty is never counted twice
	penalty_accounts = {sub.penality_account, sub.penalty_tax_account} - {None, ""}
	kept = [t for t in doc.get("taxes") or [] if t.account_head not in penalty_accounts]
	if len(kept) != len(doc.get("taxes") or []):
		doc.set("taxes", kept)
		for i, t in enumerate(doc.taxes, 1):
			t.idx = i
	doc.penality_ratio = 0

	submitted_on = getdate(today())
	if date_diff(submitted_on, doc.posting_date) <= grace:
		return
	penalty_start = add_days(doc.posting_date, cint(grace))
	ratio = math.ceil(date_diff(submitted_on, penalty_start) / every) * flt(sub.penality_ratio)
	base = sum(flt(i.amount) for i in doc.items if cint(i.get("is_penalty_item")))
	if ratio <= 0 or base <= 0:
		return

	cost_center = doc.get("cost_center") or frappe.get_cached_value("Company", doc.company, "cost_center")
	penalty_row = doc.append("taxes", {
		"charge_type": "Actual",
		"account_head": sub.penality_account,
		"description": sub.penality_account,
		"rate": ratio,
		"tax_amount": flt(ratio * base / 100, 2),
		"cost_center": cost_center,
	})
	if sub.penalty_tax_account:
		doc.append("taxes", {
			"charge_type": "On Previous Row Amount",
			"row_id": str(penalty_row.idx),
			"account_head": sub.penalty_tax_account,
			"description": sub.penalty_tax_account,
			"rate": PENALTY_TAX_RATE,
			"cost_center": cost_center,
		})
	doc.penality_ratio = ratio
	frappe.msgprint(
		_("A late payment penalty of {0}% was added: invoice date {1}, submitted on {2}.").format(
			ratio, frappe.format(doc.posting_date, "Date"), frappe.format(submitted_on, "Date")),
		indicator="orange", alert=True)


def _subscription(customer):
	"""The customer's subscription with its penalty settings (the newest one if there are several)."""
	rows = frappe.get_all(
		"Subscription",
		filters={"party_type": "Customer", "party": customer},
		fields=["name", "gross_period", "recursive_period", "penality_ratio", "penality_account", "penalty_tax_account"],
		order_by="creation desc",
		limit=1,
	)
	return rows[0] if rows else None
