import requests
import xmltodict
from datetime import datetime
import eel

# получить список товаров по запросу
@eel.expose
def get_sorted_plati_goods(
        query: str,
        sort_by: str = 'no_sort',
        pagesize=500,  # по умолчанию берем максимальный
        get_pages_num: int = 1,  # по умолчанию берем первую
        visibleonly='true',
        response='xml',  # берем xml тк только в нем инфа о последней продаже
        max_days_since_last_sale: int = 1,
        min_usd_price: float = 0,
        max_usd_price: float = 99999,
        min_numsold: int = 1,
        neg_filters: list = [],
        pos_filters: list = []
):

    # получить товары с plati
    def get_plati_goods():

        url = 'https://plati.io/api/search.ashx'
        goods_data = []
        for pnum in range(1, get_pages_num + 1):
            params = {
                'query': query,
                'pagesize': pagesize,
                'pagenum': pnum,
                'visibleOnly': visibleonly,
                'response': response
            }
            resp = requests.get(url, params=params)

            # конверируем полученный xml в dict
            data_dict = xmltodict.parse(resp.content)
            # результаты не найдены
            if not data_dict['search_result'].get('item'):
                continue

            else:

                if data_dict['search_result'].get('@total') == '1':
                    goods_data.append(data_dict['search_result']['item'])
                else:
                    # достаем list с данными о товарах
                    goods_data.extend(data_dict['search_result']['item'])

            # прервать цикл если результатов меньше, чем заданный максимум
            if int(data_dict['search_result'].get('@total')) < pagesize:
                break

        return goods_data

    # отфильтровать список товаров
    def filter_plati_goods(goods_data):

        # по нег. фильтрам
        neg_filtered_names_goods = []
        if neg_filters:
            for g_d in goods_data:
                neg_filtered = False
                for n_f in neg_filters:
                    if n_f.lower() in g_d['name'].lower():
                        neg_filtered = True
                if not neg_filtered:
                    neg_filtered_names_goods.append(g_d)
        else:
            neg_filtered_names_goods = goods_data

        # по поз. фильтрам
        pos_filtered_names_goods = []
        if pos_filters:
            for g_d in neg_filtered_names_goods:
                pos_filtered = False
                for p_f in pos_filters:
                    if p_f.lower() in g_d['name'].lower():
                        pos_filtered = True
                if pos_filtered:
                    pos_filtered_names_goods.append(g_d)
        else:
            pos_filtered_names_goods = neg_filtered_names_goods

        # по кол-ву продаж
        filtered_numsold = []
        for names in pos_filtered_names_goods:
            if float(names['numsold']) >= min_numsold:
                filtered_numsold.append(names)

        # по цене
        filtered_price = []
        for numsold in filtered_numsold:
            if min_usd_price <= float(numsold['price_usd']) <= max_usd_price:
                filtered_price.append(numsold)

        return filtered_price


    # отсортировать полученный список
    available_sorts = ['no_sort', 'by_numsold', 'by_last_sale', 'by_price_usd', 'by_price_rub']
    if sort_by not in available_sorts:
        raise ValueError(f"Выбран неверный способ сортировки. Доступные: {available_sorts}")
    def sort_plati_goods(goods_data):

        if sort_by == 'no_sort':
            return goods_data
        elif sort_by == 'by_numsold':
            goods_data.sort(key=lambda g_d: float(g_d['numsold']))
            goods_data.reverse()
            return goods_data
        elif sort_by == 'by_last_sale':
            goods_data.sort(key=lambda g_d: g_d['last_sale'])
            goods_data.reverse()
            return goods_data
        elif sort_by == 'by_price_usd':
            goods_data.sort(key=lambda g_d: float(g_d['price_usd']))
            return goods_data
        elif sort_by == 'by_price_rub':
            goods_data.sort(key=lambda g_d: float(g_d['price_rur']))
            return goods_data

    # добавить в каждый товар "человеческую дату"
    def humanize_and_filter_date(goods_data):

        date_now = datetime.now()
        filtered_date = []
        for g_d in goods_data:

            try:
                plati_last_sale_datetime = datetime.strptime(g_d['last_sale'], "%Y-%m-%dT%H:%M:%S.%f")
            except:
                plati_last_sale_datetime = datetime.strptime(g_d['last_sale'], "%Y-%m-%dT%H:%M:%S")

            date_diff = date_now - plati_last_sale_datetime

            # пропустить товары с продажами более указанного кол-ва дней
            if date_diff.days > max_days_since_last_sale:
                continue

            if date_diff.days > 0:
                g_d['hum_last_sale'] = f'{date_diff.days} дн. назад'
                g_d['last_sale_timestamp'] = plati_last_sale_datetime.timestamp()
            elif date_diff.seconds // 3600 > 0:
                hours_diff = date_diff.seconds // 3600
                g_d['hum_last_sale'] = f'{hours_diff} час. назад'
                g_d['last_sale_timestamp'] = plati_last_sale_datetime.timestamp()
            else:
                mins_diff = date_diff.seconds // 60
                g_d['hum_last_sale'] = f'{mins_diff} мин. назад'
                g_d['last_sale_timestamp'] = plati_last_sale_datetime.timestamp()

            filtered_date.append(g_d)

        return filtered_date

    goods_data = get_plati_goods()
    if not goods_data:
        return None
    filtered_goods = filter_plati_goods(goods_data)
    sorted_goods_data = sort_plati_goods(filtered_goods)
    result = humanize_and_filter_date(sorted_goods_data)

    total_numsold = sum(int(r['numsold']) for r in result)
    print(f'Всего продаж по запросу: {total_numsold}')
    print(result)

    return result

if __name__ == '__main__':
    get_sorted_plati_goods('mortal combat steam ключ')