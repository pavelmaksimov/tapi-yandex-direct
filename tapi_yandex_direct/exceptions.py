# -*- coding: utf-8 -*-
import logging
import json


class YandexDirectApiError(Exception):
    def __init__(self, response, message=None, *args, **kwargs):
        self.response = response
        self.message = message

    def __str__(self):
        logging.info("HEADERS = " + str(self.response.headers))
        logging.info("URL = " + self.response.url)
        return "{}{} {} {}".format(
            self.message + " " or "",
            self.response.status_code,
            self.response.reason,
            self.response.text,
        )


class YandexDirectServerError(YandexDirectApiError):
    pass


class YandexDirectClientError(YandexDirectApiError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jdata = json.loads(self.response.content, encoding="utf8")
        error_data = self.jdata.get("error", {})
        self.code = error_data.get("error_code")
        self.request_id = error_data.get("request_id")
        self.error_string = error_data.get("error_string")
        self.error_detail = error_data.get("error_detail")

    def __str__(self):
        str = "\n\trequest_id={},\n\tcode={},\n\terror_string={},\n\terror_detail={}"
        return str.format(
            self.request_id, self.code, self.error_string, self.error_detail
        )


class YandexDirectTokenError(YandexDirectClientError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class YandexDirectLimitError(YandexDirectApiError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return (
            "{} {} Исчерпан лимит запросов. "
            "Повторите запрос через некоторое время.\n "
            "{}".format(
                self.response.status_code, self.response.reason, self.response.text
            )
        )
