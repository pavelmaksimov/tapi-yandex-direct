# coding: utf-8
import datetime as dt
import logging

import yaml

from tapioca_yandex_direct import YandexDirect, GetTokenYandexDirect

logging.basicConfig(level=logging.DEBUG)

with open("../config.yml", "r") as stream:
    data_loaded = yaml.safe_load(stream)

ACCESS_TOKEN = data_loaded["token"]
CLIENT_ID = data_loaded["client_id"]

api = YandexDirect(
    access_token=ACCESS_TOKEN,
    retry_if_not_enough_units=False,
    is_sandbox=True,
    auto_request_generation=True,
    receive_all_objects=True
)


def test_get_campaigns():
    r = api.campaigns().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id", "Name", "State", "Status", "Type"],
                "Page": {"Limit": 2},
            },
        }
    )
    print(r)


def test_method_get_transform_result():
    r = api.campaigns().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id"],
                "Page": {"Limit": 3},
            },
        }
    )
    print(r().transform())


def test_method_add_transform_result():
    body = {
        "method": "add",
        "params": {
            "Campaigns": [
                {
                    "Name": "MyCampaignTest",
                    "StartDate": str(dt.datetime.now().date()),
                    "TextCampaign": {
                        "BiddingStrategy": {
                            "Search": {
                                "BiddingStrategyType": "HIGHEST_POSITION"
                            },
                            "Network": {
                                "BiddingStrategyType": "SERVING_OFF"
                            }
                        },
                        "Settings": []
                    }
                }
            ]
        }
    }
    r = api.campaigns().post(data=body)
    print(r().transform())


def test_get_debugtoken():
    api = GetTokenYandexDirect()
    api.debugtoken(client_id=CLIENT_ID).open_in_browser()
