from django.db import models

class Cashier(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class PaymentMethod(models.Model):
    method = models.CharField(max_length=100)

    def __str__(self):
        return self.method
    
class Department(models.Model):
    dept = models.CharField(max_length=100)
    dept_name = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.dept
    
class Storage(models.Model):
    storage_id = models.IntegerField(primary_key=True)
    storage_name = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.storage_id} - {self.storage_name or 'No Name'}"



