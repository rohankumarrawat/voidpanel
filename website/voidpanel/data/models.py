from django.db import models

# Create your models here.
class updates(models.Model):
    version = models.CharField(max_length=10,default=None)
    date = models.DateField(auto_now_add=True)



class Message(models.Model):
    text = models.TextField()  # Field for the message content
    title=models.CharField(max_length=60,default=None)
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the message is created
    photo = models.ImageField(upload_to='media/', null=True, blank=True)  # Optional photo field

    def __str__(self):
        return self.text[:10]  # Return the first 50 characters of the message

class Installed(models.Model):
    ip = models.GenericIPAddressField()
    number = models.IntegerField(default=0)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f'{self.ip} - {self.number}'
    
class admindocumentation(models.Model):
    text = models.TextField()  # Field for the message content
    link=models.CharField(max_length=60,default=None)
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the message is created

class clientdocumentation(models.Model):
    text = models.TextField()  # Field for the message content
    link=models.CharField(max_length=60,default=None)
    date = models.DateTimeField(auto_now_add=True)  # Automatically set the date when the message is created


class positive_review(models.Model):
    review = models.TextField()  # Field for the message content
    content = models.TextField(default=None)  
    user=models.CharField(max_length=60,default=None)
    date = models.DateField(auto_now_add=True)


    def __str__(self):
        return self.user  

class negative_review(models.Model):
    review = models.TextField()  # Field for the message content
    content = models.TextField(default=None)  
    user=models.CharField(max_length=60,default=None)
    category=models.CharField(max_length=60,default=None)
    date = models.DateField(auto_now_add=True)

    

    def __str__(self):
        return self.user  


