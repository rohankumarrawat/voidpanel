from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from data.models import Message, Installed, admindocumentation, clientdocumentation, updates, positive_review, negative_review


# ─── Serializers ────────────────────────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['text', 'date', 'photo']


class AdminDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = admindocumentation
        fields = ['text', 'date', 'link']


class ClientDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = clientdocumentation
        fields = ['text', 'date', 'link']


class InstalledSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installed
        fields = ['ip', 'number']


class UpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = updates
        fields = ['version']


class PositiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = positive_review
        fields = ['review', 'user', 'content']


class NegativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = negative_review
        fields = ['review', 'user', 'category', 'content']


# ─── API Views ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
def positive(request):
    serializer = PositiveSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def negative(request):
    serializer = NegativeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def latest_messages(request):
    msgs = Message.objects.all().order_by('-date')[:4]
    serializer = MessageSerializer(msgs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def update(request):
    latest = updates.objects.latest('id')
    serializer = UpdateSerializer(latest)
    return Response(serializer.data)


@api_view(['GET'])
def admindocs(request):
    docs = admindocumentation.objects.all().order_by('date')
    serializer = AdminDocSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def clientdocs(request):
    docs = clientdocumentation.objects.all().order_by('date')
    serializer = ClientDocSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def increment_number(request):
    ip_address = request.data.get('ip')
    installed_obj, _ = Installed.objects.get_or_create(ip=ip_address)
    installed_obj.number += 1
    installed_obj.save()
    serializer = InstalledSerializer(installed_obj)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ─── Page Views ─────────────────────────────────────────────────────────────────

def index(request):
    return render(request, "index.html")


def aboutus(request):
    return render(request, "aboutus.html")


def addemail(request):
    return render(request, "addemail.html")


def ssl(request):
    return render(request, "addssl.html")


def voidpanelinfo(request):
    return render(request, "blogs/voidpanelinfo.html")


def overview(request):
    return render(request, "overview.html")


def db(request):
    return render(request, "db.html")


def chpass(request):
    return render(request, "chpass.html")


def addweb(request):
    return render(request, "addweb.html")


def notifications(request):
    context = {'data': Message.objects.all().order_by('-date')}
    return render(request, "notifications.html", context)


def docs(request):
    return render(request, "docs.html")


def blog(request):
    return render(request, "blog.html")


def blog1(request):
    return render(request, "blogs/blog1.html")


def blog2(request):
    return render(request, "blogs/blog2.html")


def blog3(request):
    return render(request, "blogs/blog3.html")


def blogs(request):
    return render(request, "blogs.html")


def whmcs(request):
    return render(request, "whmcs.html")


def loginn(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == 'POST':
        email = request.POST.get('Email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            messages.error(request, "Invalid email or password")
            return redirect('/login/')
    return render(request, "login.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == 'POST':
        email = request.POST.get('Email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'register.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return render(request, 'register.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return render(request, 'register.html')
        User.objects.create_user(username=username, email=email, password=password)
        return redirect("/")
    return render(request, 'register.html')