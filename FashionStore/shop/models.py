from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="categories",blank=True, null=True)

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    GENDER_CHOICES = (
        ('M', 'Men'),
        ('W', 'Women'),
        ('K', 'Kids'),
        ('U', 'Unisex/General'),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U',
                              help_text="Select target gender for this product.")
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    color = models.CharField(max_length=50, blank=True, null=True)  # e.g., "Red", "Blue", "Black"
    size = models.CharField(max_length=50, blank=True, null=True)  # e.g., "S", "M", "L", "XL"


    def __str__(self):
        return self.name

from django.contrib.auth.models import AbstractUser
from random import randint
class CustomUser(AbstractUser):
    phone=models.IntegerField(default=0)


    is_verified = models.BooleanField(default=False) #After verification it will set to True
    otp = models.CharField(max_length=10, null=True, blank=True)#To store the generated otp in backend table


    def generate_otp(self):
         #for creating random otp number for verification

        otp_number=str(randint(1000,9999))+str(self.id)

        self.otp=otp_number

        self.save()
