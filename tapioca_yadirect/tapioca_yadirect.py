# coding: utf-8
import json
import logging
import time

from tapioca import TapiocaAdapter, generate_wrapper_from_adapter, JSONAdapterMixin
from tapioca.exceptions import ResponseProcessException, ClientError

from tapioca_yadirect import exceptions
from .resource_mapping import RESOURCE_MAPPING_V5


class YadirectClientAdapter(JSONAdapterMixin, TapiocaAdapter):
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

        low_api = Yadirect(access_token=ACCESS_TOKEN,
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

    def get_request_kwargs(self, api_params, *args, **kwargs):
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

    def process_response(self, response):
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
                    raise YadirectClientAdapter(response)

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
        error_code = response_data.get("error", {}).get("error_code", 0)
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
            request_kwargs = current_request_kwargs.copy()
            request_kwargs["data"] = json.loads(request_kwargs["data"])

            if request_kwargs["data"]["params"].get("Page"):
                request_kwargs["data"]["params"]["Page"]["Offset"] = limit
            else:
                request_kwargs["data"]["params"]["Page"] = {"Offset": limit}

            request_kwargs["data"] = json.dumps(request_kwargs["data"])
            request_kwargs_list.append(request_kwargs)

        return request_kwargs_list


Yadirect = generate_wrapper_from_adapter(YadirectClientAdapter)
