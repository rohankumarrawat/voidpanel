from django.db import models




# Create your models here.
class quick(models.Model):
    hostname = models.CharField(max_length=255,default=False)
    nameserver1 = models.CharField(max_length=255,default=False)
    nameserver2 = models.CharField(max_length=255,default=False)
    email = models.EmailField(max_length=255,default=False)
    status = models.BooleanField(default=False)
    show = models.BooleanField(default=False)
    count=models.IntegerField(default=0)

    def __str__(self):
        return self.hostname
    
class portnumber(models.Model):
    number = models.CharField(max_length=255)
 
    

class package(models.Model):
    name = models.CharField(max_length=100, unique=True)
    storage = models.TextField(help_text="Storage in GB")
    ftp = models.TextField(help_text="Storage in GB")
    subdomain = models.TextField(help_text="Storage in GB")
    bandwidth = models.TextField(help_text="Bandwidth in GB")
    # domains_allowed = models.TextField(help_text="Number of domains allowed")
    email_accounts = models.TextField(help_text="Number of email accounts allowed")
    databases_allowed = models.TextField(help_text="Number of databases allowed")
    def __str__(self):
        return self.name

class user(models.Model):
    username = models.CharField(max_length=150)
    email = models.CharField(max_length=150)
    domain = models.CharField(max_length=150)
    hosting_package = models.CharField(max_length=150) 
    is_active = models.BooleanField(default=True)
    shell = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.domain
    
class LoginActivity(models.Model):
    user = models.CharField(max_length=150)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=150)
    successful = models.BooleanField(default=True, help_text="Whether the login attempt was successful")


class domain(models.Model):
    domain = models.CharField(max_length=100, unique=True)
    email = models.CharField(max_length=255)
    php = models.CharField(max_length=10,default='8.3')
    dir = models.CharField(max_length=255)
    sslstatus = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    userdomain = models.BooleanField(default=False)
   
    def __str__(self):
        return self.domain
    
class allemail(models.Model):
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    domain = models.CharField(max_length=255)
    
   
    def __str__(self):
        return self.email


class cron(models.Model):
    domain = models.CharField(max_length=100)
    duratioin = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
   
    def __str__(self):
        return self.domain
    
class subdomainname(models.Model):
    domain = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    php = models.CharField(max_length=10,default='8.3')
    sslstatus = models.BooleanField(default=False)
    
   
    def __str__(self):
        return self.domain
    


class pythonname(models.Model):
    domain = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    main = models.CharField(max_length=100,default=None)
   
    def __str__(self):
        return self.domain
    
class mernname(models.Model):
    domain = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    main = models.CharField(max_length=100,default=None)
    port = models.CharField(max_length=100,default=None)
   
    def __str__(self):
        return self.domain
    
class phpextentions(models.Model):
    name = models.CharField(max_length=10)
    extentions = models.TextField(default=None)

class phpversion(models.Model):
    name = models.CharField(max_length=10)

class redir(models.Model):
    maindomain = models.CharField(max_length=100)
    domain = models.CharField(max_length=100)
    path = models.CharField(max_length=255)
    newpath = models.CharField(max_length=255)
    
    
   
    def __str__(self):
        return self.domain
   
class firewall(models.Model):
    status = models.BooleanField()

class ftp(models.Model):
    status = models.BooleanField()

class ftpaccount(models.Model):
    main = models.CharField(max_length=150,default=None)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=150)
    storage = models.CharField(max_length=150)
    

    def __str__(self):
        return self.username