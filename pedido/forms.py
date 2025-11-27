from django import forms

class CheckoutForm(forms.Form):
    direccion = forms.CharField(label='Dirección de Envío', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle, número...'}))
    ciudad = forms.CharField(label='Ciudad', max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    codigo_postal = forms.CharField(label='Código Postal', max_length=10, widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(label='Teléfono', max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@correo.com'})
    )

class OrderTrackingForm(forms.Form):
    numero_pedido = forms.CharField(
        label='Número de Pedido', 
        max_length=120,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PED-1-173...'})
    )
    telefono = forms.CharField(
        label='Teléfono utilizado en la compra',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    