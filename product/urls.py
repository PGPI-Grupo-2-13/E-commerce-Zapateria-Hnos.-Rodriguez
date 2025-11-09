from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
    path('categorias/', views.category_list, name='category_list'),
    path('marcas/', views.brand_list, name='brand_list'),
]