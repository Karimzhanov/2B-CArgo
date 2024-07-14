from django.db import models

class Client(models.Model):
    id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    personal_code = models.CharField(max_length=20)
    warehouse_address = models.CharField(max_length=255)
    
    def __str__(self):
        return self.first_name
    
    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


class Code(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.IntegerField()
    
    def __str__(self):
        return str(self.code)   
    
    class Meta:
        verbose_name = "Код"
        verbose_name_plural = "Коды"


