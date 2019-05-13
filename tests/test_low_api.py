# coding: utf-8

import yaml
from pandas import set_option

from tapioca_yadirect import Yadirect

set_option('display.max_columns', 100)
set_option('display.width', 1500)

with open("../config.yml", 'r') as stream:
    data_loaded = yaml.safe_load(stream)

ACCESS_TOKEN = data_loaded['token']

api = Yadirect(access_token=ACCESS_TOKEN, retry_request_if_limit=True, is_sandbox=True)


def test_campaigns():
    r = api.campaigns().get(
        data={
            "method": "get",
            "params": {"SelectionCriteria": {},
                       "FieldNames": ["Id", "Name", "State", "Status", "Type"],
                       "Page": {"Limit": 1}
                       }
        })
    print(r)
    # df = r().to_df()
    # print(len(df))
    # print(df)
