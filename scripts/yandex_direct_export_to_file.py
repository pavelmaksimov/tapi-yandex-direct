import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from tapi_yandex_direct import YandexDirect, exceptions

LOGGING_FORMAT = "%(asctime)s [%(levelname)s] %(pathname)s:%(funcName)s  %(message)s"

logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_report_name(body: dict, headers: dict):
    return hash(str((body, headers)))


def prepare_body(body: dict, headers: dict):
    body["params"]["ReportName"] = create_report_name(body, headers)


def add_extra_data(row: dict, extra_columns: Iterable, login: Optional[str]):
    if "login" in extra_columns:
        row["login"] = login


def main(
    client: YandexDirect,
    body: dict,
    headers: dict,
    resource: str,
    extra_columns: Iterable,
    login: Optional[str],
    filepath: Path,
) -> None:
    response = None
    page_iterator = None
    api_error_retries = 5
    while True:
        try:
            if response is None:
                resource_method = getattr(client, resource)
                logger.info(f"Request resource '{resource}'")
                response = resource_method().post(data=body, headers=headers)

            if resource != "reports":

                if page_iterator is None:
                    page_iterator = response().pages()

                page = next(page_iterator)

        except exceptions.YandexDirectClientError as exc:
            error_code = int(exc.error_code)
            if error_code == 9000:
                continue
            elif error_code in (52, 1000, 1001, 1002):
                if api_error_retries:
                    api_error_retries -= 1
                    continue
            raise

        except (ConnectionError, TimeoutError):
            if api_error_retries:
                api_error_retries -= 1
                continue
            raise

        except StopIteration:
            break

        else:
            if resource == "reports":
                if response.status_code in (201, 202):
                    response = None
                    continue

            logger.info(f"Save data to {filepath}")

            if resource == "reports":
                if extra_columns:
                    with open(filepath, "w", newline='') as csvfile:
                        data_iterator = response().iter_dicts()

                        for i, row in enumerate(data_iterator):
                            if i == 0:
                                writer = csv.DictWriter(
                                    csvfile, fieldnames=row.keys(), dialect="excel-tab",
                                )
                                writer.writeheader()

                            add_extra_data(row, extra_columns, login)
                            writer.writerow(row)
                else:
                    with open(filepath, "w") as csvfile:
                        csvfile.write(response.data)

                # The report has no pagination.
                break
            else:
                with open(filepath, "w", newline='') as csvfile:
                    data_iterator = page().items()

                    for i, row in enumerate(data_iterator):
                        if i == 0:
                            writer = csv.DictWriter(
                                csvfile, fieldnames=row.keys(), dialect="excel-tab"
                            )
                            writer.writeheader()

                        add_extra_data(row, extra_columns, login)
                        writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export data from Yandex Direct to tsv file"
    )
    parser.add_argument(
        "--token",
        required=True,
        type=str,
        help="Access token, detail https://yandex.ru/dev/direct/doc/dg/concepts/auth-token.html",
    )
    parser.add_argument(
        "--login",
        required=False,
        type=str,
        help="If you are making inquiries from an agency account, you must be sure to specify the account login"
    )
    parser.add_argument(
        "--extra_columns",
        nargs='+',
        required=False,
        type=str,
        choices=["login"],
        default=[],
        help="",
    )
    parser.add_argument(
        "--body_filepath",
        required=True,
        type=str,
        help="Request body, detail https://yandex.ru/dev/direct/doc/dg/concepts/JSON.html#JSON__json-request "
             "and https://yandex.ru/dev/direct/doc/reports/spec.html",
    )
    parser.add_argument(
        "--filepath",
        required=True,
        type=str,
        help="File path for save data",
    )
    parser.add_argument(
        "--use_operator_units",
        required=False,
        type=bool,
        help="HTTP-header, detail https://yandex.ru/dev/direct/doc/reports/headers.html",
        default=False,
    )
    parser.add_argument(
        "--return_money_in_micros",
        required=False,
        type=bool,
        help="HTTP-header, detail https://yandex.ru/dev/direct/doc/reports/headers.html",
        default=False,
    )
    parser.add_argument(
        "--language",
        required=False,
        type=str,
        default="ru",
        help="The language in which the data for directories and errors will be returned",
    )

    parser.add_argument(
        "--resource",
        required=True,
        type=str,
        help="",
        choices=[
            "reports",
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
            "dictionaries",
            "dynamicads",
            "feeds",
            "keywordbids",
            "keywords",
            "keywordsresearch",
            "leads",
            "negativekeywordsharedsets",
            "retargeting",
            "sitelinks",
            "smartadtargets",
            "turbopages",
            "vcards",
        ],
    )
    args = parser.parse_args()

    client = YandexDirect(
        access_token=args.token,
        login=args.login,
        retry_if_not_enough_units=True,
        language=args.language,
        retry_if_exceeded_limit=True,
        retries_if_server_error=5,
        wait_report=True,
    )
    headers = {
        "use_operator_units": str(args.use_operator_units),
        "return_money_in_micros": str(args.return_money_in_micros),
    }

    with open(args.body_filepath) as f:
        body_text = f.read()

    body = json.loads(body_text)
    if args.resource == "reports":
        prepare_body(body, headers)

    main(
        client,
        body,
        headers,
        args.resource,
        args.extra_columns,
        args.login,
        args.filepath,
    )
