# coding: utf-8
import json
import logging
import time

from tapioca import TapiocaAdapter, generate_wrapper_from_adapter, JSONAdapterMixin
from tapioca.exceptions import ResponseProcessException, ClientError

from tapioca_yandex_direct import exceptions
from .resource_mapping import RESOURCE_MAPPING_V5

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
RESPONSE_DICTIONARY_KEYS = {
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

class YandexDirectClientAdapter(JSONAdapterMixin, TapiocaAdapter):
    end_point = "https://{}/"
    api_root = end_point

    PRODUCTION_HOST = "api.direct.yandex.com"
    SANDBOX_HOST = "api-sandbox.direct.yandex.com"

    resource_mapping = RESOURCE_MAPPING_V5

    def __init__(self, *args, **kwargs):
        """
        Низкоуровневый API.

        :param access_token: str : токен доступа
        :param login: str : Логин рекламодателя — клиента рекламного агентства.
            Обязателен, если запрос осуществляется от имени агентства.
        :param use_operator_units: bool : Расходовать баллы агентства,
            а не рекламодателя при выполнении запроса.
            Заголовок допустим только в запросах от имени агентства.
        :param language: str : ru|en|{other} :
            язык в котором будут возвращены некоторые данные, например справочников.
        :param retry_request_if_limit: bool : ожидать и повторять запрос,
            если закончилась квота запросов к апи.
        :param is_sandbox: bool : включить песочницу
        :param v: int : 5 : версия апи, по умолчанию 5

        low_api = YandexDirect(access_token=ACCESS_TOKEN,
                           use_operator_units=True,
                           retry_request_if_limit=True)
        result = low_api.user2().get()
        data = result().data  # данные в формате json
        df = result().to_df()  # данные в формате pandas dataframe
        """
        super().__init__(*args, **kwargs)

    def get_api_root(self, api_params):
        if api_params.get("is_sandbox", False):
            return self.end_point.format(self.SANDBOX_HOST)
        return self.end_point.format(self.PRODUCTION_HOST)

    def generate_request_kwargs(self, api_params, *args, **kwargs):
        """
        При необходимости,
        здесь можно создать несколько наборов параметров для того,
        чтобы сделать несколько запросов.
        """
        filters = kwargs["data"]["params"].get("SelectionCriteria")
        ids_fields = [i for i in filters.keys() if i in MAX_COUNT_OBJECTS]
        if len(ids_fields) > 1:
            raise Exception(
                "Не умею генерировать несколько запросов, "
                "когда в условиях фильтрации несколько типов идентификаторов, "
                "например кампаний и групп. Оставьте что-то одно."
            )
        elif ids_fields:
            ids_field = ids_fields[0]
            ids = filters[ids_field]
            group_size = MAX_COUNT_OBJECTS[ids_field]

            if len(ids) > group_size:
                # Когда кол-во идентификаторов,
                # которые указано получить, превышают лимит максимального
                # кол-ва, которое можно запросить в одном запросе,
                # создаются несколько запросов.
                request_kwargs_list = []
                while ids:
                    kwargs["data"]["params"]["SelectionCriteria"][ids_field] = ids[
                        :group_size
                    ]
                    del ids[:group_size]
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

        if api_params.get("language", False):
            params["headers"].update({"Accept-Language": api_params.get("language")})
        else:
            params["headers"].update({"Accept-Language": "ru"})

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
            raise exceptions.YadirectServerError(response)
        else:
            try:
                jdata = response.json()
            except json.JSONDecodeError:
                raise exceptions.YadirectApiError(response)
            else:
                error_code = jdata.get("error").get("error_code", 0)

                if error_code == 152:
                    raise exceptions.YadirectLimitError(response)
                elif error_code == 53:
                    raise exceptions.YadirectTokenError(response)
                else:
                    raise YandexDirectClientAdapter(response)

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
            if api_params.get("retry_request_if_limit", False):
                logging.debug("Исчерпан лимит, повтор через 1 минуту")
                time.sleep(60)
                return True
            else:
                logging.debug("Исчерпан лимит запросов")
        return False

    def extra_request(
        self, current_request_kwargs, request_kwargs_list, response, current_result
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
        try:
            key = RESPONSE_DICTIONARY_KEYS[request_kwargs['url']]
        except KeyError:
            raise KeyError('Для этого метода преобразование данных не настроено')
        else:
            new_data = []
            for r in results:
                data = r.get('result', {}).get(key, [])
                new_data += data
            return new_data


YandexDirect = generate_wrapper_from_adapter(YandexDirectClientAdapter)
