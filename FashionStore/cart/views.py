from django.contrib.auth import login
from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from cart.models import Cart,Favorite, Order, Order_items
from shop.models import Product, CustomUser, Category
import razorpay
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import authenticate, logout
from django.db.models import Q, Count
from django.views.generic import ListView

class AddtoCartView(View):
    def get(self, request, i):
        u = request.user
        p = Product.objects.get(id=i)
        try:
            c = Cart.objects.get(user=u, product=p)
            c.quantity += 1
            c.save()
        except Cart.DoesNotExist:
            c = Cart.objects.create(user=u, product=p, quantity=1)
            c.save()
        return redirect('cart:cartview')

class CartView(View):
    def get(self, request):
        u = request.user
        c = Cart.objects.filter(user=u)
        total = 0
        for i in c:
            total += i.quantity * i.product.price
        return render(request, 'addtocart.html', {'cart': c, 'total': total})


class AddtoCartMinusView(View):
    def get(self, request, i):
        u = request.user
        p = Product.objects.get(id=i)
        try:
            c = Cart.objects.get(user=u, product=p)
            if c.quantity > 1:
                c.quantity -= 1
                c.save()
            else:
                c.delete()
        except Cart.DoesNotExist:
            pass
        return redirect('cart:cartview')

class AddtoCartdeleteView(View):
    def get(self, request, i):
        u = request.user
        p = Product.objects.get(id=i)
        try:
            c = Cart.objects.get(user=u, product=p)
            c.delete()
        except Cart.DoesNotExist:
            pass
        return redirect('cart:cartview')

def check_stock(c):
    stock = True
    for i in c:
        if i.product.stock < i.quantity:
            stock = False
            break
    return stock

from cart.forms import OrderForm

class OrderFormView(View):
    def post(self, request):
        u = request.user
        form_instance = OrderForm(request.POST)
        if form_instance.is_valid():
            order_object = form_instance.save(commit=False)
            order_object.user = u
            order_object.save()

            c = Cart.objects.filter(user=u)
            stock_available = check_stock(c)
            if stock_available:
                for i in c:
                    o = Order_items.objects.create(order=order_object, product=i.product, quantity=i.quantity)
                    o.save()

                total = 0
                for i in c:
                    total += i.quantity * i.product.price


                if order_object.payment_method == "ONLINE":
                    client = razorpay.Client(auth=('rzp_test_oCeVyBXbBVFero', 'fx3Z2TYQfYCbSSY77AQ5C0QY'))

                    response_payment = client.order.create(dict(amount=int(total * 100), currency='INR'))
                    print(response_payment)

                    order_id = response_payment['id']
                    order_object.order_id=order_id
                    order_object.is_ordered = False
                    order_object.save()
                    return render(request, 'payment.html', {'payment': response_payment, 'name': u.username})

                elif order_object.payment_method == "COD":
                    order_object.is_ordered = True
                    order_object.amount = total
                    order_object.save()
                    items = Order_items.objects.filter(order=order_object)
                    for i in items:
                        i.product.stock -= i.quantity
                        i.product.save()

                    c = Cart.objects.filter(user=u)
                    c.delete()
                    messages.success(request, "Order placed successfully!")
                    return redirect('shop:home')

                else:
                    pass


            else:
                messages.error(request, "Some items in your cart are currently out of stock or quantity exceeds available stock.")
                return render(request, 'payment.html')

    def get(self, request):
        form_instance = OrderForm()
        u = request.user

        cart_items = Cart.objects.filter(user=u)

        total = 0
        for item in cart_items:
            total += item.quantity * item.product.price

        return render(request, 'orderform.html', {'form': form_instance, 'cart': cart_items, 'total': total})


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt,name='dispatch')
class paymentsuccessView(View):
    def post(self,request,i):
        user = CustomUser.objects.get(username=i)
        login(request,user)

        response = request.POST
        print(response)

        o = Order.objects.get(order_id=response['razorpay_order_id'])
        o.is_ordered = True
        o.save()

        items = Order_items.objects.filter(order=o)
        for i in items:
            i.product.stock -= i.quantity
            i.product.save()

        c = Cart.objects.filter(user=user)
        c.delete()

        messages.success(request, "Payment successful! Your order has been placed.")
        return render(request,'payment_success.html')

class OrderSummaryView(View):
    def get(self, request):
        u=request.user
        orders=Order.objects.filter(user=u,is_ordered=True)
        return render(request,template_name='ordersummery.html',context={'orders':orders})


class FavoriteListView(View):
    def get(self, request):
        u = request.user
        if not u.is_authenticated:
            messages.info(request, "Please log in to view your favorites.")
            return redirect('shop:signin')

        favorites = Favorite.objects.filter(user=u).select_related('product')
        return render(request, 'addtofavorites.html', {'favorites': favorites})


class AddToFavoritesView(View):
    def get(self, request, product_id, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            messages.error(request, "Please log in to add items to your favorites.")
            return redirect('shop:signin')

        product = get_object_or_404(Product, id=product_id)
        favorite_item, created = Favorite.objects.get_or_create(user=u, product=product)

        if created:
            messages.success(request, f"{product.name} has been added to your favorites!")
        else:
            messages.info(request, f"{product.name} is already in your favorites.")

        return redirect('shop:productdetail', i=product_id)


class RemoveFromFavoritesView(View):
    def get(self, request, product_id, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            messages.error(request, "Please log in to modify your favorites.")
            return redirect('shop:signin')

        product = get_object_or_404(Product, id=product_id)
        favorite_item = get_object_or_404(Favorite, user=u, product=product)
        favorite_item.delete()
        messages.success(request, f"{product.name} has been removed from your favorites.")

        return redirect('cart:favorite_list')


