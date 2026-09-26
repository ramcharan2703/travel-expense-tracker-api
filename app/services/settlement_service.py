from decimal import Decimal
from typing import Any
from pymongo.database import Database

from app.schemas.summary import (
    CategorySummary,
    MemberFinancialSummary,
    SettlementTransaction,
    TripSettlementResponse,
    TripSummaryResponse,
)
from app.services.trip_service import TripService
from app.utils.object_id import to_object_id


class SettlementService:
    @staticmethod
    def _to_decimal(val: Any) -> Decimal:
        """Helper to convert BSON Decimal128, float, or str to Python Decimal."""
        if hasattr(val, "to_decimal"):
            return val.to_decimal().quantize(Decimal("0.01"))
        return Decimal(str(val)).quantize(Decimal("0.01"))

    @classmethod
    def get_trip_summary(cls, db: Database, trip_id: str) -> TripSummaryResponse:
        trip = TripService.get_trip_doc(db, trip_id)
        trip_oid = to_object_id(trip_id)

        # Initialize members map
        members_map: dict[str, dict[str, Any]] = {
            m["id"]: {
                "name": m["name"],
                "paid": Decimal("0.00"),
                "share": Decimal("0.00"),
            }
            for m in trip.get("members", [])
        }

        # Aggregate from expenses
        cursor = db.expenses.find({"trip_id": trip_oid})
        total_trip_expenses = Decimal("0.00")
        total_expenses_count = 0
        category_map: dict[str, dict[str, Any]] = {}

        for exp in cursor:
            total_expenses_count += 1
            amt = cls._to_decimal(exp["amount"])
            total_trip_expenses += amt

            # Track payer
            payer_id = exp.get("paid_by")
            if payer_id and payer_id in members_map:
                members_map[payer_id]["paid"] += amt

            # Track shares
            for split in exp.get("split_shares", []):
                m_id = split.get("member_id")
                if m_id and m_id in members_map:
                    members_map[m_id]["share"] += cls._to_decimal(split["share"])

            # Track category
            cat = exp.get("category", "Other")
            if cat not in category_map:
                category_map[cat] = {"total": Decimal("0.00"), "count": 0}
            category_map[cat]["total"] += amt
            category_map[cat]["count"] += 1

        # Format members financial summary
        members_summary: list[MemberFinancialSummary] = []
        for m_id, info in members_map.items():
            paid = info["paid"]
            share = info["share"]
            balance = paid - share
            owes = max(Decimal("0.00"), -balance)
            receives = max(Decimal("0.00"), balance)

            members_summary.append(
                MemberFinancialSummary(
                    member_id=m_id,
                    member_name=info["name"],
                    total_paid=paid,
                    total_share=share,
                    balance=balance,
                    owes=owes,
                    receives=receives,
                )
            )

        # Format category breakdown
        category_breakdown: list[CategorySummary] = []
        for cat_name, cat_data in category_map.items():
            total = cat_data["total"]
            pct = (
                (total / total_trip_expenses * Decimal("100")).quantize(Decimal("0.01"))
                if total_trip_expenses > Decimal("0.00")
                else Decimal("0.00")
            )
            category_breakdown.append(
                CategorySummary(
                    category=cat_name,
                    total_amount=total,
                    count=cat_data["count"],
                    percentage=pct,
                )
            )

        category_breakdown.sort(key=lambda x: x.total_amount, reverse=True)

        return TripSummaryResponse(
            trip_id=str(trip["_id"]),
            trip_name=trip["name"],
            total_trip_expenses=total_trip_expenses,
            total_expenses_count=total_expenses_count,
            members_summary=members_summary,
            category_breakdown=category_breakdown,
        )

    @classmethod
    def get_trip_settlement(cls, db: Database, trip_id: str) -> TripSettlementResponse:
        summary = cls.get_trip_summary(db, trip_id)

        # Separate into debtors (balance < 0) and creditors (balance > 0)
        debtors: list[dict[str, Any]] = []
        creditors: list[dict[str, Any]] = []

        threshold = Decimal("0.005")
        for m in summary.members_summary:
            if m.balance < -threshold:
                debtors.append({"id": m.member_id, "name": m.member_name, "balance": m.balance})
            elif m.balance > threshold:
                creditors.append({"id": m.member_id, "name": m.member_name, "balance": m.balance})

        transactions: list[SettlementTransaction] = []

        # Min-cash-flow greedy debt settlement matching
        while debtors and creditors:
            # Sort debtors ascending (largest debt / most negative balance first)
            debtors.sort(key=lambda x: x["balance"])
            # Sort creditors descending (largest credit first)
            creditors.sort(key=lambda x: x["balance"], reverse=True)

            debtor = debtors[0]
            creditor = creditors[0]

            debtor_owes = -debtor["balance"]
            creditor_receives = creditor["balance"]

            transfer = min(debtor_owes, creditor_receives).quantize(Decimal("0.01"))

            if transfer > Decimal("0.00"):
                transactions.append(
                    SettlementTransaction(
                        debtor_id=debtor["id"],
                        debtor_name=debtor["name"],
                        creditor_id=creditor["id"],
                        creditor_name=creditor["name"],
                        amount=transfer,
                    )
                )

            debtor["balance"] += transfer
            creditor["balance"] -= transfer

            if debtor["balance"] >= -threshold:
                debtors.pop(0)
            if creditor["balance"] <= threshold:
                creditors.pop(0)

        return TripSettlementResponse(
            trip_id=str(summary.trip_id),
            trip_name=summary.trip_name,
            total_transactions=len(transactions),
            transactions=transactions,
        )
