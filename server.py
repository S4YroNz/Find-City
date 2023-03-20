from flask import Flask, request, jsonify
import logging
import json
import random

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# создаем словарь, в котором ключ — название города,
# а значение — массив, где перечислены id картинок,
# которые мы записали в прошлом пункте.

cities = {
    'москва': ['1030494/bde797d871ab9d68ae2d',
               '937455/839b64c4d7bba8b1072a'],
    'нью-йорк': ['1030494/b5a65957538bde9218bf',
                 '1652229/f551687ab964f8e1d310'],
    'париж': ["1540737/5e003414549e2fcd80ef",
              '965417/8fe1424f946aa9d99225']
}

# создаем словарь, где для каждого пользователя
# мы будем хранить его имя
sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info(f'Request: {request.json!r}')
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info(f'Response: {response!r}')
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']

    # если пользователь новый, то просим его представиться.
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови свое имя!'
        # создаем словарь в который в будущем положим имя пользователя
        sessionStorage[user_id] = {
            'first_name': None,
            'playing': False,
            'cities': cities
        }
        return

    # если пользователь не новый, то попадаем сюда.
    # если поле имени пустое, то это говорит о том,
    # что пользователь еще не представился.
    if sessionStorage[user_id]['first_name'] is None:
        # в последнем его сообщение ищем имя.
        first_name = get_first_name(req)
        # если не нашли, то сообщаем пользователю что не расслышали.
        if first_name is None:
            res['response']['text'] = \
                'Не расслышала имя. Повтори, пожалуйста!'
        # если нашли, то приветствуем пользователя.
        # И спрашиваем какой город он хочет увидеть.
        else:
            sessionStorage[user_id]['first_name'] = first_name
            res['response'][
                'text'] = 'Приятно познакомиться, ' \
                          + first_name.title() \
                          + '. Я - Алиса. Отгадаешь город по фото?'
            # получаем варианты buttons из ключей нашего словаря cities
            res['response']['buttons'] = [
                {
                    'title': city.title(),
                    'hide': True
                } for city in cities
            ]
    # если мы знакомы с пользователем и он нам что-то написал,
    # то это говорит о том, что он уже говорит о городе,
    # что хочет увидеть.
    else:
        if not sessionStorage[user_id]['playing']:
            if req['request']['original_utterance'].lower() == 'нет':
                res['response']['end_session'] = True
                return
            elif req['request']['original_utterance'].lower() == 'да':
                sessionStorage[user_id]['playing'] = True
                if len(sessionStorage[user_id]['cities']) == 0:
                    res['response']['end_session'] = True
                    return
                else:
                    card = choose_city(user_id)
                    res['response']['card'] = card
                return
        else:
            if get_country(req) == sessionStorage[user_id]['answer']:
                sessionStorage[user_id]['playing'] = False
                res['response']['text'] = 'Правильно! Сыграем еще?'
            else:
                if len(sessionStorage[user_id]['cities'][sessionStorage[user_id]['answer']]) != 0:
                    res['response']['card'] = {
                        "type": "BigImage",
                        "image_id": sessionStorage[user_id]['cities'][sessionStorage[user_id]['answer']][0],
                        "title": "Вот тебе еще одна картинка этого города",
                        "description": ""
                    }
                    del sessionStorage[user_id]['cities']['answer']
                    return
                else:
                    res['response']['text'] = f'Вы пытались. Это {sessionStorage[user_id]["answer"]}. Сыграем еще?'
                    del sessionStorage[user_id]['cities'][sessionStorage[user_id]['answer']]
                    sessionStorage[user_id]['playing'] = False
                    return


def choose_city(user_id):
    city = None
    while city is None:
        cities = sessionStorage[user_id]['cities']
        city = cities[random.choice(list(cities.keys()))]
        if len(cities[city]) == 0:
            del sessionStorage[user_id]['cities'][city]
            city = None
    sessionStorage[user_id]['answer'] = city
    return {
        "type": "BigImage",
        "image_id": city.pop(random.randint(0, len(city) - 1)),
        "title": "Что это за город?",
        "description": ""
    }


def get_country(req):
    # перебираем именованные сущности
    for entity in req['request']['nlu']['entities']:
        # если тип YANDEX.GEO то пытаемся получить город(city),
        # если нет, то возвращаем None
        if entity['type'] == 'YANDEX.GEO':
            # возвращаем None, если не нашли сущности с типом YANDEX.GEO
            return entity['value'].get('country', None)


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name',
            # то возвращаем ее значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
