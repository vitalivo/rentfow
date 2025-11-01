# leases/urls/api_urls.py
from django.urls import path
from .. import views

urlpatterns = [
    path('properties/', views.property_list_create, name='property-list-create'),
    path('tenants/', views.tenant_list, name='tenant-list'),
    path('leases/', views.lease_list, name='lease-list'),
    path('leases/create/', views.lease_create_grpc, name='lease-create-grpc'),
]