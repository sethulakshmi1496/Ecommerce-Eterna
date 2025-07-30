"""
URL configuration for FashionStore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
# shop/urls.py
from django.urls import path
from shop import views

app_name="shop"

urlpatterns = [
    path('', views.HomeView.as_view(), name="home"),

    # Product related URLs
    path('products/', views.ProductListView.as_view(), name="product_list"),
    path('products/category/<int:category_id>/', views.ProductListView.as_view(), name="products_by_category"),
    path('products/subcategory/<int:subcategory_id>/', views.ProductListView.as_view(), name="products_by_subcategory"),
    path('productdetail/<int:pk>/',views.ProductDetailView.as_view(),name="productdetail"), # Note: Chatbot expects /products/<id>/ for product detail links

    # Authentication & Admin related URLs
    path('signup/',views.SignupView.as_view(),name="signup"),
    path('signin/',views.SigninView.as_view(),name="signin"),
    path('otp-verify/',views.OtpVerificationView.as_view(),name="verify"),
    path('signout/',views.SignOutView.as_view(),name="signout"),
    path('addcategory/',views.AddCategoryView.as_view(),name="add_category"),
    path('addproduct/', views.AddProductView.as_view(), name="add_product"),

    # Static/Informational Pages (as referenced in chatbot_data.json)
    path('faqs/', views.FaqsView.as_view(), name='faqs'),
    path('help/', views.HelpView.as_view(), name='help'),
    path('support/', views.SupportView.as_view(), name='support'),
    path('contactus/', views.ContactusView.as_view(), name='contactus'),
    # Add these if you have views for them and want the chatbot to link to them:
    # path('returns/', views.ReturnsPolicyView.as_view(), name='returns_policy'), # Example
    # path('track-order/', views.OrderTrackingView.as_view(), name='track_order'), # Example
    # path('promotions/', views.PromotionsView.as_view(), name='promotions'), # Example
    # path('size-guide/', views.SizeGuideView.as_view(), name='size_guide'), # Example
    # path('feedback/', views.FeedbackView.as_view(), name='feedback'), # Example
    # path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'), # Example
    # path('about/', views.AboutUsView.as_view(), name='about_us'), # Example

# --- CHATBOT URL ---
    path('chatbot/', views.ChatbotView.as_view(), name='chatbot'),
    # ... (URLs for any new pages linked in chatbot_intents.json like /returns/, /track-order/ etc.) ...
    path('returns/', views.HelpView.as_view(), name='returns_policy'), # Example placeholder
    path('track-order/', views.HelpView.as_view(), name='track_order'), # Example placeholder
    path('feedback/', views.HelpView.as_view(), name='feedback'), # Example placeholder
    path('promotions/', views.HelpView.as_view(), name='promotions'), # Example placeholder
    path('size-guide/', views.HelpView.as_view(), name='size_guide'), # Example placeholder
    path('shipping-info/', views.HelpView.as_view(), name='shipping_info'), # Example placeholder
    path('register/', views.SignupView.as_view(), name='register'), # Example, if your signup is /register/
    path('about/', views.HelpView.as_view(), name='about_us'), # Example placeholder
    # ... and so on for any pages mentioned in your JSON's <a> tags.



]