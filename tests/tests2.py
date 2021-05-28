import datetime as dt
import logging

import yaml

from tapi_yandex_direct import YandexDirect

logging.basicConfig(level=logging.DEBUG)

with open("../config.yml", "r") as stream:
    data_loaded = yaml.safe_load(stream)

ACCESS_TOKEN = data_loaded["token"]
CLIENT_ID = data_loaded["client_id"]

api = YandexDirect(
    access_token=ACCESS_TOKEN,
    is_sandbox=False,
    retry_if_not_enough_units=False,
    retry_if_exceeded_limit=False,
    retries_if_server_error=5,
    # Параметры для ресурса Reports
    processing_mode="offline",
    wait_report=True,
    return_money_in_micros=True,
    skip_report_header=True,
    skip_column_header=False,
    skip_report_summary=True,
)


# def test_get_debugtoken():
#     api.debugtoken(client_id=CLIENT_ID).open_in_browser()


def test_get_clients():
    r = api.clients().post(
        data={
            "method": "get",
            "params": {
                "FieldNames": ["ClientId", "Login"],
            },
        }
    )
    print(r)
    print(r().extract())


def test_get_campaigns():
    campaigns = api.campaigns().post(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {"States": ["ON", "OFF"]},
                "FieldNames": ["Id", "Name", "State", "Status", "Type"],
            },
                "Page": {"Limit": 1000},
        }
    )
    print(campaigns)


def test_method_add():
    body = {
        "method": "add",
        "params": {
            "Campaigns": [
                {
                    "Name": "MyCampaignTest",
                    "StartDate": str(dt.datetime.now().date()),
                    "TextCampaign": {
                        "BiddingStrategy": {
                            "Search": {"BiddingStrategyType": "HIGHEST_POSITION"},
                            "Network": {"BiddingStrategyType": "SERVING_OFF"},
                        },
                        "Settings": [],
                    },
                }
            ]
        },
    }
    r = api.campaigns().post(data=body)
    print(r().extract())


def test_get_report():
    report = api.reports().post(
        data={
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Date", "CampaignId", "Clicks", "Cost"],
                "OrderBy": [{"Field": "Date"}],
                "ReportName": "Actual Data11111",
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "DateRangeType": "LAST_7_DAYS",
                "Format": "TSV",
                "IncludeVAT": "YES",
                "IncludeDiscount": "YES",
            }
        }
    )
    print(report.columns)
    print(report().to_values())
    print(report().to_lines())
    print(report().to_columns())


def test_get_report2():
    for i in range(7):
        r = api.reports().post(
            data={
                "params": {
                    "SelectionCriteria": {},
                    "FieldNames": ["Date", "CampaignId", "Clicks", "Cost"],
                    "OrderBy": [{"Field": "Date"}],
                    "ReportName": "Actual Data12 f 1" + str(i),
                    "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                    "DateRangeType": "LAST_WEEK",
                    "Format": "TSV",
                    "IncludeVAT": "YES",
                    "IncludeDiscount": "YES",
                }
            }
        )
        print(r().response.status_code)
