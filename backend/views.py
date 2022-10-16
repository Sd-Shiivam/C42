# from msilib.schema import Error
import random
import requests
import os
import json
from .models import *
from time import sleep
import subprocess
from datetime import datetime
from django.contrib import messages
#from pydrive.auth import GoogleAuth
#from pydrive.drive import GoogleDrive
from dateutil.relativedelta import relativedelta
from django.http.response import HttpResponse
from django.shortcuts import redirect, render
# Create your views here.
invoice_cart = []
today_backup = False
internet = True


def network():
    global internet
    try:
        requests.get('http://www.google.com?')
        internet = True
    except:
        internet = False


def new_month():
    new_month = False
    with open('month.txt', 'r') as f:
        month_check = f.read()
        if str(datetime.now().date().strftime('%B')) == month_check:
            new_month = False
        else:
            with open('month.txt', 'w') as f2:
                f2.write(datetime.now().date().strftime('%B'))
                new_month = True
            report_history().save()
    return new_month


def newday():
    new_day = False
    with open('date.txt', 'r') as f:
        date_check = f.read()
        if str(datetime.now().date().strftime('%B %d, %Y')) == date_check:
            new_day = False
        else:
            with open('date.txt', 'w') as f2:
                f2.write(datetime.now().date().strftime('%B %d, %Y'))
                new_day = True
            for s in staf.objects.all():
                attendence(staf_name=staf.objects.get(name=s.name)).save()
            shopopen(state='Open').save()
    return new_day


newday()
new_month()


def index(request):
    parm = {}
    return render(request, 'home.html', parm)


def prod(request):
    if request.method == 'POST':
        prods = []
        types = 'search'
        query = str(request.POST.get('query')).lower()
        try:
            querys = query.split(' ')
            querys.append(query)
            for i in products.objects.all():
                for q in querys:
                    if str(q).lower() in str(i.name).lower():
                        if i not in prods:
                            prods.append(i)
        except:
            pass
        if len(prods) == 0:
            messages.success(
                request, f'No product Found similar to [{querys[0]}] ')
            return redirect('home')
    else:
        prods = products.objects.all()
        types = 'allprod'

    parm = {
        'Products': reversed(prods),
        'total': len(prods),
        'cats': category.objects.all(),
        'typ': types,
        'cart': len(invoice_cart),
        'all_cart': invoice_cart,
    }
    return render(request, 'allprod.html', parm)


def addprods(request):
    try:
        name = request.GET.get('name')
        cat = request.GET.get('cat')
        price1 = request.GET.get('price1')
        price2 = request.GET.get('price2')
        stock = request.GET.get('stock')
        products(name=name, category=category.objects.get(name=cat),
                 Sale_price=price1, Buy_price=price2, stock=stock).save()
        r = report_history.objects.all().last()
        r.imports_price += int(float(price2))
        r.imports += 1
        r.save()
        return HttpResponse('Product Added to database')
    except:
        return HttpResponse('Some Error happen')


def edit_prod(request):
    try:
        p_id = request.GET.get('p_id')
        name = request.GET.get('name')
        price1 = request.GET.get('price1')
        price2 = request.GET.get('price2')
        p = products.objects.get(id=p_id)
        p.name = name
        p.Sale_price = price1
        p.Buy_price = price2
        p.save()
        return HttpResponse('Product updated successfully')
    except:
        return HttpResponse('Some Error happen')


def plustock(request):
    prod_id = request.GET.get('prodid')
    p = products.objects.get(id=prod_id)
    p.stock += 1
    p.save()
    r = report_history.objects.all().last()
    r.imports += 1
    r.imports_price += int(float(p.Buy_price))
    r.save()
    return HttpResponse('Stock updated successfully')


def minustock(request):
    prod_id = request.GET.get('prodid')
    p = products.objects.get(id=prod_id)
    p.stock -= 1
    p.save()
    r = report_history.objects.all().last()
    r.export += p.Sale_price
    r.save()
    sellhistory(detail=p.name, total=p.Sale_price).save()
    return HttpResponse('Stock updated successfully')


def note(request):
    if request.method == 'POST':
        note = request.POST.get('Note_body')
        print(note)
        notes(note_body=note).save()
        return HttpResponse('Note added successfully.')
    parm = {
        'notes': reversed(notes.objects.all())
    }
    return render(request, 'notes.html', parm)


def invoice_collect(request):
    try:
        global invoice_cart
        prod_id = request.GET.get('prod_id')
        p = products.objects.get(id=prod_id)
        raw_data = {'id': prod_id, 'name': p.name, 'price': p.Sale_price,
                    'quantity': 1, 'dec': '', 'total': p.Sale_price}
        if raw_data not in invoice_cart:
            invoice_cart.append(raw_data)
            return HttpResponse('Product Added to invoice product list')
        else:
            return HttpResponse('Product already invoice product list')

    except:
        return HttpResponse('Something went wrong')


def invoice_list(request):
    if request.method == 'POST':
        if request.POST.get('ids'):
            id = request.POST.get('ids')
            name = str(invoice.objects.get(id2=id).customer).split('|')[0]
            address = ''
            phone = 0
            gst = 0
            sub_total = 0
            ord = invoice.objects.get(id2=id).order_detail
            ord = ord.replace("\'", "\"")
            ord = json.loads(ord)
            for p in ord:
                sub_total += int(float(p['total']))
            for c in customer.objects.all():
                if c.name in name:
                    address = c.address
                    phone = c.contact
                    gst = c.gst_no
                    badge = c.badge
            try:
                parm = {
                    'id': id,
                    'badge': badge,
                    'Invoice_type': invoice.objects.get(id2=id).inv_type,
                    'date_time': invoice.objects.get(id2=id).order_date,
                    'Customer_Name': name,
                    'Customer_Address': address,
                    'Phone_number': phone,
                    'Customer_GSTNo': gst,
                    'Discount': invoice.objects.get(id2=id).offer,
                    'pay_mod': invoice.objects.get(id2=id).pay_mode,
                    'sub_total': sub_total,
                    'total': invoice.objects.get(id2=id).total_paid,
                    'GST': '18',
                    'prods': ord,
                    'mode': 'oldview',
                    'invoicetemp': invoice_template.objects.all()[0],
                    'footlines': str(invoice_template.objects.all()[0].footerlines).split('|'),
                }
                return render(request, 'view_invoice.html', parm)

            except:
                messages.success(request, f'invoice history error')
                return redirect('/')
        elif request.POST.get('up_value'):
            s = invoice.objects.get(id2=request.POST.get('id_inv'))
            s.state = request.POST.get('up_value')
            s.save()
            return HttpResponse('Invoice updated succesfully')
    # inv0 = invoice.objects.filter(month=format(
    #     datetime.now() - relativedelta(months=3), '%B'))
    # inv1 = invoice.objects.filter(month=format(
    #     datetime.now() - relativedelta(months=1), '%B'))
    # inv2 = invoice.objects.filter(month=format(
    #     datetime.now() - relativedelta(months=2), '%B'))
    # gst_tax = reversed(inv0 | inv1 | inv2)
    # s = 0
    # for i in gst_tax:
    #     s = int(float(i.total_paid)) + int(float(s))
    #     print(i.total_paid)
    #     if s >= 108594:
    #         print(i.id2)
    #         break
    #     if i.id2 == '#BHARAT00192':
    #         break
    parm = {
        'invoices': reversed(invoice.objects.all()),
    }
    return render(request, 'invoice_list.html', parm)


def stafs(request):
    if request.method == 'POST':
        ids = request.POST.get('at_id')
        state = request.POST.get('state')
        n = attendence.objects.get(id=ids)
        n.state = state
        n.save()
        return HttpResponse('Attendence marked successfully')
    staf_today = []

    for s in staf.objects.all():
        name = s.name
        contact = s.contact
        at = attendence.objects.get(staf_name=staf.objects.get(name=s.name),
                                    date=datetime.now().date().strftime('%B %d, %Y'))
        state = at.state
        id = at.id
        staf_today.append(
            {'id': id, 'name': name, 'contact': contact, 'state': state})

    parm = {
        'stafs': staf_today,
        'today': datetime.now().date().strftime('%B %d, %Y'),
    }
    return render(request, 'stafe.html', parm)


def invoice_create(request):
    if request.GET.get('custome') == 'true':
        global invoice_cart
        raw_data = {'id': f'T{random.randint(0,100)}', 'name': request.GET.get('prodname'), 'price': request.GET.get('prodprice'),
                    'quantity': request.GET.get('prodqunt'), 'dec': request.GET.get('proddec'), 'total': int(float(request.GET.get('prodprice')))*int(request.GET.get('prodqunt'))}
        invoice_cart.append(raw_data)
        return HttpResponse('Item Added to invoice cart.')
    if request.GET.get('ids'):
        ids = request.GET.get('ids')
        for itm in invoice_cart:
            if itm['id'] == ids:
                invoice_cart.remove(itm)
        return HttpResponse('Item removed from invoice cart.')
    parm = {
        'inv_cart': invoice_cart,
        'customers': customer.objects.all(),
        'ins': len(invoice_cart),
    }
    return render(request, 'invoice_create.html', parm)


def clear_cart(request):
    global invoice_cart
    invoice_cart = []
    return HttpResponse('Invoice cart clear.')


def gen_invoice(request):
    global invoice_cart
    if request.method == 'POST':
        if len(request.POST.get('customer_name')) == 0:
            messages.success(request, 'Please enter correct details')
            return redirect('/')
        try:
            if invoice.objects.all().last():
                il = str(invoice.objects.all().last().id2).split('T')
                id2 = f"{il[0]}T{str(int(il[1])+1).zfill(5)}"
            else:
                id2 = "#INV00000"
        except:
            id2 = "#INV00040"
        Date_Time = f"{datetime.now().date().strftime('%B %d, %Y')} | {datetime.now().time().strftime('%H:%M:%S')}"
        Customer_Name = request.POST.get('customer_name')
        pay_mod = request.POST.get('paymod')
        Customer_Address = request.POST.get('address')
        Phone_number = request.POST.get('Phone_number')
        Customer_GSTNo = request.POST.get('gst_no')
        gst_p = request.POST.get('gst_per')
        Discount = request.POST.get('discount')
        Invoice_type = request.POST.get('invoice_type')
        if len(Discount) == 0 or Discount == 0:
            Discount = 00.00
        sub_total = 0
        if request.POST.get('oldone') == 'Old':
            badge = 'New'
            try:
                if customer.objects.all().last():
                    il = str(invoice.objects.all().last().id2).split('T')
                    c_id = f"{il[0]}T{str(int(il[1])+1).zfill(5)}"
                else:
                    c_id = "#CINV00001"
            except:
                c_id = "#CINV00001"
            s = customer(id2=c_id, name=Customer_Name, address=Customer_Address, contact=Phone_number,
                         gst_no=Customer_GSTNo, badge='New', buys=1).save()
        else:
            c_id = request.POST.get('oldone')
            c = customer.objects.get(id2=c_id)
            c.buys = 1 + int(c.buys)
            if int(c.buys) == 5:
                c.badge = 'Star'
            badge = c.badge
            c.save()
        for p in invoice_cart:
            sub_total += int(float(p['total']))
        try:
            total1 = int(sub_total) - int(float(Discount))
        except:
            total1 = int(sub_total)
        if Invoice_type == 'Gst_Invoice':
            total = ((int(gst_p)/100)*total1)+total1
        else:
            total = total1

        invoice(id2=id2, customer=customer.objects.get(id2=c_id),
                order_detail=invoice_cart, offer=Discount, pay_mode=pay_mod, inv_type=Invoice_type, total_paid=total).save()
        for i in invoice_cart:
            if 'T' not in i['id']:
                p = products.objects.get(id=i['id'])
                p.trend = int(1) + int(p.trend)
                p.save()
        parm = {
            'id': id2,
            'badge': badge,
            'Invoice_type': Invoice_type,
            'date_time': Date_Time,
            'Customer_Name': Customer_Name,
            'Customer_Address': Customer_Address,
            'Phone_number': Phone_number,
            'Customer_GSTNo': Customer_GSTNo,
            'Discount': Discount,
            'pay_mod': pay_mod,
            'sub_total': sub_total,
            'total': total,
            'GST': gst_p,
            'prods': invoice_cart,
            'invoicetemp': invoice_template.objects.all()[0],
            'footlines': str(invoice_template.objects.all()[0].footerlines).split('|'),
        }
        for p in invoice_cart:
            if 'T' not in i['id']:
                up = products.objects.get(id=p['id'])
                up.stock += -int(p['quantity'])
                if up.stock < 0:
                    up.stock = 0
                up.save()
        r = report_history.objects.all().last()
        r.export += int(float(total))
        r.save()
        invoice_cart = []
        return render(request, 'view_invoice.html', parm)

    return HttpResponse('working')
    # return render(request, 'temp_invoice.html')


def invoice_cart_update(request):
    global invoice_cart
    id = request.GET.get('id')
    for i in invoice_cart:
        if int(i['id']) == int(id):
            typ = request.GET.get('typ')
            if str(typ) == 'quantity':
                quantity = request.GET.get('data')
                i['quantity'] = quantity
                i['total'] = int(float(i['price']))*int(quantity)
            else:
                dec = request.GET.get('data')
                i['dec'] = dec
    return HttpResponse('Cart updated')


def sale_history(request):
    if request.method == 'POST':
        name = request.POST.get('detail')
        price = request.POST.get('price')
        r = report_history.objects.all().last()
        r.export += int(float(price))
        r.save()
        sellhistory(detail=name, total=price).save()
        return HttpResponse('Selldetail added')
    parm = {
        'date': f"{datetime.now().date().strftime('%B %d, %Y')}{datetime.now().time().strftime('%H:%M:%S')}",
        'history': reversed(sellhistory.objects.all()),
        'prods': products.objects.all(),
    }
    return render(request, 'sale_history.html', parm)


def pay_history(request):
    if request.method == 'POST':
        stafs = request.POST.get('name')
        pay = request.POST.get('pay')
        paymenthistory(staf_name=staf.objects.get(name=stafs), pay=pay).save()
        return HttpResponse('Pay history added successfully.')
    parm = {
        'pays': reversed(paymenthistory.objects.all()),
        'stf': staf.objects.all(),
        'td': f"{datetime.now().date().strftime('%B %d, %Y')}{datetime.now().time().strftime('%H:%M:%S')}",
    }
    return render(request, 'payment.html', parm)


def lastmonth():
    last_month = datetime.now() - relativedelta(months=1)
    return format(last_month, '%B')


def record(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        address = request.POST.get('address')
        customer(name=name, contact=contact, address=address).save()
        return HttpResponse(f'{name} is add to customer list.')
    staf_pay = []
    staf_aden = []
    Total_pay_staf = 0
    today_sale = []
    for i in staf.objects.all():
        staf_aden.append({'name': i.name, 'persent': 0})
    for a in staf_aden:
        for p in attendence.objects.all():
            if str(datetime.now().date().strftime('%B')).lower() in str(p.date).lower():
                if str(a['name']).lower() == str(p.staf_name).lower():
                    if p.state == 'Present':
                        a['persent'] += 1
    for s in invoice.objects.all():
        if str(datetime.now().date().strftime('%B %d, %Y')) in s.order_date:
            today_sale.append(
                {'name': f'invoice[{s.id2}]', 'payed': s.total_paid})
    for s in sellhistory.objects.all():
        if str(datetime.now().date().strftime('%B %d, %Y')) in s.date:
            today_sale.append({'name': s.detail, 'payed': s.total})
    for s in staf.objects.all():
        staf_pay.append({'name': s.name, 'pay': 0})
    for i in staf_pay:
        for p in paymenthistory.objects.filter(month=datetime.now().date().strftime('%B')):
            if str(i['name']).lower() == str(p.staf_name).lower():
                i['pay'] = int(float(i['pay'])) + int(float(p.pay))
                Total_pay_staf += int(float(i['pay']))

    rpthis = report_history.objects.all().last()
    try:
        rp_last = report_history.objects.get(month=lastmonth())
        last_sale = rp_last.export
        stock_last = rp_last.imports
        last_import = rp_last.imports_price
    except:
        last_sale = 0
        stock_last = 0
        last_import = 0

    parm = {
        'mont': f"{datetime.now().date().strftime('%B')}",
        'cust_total': len(customer.objects.filter(month=datetime.now().date().strftime('%B'))),
        'sales': rpthis.export,
        'last_sale': last_sale,
        't_prod': rpthis.imports,
        'stock_last': stock_last,
        'total_buy': rpthis.imports_price,
        'trend': products.objects.all().order_by('-trend')[0:10],
        'last_import': last_import,
        'customer': customer.objects.filter(month=datetime.now().date().strftime('%B'))[0:5],
        'staf_pay': staf_pay,
        'staf_aden': staf_aden,
        'all_cust1': customer.objects.all()[0:int(len(customer.objects.all())/3)],
        'all_cust2': customer.objects.all()[int(len(customer.objects.all())/3):(int(len(customer.objects.all())/3)+int(len(customer.objects.all())/3))],
        'all_cust3': customer.objects.all()[(int(len(customer.objects.all())/3)+int(len(customer.objects.all())/3)):len(customer.objects.all())],
        'Total_pay_staf': Total_pay_staf,
        'check_today_sale': len(today_sale),
        'today_sale': today_sale,
        'stotal_shop_opend': len(shopopen.objects.filter(month=datetime.now().date().strftime('%B'))),
        'lastmont': lastmonth(),
        'last_month_customer': len(customer.objects.filter(month=lastmonth())),
    }
    return render(request, 'report.html', parm)


def backup(request):
    global today_backup, internet
    network()
    if today_backup == False:
        if internet == True:
            os.system(
                "python .\manage.py dumpdata --natural-foreign --natural-primary -e contenttypes --indent 4 > backup.json")
            with open('backup.json', 'r') as f:
                data_back = f.read()
            os.system('del backup.json')
            gauth = GoogleAuth()
            gauth.LoadCredentialsFile("mycreds.txt")
            if gauth.credentials is None:
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                gauth.Refresh()
            else:
                gauth.Authorize()
            gauth.SaveCredentialsFile("mycreds.txt")
            drive = GoogleDrive(gauth)
            file_metadata = {'title': 'backup.json',
                             'parents': [{'kind': 'drive#fileLink',
                                          'id': '1VJuWUSOSqB0ew3GlyPLibm7Jzx1GXVXg'}], 'id': '1wMptWuXmg0wjIe_hummzzUUYCjN3NtC5'}
            file1 = drive.CreateFile(file_metadata)
            file1.SetContentString(data_back)
            file1.Upload()
            return HttpResponse('Backup generated successfully.')
        else:
            return HttpResponse('Connect to internet to generate backup.')
    else:
        return HttpResponse('Today Backup is already generated.')

    return HttpResponse('backup System under development.')
