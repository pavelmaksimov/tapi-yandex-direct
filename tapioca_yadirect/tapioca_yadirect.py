# coding: utf-8
import logging
import time
import datetime as datetime_
from datetime import datetime, timedelta
import json

import pandas as pd
import requests
from dateutil import parser
from pandas.io.json import json_normalize
from tapioca import (
    TapiocaAdapter, generate_wrapper_from_adapter, JSONAdapterMixin, )
from tapioca.exceptions import ResponseProcessException, ClientError, ServerError, NotFound404Error
from tapioca_yadirect import exceptions
from .resource_mapping import RESOURCE_MAPPING_V5

logging.basicConfig(level=logging.INFO)


class YadirectClientAdapter(JSONAdapterMixin, TapiocaAdapter):
    end_point = 'https://{}/'
    api_root = end_point

    PRODUCTION_HOST = 'api.direct.yandex.com'
    SANDBOX_HOST = 'api-sandbox.direct.yandex.com'

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
        version = kwargs.get('v')
        if version:
            if version == 5:
                self.resource_mapping = RESOURCE_MAPPING_V5
            else:
                raise Exception('Для версии {} не указана схема ресурсов'.format(version))
        else:
            self.resource_mapping = RESOURCE_MAPPING_V5

        super().__init__(*args, **kwargs)

    def get_api_root(self, api_params):
        if api_params.get('is_sandbox', False):
            return self.end_point.format(self.SANDBOX_HOST)
        return self.end_point.format(self.PRODUCTION_HOST)

    def get_request_kwargs(self, api_params, *args, **kwargs):
        params = super().get_request_kwargs(api_params, *args, **kwargs)

        token = api_params.get('access_token')
        if token:
            params['headers'].update(
                {'Authorization': 'Bearer {}'.format(token)})

        login = api_params.get('login')
        if login:
            params['headers'].update({'Client-Login': login})

        use_operator_units = api_params.get('use_operator_units')
        if use_operator_units:
            params['headers'].update({'Use-Operator-Units': use_operator_units})

        if api_params.get('language', False):
            params['headers'].update(
                {'Accept-Language': api_params.get('language')})
        else:
            params['headers'].update({'Accept-Language': 'ru'})

        return params

    def get_error_message(self, data, response=None):
        try:
            if not data and response.content.strip():
                data = json.loads(response.content.decode('utf-8'))

            if data:
                return data.get('error', None)
        except json.JSONDecodeError:
            return response.text

    def process_response(self, response):
        if response.status_code == 404:
            raise ResponseProcessException(NotFound404Error, None)
        elif 500 <= response.status_code < 600:
            raise ResponseProcessException(ServerError, None)

        data = self.response_to_native(response)

        if 400 <= response.status_code < 500:
            raise ResponseProcessException(ClientError, data)

        data = super().process_response(response)
        if data.get('error'):
            raise ResponseProcessException(ClientError, data)
        return data

    def wrapper_call_exception(self, response, tapioca_exception,
                               api_params, *args, **kwargs):

        if 500 <= response.status_code < 600:
            raise exceptions.YadirectServerError(response)
        else:
            try:
                jdata = response.json()
            except json.JSONDecodeError:
                raise exceptions.YadirectApiError(response)
            else:
                error_code = jdata.get('error').get('error_code', 0)

                if error_code == 152:
                    raise exceptions.YadirectLimitError(response)
                elif error_code == 53:
                    raise exceptions.YadirectTokenError(response)
                else:
                    raise YadirectClientAdapter(response)

    def retry_request(self, response, tapioca_exception, api_params,
                      *args, **kwargs):
        """
        Условия повторения запроса.

        response = tapioca_exception.client().response
        status_code = tapioca_exception.client().status_code
        response_data = tapioca_exception.client().data
        """
        response_data = tapioca_exception.client().data
        error_code = response_data.get('error').get('error_code', 0)
        if error_code == 152:
            if api_params.get('retry_request_if_limit', False):
                logging.debug('Исчерпан лимит, повтор через 1 минуту')
                time.sleep(60)
                return True
            else:
                logging.debug('Исчерпан лимит запросов')
        return False

    def to_df(self, data, *args, **kwargs):
        """Преобразование в DataFrame"""
        print(*args, **kwargs)
        try:
            df = json_normalize(data.get('result'))
        except Exception:
            raise TypeError('Не удалось преобразовать в DataFrame')
        else:
            return df

    def extra_request(self, current_request_kwargs, request_kwargs_list,
                      response, current_result):
        limit = current_result.get('result', {}).get('LimitedBy', False)
        if limit:
            request_kwargs = current_request_kwargs.copy()
            request_kwargs['data'] = json.loads(request_kwargs['data'])

            if request_kwargs['data']['params'].get('Page'):
                request_kwargs['data']['params']['Page']['Offset'] = limit
            else:
                request_kwargs['data']['params']['Page'] = {"Offset": limit}

            request_kwargs['data'] = json.dumps(request_kwargs['data'])
            request_kwargs_list.append(request_kwargs)

        return request_kwargs_list


Yadirect = generate_wrapper_from_adapter(YadirectClientAdapter)

# class MytargetAuth:
#     OAUTH_TOKEN_URL = 'api/v2/oauth2/token.json'
#     DELETE_TOKEN_URL = 'api/v2/oauth2/token/delete.json'
#     OAUTH_USER_URL = 'oauth2/authorize'
#     GRANT_CLIENT = 'client_credentials'
#     GRANT_AGENCY_CLIENT = 'agency_client_credentials'
#     GRANT_RERFESH = 'refresh_token'
#     GRANT_AUTH_CODE = 'authorization_code'
#     OAUTH_ADS_SCOPES = ('read_ads', 'read_payments', 'create_ads')
#     OAUTH_AGENCY_SCOPES = (
#         'create_clients', 'read_clients', 'create_agency_payments'
#     )
#     OAUTH_MANAGER_SCOPES = (
#         'read_manager_clients', 'edit_manager_clients', 'read_payments'
#     )
#
#     def __init__(self, is_sandbox=False):
#         self.adapter = YadirectClientAdapter(access_token=None)
#         self.is_sandbox = is_sandbox
#
#     def _request_oauth(self, scheme, **kwargs):
#         """
#         https://target.my.com/adv/api-marketing/doc/authorization
#
#         :return: str, json
#         """
#         url = self.adapter.get_url_root(kwargs) + scheme
#         response = requests.post(url, data=kwargs)
#
#         if response.status_code == 403:
#             raise exceptions.YadirectTokenLimitError(response)
#         elif response.status_code == 401:
#             raise exceptions.YadirectTokenError(response)
#         elif 200 <= response.status_code < 300:
#             try:
#                 return response.json()
#             except Exception:
#                 return response.text
#         else:
#             raise exceptions.YadirectApiError(response)
#
#     def get_client_token(self, client_id, client_secret,
#                          permanent='false', **kwargs):
#         """
#         https://target.my.com/adv/api-marketing/doc/authorization
#
#         :param permanent: str : false|true : вечный токен
#         :return: {
#             "access_token": "...",
#             "token_type": "Bearer",
#             "expires_in": "None",
#             "refresh_token": "...",
#             "tokens_left": 0
#         }
#         """
#         return self._request_oauth(
#             scheme=self.OAUTH_TOKEN_URL, grant_type=self.GRANT_CLIENT,
#             client_id=client_id, client_secret=client_secret,
#             permanent=permanent, is_sandbox=self.is_sandbox, **kwargs)
#
#     def get_agency_client_token(self, client_id, client_secret,
#                                 agency_client_name,
#                                 permanent='false', **kwargs):
#         """
#         https://target.my.com/adv/api-marketing/doc/authorization
#
#         Эта схема протокола OAuth2 не является стандартной.
#         Она была реализована для того, чтобы дать возможность агентствам
#         и менеджерам создавать токены доступа для своих клиентов
#         без подтверждения от клиента. Схема очень похожа на стандартную
#         Client Credentials Grant за исключением того, что в запросе
#         нужно передавать дополнительный параметр "agency_client_name"
#         (username из запроса AgencyClients или ManagerClients)
#
#         :param agency_client_name: username из запроса AgencyClients или ManagerClients
#         :param permanent: str : false|true : вечный токен
#         :return:
#         """
#         return self._request_oauth(
#             scheme=self.OAUTH_TOKEN_URL,
#             grant_type=self.GRANT_AGENCY_CLIENT,
#             client_id=client_id, client_secret=client_secret,
#             agency_client_name=agency_client_name,
#             permanent=permanent, is_sandbox=self.is_sandbox,
#             **kwargs)
#
#     def oauth_url(self, client_id, scopes=OAUTH_ADS_SCOPES,
#                   state=None):
#         """
#         https://target.my.com/adv/api-marketing/doc/authorization
#         Формирует ссылку для перенаправления юзера на страницу авторизации
#
#         :param scopes: разрешения
#             В одном запросе могут быть указаны права разных групп.
#             myTarget определяет тип аккаунта текущего пользователя и
#             открывает только соответствующие права. Более того,
#             если в запросе, к примеру, перечислены все права,
#             и пользователь при этом является агентством, то ему будет
#             предложено выбрать к какому аккаунту он хочет
#             дать доступ - к агентсткому с агентскими правами,
#             какому-либо из менеджерских с менеджерскими или к одному
#             из клиентских с правами доступа к клиентским данным.
#
#             Для обычного пользователя-рекламодателя:
#             read_ads — чтение статистики и РК;
#             read_payments — чтение денежных транзакций и баланса;
#             create_ads — создание и редактирование настроек РК, баннеров,
#                 аудиторий (ставки, статус, таргетинги и т.п.).
#
#             Для пользователей-агентств и пользователей-представительств:
#             create_clients — создание новых клиентов;
#             read_clients — просмотр клиентов и операции от их имени;
#             create_agency_payments — переводы средств на счёта клиентов и обратно.
#
#             Для пользователей-менеджеров:
#             read_manager_clients — просмотр клиентов и операции от их имени;
#             edit_manager_clients — изменение параметров клиентов;
#             read_payments — чтение денежных транзакций и баланса;
#
#         :param state: сгенерированный на стороне клиента токен,
#             используется для предотвращения CSRF
#         :return: {'state': state, 'url': url}
#         """
#         url_root = self.adapter.get_url_root({'is_sandbox': self.is_sandbox})
#         if not state:
#             state = 'none123'
#         scopes = ','.join(map(str, scopes))
#         url = '{}{}?response_type=code&client_id={}&state={}&scope={}' \
#             .format(url_root, self.OAUTH_USER_URL, client_id, state, scopes)
#
#         return {'state': state, 'url': url}
#
#     def get_authorization_token(self, client_id, code, **kwargs):
#         """
#         https://target.my.com/adv/api-marketing/doc/authorization
#
#         :param code: код, полученный после авторизации
#         :return: {
#             "access_token": "...",
#             "token_type": "Bearer",
#             "expires_in": "None",
#             "refresh_token": "...",
#             "tokens_left": 0
#         }
#         """
#         return self._request_oauth(
#             scheme=self.OAUTH_TOKEN_URL, grant_type=self.GRANT_AUTH_CODE,
#             code=code, client_id=client_id, is_sandbox=self.is_sandbox,
#             **kwargs)
#
#     def refresh_token(self, client_id, client_secret,
#                       refresh_token, **kwargs):
#         """
#         https://target.my.com/adv/api-marketing/doc/authorization
#         Обновление токена доступа
#
#         :return: {
#           "access_token": "{new_access_token}",
#           "token_type": "bearer",
#           "scope": "{scope}",
#           "expires_in": "86400",
#           "refresh_token": "{refresh_token}"
#         }
#         """
#         return self._request_oauth(
#             scheme=self.OAUTH_TOKEN_URL, grant_type=self.GRANT_RERFESH,
#             refresh_token=refresh_token, client_id=client_id,
#             client_secret=client_secret, is_sandbox=self.is_sandbox,
#             **kwargs)
#
#     def delete_tokens(self, client_id, client_secret):
#         """https://target.my.com/adv/api-marketing/doc/authorization"""
#         return self._request_oauth(scheme=self.DELETE_TOKEN_URL,
#                                    client_id=client_id,
#                                    client_secret=client_secret,
#                                    is_sandbox=self.is_sandbox)
