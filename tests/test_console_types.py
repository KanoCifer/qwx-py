"""console 的模型解析：字段、可选性与未知字段保留。"""

from __future__ import annotations

import json

from qwx.console.types import (
    AccruedCharges,
    APICount,
    EndpointFinance,
    EndpointStats,
    FinanceResult,
    PendingBill,
    ResourcePlan,
    SavingsPlan,
    StatsOptions,
    StatsResult,
)

FINANCE_BODY = json.dumps(
    {
        "metadata": {"tag": "2a9873efd0a6c75665dc4f6116b19bdf"},
        "asOf": "2024-04-03T17:13Z",
        "currency": "CNY",
        "balance": -17.54,
        "accruedCharges": {
            "previousDay": 28.92,
            "thisMonth": 113.12,
            "sinceLastBill": 113.12,
        },
        "pendingBills": [
            {
                "number": "20681CYX",
                "date": "2024-04-01T10:00Z",
                "type": "PayAsYouGo",
                "status": "unpaid",
                "amount": 535.1,
                "amountDue": 17.54,
                "dueDate": "2024-04-10T23:59Z",
            },
            {
                "number": "605D0FYX",
                "date": "2024-04-02T13:34Z",
                "type": "SavingsPlans",
                "status": "unpaid",
                "amount": 2000,
                "amountDue": 2000,
                "dueDate": "2024-04-30T12:59Z",
            },
        ],
        "availableSavingsPlans": [
            {
                "billNumber": "605D0FYX",
                "status": "pending",
                "term": "1",
                "commitments": 2000,
                "utilized": 0,
                "effectiveTime": "2024-04-30T13:00Z",
            }
        ],
        "availableResourcePlans": [
            {
                "billNumber": "613D1FYX",
                "status": "active",
                "requests": "1000000",
                "commitments": 2000,
                "utilized": 12,
                "effectiveTime": "2024-04-03T17:00Z",
            }
        ],
    }
)

STATS_BODY = json.dumps(
    {
        "metadata": {"tag": "dcd6183920ebf9f5aa3fd066ed68e61b"},
        "asOf": "2025-05-12T02:59Z",
        "success": [
            {"api": "Weather", "hours": [482, 475, 520]},
            {"api": "Geo", "hours": [20, 16, 0]},
        ],
        "errors": [{"api": "Weather", "hours": [3, 1, 4]}],
    }
)


def test_finance_result_parses_fields() -> None:
    got = FinanceResult.model_validate_json(FINANCE_BODY)

    assert got.metadata.tag == "2a9873efd0a6c75665dc4f6116b19bdf"
    assert got.as_of == "2024-04-03T17:13Z"
    assert got.currency == "CNY"
    assert got.balance == -17.54
    assert got.accrued_charges.previous_day == 28.92
    assert got.accrued_charges.this_month == 113.12
    assert got.accrued_charges.since_last_bill == 113.12

    assert len(got.pending_bills) == 2
    bill = got.pending_bills[0]
    assert bill.number == "20681CYX"
    assert bill.type == "PayAsYouGo"
    assert bill.status == "unpaid"
    assert bill.amount == 535.1
    assert bill.amount_due == 17.54
    assert bill.date == "2024-04-01T10:00Z"
    assert bill.due_date == "2024-04-10T23:59Z"

    assert len(got.available_savings_plans) == 1
    plan = got.available_savings_plans[0]
    assert plan.bill_number == "605D0FYX"
    assert plan.status == "pending"
    assert plan.term == "1"
    assert plan.commitments == 2000
    assert plan.utilized == 0
    assert plan.effective_time == "2024-04-30T13:00Z"

    assert len(got.available_resource_plans) == 1
    resource = got.available_resource_plans[0]
    assert resource.bill_number == "613D1FYX"
    assert resource.status == "active"
    # 上游给的是字符串 "1000000"，按数值用。
    assert int(resource.requests) == 1000000
    assert resource.commitments == 2000
    assert resource.utilized == 12
    assert resource.effective_time == "2024-04-03T17:00Z"


def test_finance_result_accepts_numeric_requests() -> None:
    got = ResourcePlan.model_validate({"requests": 1000000})
    assert got.requests == 1000000


def test_finance_result_missing_fields_fall_back_to_defaults() -> None:
    got = FinanceResult.model_validate_json("{}")

    assert got.metadata.tag == ""
    assert got.metadata.attributions == []
    assert got.as_of == ""
    assert got.currency == ""
    assert got.balance == 0.0
    assert got.accrued_charges == AccruedCharges()
    assert got.pending_bills == []
    assert got.available_savings_plans == []
    assert got.available_resource_plans == []


def test_pending_bill_missing_fields_fall_back_to_defaults() -> None:
    got = PendingBill.model_validate_json("{}")

    assert got.number == ""
    assert got.date == ""
    assert got.type == ""
    assert got.status == ""
    assert got.amount == 0.0
    assert got.amount_due == 0.0
    assert got.due_date == ""


def test_savings_plan_missing_fields_fall_back_to_defaults() -> None:
    got = SavingsPlan.model_validate_json("{}")

    assert got.bill_number == ""
    assert got.status == ""
    assert got.term == ""
    assert got.commitments == 0.0
    assert got.utilized == 0.0
    assert got.effective_time == ""


def test_stats_result_parses_fields() -> None:
    got = StatsResult.model_validate_json(STATS_BODY)

    assert got.metadata.tag == "dcd6183920ebf9f5aa3fd066ed68e61b"
    assert got.as_of == "2025-05-12T02:59Z"

    assert len(got.success) == 2
    assert got.success[0].api == "Weather"
    assert got.success[0].hours == [482, 475, 520]
    assert got.success[1].api == "Geo"

    assert len(got.errors) == 1
    assert got.errors[0].api == "Weather"
    assert got.errors[0].hours == [3, 1, 4]


def test_stats_result_missing_fields_fall_back_to_defaults() -> None:
    got = StatsResult.model_validate_json("{}")

    assert got.metadata.tag == ""
    assert got.as_of == ""
    assert got.success == []
    assert got.errors == []


def test_api_count_missing_fields_fall_back_to_defaults() -> None:
    got = APICount.model_validate_json("{}")

    assert got.api == ""
    assert got.hours == []


def test_unknown_fields_are_kept() -> None:
    got = StatsResult.model_validate(
        {
            "asOf": "2025-05-12T02:59Z",
            "newUpstreamField": "keep me",
            "success": [{"api": "Weather", "hours": [1], "extra": 2}],
        }
    )

    assert got.model_extra is not None
    assert got.model_extra["newUpstreamField"] == "keep me"
    assert got.success[0].model_extra is not None
    assert got.success[0].model_extra["extra"] == 2


def test_stats_options_defaults() -> None:
    opts = StatsOptions()
    assert opts.project == ""
    assert opts.credential == ""

    opts = StatsOptions(project="proj-1")
    assert opts.project == "proj-1"
    assert opts.credential == ""


def test_endpoint_constants_are_frozen() -> None:
    assert EndpointFinance == "finance/v1/summary"
    assert EndpointStats == "metrics/v1/stats"
