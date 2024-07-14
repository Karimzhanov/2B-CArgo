from django.contrib import admin
from .models import Client, Code


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'phone_number', 'personal_code', 'warehouse_address')

@admin.register(Code)
class CodeAdmin(admin.ModelAdmin):
    list_display = ('id',  'code')
