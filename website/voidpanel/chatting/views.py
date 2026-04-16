from django.shortcuts import render
import json
from django.http import JsonResponse, StreamingHttpResponse
from chatting.models import message as messagekaro
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
import requests
import os
from openai import OpenAI

# Initialize Hugging Face Together client once
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",  # Make sure you set HF_TOKEN in environment
)

# Global variables
messages = []
current = True
coderun = True


def index(request):
    global current
    current = True
    grouped_by_name = defaultdict(list)
    if request.user.is_authenticated:
        todis = messagekaro.objects.filter(user=request.user).order_by('-id')
        group_count = 0
        max_groups = 10

        # Group messages by 'name', stopping after 10 groups
        for message in todis:
            if message.name not in grouped_by_name:
                group_count += 1
                if group_count > max_groups:
                    break
            grouped_by_name[message.name].append({
                'user': message.user,
            })
    return render(request, "chatting/index.html", {'grouped_by_name': dict(grouped_by_name)})


def index1(request, data):
    global current
    current = False
    request.session['current'] = data
    grouped_by_name = defaultdict(list)
    grouped_by_name_ = defaultdict(list)
    if request.user.is_authenticated:
        todis = messagekaro.objects.filter(user=request.user).order_by('-id')
        ew = messagekaro.objects.filter(user=request.user, name=data)

        # Group messages by 'name', stopping after 10 groups
        group_count = 0
        max_groups = 10
        for message in todis:
            if message.name not in grouped_by_name:
                group_count += 1
                if group_count > max_groups:
                    break
            grouped_by_name[message.name].append({'name': message.name})

        for message in ew:
            grouped_by_name_[message.name].append({
                'fromai': message.fromai,
                'toai': message.toai,
            })

    return render(request, "chatting/index1.html", {
        'grouped_by_name': dict(grouped_by_name),
        'grouped_by_name_': dict(grouped_by_name_)
    })


@csrf_exempt
def negative(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            review = data.get('review', "none")
            content = data.get('content', "none")
            category = data.get('category', "none")

            user_val = request.user if request.user.is_authenticated else "None"
            url = 'https://voidpanel.com/negative/'
            payload = {'review': review, 'content': content, 'user': user_val, 'category': category}
            requests.post(url, data=payload)

            return JsonResponse({'message': 'Form submitted successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)


@csrf_exempt
def positive(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            review = data.get('review', "none")
            content = data.get('content', "none")
            user_val = request.user if request.user.is_authenticated else "None"
            url = 'https://voidpanel.com/positive/'
            payload = {'review': review, 'content': content, 'user': user_val}
            requests.post(url, data=payload)

            return JsonResponse({'message': 'Form submitted successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)


def ai(request):
    return render(request, "chatting/ai.html")


def profile(request):
    return render(request, "chatting/profile.html")


@csrf_exempt
def chatmessage(request):
    """
    Handle chat messages and stream Qwen2.5-Coder responses
    """
    global current, coderun, messages

    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get('message', '')
        coderun = True

        if current:
            request.session['current'] = message
            current = False

        def generate_data():
            nonlocal message
            datatoshow = ""
            tosave = ""
            messages.append({"role": "user", "content": message})

            # Use Hugging Face Together API with streaming
            stream = client.chat.completions.create(
                model="Qwen/Qwen2.5-Coder-32B-Instruct",
                messages=messages,
                max_tokens=1000,
                stream=True
            )
            for chunk in stream:
                if not coderun:
                    break

                # Correct access
                content = chunk.choices[0].delta.content
                datatoshow += content
                ds = content.strip()

                # Remove standalone backticks
                if ds == "`":
                    content = content.replace('`', '')

                # Replace Alibaba with Voidpanel
                content = content.replace("Alibaba", "Voidpanel").replace("alibaba", "Voidpanel")

                # Handle spaces and newlines
                if content.isspace():
                    countnu = content.count(' ')
                    yield "&nbsp;" * countnu
                    tosave += "&nbsp;" * countnu
                elif '\n' in content:
                    yield content.replace('\n', '<br>')
                    tosave += content.replace('\n', '<br>')
                else:
                    yield content
                    tosave += content



            # Append assistant response to conversation
            messages.append({"role": "assistant", "content": datatoshow})

            # Save chat to DB
            if request.user.is_authenticated:
                messagekaro.objects.create(
                    user=request.user,
                    toai=message,
                    name=request.session.get('current'),
                    fromai=tosave
                )

        return StreamingHttpResponse(generate_data(), content_type="text/html")


@csrf_exempt
def stopcode(request):
    global coderun
    if request.method == 'POST':
        coderun = False
        return JsonResponse({'status': "done"})
    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)
