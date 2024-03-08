import json
import re
import time

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from openpyxl import Workbook
from selenium.common import NoSuchWindowException

from config import catalog, pages, headless, minimum_percentage, max_price, min_price, max_price_with_discounted, \
    cookie_file

wb = Workbook()

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"


def load_cookies():
    with open(cookie_file, encoding="utf-8", errors="ignore") as config_file:
        cookies = json.load(config_file)
    return [[cookie["name"], cookie["value"]] for cookie in cookies]


def parse(driver, page: int):
    url = f"https://megamarket.ru/catalog/{catalog}/page-{page}"
    driver.get(url)
    html = BeautifulSoup(driver.page_source, "html.parser")
    catalog_items = html.find("div", class_="catalog-listing-content")
    if catalog_items is None:
        print(f"Нет каталога | Рекурсия на странице {url}")
        return parse(driver, page)

    items = catalog_items.find_all("div", class_="item-block")
    if len(items) == 0:
        print(f"0 Предметов | Рекурсия на странице {url}")
        return parse(driver, page)

    for item in items:
        item_bonus = item.find("div", class_="item-bonus")
        if item_bonus is None:
            continue
        item_title = item.find("a", class_="ddl_product_link").text.strip()
        usual_price = int(
            re.findall(r"\d+", item.find("div", class_="item-price").find("span").text.replace(" ", ""))[0])
        percentage_discount = int(
            re.findall(r"\d+", item_bonus.find("span", class_="bonus-percent").text.replace(" ", ""))[0])
        number_of_bonuses = int(item_bonus.find("span", class_="bonus-amount").text.replace(" ", ""))
        discounted_price = usual_price - number_of_bonuses

        if percentage_discount < minimum_percentage:
            continue
        if usual_price > max_price:
            continue
        if usual_price < min_price:
            continue
        if discounted_price > max_price_with_discounted:
            continue

        item_url = "https://megamarket.ru" + item.find("a", class_="ddl_product_link").get("href").strip()
        print(f"{time.strftime('%H:%M:%S %d/%m/%Y')}\n"
              f"Название: {item_title}\n"
              f"Цена со скидкой: {discounted_price}\n"
              f"Цена без скидки: {usual_price}\n"
              f"Количество бонусов: {number_of_bonuses}\n"
              f"Скидка в процентах: {percentage_discount}\n"
              f"Ссылка: {item_url}\n\n")

        ws = wb.active
        ws.append([
            item_title,
            discounted_price,
            usual_price,
            number_of_bonuses,
            percentage_discount,
            item_url
        ])

        wb.save(f"{catalog}.xlsx")

    return True


def main():
    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={user_agent}")
    options.add_argument('--disable-notifications')
    if headless:
        options.add_argument("--headless")
    driver = uc.Chrome(options=options)
    driver.get("https://megamarket.ru/")
    cookies = load_cookies()
    print("Подгрузка куки файлов")
    for name, value in cookies:
        driver.add_cookie({"name": name, "value": value})
    driver.get("https://megamarket.ru/")
    print("Start")

    try:
        current_page = 1

        ws = wb.active
        ws.append([
            "Название",
            "Цена со скидкой",
            "Цена без скидки",
            "Количество бонусов",
            "Скидка в процентах",
            "Ссылка"
        ])
        while current_page != pages + 1:
            result = parse(driver, current_page)
            if result:
                print(f"{time.strftime('%H:%M:%S %d/%m/%Y')} | {current_page} / {pages}")
            else:
                break
            current_page += 1

        print("Все товары просмотрены")

    except Exception as e:
        print(e)
    finally:
        try:
            driver.close()
            driver.quit()
        except NoSuchWindowException:
            driver.quit()

    print("Finish")


if __name__ == "__main__":
    main()
