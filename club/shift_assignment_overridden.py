import frappe
from frappe.model.document import Document
from hrms.hr.doctype.shift_assignment.shift_assignment import ShiftAssignment

class Overlapping(Document):
    def validate_overlapping_shifts(self):
        print("nothing to do now")
