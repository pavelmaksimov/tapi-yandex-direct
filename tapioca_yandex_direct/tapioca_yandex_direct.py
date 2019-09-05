# coding: utf-8
import json
import logging
import time

from tapioca import TapiocaAdapter, generate_wrapper_from_adapter, JSONAdapterMixin
from tapioca.exceptions import ResponseProcessException, ClientError

from tapioca_yandex_direct import exceptions
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
    "HasSearchVolumeResults": "HasSearchVolumeResults",
    "get": {
        "https://api.direct.yandex.com/json/v5/campaigns": "Campaigns",
        "https://api.direct.yandex.com/json/v5/adgroups": "AdGroups",
        "https://api.direct.yandex.com/json/v5/ads": "Ads",
        "https://api.direct.yandex.com/json/v5/audiencetargets": "AudienceTargets",
        "https://api.direct.yandex.com/json/v5/creatives": "Creatives",
        "https://api.direct.yandex.com/json/v5/adimages": "AdImages",
        "https://api.direct.yandex.com/json/v5/vcards": "VCards",
        "https://api.direct.yandex.com/json/v5/sitelinks": "SitelinksSets",
        "https://api.direct.yandex.com/json/v5/adextensions": "AdExtensions",
        "https://api.direct.yandex.com/json/v5/keywords": "Keywords",
        "https://api.direct.yandex.com/json/v5/retargetinglists": "RetargetingLists",
        "https://api.direct.yandex.com/json/v5/bids": "Bids",
        "https://api.direct.yandex.com/json/v5/keywordbids": "KeywordBids",
        "https://api.direct.yandex.com/json/v5/bidmodifiers": "BidModifiers",
        "https://api.direct.yandex.com/json/v5/agencyclients": "Clients",
        "https://api.direct.yandex.com/json/v5/clients": "Clients",
        "https://api.direct.yandex.com/json/v5/leads": "Leads",
        "https://api.direct.yandex.com/json/v5/dynamictextadtargets": "Webpages",
        "https://api.direct.yandex.com/json/v5/turbopages": "TurboPages",
        "https://api.direct.yandex.com/json/v5/negativekeywordsharedsets": "NegativeKeywordSharedSets",
    }
}


class YandexDirectClientAdapter(JSONAdapterMixin, TapiocaAdapter):
    api_root = "https://{}/"

    PRODUCTION_HOST = "api.direct.yandex.com"
    SANDBOX_HOST = "api-sandbox.direct.yandex.com"

    resource_mapping = RESOURCE_MAPPING_V5

    def __init__(self, *args, **kwargs):
        """
        :param access_token: str : токен доступа
        :param login: str : Логин рекламодателя — клиента рекламного агентства.
            Обязателен, если запрос осуществляется от имени агентства.
        :param use_operator_units: bool : Расходовать баллы агентства,
            а не рекламодателя при выполнении запроса.
            Заголовок допустим только в запросах от имени агентства.
        :param language: str : ru|en|{other} :
            язык в котором будут возвращены некоторые данные, например справочников.
        :param retry_if_not_enough_units: bool : ожидать и повторять запрос,
            если закончилась квота запросов к апи.
        :param auto_request_generation: bool :
            Сделать несколько запросов, если в условиях фильтрации
            кол-во идентификаторов превышает максмимальное разрешенное кол-во.
        :param is_sandbox: bool : включить песочницу
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
        if api_params["auto_request_generation"] and kwargs["data"]["method"] == "get":
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

        return params

    def get_error_message(self, data, response=None):
        try:
            if not data and response.content.strip():
                data = json.loads(response.content.decode("utf-8"))

            if data:
                return data.get("error", None)
        except json.JSONDecodeError:
            return response.text

    def process_response(self, response, **request_kwargs):
        data = super().process_response(response)
        if data.get("error"):
            raise ResponseProcessException(ClientError, data)
        return data

    def wrapper_call_exception(
        self, response, tapioca_exception, api_params, *args, **kwargs
    ):
        if 500 <= response.status_code < 600:
            raise exceptions.YandexDirectServerError(response)
        else:
            try:
                jdata = response.json()
            except json.JSONDecodeError:
                raise exceptions.YandexDirectApiError(response)
            else:
                error_code = jdata.get("error").get("error_code", 0)

                if error_code == 152:
                    raise exceptions.YandexDirectLimitError(response)
                elif error_code == 53:
                    raise exceptions.YandexDirectTokenError(response)
                else:
                    raise exceptions.YandexDirectClientError(response)

    def response_to_native(self, response):
        if response.content.strip():
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text

    def retry_request(self, response, tapioca_exception, api_params, *args, **kwargs):
        """
        Условия повторения запроса.

        response = tapioca_exception.client().response
        status_code = tapioca_exception.client().status_code
        response_data = tapioca_exception.client().data
        """
        response_data = tapioca_exception.client().data
        error_code = (response_data or {}).get("error", {}).get("error_code", 0)
        if error_code == 152:
            if api_params.get("retry_if_not_enough_units", False):
                logging.debug("Исчерпан лимит, повтор через 1 минуту")
                time.sleep(60)
                return True
            else:
                logging.debug("Исчерпан лимит запросов")
        return False

    def extra_request(
        self, api_params, current_request_kwargs, request_kwargs_list, response, current_result
    ):
        limit = current_result.get("result", {}).get("LimitedBy", False)
        if limit:
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

    def transform(self, results, request_kwargs, *args, **kwargs):
        """Преобразование данных"""
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
                    url = request_kwargs['url'].replace(
                        self.SANDBOX_HOST, self.PRODUCTION_HOST
                    )
                    key = key[url]
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
                return results[0]["result"][key]


class GetTokenYandexDirectClientAdapter(JSONAdapterMixin, TapiocaAdapter):
    resource_mapping = RESOURCE_MAPPING_OAUTH

    def get_api_root(self, api_params):
        return "https://"


YandexDirect = generate_wrapper_from_adapter(YandexDirectClientAdapter)
GetTokenYandexDirect = generate_wrapper_from_adapter(GetTokenYandexDirectClientAdapter)
