import io
import logging
import time
from typing import Union, Optional, Dict, List, Iterator

import orjson
from requests import Response
from tapi2 import TapiAdapter, generate_wrapper_from_adapter, JSONAdapterMixin
from tapi2.exceptions import ResponseProcessException, ClientError, TapiException

from tapi_yandex_direct import exceptions
from tapi_yandex_direct.resource_mapping import RESOURCE_MAPPING_V5

logger = logging.getLogger(__name__)

RESULT_DICTIONARY_KEYS_OF_API_METHODS = {
    "add": "AddResults",
    "update": "UpdateResults",
    "unarchive": "UnarchiveResults",
    "suspend": "SuspendResults",
    "resume": "ResumeResults",
    "delete": "DeleteResults",
    "archive": "ArchiveResults",
    "moderate": "ModerateResults",
    "setBids": "SetBidsResults",
    "set": "SetResults",
    "setAuto": "SetAutoResults",
    "toggle": "ToggleResults",
    "checkDictionaries": "result",
    "checkCampaigns": "Campaigns",
    "check": "Modified",
    "HasSearchVolumeResults": "HasSearchVolumeResults",
    "get": {
        "/json/v5/campaigns": "Campaigns",
        "/json/v5/adgroups": "AdGroups",
        "/json/v5/ads": "Ads",
        "/json/v5/audiencetargets": "AudienceTargets",
        "/json/v5/creatives": "Creatives",
        "/json/v5/adimages": "AdImages",
        "/json/v5/vcards": "VCards",
        "/json/v5/sitelinks": "SitelinksSets",
        "/json/v5/adextensions": "AdExtensions",
        "/json/v5/keywords": "Keywords",
        "/json/v5/retargetinglists": "RetargetingLists",
        "/json/v5/bids": "Bids",
        "/json/v5/keywordbids": "KeywordBids",
        "/json/v5/bidmodifiers": "BidModifiers",
        "/json/v5/agencyclients": "Clients",
        "/json/v5/clients": "Clients",
        "/json/v5/leads": "Leads",
        "/json/v5/dynamictextadtargets": "Webpages",
        "/json/v5/turbopages": "TurboPages",
        "/json/v5/negativekeywordsharedsets": "NegativeKeywordSharedSets",
        "/json/v5/feeds": "Feeds",
        "/json/v5/smartadtargets": "SmartAdTargets",
        "/json/v5/businesses": "Businesses",
    },
}
REPORTS_RESOURCE_URL = "/json/v5/reports"


class YandexDirectClientAdapter(JSONAdapterMixin, TapiAdapter):
    resource_mapping = RESOURCE_MAPPING_V5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_api_root(self, api_params: dict, resource_name: str) -> str:
        if resource_name == "debugtoken":
            return "https://"
        elif api_params.get("is_sandbox"):
            return "https://api-sandbox.direct.yandex.com/"
        else:
            return "https://api.direct.yandex.com/"

    def get_request_kwargs(self, api_params: dict, *args, **kwargs) -> dict:
        """Обогащение запроса, параметрами"""
        params = super().get_request_kwargs(api_params, *args, **kwargs)

        token = api_params.get("access_token")
        if token:
            params["headers"].update({"Authorization": "Bearer {}".format(token)})

        login = api_params.get("login")
        if login:
            params["headers"].update({"Client-Login": login})

        use_operator_units = api_params.get("use_operator_units")
        if use_operator_units:
            params["headers"].update({"Use-Operator-Units": use_operator_units})

        language = api_params.get("language")
        if language:
            params["headers"].update({"Accept-Language": language})

        params["headers"]["processingMode"] = api_params.get("processing_mode", "auto")
        params["headers"]["returnMoneyInMicros"] = str(
            api_params.get("return_money_in_micros", False)
        ).lower()
        params["headers"]["skipReportHeader"] = str(
            api_params.get("skip_report_header", True)
        ).lower()
        params["headers"]["skipColumnHeader"] = str(
            api_params.get("skip_column_header", False)
        ).lower()
        params["headers"]["skipReportSummary"] = str(
            api_params.get("skip_report_summary", True)
        ).lower()

        if "receive_all_objects" in api_params:
            raise exceptions.BackwardCompatibilityError(
                "parameter 'receive_all_objects'"
            )

        if "auto_request_generation" in api_params:
            raise exceptions.BackwardCompatibilityError(
                "parameter 'auto_request_generation'"
            )

        return params

    def get_error_message(
        self, data: Union[None, dict], response: Response = None
    ) -> dict:
        if data is None:
            return {"error_text": response.content.decode()}
        else:
            return data

    def format_data_to_request(self, data) -> Optional[bytes]:
        if data:
            return orjson.dumps(data)

    def response_to_native(self, response: Response) -> Union[dict, str]:
        if response.content.strip():
            try:
                return orjson.loads(response.content.decode())
            except ValueError:
                return response.text

    def process_response(
        self, response: Response, request_kwargs: dict, **kwargs
    ) -> dict:
        request_kwargs["data"] = orjson.loads(request_kwargs["data"])

        if response.status_code == 502:
            raise exceptions.YandexDirectApiError(
                response,
                "The report generation time has exceeded the server limit. "
                "Please try to change the request parameters, "
                "reduce the period or the amount of requested data.",
                **kwargs
            )
        elif response.status_code == 405:
            raise exceptions.YandexDirectApiError(
                response,
                "This resource does not support the HTTP method {}\n".format(
                    response.request.method
                ),
                **kwargs
            )

        data = self.response_to_native(response)

        if isinstance(data, dict) and data.get("error"):
            raise ResponseProcessException(ClientError, data)
        elif response.status_code in (201, 202):
            raise ResponseProcessException(ClientError, data)
        else:
            data = super().process_response(response, request_kwargs, **kwargs)

        if response.request.path_url == REPORTS_RESOURCE_URL:
            lines = self._iter_lines(data=data, response=response, **kwargs)
            kwargs["store"]["columns"] = next(lines).split("\t")
        else:
            kwargs["store"].pop("columns", None)

        return data

    def error_handling(
        self,
        tapi_exception: TapiException,
        error_message: dict,
        repeat_number: int,
        response: Response,
        request_kwargs: dict,
        api_params: dict,
        **kwargs
    ) -> None:
        if response.status_code in (201, 202):
            pass
        elif "error_text" in error_message:
            raise exceptions.YandexDirectApiError(
                response, error_message["error_text"], **kwargs
            )
        else:
            error_data = error_message.get("error", {})
            error_code = int(error_data.get("code", 0))

            if error_code == 152:
                raise exceptions.YandexDirectNotEnoughUnitsError(
                    response, error_message, **kwargs
                )
            elif (
                error_code == 53
                or error_data["error_detail"] == "OAuth token is missing"
            ):
                raise exceptions.YandexDirectTokenError(
                    response, error_message, **kwargs
                )
            elif error_code in (56, 506, 9000):
                raise exceptions.YandexDirectRequestsLimitError(
                    response, error_message, **kwargs
                )
            else:
                raise exceptions.YandexDirectClientError(
                    response, error_message, **kwargs
                )

    def retry_request(
        self,
        tapi_exception: TapiException,
        error_message: dict,
        repeat_number: int,
        response: Response,
        request_kwargs: dict,
        api_params: dict,
        **kwargs
    ) -> bool:
        status_code = response.status_code
        error_data = error_message.get("error", {})
        error_code = int(error_data.get("code", 0))

        if status_code in (201, 202):
            logger.info("Report not ready")
            if api_params.get("wait_report", True):
                sleep = int(response.headers.get("retryIn", 10))
                logger.info("Re-request after {} seconds".format(sleep))
                time.sleep(sleep)
                return True

        if error_code == 152:
            if api_params.get("retry_if_not_enough_units", False):
                logger.warning("Not enough units, re-request after 5 minutes")
                time.sleep(60 * 5)
                return True
            else:
                logger.error("Not enough units to request")

        elif error_code == 506 and api_params.get("retry_if_exceeded_limit", True):
            logger.warning("API requests exceeded, re-request after 10 seconds")
            time.sleep(10)
            return True

        elif error_code == 56 and api_params.get("retry_if_exceeded_limit", True):
            logger.warning("Method request limit exceeded. Re-request after 10 seconds")
            time.sleep(10)
            return True

        elif error_code == 9000 and api_params.get("retry_if_exceeded_limit", True):
            logger.warning(
                "Created by max number of reports. Re-request after 10 seconds"
            )
            time.sleep(10)
            return True

        elif error_code in (52, 1000, 1001, 1002) or status_code == 500:
            if repeat_number < api_params.get("retries_if_server_error", 5):
                logger.warning("Server error. Re-request after 1 second")
                time.sleep(1)
                return True

        return False

    def get_iterator_next_request_kwargs(
        self,
        response_data: Dict[str, dict],
        response: Response,
        request_kwargs: dict,
        api_params: dict,
        **kwargs
    ) -> Optional[dict]:
        limit = response_data["result"].get("LimitedBy")
        if limit:
            page = request_kwargs["data"]["params"].setdefault("Page", {})
            page["Offset"] = limit

            return request_kwargs

    def get_iterator_pages(self, response_data: dict, **kwargs) -> List[List[dict]]:
        return [self.extract(response_data, **kwargs)]

    def get_iterator_items(self, data: Union[dict, List[dict]], **kwargs) -> List[dict]:
        if "result" in data:
            return self.extract(data, **kwargs)
        return data

    def get_iterator_iteritems(self, response_data: dict, **kwargs) -> List[dict]:
        return self.extract(response_data, **kwargs)

    def _iter_lines(self, data: str, response: Response, **kwargs) -> Iterator[str]:
        if response.request.path_url != REPORTS_RESOURCE_URL:
            raise NotImplementedError("For reports resource only")

        lines = io.StringIO(data)
        iterator = (line.replace("\n", "") for line in lines)

        return iterator

    def iter_lines(self, **kwargs) -> Iterator[str]:
        iterator = self._iter_lines(**kwargs)
        next(iterator)  # skipping columns
        yield from iterator

    def iter_values(self, **kwargs) -> Iterator[list]:
        for line in self.iter_lines(**kwargs):
            yield line.split("\t")

    def iter_dicts(self, **kwargs) -> Iterator[dict]:
        for line in self.iter_lines(**kwargs):
            yield dict(zip(kwargs["store"]["columns"], line.split("\t")))

    def to_values(self, **kwargs) -> List[list]:
        return list(self.iter_values(**kwargs))

    def to_lines(self, **kwargs) -> List[str]:
        return list(self.iter_lines(**kwargs))

    def to_columns(self, **kwargs):
        columns = [[] for _ in range(len(kwargs["store"]["columns"]))]
        for values in self.iter_values(**kwargs):
            for i, col in enumerate(columns):
                col.append(values[i])

        return columns

    def to_dict(self, **kwargs) -> List[dict]:
        return [
            dict(zip(kwargs["store"]["columns"], values))
            for values in self.iter_values(**kwargs)
        ]

    def to_dicts(self, **kwargs) -> List[dict]:
        return self.to_dict(**kwargs)

    def extract(
        self, data: dict, response: Response, request_kwargs: dict, **kwargs
    ) -> List[dict]:
        if response.request.path_url == REPORTS_RESOURCE_URL:
            raise NotImplementedError("Report resource not supported")

        method = request_kwargs["data"]["method"]
        try:
            key = RESULT_DICTIONARY_KEYS_OF_API_METHODS[method]
        except KeyError:
            raise KeyError(
                "Result extract is not implemented for method '{}'".format(method)
            )
        else:
            if method == "get":
                resource_map = key
                try:
                    key = resource_map[response.request.path_url]
                except KeyError:
                    raise KeyError(
                        "Result extract is not implemented for resource '{}'".format(
                            response.request.path_url
                        )
                    )
                else:
                    return data.get("result", {}).get(key, [])
            else:
                data = data["result"]
                if key == "result":
                    return data
                return data[key]

    def transform(self, *args, **kwargs):
        raise exceptions.BackwardCompatibilityError("method 'transform'")


YandexDirect = generate_wrapper_from_adapter(YandexDirectClientAdapter)
