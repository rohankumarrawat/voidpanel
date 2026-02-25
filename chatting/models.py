from django.db import models

# Create your models here.
class message(models.Model):
    fromai = models.TextField(default="None")  # Field for the message content
    toai = models.TextField(default="None")  
    user=models.CharField(max_length=60,default="None")
    name=models.CharField(max_length=60,default="None")
    date = models.DateField(auto_now_add=True)