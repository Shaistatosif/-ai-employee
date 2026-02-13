"""
Odoo Community integration for Personal AI Employee System.

Connects to Odoo Community Edition via XML-RPC API for:
- Creating invoices
- Logging expenses
- Checking account balances
- Creating contacts

All financial actions require HITL approval.
Odoo Community is self-hosted and free.
"""

import logging
import re
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from typing import Optional

from actions.base_action import BaseAction, ActionResult, ActionStatus
from config import settings

logger = logging.getLogger(__name__)


class OdooClient:
    """
    Lightweight Odoo XML-RPC client.

    Connects to Odoo Community Edition's standard XML-RPC endpoints:
    - /xmlrpc/2/common (authentication)
    - /xmlrpc/2/object (CRUD operations)
    """

    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self._uid: Optional[int] = None
        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def authenticate(self) -> bool:
        """Authenticate with Odoo and get user ID."""
        try:
            self._uid = self._common.authenticate(
                self.db, self.username, self.password, {}
            )
            return self._uid is not None and self._uid > 0
        except Exception as e:
            logger.error(f"Odoo authentication failed: {e}")
            return False

    @property
    def uid(self) -> int:
        if not self._uid:
            if not self.authenticate():
                raise RuntimeError("Odoo authentication failed")
        return self._uid

    def execute(self, model: str, method: str, *args, **kwargs):
        """Execute an Odoo model method."""
        return self._models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )

    def create(self, model: str, values: dict) -> int:
        """Create a record."""
        return self.execute(model, "create", [values])

    def search_read(self, model: str, domain: list, fields: list, limit: int = 10) -> list:
        """Search and read records."""
        return self.execute(
            model, "search_read", domain,
            fields=fields, limit=limit
        )


def _get_odoo_client() -> Optional[OdooClient]:
    """Get configured Odoo client or None if not configured."""
    url = settings.odoo_url
    db = settings.odoo_db
    username = settings.odoo_username
    password = settings.odoo_password

    if not all([url, db, username, password]):
        return None

    return OdooClient(url, db, username, password)


class OdooInvoiceAction(BaseAction):
    """
    Creates invoices in Odoo Community.

    HITL: All financial actions require approval.
    """

    def __init__(self):
        super().__init__(name="odoo_invoice")

    def can_handle(self, task_data: dict) -> bool:
        task_type = task_data.get("type", "").lower()
        if task_type in ("invoice", "odoo_invoice", "create_invoice"):
            return True
        body = task_data.get("body", "").lower()
        if "invoice" in body and ("odoo" in body or "create" in body):
            return True
        return False

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        logger.info(f"Creating Odoo invoice for: {task_path.name}")

        # Extract invoice data
        invoice = self._extract_invoice_data(task_data)

        if not invoice.get("partner"):
            return ActionResult(
                status=ActionStatus.FAILED,
                message="Missing partner/customer name",
                error="Invoice requires a partner (customer) name",
            )

        # Dry run check
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create invoice in Odoo:")
            logger.info(f"  Partner: {invoice['partner']}")
            logger.info(f"  Amount: ${invoice['amount']}")

            result = ActionResult(
                status=ActionStatus.SKIPPED,
                message=f"[DRY RUN] Invoice for {invoice['partner']} (${invoice['amount']}) prepared",
                data=invoice,
            )
            self._log_execution(task_path, result, invoice)
            return result

        # Try Odoo connection
        client = _get_odoo_client()
        if not client:
            # Fallback: create invoice draft in vault
            return self._create_invoice_draft(invoice, task_path)

        try:
            if not client.authenticate():
                return self._create_invoice_draft(invoice, task_path)

            # Create partner if needed
            partners = client.search_read(
                "res.partner",
                [["name", "=", invoice["partner"]]],
                ["id", "name"],
                limit=1,
            )

            if partners:
                partner_id = partners[0]["id"]
            else:
                partner_id = client.create("res.partner", {
                    "name": invoice["partner"],
                    "is_company": True,
                })

            # Create invoice
            invoice_id = client.create("account.move", {
                "move_type": "out_invoice",
                "partner_id": partner_id,
                "invoice_line_ids": [(0, 0, {
                    "name": invoice.get("description", "Service"),
                    "quantity": 1,
                    "price_unit": invoice["amount"],
                })],
            })

            result = ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Invoice created in Odoo (ID: {invoice_id})",
                data={"odoo_invoice_id": invoice_id, **invoice},
            )
            self._log_execution(task_path, result, invoice)
            return result

        except Exception as e:
            logger.error(f"Odoo invoice creation failed: {e}")
            return self._create_invoice_draft(invoice, task_path)

    def _extract_invoice_data(self, task_data: dict) -> dict:
        """Extract invoice fields from task data."""
        body = task_data.get("body", "")
        return {
            "partner": task_data.get("partner") or task_data.get("customer") or self._extract_field(body, "Partner|Customer|Client|Bill To"),
            "amount": task_data.get("amount") or self._extract_amount(body),
            "description": task_data.get("description") or task_data.get("title", "Service"),
            "due_date": task_data.get("due_date", ""),
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract a field value from text."""
        match = re.search(rf"(?:{pattern}):\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_amount(self, text: str) -> float:
        """Extract monetary amount from text."""
        amounts = re.findall(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        if amounts:
            return float(amounts[0].replace(",", ""))
        return 0.0

    def _create_invoice_draft(self, invoice: dict, task_path: Path) -> ActionResult:
        """Fallback: create invoice draft in vault when Odoo is unavailable."""
        drafts_path = settings.drafts_path / "Invoices"
        drafts_path.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        filename = f"invoice_{now.strftime('%Y%m%d_%H%M%S')}_{invoice.get('partner', 'unknown')}.md"
        draft_path = drafts_path / filename

        content = f"""---
type: odoo_invoice
status: draft
created: '{now.isoformat()}'
partner: '{invoice.get("partner", "")}'
amount: {invoice.get("amount", 0)}
requires_approval: true
---

# Invoice Draft

**Partner/Customer**: {invoice.get("partner", "N/A")}
**Amount**: ${invoice.get("amount", 0):.2f}
**Description**: {invoice.get("description", "Service")}
**Due Date**: {invoice.get("due_date", "N/A")}

---

## Instructions

Odoo is not configured or unavailable. To process this invoice:

1. Log into Odoo Community at your self-hosted instance
2. Create the invoice manually with the details above
3. Or configure ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD in .env

---

*Draft created by AI Employee System*
"""

        draft_path.write_text(content, encoding="utf-8")

        result = ActionResult(
            status=ActionStatus.SUCCESS,
            message=f"Invoice draft created (Odoo unavailable): {draft_path.name}",
            data={"draft_path": str(draft_path), **invoice},
        )
        self._log_execution(task_path, result, {"draft_path": str(draft_path)})
        return result


class OdooExpenseAction(BaseAction):
    """
    Logs expenses in Odoo Community.

    HITL: All financial actions require approval.
    """

    def __init__(self):
        super().__init__(name="odoo_expense")

    def can_handle(self, task_data: dict) -> bool:
        task_type = task_data.get("type", "").lower()
        if task_type in ("expense", "odoo_expense", "log_expense"):
            return True
        body = task_data.get("body", "").lower()
        if "expense" in body and ("log" in body or "record" in body or "odoo" in body):
            return True
        return False

    def execute(self, task_data: dict, task_path: Path) -> ActionResult:
        logger.info(f"Logging Odoo expense for: {task_path.name}")

        body = task_data.get("body", "")
        expense = {
            "name": task_data.get("title") or task_data.get("description", "Expense"),
            "amount": task_data.get("amount") or self._extract_amount(body),
            "category": task_data.get("category", "General"),
            "date": task_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        }

        if self.dry_run:
            result = ActionResult(
                status=ActionStatus.SKIPPED,
                message=f"[DRY RUN] Expense ${expense['amount']} ({expense['name']}) prepared",
                data=expense,
            )
            self._log_execution(task_path, result, expense)
            return result

        client = _get_odoo_client()
        if not client:
            return self._create_expense_draft(expense, task_path)

        try:
            if not client.authenticate():
                return self._create_expense_draft(expense, task_path)

            expense_id = client.create("hr.expense", {
                "name": expense["name"],
                "total_amount": expense["amount"],
                "date": expense["date"],
            })

            result = ActionResult(
                status=ActionStatus.SUCCESS,
                message=f"Expense logged in Odoo (ID: {expense_id})",
                data={"odoo_expense_id": expense_id, **expense},
            )
            self._log_execution(task_path, result, expense)
            return result

        except Exception as e:
            logger.error(f"Odoo expense creation failed: {e}")
            return self._create_expense_draft(expense, task_path)

    def _extract_amount(self, text: str) -> float:
        amounts = re.findall(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        return float(amounts[0].replace(",", "")) if amounts else 0.0

    def _create_expense_draft(self, expense: dict, task_path: Path) -> ActionResult:
        """Fallback: create expense draft in vault."""
        drafts_path = settings.drafts_path / "Expenses"
        drafts_path.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        filename = f"expense_{now.strftime('%Y%m%d_%H%M%S')}.md"
        draft_path = drafts_path / filename

        content = f"""---
type: odoo_expense
status: draft
created: '{now.isoformat()}'
amount: {expense.get("amount", 0)}
category: '{expense.get("category", "General")}'
requires_approval: true
---

# Expense Record

**Description**: {expense.get("name", "N/A")}
**Amount**: ${expense.get("amount", 0):.2f}
**Category**: {expense.get("category", "General")}
**Date**: {expense.get("date", "N/A")}

---

## Instructions

Odoo is not configured. Configure ODOO_URL in .env to auto-log expenses.

---

*Draft created by AI Employee System*
"""

        draft_path.write_text(content, encoding="utf-8")

        result = ActionResult(
            status=ActionStatus.SUCCESS,
            message=f"Expense draft created (Odoo unavailable): {draft_path.name}",
            data={"draft_path": str(draft_path), **expense},
        )
        self._log_execution(task_path, result, {"draft_path": str(draft_path)})
        return result
