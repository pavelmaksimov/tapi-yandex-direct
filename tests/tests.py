import logging

import responses

from tapi_yandex_direct import YandexDirect

logging.basicConfig(level=logging.DEBUG)

ACCESS_TOKEN = ""
CLIENT_ID = ""

client = YandexDirect(
    access_token=ACCESS_TOKEN,
    is_sandbox=False,
    retry_if_not_enough_units=False,
    retry_if_exceeded_limit=False,
    retries_if_server_error=5,
    # For Reports resource.
    processing_mode="offline",
    wait_report=True,
    return_money_in_micros=True,
    skip_report_header=True,
    skip_column_header=False,
    skip_report_summary=True,
)


@responses.activate
def test_sanity():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": []}},
        status=200,
    )

    result = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )
    assert result.data == {"result": {"Clients": []}}


@responses.activate
def test_extract():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": []}},
        status=200,
    )

    result = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )
    assert result().extract() == []


@responses.activate
def test_iter_items():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 1}, {"id": 2}], "LimitedBy": 1}},
        status=200,
    )

    clients = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )

    ids = []
    for item in clients().items():
        ids.append(item["id"])

    assert ids == [1, 2]


@responses.activate
def test_iter_pages_and_items():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 1}], "LimitedBy": 1}},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 2}]}},
        status=200,
    )

    clients = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )

    ids = []
    for page in clients().pages():
        for item in page().items():
            ids.append(item["id"])

    assert ids == [1, 2]


@responses.activate
def test_iter_items():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 1}], "LimitedBy": 1}},
        status=200,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/clients",
        json={"result": {"Clients": [{"id": 2}]}},
        status=200,
    )

    clients = client.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )

    ids = []
    for item in clients().iter_items():
        ids.append(item["id"])

    assert ids == [1, 2]


@responses.activate
def test_get_report():
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/reports",
        headers={"retryIn": "0"},
        status=202,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/reports",
        headers={"retryIn": "0"},
        status=202,
    )
    responses.add(
        responses.POST,
        "https://api.direct.yandex.com/json/v5/reports",
        body="col1\tcol2\nvalue1\tvalue2\nvalue10\tvalue20\n",
        status=200,
    )
    report = client.reports().post(
        data={
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Date", "CampaignId"],
                "OrderBy": [{"Field": "Date"}],
                "ReportName": "report name",
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "DateRangeType": "TODAY",
                "Format": "TSV",
                "IncludeVAT": "YES",
                "IncludeDiscount": "YES",
            }
        }
    )
    assert report.columns == ["col1", "col2"]
    assert report().to_values() == [["value1", "value2"], ["value10", "value20"]]
    assert report().to_lines() == ["value1\tvalue2", "value10\tvalue20"]
    assert report().to_columns() == [["value1", "value10"], ["value2", "value20"]]
    assert report().to_dicts() == [
        {"col1": "value1", "col2": "value2"},
        {"col1": "value10", "col2": "value20"},
    ]
