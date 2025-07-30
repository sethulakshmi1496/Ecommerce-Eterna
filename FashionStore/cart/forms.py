from django import forms
from cart.models import Order
class OrderForm(forms.ModelForm):
    payment_choices=(('COD','COD')),(('ONLINE','ONLINE'))
    payment_method=forms.ChoiceField(choices=payment_choices,widget=forms.RadioSelect)


    class Meta:
        model=Order
        fields=['address','phone','payment_method']