# Python client for [API Yandex Direct](https://yandex.ru/dev/metrika/doc/api2/concept/about-docpage/)

![Supported Python Versions](https://img.shields.io/static/v1?label=python&message=>=3.6&color=green)
[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/vintasoftware/tapioca-wrapper/master/LICENSE)
[![Downloads](https://pepy.tech/badge/tapi-yandex-direct)](https://pepy.tech/project/tapi-yandex-direct)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>

## Installation

Prev version

    pip install --upgrade tapi-yandex-direct==2020.12.15

Last version. Has backward incompatible changes.

    pip install --upgrade tapi-yandex-direct==2021.5.29

## Examples

[Ipython Notebook](https://github.com/pavelmaksimov/tapi-yandex-direct/blob/master/examples.ipynb)


## Documentation
[Справка](https://yandex.ru/dev/direct/) Api Яндекс Директ


### Client params
```python
from tapi_yandex_direct import YandexDirect

ACCESS_TOKEN = "{your_access_token}"

client = YandexDirect(
    # Required parameters:

    access_token=ACCESS_TOKEN,
    # If you are making inquiries from an agent account, you must be sure to specify the account login.
    login="{login}",

    # Optional parameters:

    # Enable sandbox.
    is_sandbox=False,
    # Repeat request when units run out
    retry_if_not_enough_units=False,
    # The language in which the data for directories and errors will be returned.
    language="ru",
    # Repeat the request if the limits on the number of reports or requests are exceeded.
    retry_if_exceeded_limit=True,
    # Number of retries when server errors occur.
    retries_if_server_error=5
)
```

### Resource methods
```python
print(dir(client))
[
    "adextensions",
    "adgroups",
    "adimages",
    "ads",
    "agencyclients",
    "audiencetargets",
    "bidmodifiers",
    "bids",
    "businesses",
    "campaigns",
    "changes",
    "clients",
    "creatives",
    "debugtoken",
    "dictionaries",
    "dynamicads",
    "feeds",
    "keywordbids",
    "keywords",
    "keywordsresearch",
    "leads",
    "negativekeywordsharedsets",
    "reports",
    "retargeting",
    "sitelinks",
    "smartadtargets",
    "turbopages",
    "vcards",
]
```
or look into [resource mapping](tapi_yandex_direct/resource_mapping.py)

### Request

API requests are made over HTTPS using the POST method.
Input data structures are passed in the body of the request.

```python
import datetime as dt

# Get campaigns.
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)
print(campaigns)
# <TapiClient object
# {   'result': {   'Campaigns': [   {   'Id': 338157,
#                                        'Name': 'Test API Sandbox campaign 1'},
#                                    {   'Id': 338158,
#                                        'Name': 'Test API Sandbox campaign 2'}],
#                   'LimitedBy': 2}}>


# Extract raw data.
data = campaigns.data
assert isinstance(data, dict)


# Create a campaign.
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
result = client.campaigns().post(data=body)
print(result)
# <TapiClient object
# {'result': {'AddResults': [{'Id': 417065}]}}>

# Extract raw data.
data = campaigns.data
assert isinstance(data, dict)
print(result)
# {'result': {'AddResults': [{'Id': 417066}]}}
```


### Client methods

Result extraction method.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)

# Request response.
print(campaigns.response)
print(campaigns.request_kwargs)
print(campaigns.status_code)
print(campaigns.data)
```

### .extract()

Result extraction method.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)
campaigns_list = campaigns().extract()
assert isinstance(campaigns_list, list)
print(campaigns_list)
# [{'Id': 338157, 'Name': 'Test API Sandbox campaign 1'},
#  {'Id': 338158, 'Name': 'Test API Sandbox campaign 2'}]
```


### .items()

Iterating result items.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
campaigns = client.campaigns().post(data=body)

for item in campaigns().items():
    print(item)
    # {'Id': 338157, 'Name': 'Test API Sandbox campaign 1'}
    assert isinstance(item, dict)
```


### .pages()

Iterating to get all the data.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
        "Page": {"Limit": 2}
    },
}
campaigns = client.campaigns().post(data=body)

# Iterating requests data.
for page in campaigns().pages():
    assert isinstance(page.data, list)
    print(page.data)
    # [{'Id': 338157, 'Name': 'Test API Sandbox campaign 1'},
    #  {'Name': 'Test API Sandbox campaign 2', 'Id': 338158}]

    # Iterating items of page data.
    for item in page().items():
        print(item)
        # {'Id': 338157, 'Name': 'Test API Sandbox campaign 1'}
        assert isinstance(item, dict)
```


### .iter_items()

After each request, iterates over the items of the request data.

```python
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
        "Page": {"Limit": 2}
    },
}
campaigns = client.campaigns().post(data=body)

# Iterates through the elements of all data.
for item in campaigns().iter_items():
    assert isinstance(item, dict)
    print(item)

# {'Name': 'MyCampaignTest', 'Id': 417065}
# {'Name': 'MyCampaignTest', 'Id': 417066}
# {'Id': 338157, 'Name': 'Test API Sandbox campaign 1'}
# {'Name': 'Test API Sandbox campaign 2', 'Id': 338158}
# {'Id': 338159, 'Name': 'Test API Sandbox campaign 3'}
# {'Name': 'MyCampaignTest', 'Id': 415805}
# {'Id': 416524, 'Name': 'MyCampaignTest'}
# {'Id': 417056, 'Name': 'MyCampaignTest'}
# {'Id': 417057, 'Name': 'MyCampaignTest'}
# {'Id': 417058, 'Name': 'MyCampaignTest'}
# {'Id': 417065, 'Name': 'MyCampaignTest'}
# {'Name': 'MyCampaignTest', 'Id': 417066}
```


## Reports

```python
from tapi_yandex_direct import YandexDirect

ACCESS_TOKEN = "{ваш токен доступа}"

client = YandexDirect(
    # Required parameters:

    access_token=ACCESS_TOKEN,
    # If you are making inquiries from an agent account, you must be sure to specify the account login.
    login="{login}",

    # Optional parameters:

    # Enable sandbox.
    is_sandbox=False,
    # Repeat request when units run out
    retry_if_not_enough_units=False,
    # The language in which the data for directories and errors will be returned.
    language="ru",
    # Repeat the request if the limits on the number of reports or requests are exceeded.
    retry_if_exceeded_limit=True,
    # Number of retries when server errors occur.
    retries_if_server_error=5,

    # Report resource parameters:

    # Report generation mode: online, offline or auto.
    processing_mode="offline",
    # When requesting a report, it will wait until the report is prepared and download it.
    wait_report=True,
    # Monetary values in the report are returned in currency with an accuracy of two decimal places.
    return_money_in_micros=False,
    # Do not display a line with the report name and date range in the report.
    skip_report_header=True,
    # Do not display a line with field names in the report.
    skip_column_header=False,
    # Do not display a line with the number of statistics lines in the report.
    skip_report_summary=True,
)

body = {
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Date", "CampaignId", "Clicks", "Cost"],
        "OrderBy": [{
            "Field": "Date"
        }],
        "ReportName": "Actual Data",
        "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
        "DateRangeType": "LAST_WEEK",
        "Format": "TSV",
        "IncludeVAT": "YES",
        "IncludeDiscount": "YES"
    }
}
report = client.reports().post(data=body)
print(report.data)
# 'Date\tCampaignId\tClicks\tCost\n'
# '2019-09-02\t338151\t12578\t9210750000\n'
```


### .columns

Extract column names.
```python
report = client.reports().post(data=body)
print(report.columns)
# ['Date', 'CampaignId', 'Clicks', 'Cost']
```


### .to_lines()

```python
report = client.reports().post(data=body)
print(report().to_lines())
# list[str]
# [..., '2019-09-02\t338151\t12578\t9210750000']
```


### .to_values()

```python
report = client.reports().post(data=body)
print(report().to_values())
# list[list[str]]
# [..., ['2019-09-02', '338151', '12578', '9210750000']]
```


### .to_dict()

```python
report = client.reports().post(data=body)
print(report().to_dict())
# list[dict]
# [..., {'Date': '2019-09-02', 'CampaignId': '338151', 'Clicks': '12578', 'Cost': 9210750000'}]
```


### .to_columns()

```python
report = client.reports().post(data=body)
print(report().to_columns())
# list[list[str], list[str], list[str], list[str]]
# [[..., '2019-09-02'], [..., '338151'], [..., '12578'], [..., '9210750000']]
```


## Features

Information about the resource.
```python
client.campaigns().help()
```

Open resource documentation
```python
client.campaigns().open_docs()
```

Send a request in the browser.
```python
client.campaigns().open_in_browser()
```


## Dependences
- requests
- [tapi_wrapper](https://github.com/pavelmaksimov/tapi-wrapper)


## CHANGELOG
v2021.5.29
- Fix stub file (syntax highlighting)


v2021.5.25
- Add stub file (syntax highlighting)
- Add methods 'iter_dicts', 'to_dicts'


## Автор
Павел Максимов

Связаться со мной можно в
[Телеграм](https://t.me/pavel_maksimow)
и в
[Facebook](https://www.facebook.com/pavel.maksimow)

Удачи тебе, друг! Поставь звездочку ;)
