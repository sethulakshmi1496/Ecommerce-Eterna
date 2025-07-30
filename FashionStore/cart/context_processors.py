from cart.models import Cart
from cart.models import  Favorite


def cart_and_favorite_counts(request):
    cart_total_quantity = 0
    favorite_items_count = 0

    if request.user.is_authenticated:
        user = request.user

        cart_items = Cart.objects.filter(user=user)
        for item in cart_items:
            cart_total_quantity += item.quantity

        favorite_items_count = Favorite.objects.filter(user=user).count()

    return {
        'cart_item_count': cart_total_quantity,
        'favorite_item_count': favorite_items_count,
    }