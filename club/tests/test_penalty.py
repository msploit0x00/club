# Copyright (c) 2026, ds and Contributors
"""Late payment penalty on subscription invoices (club.penalty), added on submit.

Run:
    CI=1 bench --site theclub.local run-tests --module club.tests.test_penalty --skip-test-records --skip-before-tests
"""
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

CUSTOMER = "RENT-PAY-2023-00022"  # subscription ACC-SUB-2023-00054: grace 7, every 7, 1%
ITEM = "ايجار المحل"


class TestPenalty(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Customer", CUSTOMER) or not frappe.db.exists("Item", ITEM):
			self.skipTest("needs the club rent customer and item")
		self.sub = frappe.db.get_value("Subscription", {"party": CUSTOMER},
									   ["penality_account", "penalty_tax_account"], as_dict=True)
		self.patch_today = mock.patch("club.penalty.today", return_value="2026-11-25")
		self.patch_today.start()
		self.addCleanup(self.patch_today.stop)
		self.addCleanup(frappe.db.rollback)

	def invoice(self, posting="2026-10-01", from_date=True, **values):
		si = frappe.get_doc({
			"doctype": "Sales Invoice", "customer": CUSTOMER, "company": "The Club",
			"set_posting_time": 1, "posting_date": posting, "due_date": add_days(posting, 30),
			"from_date": posting if from_date else None, "to_date": add_days(posting, 29) if from_date else None,
			"items": [{"item_code": ITEM, "qty": 1, "rate": 1000}],
			"taxes_and_charges": None, "taxes": [], **values,
		})
		si.flags.ignore_permissions = True
		si.insert()
		return si

	def penalty_rows(self, si):
		return [t for t in si.taxes if t.account_head == self.sub.penality_account]

	def test_late_invoice_gets_the_penalty_on_submit(self):
		si = self.invoice()
		self.assertFalse(self.penalty_rows(si), "no penalty on save")
		si.submit()
		si.reload()
		rows = self.penalty_rows(si)
		# 2026-10-01 + 7 grace = 2026-10-08; 48 days to 2026-11-25; ceil(48/7) = 7 -> 7% of 1000
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].tax_amount, 70)
		self.assertEqual(frappe.utils.flt(si.penality_ratio), 7)
		self.assertEqual(si.grand_total, 1070)
		self.assertEqual(sum(p.payment_amount for p in si.payment_schedule), si.grand_total)

	def test_within_the_grace_no_penalty(self):
		si = self.invoice(posting="2026-11-20")
		si.submit()
		self.assertFalse(self.penalty_rows(si))
		self.assertEqual(si.grand_total, 1000)

	def test_invoice_without_from_date_is_not_a_subscription_invoice(self):
		si = self.invoice(from_date=False)
		si.submit()
		self.assertFalse(self.penalty_rows(si))

	def test_amended_invoice_does_not_count_the_penalty_twice(self):
		si = self.invoice()
		si.append("taxes", {"charge_type": "Actual", "account_head": self.sub.penality_account,
							"description": "old penalty", "tax_amount": 999,
							"cost_center": frappe.get_cached_value("Company", "The Club", "cost_center")})
		si.save()
		si.submit()
		rows = self.penalty_rows(si)
		self.assertEqual([r.tax_amount for r in rows], [70])

	def test_tax_on_the_penalty_when_set(self):
		tax_account = frappe.db.get_value("Account", {"company": "The Club", "is_group": 0, "account_type": "Tax"}, "name")
		if not tax_account:
			self.skipTest("no tax account")
		frappe.db.set_value("Subscription", {"party": CUSTOMER}, "penalty_tax_account", tax_account)
		self.sub.penalty_tax_account = tax_account
		si = self.invoice()
		si.submit()
		tax = [t for t in si.taxes if t.account_head == tax_account]
		self.assertEqual(len(tax), 1)
		# 14% of 70 = 9.8, rounded to the site's currency precision
		self.assertEqual(tax[0].tax_amount, frappe.utils.flt(9.8, tax[0].precision("tax_amount")))
		self.assertEqual(si.grand_total, frappe.utils.flt(1070 + tax[0].tax_amount, si.precision("grand_total")))
