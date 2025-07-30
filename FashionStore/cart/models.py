from django.db import models

from shop.models import CustomUser

from shop.models import Product


class Cart(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity=models.IntegerField(default=1)
    date_added=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    def subtotal(self):
        return self.quantity*self.product.price

from django.utils import timezone
class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address=models.TextField()
    phone=models.IntegerField()
    payment_method=models.CharField(max_length=20)
    order_id=models.CharField(null=True,max_length=50)
    is_ordered=models.BooleanField(default=False)
    amount=models.IntegerField(null=True)
    ordered_date=models.DateTimeField(default=timezone.now)
    delivery_status=models.BooleanField(default=False)
    def __str__(self):
        return str(self.order_id)

class Order_items(models.Model):
    order=models.ForeignKey(Order, on_delete=models.CASCADE,related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity=models.IntegerField()


class Favorite(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.user.username
