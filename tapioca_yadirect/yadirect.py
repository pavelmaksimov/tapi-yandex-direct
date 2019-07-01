# -*- coding: utf-8 -*-
import datetime as datetime_
import logging
from datetime import datetime, timedelta

import pandas as pd
from dateutil import parser
from pandas.io.json import json_normalize

from tapioca_yadirect import Yadirect
from tapioca_yadirect.tapioca_yadirect import YadirectClientAdapter

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
ID_FIELDS = [
    "CampaignIds",
    "AdGroupIds",
    "Ids",
    "AdIds",
    "Logins",
    "RetargetingListIds",
    "InterestIds",
    "AccountIDS",
    "KeywordIds",
]
DICT_KEY_RESPONCE = {
    "campaigns": "Campaigns",
    "adgroups": "AdGroups",
    "ads": "Ads",
    "audiencetargets": "AudienceTargets",
    "dynamictextadtargets": "Webpages",
    "creatives": "Creatives",
    "adimages": "AdImages",
    "vcards": "VCards",
    "sitelinks": "SitelinksSets",
    "adextensions": "AdExtensions",
    "keywords": "Keywords",
    "retargetinglists": "RetargetingLists",
    "bids": "Bids",
    "keywordbids": "KeywordBids",
    "bidmodifiers": "BidModifiers",
    "clients": "Clients",
    "agencyclients": "Clients",
    "leads": "Leads",
    "changes": NotImplementedError(),
    "dictionaries": NotImplementedError(),
    "keywordsresearch": NotImplementedError(),
    "balance": NotImplementedError(),
}
# Максимальное кол-во параллельных потоков.
SIZE_POOL = 5


class YadirectLight:
    CAMPAIGN_STATS = "campaigns"
    BANNER_STATS = "banners"
    USER_STATS = "users"
    _SUMMARY_STATS = "summary"
    _DAY_STATS = "day"

    def __init__(
        self,
        access_token,
        as_dataframe=False,
        retry_request_if_limit=True,
        language="ru",
        *args,
        **kwargs
    ):
        """
        Обертка над низкоуровневой оберткой Yadirect.

        :param access_token: str : токен доступа
        :param as_dataframe: bool : преобразовывать в DataFrame
        :param retry_request_if_limit: bool : ожидать и повторять запрос,
            если закончилась квота запросов к апи.
        :param default_url_params: dict : параметры по умолчанию для вставки в url
        :param language: str : ru|en|{other} :
            язык в котором будут возвращены некоторые данные, например справочников.
        :param args:
        :param kwargs:
        """
        self._adapter = YadirectClientAdapter(
            access_token=access_token,
            retry_request_if_limit=retry_request_if_limit,
            language=language,
            *args,
            **kwargs
        )
        self.low_api = Yadirect(
            access_token=access_token,
            retry_request_if_limit=retry_request_if_limit,
            language=language,
            *args,
            **kwargs
        )
        self.as_dataframe = as_dataframe

    def _grouper_list(self, arr, count):
        """Делит список на мелкие списки по размеру в count"""
        if count == 1:
            return [[i] for i in arr]
        else:
            count = len(arr) // count + 1
            return [arr[i::count] for i in range(count)]

    def _period_range(self, date_from, date_to, delta):
        """
        Генерация периодов для получения статистики.

        :param delta: int : кол-во дней в одном периоде
        :return: [..., ('2019-01-01', '2019-01-01')]
        """
        if not isinstance(date_from, datetime) and not isinstance(
            date_from, datetime_.date
        ):
            date_from = parser.parse(date_from)
        if not isinstance(date_from, datetime) and not isinstance(
            date_from, datetime_.date
        ):
            date_to = parser.parse(date_to)

        periods = []
        dt2 = None
        while True:
            dt1 = dt2 + timedelta(1) if dt2 else date_from
            dt2 = dt1 + timedelta(delta)
            if dt2 > date_to:
                if dt1 <= date_to:
                    periods.append(
                        (dt1.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d"))
                    )
                break
            periods.append((dt1.strftime("%Y-%m-%d"), dt2.strftime("%Y-%m-%d")))
        return periods

    def _stats_to_df(self, results):
        """Преобразует данные статистики в dataframe."""
        try:
            df_list = []
            for result in results:
                result = result().data
                for i in result["items"]:
                    rows = i.get("rows") or i.get("total")
                    df_ = json_normalize(rows)
                    df_["id"] = i["id"]
                    df_list.append(df_)
            df = pd.concat(df_list, sort=False).reset_index(drop=True)
        except Exception:
            raise TypeError("Не удалось преобразовать в DataFrame")
        else:
            return df

    def _objects_to_df(self, results):
        """Преобразует данные объектов в dataframe."""
        try:
            df_list = []
            for result in results:
                data = result().data
                df_ = json_normalize(data.get("items") or result)
                df_list.append(df_)
            df = pd.concat(df_list, sort=False).reset_index(drop=True)
        except Exception:
            raise TypeError("Не удалось преобразовать в DataFrame")
        else:
            return df

    def _to_format(self, method, results, as_dataframe=None, is_union_results=True):
        """Преобразует в указанный формат."""
        if (self.as_dataframe and as_dataframe is not False) or as_dataframe:
            if method == self.get_stats.__name__:
                return self._stats_to_df(results)
            else:
                return self._objects_to_df(results)

        elif is_union_results:
            # Объединить данные в один список.
            union = []
            for result in results:
                try:
                    union += result().data["items"]
                except KeyError:
                    logging.info("Не смог найти ключ items в {}".format(result))
                    raise
            return union
        else:
            # Каждый ответ отдельно, в списке.
            return results

    def _request_objects(
        self, resource, limit=None, params=None, limit_in_request=50, as_dataframe=False
    ):
        """Метод запрашивает все объекты."""
        if params and params.get("limit"):
            raise ValueError("Укажите limit при вызове метода, а не в параметре.")
        params = params or {}
        offset = params.get("offset") or 0
        # 1 ставим, чтоб сделать первый запрос,
        # далее из ответа станет ясно, сколько еще сделать запросов.
        count = limit or 1
        results = []
        while count > offset:
            if limit and limit_in_request > limit:
                limit_in_request = limit
            if limit and (count - offset) / limit_in_request < 1:
                # При последнем запросе, нужно ограничить
                # кол-во запрашиваемых объектов до оставшегося кол-ва.
                limit_in_request = count - offset

            params_ = {"limit": limit_in_request, "offset": offset, **params}
            result = resource.get(params=params_)
            data = result().data
            results.append(result)

            if not data.get("count"):
                # Есть нет count, значит есть только один объект.
                break
            elif limit and data.get("count") < limit:
                # Если объектов меньше, чем указанно в limit,
                # то уменьшается кол-во объектов которое будет получено.
                count = data.get("count")
            elif limit:
                # Запрашивается столько объектов сколько в limit.
                count = limit
            else:
                # Получение всех объектов.
                count = data.get("count")

            offset = data["offset"] + limit_in_request

        return self._to_format(
            self._request_objects.__name__, results, as_dataframe=as_dataframe
        )

    def _get_objects_for_request_stats(self, object_type, limit):
        """
        Получение идентификаторов объектов,
        по которым будет запрошена статистика.
        """
        if object_type == self.CAMPAIGN_STATS:
            data = self.get_campaigns(
                limit=limit, as_dataframe=False, params={"fields": "id"}
            )
            ids = [i["id"] for i in data]

        elif object_type == self.BANNER_STATS:
            data = self.get_banners(
                limit=limit, as_dataframe=False, params={"fields": "id"}
            )
            ids = [i["id"] for i in data]

        elif object_type == self.USER_STATS:
            r = self.low_api.user2().get()
            data = r().data
            ids = [data["id"]]
        else:
            raise ValueError(
                "Не известный object_type, "
                "разерешены только: {}, {}, {}".format(
                    self.CAMPAIGN_STATS, self.BANNER_STATS, self.USER_STATS
                )
            )
        return ids

    def get_stats(
        self,
        object_type=CAMPAIGN_STATS,
        date_from=None,
        date_to=None,
        metrics=None,
        ids=None,
        as_dataframe=None,
        limit=None,
        limit_in_request=200,
        interval=92,
        is_union_results=True,
    ):
        """
        https://target.my.com/adv/api-marketing/doc/stat-v2

        Если не указаны date_from и date_to, то вернется суммарная статистика.
        Если не указаны идентификаторы объектов в ids, то они все будут получены
        и вставлены в запрос статистики. Ограничить можно через limit.

        :param object_type: str : banners|campaigns|users :
            Если нету, то будет сделан запрос объектов и
            потом вставлены в запрос к статистике.
        :param date_from: none, str, datatime : YYYY-MM-DD[THH:MM[:SS]] :
            Начальная дата. Только для day.json.
            Если отсутствует, будет запрошена стат. за все время.
        :param date_to: none, str, datatime : YYYY-MM-DD[THH:MM[:SS]] :
            Конечная дата (включительно). Только для day.json.
            Если отсутствует, будет запрошена стат. за все время.
        :param ids: list : Список идентификаторов баннеров, кампаний или пользователей.
        :param metrics: str, list : Список наборов метрик.
        :param as_dataframe: bool : преобразовать в формат Pandas DataFrame.
        :param limit: int : Макс. кол-во случайных объектов,
            для которых запросить статистику. Например для теста.
        :param interval: int : кол-во дней в периоде в одном запросе, максимум 92
        :param is_union_results: bool : объединить результаты в один список
        :return dict, list :

        if as_dataframe True:
            DataFrame
        elif is_union_results True:
            [{"items": [...], "total": [...]},
             {"items": [...], "total": [...]}]
        elif is_union_results False:
            {"items": [...], "total": [...]}

        =====

        data: {
            "items": [{
                "id": 857683,
                "rows": [{
                    "date": "2017-09-20",
                    "base": {
                        "shows": 123757,
                        "clicks": 672,
                        "goals": 9,
                        "spent": "155.8",
                        "cpm": "1.25",
                        ...
                    },
                    "events": {
                        "opening_app": 0,
                        "opening_post": 0,
                        "moving_into_group": 0,
                        "clicks_on_external_url": 0,
                        ...
                    },
                    "uniques": {...},
                    "video": {...},
                    "viral": {...},
                    "tps": {...}
                },
                {
                    "date": "2017-09-21",
                    "base": {...},
                    "events": {...},
                    "uniques": {...},
                    "video": {...},
                    "viral": {...},
                    "tps": {...}
                }],
                "total": {
                    "base": {...},
                    "events": {...},
                    "uniques": {...},
                    "video": {...},
                    "viral": {...},
                    "tps": {...}
                }
            }],
            "total": {
                "base": {...},
                "events": {...},
                "video": {...},
                "viral": {...},
                "tps": {...}
            }
        }
        """
        if limit_in_request > 200:
            raise ValueError("limit_in_request должен быть <= 200")
        if interval > 92:
            raise ValueError("delta_period должен быть <= 92")
        if interval < 1:
            raise ValueError("interval должен быть больше 0")

        if not ids:
            ids = self._get_objects_for_request_stats(object_type, limit=limit)

        get_params = {}
        if metrics:
            if isinstance(metrics, list):
                metrics = ",".join(map(str, metrics))
            get_params.update(metrics=metrics)

        if date_from or date_to:
            # Макс. период запроса 92 дня.
            # Если запрашиваемый интервал превышает,
            # то разделяется на несколько перидов.
            time_mode = self._DAY_STATS
            periods = self._period_range(date_from, date_to, delta=interval - 1)
        else:
            time_mode = self._SUMMARY_STATS
            periods = [{}]

        # Создаются список списков из объектов, для запросов.
        # Макс. кол-во объектов для запроса 200 дня.
        ids_groups = self._grouper_list(ids, limit_in_request)

        results = []
        for ids in ids_groups:
            ids_str = ",".join(map(str, ids))

            for period in periods:
                if period:
                    get_params.update(date_from=period[0])
                    get_params.update(date_to=period[1])

                result = self.low_api.stats2(
                    object_type=object_type, time_mode=time_mode, ids=ids_str
                ).get(params=get_params)

                results.append(result)

        return self._to_format(
            self.get_stats.__name__, results, as_dataframe, is_union_results
        )

    def get_campaigns(
        self, params=None, as_dataframe=None, limit=None, limit_in_request=50
    ):
        """
        https://target.my.com/doc/apiv2/ru/resources/campaigns.html
        https://target.my.com/doc/apiv2/ru/objects/ads2.api_v2.campaigns.CampaignResource.html

        :param limit: int : количество объектов в ответе, если None будут получены все
        :param params: dict :
            Поля
                fields=age_restrictions,audit_pixels,autobidding_mode,banner_uniq_shows_limit,budget_limit,budget_limit_day,cr_max_price,created,date_end,date_start,delivery,enable_utm,id,issues,mixing,name,objective,package_id,price,priced_goal,pricelist_id,shows_limit,status,targetings,uniq_shows_limit,uniq_shows_period,updated,utm
            Фильтры
                _id=6617841
                _id__in=6617841,6711647
                _status=active
                _status__ne=active
                _status__in=active,blocked
                _last_updated__gt=2018-01-01 00:00:00
                _last_updated__gte=2018-01-01 00:00:00
                _last_updated__lt=2018-01-01 00:00:00
                _last_updated__lte=2018-01-01 00:00:00
            Сортировка
                sorting=id - по возрастанию
                sorting=-id - по убыванию
                sorting=name - по возрастанию
                sorting=-name - по убыванию
                sorting=status - по возрастанию
                sorting=-status - по убыванию
            по нескольким полям
                sorting=status,name,-id
        :param limit_in_request: int : кол-во объектов в одном запросе
        :param as_dataframe: bool : вернуть в формате dataframe
        :return: list, dataframe
        """
        return self._request_objects(
            resource=self.low_api.campaigns2(),
            limit=limit,
            params=params,
            limit_in_request=limit_in_request,
            as_dataframe=as_dataframe,
        )

    def get_banners(
        self, params=None, as_dataframe=None, limit=None, limit_in_request=50
    ):
        """
        https://target.my.com/doc/apiv2/ru/resources/banners.html
        https://target.my.com/doc/apiv2/ru/objects/ads2.api_v2.banners.BannerResource.html

        :param limit: int : количество объектов в ответе,
            по умолчанию будут получены все
        :param params: dict :
            Поля
                fields=call_to_action,campaign_id,content,created,deeplink,delivery,id,issues,moderation_reasons,moderation_status,products,status,textblocks,updated,urls,user_can_request_remoderation,video_params
            Фильтры
                _id=26617841
                _id__in=26617841,26711647
                _campaign_id=6617841
                _campaign_id__in=6617841,6711647
                _campaign_status=active
                _campaign_status__ne=active
                _campaign_status__in=active,blocked
                _status=active
                _status__ne=active
                _status__in=active,blocked
                _updated__gt=2018-01-01 00:00:00
                _updated__gte=2018-01-01 00:00:00
                _updated__lt=2018-01-01 00:00:00
                _updated__lte=2018-01-01 00:00:00
                _url=mail.ru
                _textblock=купить насос
        :param limit_in_request: int : кол-во объектов в одном запросе
        :param as_dataframe: bool : вернуть в формате dataframe
        :return: list, dataframe
        """
        return self._request_objects(
            resource=self.low_api.banners2(),
            limit=limit,
            params=params,
            limit_in_request=limit_in_request,
            as_dataframe=as_dataframe,
        )
