# Python библиотека для запросов к [API Яндекс Директ](https://yandex.ru/dev/direct/)

Написано на версии python 3.5

## Установка
```
pip install --upgrade git+https://github.com/pavelmaksimov/tapioca-wrapper#egg=tapioca-wrapper-2019.9.5
pip install --upgrade git+https://github.com/pavelmaksimov/tapioca-yandex-direct.git
```

## Примеры

Примеры находятся тут

## Документация

###### Справка Api Яндекс Директ https://yandex.ru/dev/direct/

``` python
from tapioca_yandex_direct import YandexDirect

ACCESS_TOKEN = {ваш токен доступа}

api = YandexDirect(
    # Токен доступа.
    access_token=ACCESS_TOKEN, 
    # Когда False не будет повторять запрос, если закончаться баллы.
    retry_if_not_enough_units=False,
    # Когда True cделает несколько запросов, если кол-во идентификаторов 
    # в условиях фильтрации SelectionCriteria будет больше, 
    # чем можно запросить в одном запросе. Работает для метода "get".
    auto_request_generation=True,
    # Когда True будет посылать запросы, пока не получит все объекты.
    receive_all_objects=True,
    # True включить песочницу.
    is_sandbox=True,
    # Если вы делаете запросы из под агентского аккаунта, 
    # вам нужно указать логин аккаунта для которого будете делать запросы.
    #login="{логин аккаунта Я.Директ}"
)
```

Генерация класса **YandexDirect** происходит динамически, 
поэтому узнать о добавленных в схему ресурсах, можно так.
``` python
print(dir(api))
```

## Запрос к ресурсу API. 
Запросы к API выполняются по протоколу HTTPS методом POST.
Входные структуры данных передаются в теле запроса.

```python
# Получить все кампании.
body = {
    "method": "get",
    "params": {
        "SelectionCriteria": {},
        "FieldNames": ["Id","Name"],
    },
}
result = api.campaigns().post(data=body)

# Создать кампанию.
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
result = api.campaigns().post(data=body)
```

#### Формат возвращаемых данных.
Данные возвращаются в формате объекта **Tapioca**.

```python
print(result)
print(result().status_code)
print(result().response)
print(result().response.headers)
``` 
##### Вернуть в формате **JSON**
```python
print(result().data)
[{'result': {'Campaigns': [{'Id': 338151,
                            'Name': 'Test API Sandbox campaign 1'}],
             'LimitedBy': 1}},
 {'result': {'Campaigns': [{'Id': 338152,
                            'Name': 'Test API Sandbox campaign 2'}],
             'LimitedBy': 2}},]
# В списке может находится несколько ответов.
```
##### Преобразование ответа

Для ответов API Я.Директ есть функция преобразования **transform**.
Она извлечет данные из словаря и соединит все ответы в один список, 
если запросов было несколько.
Работает только запросов с методом "get".
```python
print(result().transform())
[{'Id': 338151, 'Name': 'Test API Sandbox campaign 1'},
 {'Id': 338152, 'Name': 'Test API Sandbox campaign 2'}]
```

## Примеры
Больше примеров есть в [Ipython Notebook](https://github.com/pavelmaksimov/tapioca-yandex-direct/blob/master/examples.ipynb)

## Фичи
Открыть документация метода
```python
api.campaigns().open_docs()
```

Послать запрос в браузере.
```python
api.campaigns().open_in_browser()
```


## Зависимости
- requests 
- [tapioca_wrapper](https://github.com/pavelmaksimov/tapioca-wrapper) 

## Автор
Павел Максимов

Связаться со мной можно в 
[Телеграм](https://t.me/pavel_maksimow) 
и в 
[Facebook](https://www.facebook.com/pavel.maksimow)

Удачи тебе, друг! Поставь звездочку ;)

## Другое
- Как работает обертка [Tapioca](http://tapioca-wrapper.readthedocs.org/en/stable/quickstart.html)
