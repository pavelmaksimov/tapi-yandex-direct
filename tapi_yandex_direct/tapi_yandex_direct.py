# coding: utf-8
import json
import logging
import time

import simplejson
from tapi import TapiAdapter, generate_wrapper_from_adapter, JSONAdapterMixin
from tapi.exceptions import ResponseProcessException, ClientError

from tapi_yandex_direct import exceptions
from .resource_mapping import RESOURCE_MAPPING_V5, RESOURCE_MAPPING_OAUTH

# Максимальное кол-во объектов в одном запросе.
MAX_COUNT_OBJECTS = {
    "Ids": 10000,
    "KeywordIds": 10000,
    "RetargetingListIds": 1000,
    "InterestIds": 1000,
    "AdGroupIds": 1000,
    "AdIds": 1000,
    "CampaignIds": 10,
    "AccountIDS": 100,
    "Logins": 50,
}
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
    "checkCampaigns": "result",
    "check": "result",
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
    }
}
URL_PATH_REPORTS = "/json/v5/reports"


class YandexDirectClientAdapter(JSONAdapterMixin, TapiAdapter):
    api_root = "https://{}/"

    PRODUCTION_HOST = "api.direct.yandex.com"
    SANDBOX_HOST = "api-sandbox.direct.yandex.com"

    resource_mapping = RESOURCE_MAPPING_V5

    def __init__(self, *args, **kwargs):
        """
        :param access_token: str : токен доступа
        :param login: str : Логин рекламодателя — клиента рекламного агентства.
            Обязателен, если запрос осуществляется от имени агентства.
        :param use_operator_units: bool : False : Расходовать баллы агентства,
            а не рекламодателя при выполнении запроса.
            Заголовок допустим только в запросах от имени агентства.
        :param language: str : ru|en|{other} : ru
            язык в котором будут возвращены некоторые данные, например справочников.
        :param retry_if_not_enough_units: bool : False : ожидать и повторять запрос,
            если закончилась квота запросов к апи.
        :param auto_request_generation: bool : False :
            Сделать несколько запросов, если в условиях фильтрации
            кол-во идентификаторов превышает максмимальное разрешенное кол-во.
        :param receive_all_objects: bool : False :
            Если в запросе не будут получены все объекты,
            то будут сделаны дополнительные запросы.
        :param is_sandbox: bool : False : включить песочницу
        :param wait_report: bool : True : ждать готовности отчета
        :param retry_if_exceeded_queue_size_limit: bool : True : ожидать и повторять запрос,
            если закончилась квота запросов к апи.
        :param retries_if_server_error: int : 5 : число повторов при серверной ошибке
        """
        super().__init__(*args, **kwargs)

    def get_api_root(self, api_params):
        if api_params.get("is_sandbox", False):
            return self.api_root.format(self.SANDBOX_HOST)
        return self.api_root.format(self.PRODUCTION_HOST)

    def generate_request_kwargs(self, api_params, *args, **kwargs):
        """
        При необходимости,
        здесь можно создать несколько наборов параметров для того,
        чтобы сделать несколько запросов.
        """
        cond = api_params.get("auto_request_generation", False)
        if cond and kwargs["data"].get("method") == "get":
            filters = kwargs["data"].get("params", {}).get("SelectionCriteria", {})
            ids_fields = [i for i in filters.keys() if i in MAX_COUNT_OBJECTS]
            if len(ids_fields) > 1:
                raise Exception(
                    "Не умею генерировать несколько запросов, "
                    "когда в условиях фильтрации "
                    "несколько типов идентификаторов, "
                    "например кампаний и групп. Оставьте что-то одно "
                    "или отключите auto_request_generation"
                )
            elif ids_fields:
                ids_field = ids_fields[0]
                ids = filters[ids_field]
                size = MAX_COUNT_OBJECTS[ids_field]

                if not isinstance(ids, list):
                    raise TypeError("Поле {} должно быть списком".format(ids_field))

                if len(ids) > size:
                    # Когда кол-во идентификаторов,
                    # которые указано получить, превышают лимит максимального
                    # кол-ва, которое можно запросить в одном запросе,
                    # создаются несколько запросов.
                    request_kwargs_list = []
                    while ids:
                        kwargs["data"]["params"]["SelectionCriteria"][ids_field] = ids[:size]
                        del ids[:size]
                        request_kwargs = self.get_request_kwargs(
                            api_params, *args, **kwargs
                        )
                        request_kwargs_list.append(request_kwargs)

                    return request_kwargs_list

        return [self.get_request_kwargs(api_params, *args, **kwargs)]

    def get_request_kwargs(self, api_params, *args, **kwargs):
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

        params["headers"].update({"Accept-Language": api_params.get("language", "ru")})
        params["headers"]["processingMode"] = api_params.get("processing_mode", "auto")
        params["headers"]["returnMoneyInMicros"] = str(api_params.get("return_money_in_micros", False)).lower()
        params["headers"]["skipReportHeader"] = str(api_params.get("skip_report_header", True)).lower()
        params["headers"]["skipColumnHeader"] = str(api_params.get("skip_column_header", False)).lower()
        params["headers"]["skipReportSummary"] = str(api_params.get("skip_report_summary", True)).lower()

        return params

    def get_error_message(self, data, response=None):
        try:
            if not data and response.content.strip():
                data = json.loads(response.content.decode("utf-8"))

            if data:
                return data.get("error", None)
        except (json.JSONDecodeError, simplejson.JSONDecodeError):
            return response.text

    def process_response(self, response, **request_kwargs):
        if response.status_code == 502:
            raise exceptions.YandexDirectServerError(
                response,
                "Время формирования отчета превысило серверное ограничение. "
                "Пожалуйста, попробуйте изменить параметры запроса - "
                "уменьшить период и количество запрашиваемых данных."
            )
        elif response.status_code == 405:
            raise exceptions.YandexDirectServerError(
                response,
                "Данный ресурс не обрабатывает HTTP метод {}\n"
                    .format(response.request.method)
            )
        # При ошибке 500 и в других в ответах может быть json с ошибками.
        data = self.response_to_native(response)

        if isinstance(data, dict):
            if data.get("error"):
                raise ResponseProcessException(ClientError, data)
        elif response.status_code in (201, 202):
            raise ResponseProcessException(ClientError, data)
        else:
            data = super().process_response(response)

        return data

    def wrapper_call_exception(
        self, response, tapi_exception, api_params, *args, **kwargs
    ):
        if response.status_code in (201, 202):
            pass
        else:
            try:
                jdata = json.loads(response.content.decode("utf-8"))
            except (json.JSONDecodeError, simplejson.JSONDecodeError):
                raise exceptions.YandexDirectApiError(response)
            else:
                error_code = int(jdata.get("error").get("error_code", 0))

                if error_code == 152:
                    raise exceptions.YandexDirectLimitError(response)
                elif error_code == 53:
                    raise exceptions.YandexDirectTokenError(response)
                elif (
                    error_code == 9000
                    and api_params.get("retry_if_exceeded_limit", False) is False
                ):
                    raise exceptions.YandexDirectApiError(
                        response,
                        "В данный момент на сервере готовятся максимальное "
                        "кол-во отчетов. Повторите запрос позже."
                    )
                else:
                    raise exceptions.YandexDirectClientError(response)

    def response_to_native(self, response):
        if response.content.strip():
            try:
                return json.loads(response.content.decode("utf-8"))
            except (json.JSONDecodeError, simplejson.JSONDecodeError):
                return response.text

    def retry_request(
        self,
        response,
        tapi_exception,
        api_params,
        count_request_error,
        *args, **kwargs
    ):
        """
        Условия повторения запроса.

        response = tapi_exception.client().response
        status_code = tapi_exception.client().status_code
        response_data = tapi_exception.client().data
        """
        status_code = tapi_exception.client().status_code
        response_data = tapi_exception.client().data
        error_code = int((response_data or {}).get("error", {}).get("error_code", 0))

        if status_code in (201, 202):
            logging.info("Отчет не готов")
            if api_params.get("wait_report", True):
                sleep = int(response.headers.get("retryIn", 10))
                logging.warning("Повтор через {} сек.".format(sleep))
                time.sleep(sleep)
                return True

        if error_code == 152:
            if api_params.get("retry_if_not_enough_units", False):
                logging.warning("Нехватает баллов, повтор через 5 минут")
                time.sleep(60 * 5)
                return True
            else:
                logging.error("Нехватает баллов для запроса")
        elif error_code == 506 and api_params.get("retry_if_exceeded_limit", True):
            logging.warning("Превышено количество запросов к API, повтор через 10 секунд")
            time.sleep(10)
            return True
        elif error_code == 56 and api_params.get("retry_if_exceeded_limit", True):
            logging.warning('Превышен лимит запросов метода. Повторный запрос через 10 секунд')
            time.sleep(10)
            return True
        elif error_code == 9000 and api_params.get("retry_if_exceeded_limit", True):
            logging.warning('Создано макс. кол-во отчетов. Повторный запрос через 10 секунд')
            time.sleep(10)
            return True
        elif error_code in (52, 1000, 1001, 1002) or status_code == 500:
            if count_request_error < api_params.get("retries_if_server_error", 5):
                logging.warning('Серверная ошибка. Повторный запрос через 1 секунду')
                time.sleep(1)
                return True

        return False

    def extra_request(
        self,
        api_params,
        current_request_kwargs,
        request_kwargs_list,
        response,
        current_result
    ):
        if response.request.path_url != URL_PATH_REPORTS:
            limit = current_result.get("result", {}).get("LimitedBy", False)
            if api_params.get("receive_all_objects") and limit:
                # Дополнительный запрос, если не все данные получены.
                request_kwargs = current_request_kwargs.copy()
                request_kwargs["data"] = json.loads(request_kwargs["data"])

                if request_kwargs["data"]["params"].get("Page"):
                    request_kwargs["data"]["params"]["Page"]["Offset"] = limit
                else:
                    request_kwargs["data"]["params"]["Page"] = {"Offset": limit}

                request_kwargs["data"] = json.dumps(request_kwargs["data"])
                request_kwargs_list.append(request_kwargs)

        return request_kwargs_list

    def transform_results(self, results, requests_kwargs, responses, api_params):
        if responses[0].request.path_url == URL_PATH_REPORTS:
            return (results or [False])[0]
        else:
            return results

    def transform(self, results, request_kwargs, response, api_params, *args, **kwargs):
        """Преобразование данных"""
        if response.request.path_url == URL_PATH_REPORTS:
            data = results or ""
            new_data = [i.split("\t") for i in data.split("\n")]
            # Удаление последней пустой строки.
            new_data = new_data[:-1] if new_data[-1] == [""] else new_data
            return new_data
        else:
            method = json.loads(request_kwargs["data"])["method"]
            try:
                key = RESULT_DICTIONARY_KEYS_OF_API_METHODS[method]
            except KeyError:
                raise KeyError(
                    "Для запроса с методом '{}' преобразование "
                    "данных не настроено".format(method)
                )
            else:
                if method == "get":
                    try:
                        key = key[response.request.path_url]
                    except KeyError:
                        raise KeyError(
                            'Для этого ресурса преобразование данных не настроено'
                        )
                    else:
                        new_data = []
                        for r in results:
                            data = r.get('result', {}).get(key, [])
                            new_data += data
                        return new_data
                else:
                    if len(results) > 1:
                        logging.warning(
                            "При преобразовании данных было обнаружено "
                            "несколько ответов. "
                            "Такое поведение не предусмотрено. "
                            "Был извлечен только первый ответ."
                        )
                    if key == "result":
                        return results[0]["result"]
                    return results[0]["result"][key]


class GetTokenYandexDirectClientAdapter(JSONAdapterMixin, TapiAdapter):
    resource_mapping = RESOURCE_MAPPING_OAUTH

    def get_api_root(self, api_params):
        return "https://"


YandexDirect = generate_wrapper_from_adapter(YandexDirectClientAdapter)
GetTokenYandexDirect = generate_wrapper_from_adapter(GetTokenYandexDirectClientAdapter)
