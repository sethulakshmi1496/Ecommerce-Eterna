from django.contrib import admin
from shop.models import Category, SubCategory, Product,CustomUser

admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(Product)
admin.site.register(CustomUser)
