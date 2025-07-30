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


from shop.models import Category
from shop.forms import CategoryForm, ProductForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from shop.forms import SignupForm, LoginForm
from shop.models import SubCategory # Import SubCategory

class HomeView(View):
    def get(self, request):
        categories = Category.objects.prefetch_related('subcategories').all()
        return render(request, 'home.html', {'categories': categories})


class ProductListView(ListView):
    model = Product
    template_name = 'products.html'
    context_object_name = 'products'
    paginate_by = 9

    def get_queryset(self):
        queryset = super().get_queryset().filter(available=True).order_by('-created')

        category_id = self.kwargs.get('category_id')
        if not category_id:
            category_id = self.request.GET.get('category_id')

        subcategory_id = self.kwargs.get('subcategory_id')
        if not subcategory_id:
            subcategory_id = self.request.GET.get('subcategory_id')

        if subcategory_id:
            try:
                current_subcategory = get_object_or_404(SubCategory, id=subcategory_id)
                queryset = queryset.filter(subcategory=current_subcategory)
            except ValueError:
                pass
        elif category_id:
            try:
                category = get_object_or_404(Category, id=category_id)
                queryset = queryset.filter(category=category)
            except ValueError:
                pass
        query = self.request.GET.get('q')
        if query:

            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(subcategory__name__icontains=query)
            ).distinct()

        price_range = self.request.GET.get('price_range')
        if price_range:
            try:
                min_price, max_price = map(int, price_range.split('-'))
                queryset = queryset.filter(price__gte=min_price, price__lte=max_price)
            except ValueError:
                pass

        color = self.request.GET.get('color')
        if color:
            queryset = queryset.filter(color__iexact=color)

        size = self.request.GET.get('size')
        if size:
            queryset = queryset.filter(size__iexact=size)

        sort_by = self.request.GET.get('sort_by')
        if sort_by == 'popularity':
            queryset = queryset.order_by('-id')
        elif sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'latest':
            queryset = queryset.order_by('-created')
        print(queryset.query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['all_categories'] = Category.objects.annotate(
            product_count=Count('product', filter=Q(product__available=True))
        )

        current_category = None
        current_subcategory = None

        subcategory_id = self.kwargs.get('subcategory_id') or self.request.GET.get('subcategory_id')
        if subcategory_id:
            current_subcategory = get_object_or_404(SubCategory, id=subcategory_id)
            current_category = current_subcategory.category
        else:
            category_id = self.kwargs.get('category_id') or self.request.GET.get('category_id')
            if category_id:
                current_category = get_object_or_404(Category, id=category_id)

        context['current_category'] = current_category
        context['current_subcategory'] = current_subcategory

        context['available_colors'] = Product.objects.filter(available=True).exclude(color__isnull=True).exclude(color__exact='').values_list('color', flat=True).distinct().order_by('color')
        context['available_sizes'] = Product.objects.filter(available=True).exclude(size__isnull=True).exclude(size__exact='').values_list('size', flat=True).distinct().order_by('size')

        context['total_products_count'] = Product.objects.filter(available=True).count()

        return context


class ProductDetailView(View):
    def get(self,request,i):
        p=Product.objects.get(id=i)
        return render(request,'productdetail.html',{'product':p})


class SignupView(View):
    def post(self,request):
        form_instance=SignupForm(request.POST)
        if form_instance.is_valid():
            user=form_instance.save(commit=False)
            user.is_active=False
            user.save()
            user.generate_otp()
            send_mail(
                "Ecommerce1 OTP",
                user.otp,
                "sethulakshmi1496@gmail.com",
                [user.email],
                fail_silently=False,
            )
            print('hello')
            return redirect('shop:verify')
        else:
            return render(request, 'signup.html', {'form': form_instance})

    def get(self,request):
        form_instance=SignupForm()
        return render(request,'signup.html',{'form':form_instance})


class OtpVerificationView(View):
    def post(self,request):
        otp=request.POST.get('otp')
        print(otp)
        try:
            u=CustomUser.objects.get(otp=otp)
            u.is_active=True
            u.is_verified=True
            u.otp=None
            u.save()
            messages.success(request, "Account verified successfully! You can now sign in.")
            return redirect('shop:signin')
        except CustomUser.DoesNotExist:
            messages.error(request,"Invalid OTP")
            return redirect('shop:verify')
    def get(self,request):
        return render(request,'otp_verify.html')


class SigninView(View):
    def post(self,request):
        form_instance=LoginForm(request.POST)
        if form_instance.is_valid():
            name=form_instance.cleaned_data['username']
            pwd=form_instance.cleaned_data['password']
            user=authenticate(username=name,password=pwd)
            if user and user.is_superuser==True:
                login(request,user)
                messages.success(request, f"Welcome, Admin {user.username}!")
                return redirect('shop:home')
            elif user and user.is_superuser==False:
                login(request, user)
                messages.success(request, f"Welcome, {user.username}!")
                return redirect('shop:home')
            else:
                messages.error(request, "Invalid username or password.")
                return redirect('shop:signin')
        else:
            messages.error(request, "Please enter valid credentials.")
            return render(request, 'login.html', {'form': form_instance})


    def get(self,request):
        form_instance=LoginForm()
        return render(request,'login.html',{'form':form_instance})


class SignOutView(View):
    def get(self,request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('shop:signin')


class HelpView(View):
    def get(self, request):
        return render(request, 'help.html')

class SupportView(View):
    def get(self, request):
        return render(request, 'support.html')

class FaqsView(View):
    def get(self, request):
        return render(request, 'faqs.html')

class ContactusView(View):
    def get(self, request):
        return render(request, 'contactus.html')


class AddCategoryView(View):
    def get(self, request):
        form_instance = CategoryForm()
        return render(request, 'add_category.html', {'form': form_instance})
    def post(self,request):
        form_instance=CategoryForm(request.POST,request.FILES)
        if form_instance.is_valid():
            form_instance.save()
            messages.success(request, "Category added successfully!")
            return redirect('shop:home')
        else:
            messages.error(request, "Error adding category. Please check your input.")
            return render(request, 'add_category.html', {'form': form_instance})


class AddProductView(View):
    def get(self,request):
        form_instance=ProductForm()
        return render(request,'add_product.html',{'form':form_instance})
    def post(self,request):
        form_instance=ProductForm(request.POST,request.FILES)
        if form_instance.is_valid():
            form_instance.save()
            messages.success(request, "Product added successfully!")
            return redirect('shop:home')
        else:
            messages.error(request, "Error adding product. Please check your input.")
            return render(request, 'add_product.html', {'form': form_instance})













