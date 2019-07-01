# coding: utf-8
import logging
import yaml
from pandas import set_option

from tapioca_yadirect import Yadirect

set_option("display.max_columns", 100)
set_option("display.width", 1500)

logging.basicConfig(level=logging.DEBUG)

with open("../config.yml", "r") as stream:
    data_loaded = yaml.safe_load(stream)

ACCESS_TOKEN = data_loaded["token"]

api = Yadirect(
    access_token=ACCESS_TOKEN, retry_request_if_limit=False, is_sandbox=False
)


def test_get_campaigns():
    r = api.campaigns().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id", "Name", "State", "Status", "Type"],
                "Page": {"Limit": 1},
            },
        }
    )
    print(r)


def test_get_bids():
    r = api.bids().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {"CampaignIds": ["320387"]},
                "FieldNames": ["KeywordId"],
            },
        }
    )
    print(r)


def test_resume_campaigns():
    r = api.campaigns().post(
        data={"method": "resume", "params": {"SelectionCriteria": {"Ids": ["320389"]}}}
    )
    print(r)
