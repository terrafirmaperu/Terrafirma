from config.wsgi import *
from django.db.models import F
import requests
import json
import random
from random import randint
from config import settings
from core.pos.models import *

# src = os.path.join(settings.BASE_DIR, 'deploy/data/productos.json')
# print(src)
from core.security.models import *


def insert_products():
    with open(f'{settings.BASE_DIR}/deploy/json/products.json', encoding='utf8') as json_file:
        data = json.load(json_file)
        for p in data['rows'][0:80]:
            row = p['value']
            category = Category.objects.filter(name=row['marca'])
            if not category.exists():
                category = Category()
                category.name = row['marca']
                category.save()
            else:
                category = category[0]
            p = Product()
            p.name = row['nombre']
            p.category_id = category.id
            p.price = randint(1, 10)
            p.pvp = (float(p.price) * 0.12) + float(p.price)
            p.save()
            print(p.name)


def insert_purchase():
    for i in range(1, 5):
        purchase = Purchase()
        purchase.payment_condition = 'contado'
        purchase.save()

        for d in range(1, 20):
            det = PurchaseDetail()
            det.purchase_id = purchase.id
            det.product_id = randint(1, Product.objects.all().count())
            while purchase.purchasedetail_set.filter(product_id=det.product_id).exists():
                det.product_id = randint(1, Product.objects.all().count())
            det.cant = randint(1, 50)
            det.price = det.product.pvp
            det.subtotal = float(det.price) * det.cant
            det.save()
            det.product.stock += det.cant
            det.product.save()

        purchase.calculate_invoice()
        print(i)


def insert_sale():
    user = User()
    user.first_name = 'Ana Gabriela'
    user.last_name = 'Matute Guamán'
    user.dni = '0928745123'
    user.email = 'gabrielamatuteg1@gmail.com'
    user.username = user.dni
    user.set_password(user.dni)
    user.save()
    client = Client()
    client.user = user
    client.mobile = '0979014553'
    client.address = 'Milagro, cdla. Dager avda tumbez y zamora'
    client.save()
    for i in range(1, 11):
        sale = Sale()
        sale.client_id = 1
        sale.iva = 0.12
        sale.save()
        for d in range(1, 8):
            numberList = list(Product.objects.filter(stock__gt=0).values_list(flat=True))
            det = SaleDetail()
            det.sale_id = sale.id
            det.product_id = random.choice(numberList)
            while sale.saledetail_set.filter(product_id=det.product_id).exists():
                det.product_id = random.choice(numberList)
            det.cant = randint(1, det.product.stock)
            det.price = det.product.pvp
            det.subtotal = float(det.price) * det.cant
            det.save()
            det.product.stock -= det.cant
            det.product.save()

        sale.calculate_invoice()
        sale.cash = sale.total
        sale.save()
        print(i)


def generate_name():
    numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    letter = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'ñ', 'o', 'p', 'q', 'r', 's', 't',
              'u', 'v', 'w', 'x', 'y', 'z']
    data = numbers + letter
    result = ''.join(random.choices(data, k=5))
    print('factora{}'.format(result))


def generate_pozzo():
    numbers = []
    for i in range(1, 16):
        number = random.randint(1, 25)
        while number in numbers:
            number = random.randint(1, 25)
        numbers.append(number)
    for n in numbers:
        print(n)


# insert_sale()


def consume_api():
    try:
        params = {
            'Content-Type': 'application/json',
            'Authentication': 'bearer 67d77300c39a8a69e9773a4d6e5e960d35e4959b'
        }
        r = requests.get("https://api.tiendanube.com/v1/1658188/store/", headers=params)
        print(r.headers)
        if r.status_code == 200:
            print(r.text)
        else:
            print(r.text)
    except Exception as e:
        print(e)


# insert_products()
# insert_purchase()
# insert_sale()
generate_name()
