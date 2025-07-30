"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from cart import views
app_name="cart"
urlpatterns = [
    path('addtocart/<int:i>',views.AddtoCartView.as_view(),name="addtocart"),
    path('cartview',views.CartView.as_view(),name="cartview"),
    path('addtocartminus/<int:i>',views.AddtoCartMinusView.as_view(),name="addtocartminus"),

    path('addtocartdelete/<int:i>',views.AddtoCartdeleteView.as_view(),name="addtocartdelete"),
    path('orderform',views.OrderFormView.as_view(),name="orderform"),
    path('paymentsuccess/<i>', views.paymentsuccessView.as_view(), name="paymentsuccess"),

    path('ordersummery/', views.OrderSummaryView.as_view(), name="ordersummery"),

    path('favorites/add/<int:product_id>/', views.AddToFavoritesView.as_view(), name='add_to_favorites'),
    path('favorites/remove/<int:product_id>/', views.RemoveFromFavoritesView.as_view(), name='remove_from_favorites'),
    path('favorites/view/', views.FavoriteListView.as_view(), name='favorite_list'),

]