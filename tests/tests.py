# coding: utf-8
import logging
import yaml

from tapioca_yandex_direct import YandexDirect, GetTokenYandexDirect

logging.basicConfig(level=logging.DEBUG)

with open("../config.yml", "r") as stream:
    data_loaded = yaml.safe_load(stream)

ACCESS_TOKEN = data_loaded["token"]
CLIENT_ID = data_loaded["client_id"]

api = YandexDirect(
    access_token=ACCESS_TOKEN, retry_request_if_limit=False, is_sandbox=True
)


def test_get_campaigns():
    r = api.campaigns().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id", "Name", "State", "Status", "Type"],
                "Page": {"Limit": 100},
            },
        }
    )
    print(r)


def test_transform():
    r = api.campaigns().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id"],
                "Page": {"Limit": 100},
            },
        }
    )
    print(r().transform())


def test_get_bids():
    r = api.bids().post(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {"CampaignIds": ["45575727"]},
                "FieldNames": [
                    "CampaignId",
                    "AdGroupId",
                    "KeywordId",
                    "ServingStatus",
                    "Bid",
                    "ContextBid",
                    "StrategyPriority",
                    "CompetitorsBids",
                    "SearchPrices",
                    "ContextCoverage",
                    "MinSearchPrice",
                    "CurrentSearchPrice",
                    "AuctionBids",
                ],
            },
        }
    )
    print(r)


def test_get_light_bids():
    r = api.bids().post(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {
                    # "AdGroupIds": ["1234567"],
                    "CampaignIds": [
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                        "45575727",
                    ]
                },
                "FieldNames": [
                    "CampaignId",
                    "AdGroupId",
                    "KeywordId",
                    "Bid",
                    "ContextBid",
                    "ContextCoverage",
                    "CurrentSearchPrice",
                    "AuctionBids",
                ],
            },
        }
    )
    print(r)


def test_resume_campaigns():
    r = api.campaigns().post(
        data={"method": "resume", "params": {"SelectionCriteria": {"Ids": ["320389"]}}}
    )
    print(r)


def test_get_keywords():
    r = api.keywords().get(
        data={
            "method": "get",
            "params": {
                "SelectionCriteria": {"Ids": ["16837839710"]},
                "FieldNames": ["Id", "Keyword", "State", "Status", "Bid", "ContextBid"],
                # "Page": {"Limit": 1},
            },
        }
    )
    print(r)


def test_keywordbids():
    r = api.keywordbids().post(
        data={
            "method": "set",
            "params": {
                "KeywordBids": [{"KeywordId": 16837839710, "SearchBid": 0.33 * 1000000}]
            },
        }
    )
    print(r)


def test_get_debugtoken():
    api = GetTokenYandexDirect()
    api.debugtoken(client_id=CLIENT_ID).open_in_browser()
