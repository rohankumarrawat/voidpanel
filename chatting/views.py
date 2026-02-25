from django.shortcuts import render
import json
from django.core.cache import cache
def set_cancel_flag():
    cache.set('cancel_loop', True, timeout=300)  # Timeout in seconds

# Clear cancel flag
def clear_cancel_flag():
    cache.delete('cancel_loop')

# Check cancel flag
def is_cancel_flag_set():
    return cache.get('cancel_loop', False)
from django.http import JsonResponse
from chatting.models import message as messagekaro
from huggingface_hub import InferenceClient
import os
client = InferenceClient(api_key=os.getenv("HUGGINGFACE_API_KEY", ""))
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import requests
from collections import defaultdict
grouped_by_name=None
def index(request):
    global current
    current=True
    grouped_by_name = defaultdict(list)
    if request.user.is_authenticated:
        todis=messagekaro.objects.filter(user=request.user).order_by('-id')
        
        group_count = 0  # Counter to keep track of the number of groups
        max_groups = 10  # Maximum number of groups

        # Group messages by 'name', stopping after 10 groups
        for message in todis:
            if message.name not in grouped_by_name:
                group_count += 1
                if group_count > max_groups:
                    break  # Stop the loop if we exceed the group limit
            grouped_by_name[message.name].append({
                'user': message.user,

    })
      


         
    return render(request,"chatting/index.html",{'grouped_by_name': dict(grouped_by_name)})



def index1(request,data):
    global current
    current=False
    request.session['current']=data
    grouped_by_name = defaultdict(list)
    grouped_by_name_ = defaultdict(list)
    if request.user.is_authenticated:
        

        todis=messagekaro.objects.filter(user=request.user).order_by('-id')
        
        group_count = 0  # Counter to keep track of the number of groups
        max_groups = 10  # Maximum number of groups
        ew=messagekaro.objects.filter(user=request.user,name=data)

        # Group messages by 'name', stopping after 10 groups
        for message in todis:
            if message.name not in grouped_by_name:
                group_count += 1
                if group_count > max_groups:
                    break  # Stop the loop if we exceed the group limit
            grouped_by_name[message.name].append({
                'name': message.name,


    })
            
        for message in ew:
            if message.name not in grouped_by_name_:
                group_count += 1
               
            grouped_by_name_[message.name].append({
                'fromai': message.fromai,
                'toai': message.toai,
              


    })
            
        

      


         
    return render(request,"chatting/index1.html",{'grouped_by_name': dict(grouped_by_name),'grouped_by_name_': dict(grouped_by_name_)})

@csrf_exempt  
def negative(request):

    if request.method == 'POST':
        print("Hello")
        try:
            data = json.loads(request.body)
            review = data.get('review')
            if not review:
                 review="none"
            content = data.get('content')
            if not content:
                 content="none"
            category = data.get('category')
            if not category:
                 category="none"
            if request.user.is_authenticated:
                url = 'https://voidpanel.com/negative/'

                data = {

                    'review': review,

                    'content': content,
                    'user':request.user,
                    'category':category

                }


                response = requests.post(url, data=data)
            else:
                url = 'https://voidpanel.com/negative/'

                data = {

                    'review': review,

                    'content': content,
                    'user':"None",
                    'category':category

                }


                response = requests.post(url, data=data)




            return JsonResponse({
                'message': 'Form submitted successfully!',
            }, status=200)

      
        except Exception as e:
            print(e)
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)

@csrf_exempt  
def positive(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            review = data.get('review')
            if not review:
                 review="none"
                 
            
            content = data.get('content')
            if request.user.is_authenticated:
                url = 'https://voidpanel.com/positive/'

                data = {

                    'review': review,

                    'content': content,
                    'user':request.user

                }


                response = requests.post(url, data=data)
            else:
                url = 'https://voidpanel.com/positive/'

                data = {

                    'review': review,

                    'content': content,
                    'user':"None"

                }


                response = requests.post(url, data=data)




            return JsonResponse({
                'message': 'Form submitted successfully!',
            }, status=200)

      
        except Exception as e:
            print(e)
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)


def ai(request):
    return render(request,"chatting/ai.html")

def profile(request):
    return render(request,"chatting/profile.html")
messages = []
current=True
def chatmessage(request):
        global current
       
        clear_cancel_flag()  
     
        if request.method =="POST":
               data = json.loads(request.body) 
               message = data.get('message') 
   
               if current:
                    request.session['current']=message
                    current=False
            
               def generate_data():
                inside_code_block=False
                messages.append({"role": "user", "content": message})
                stream = client.chat.completions.create(model="Qwen/Qwen2.5-Coder-32B-Instruct",messages=messages,max_tokens=1000,stream=True)
                datatoshow=""
                tosave=""
                for chunk in stream:
                            if is_cancel_flag_set():
                                 break
                      
                            content = chunk.choices[0].delta.content
                            datatoshow+=content
                            ds=content.strip()
                            if ds == "`":
                                  content=content.replace('`',"")

                            if "Alibaba" or "alibaba" in content:
                                  
                                  content=content.replace("Alibaba","Voidpanel")
                                  content=content.replace("alibaba","Voidpanel")
          
                            if content.isspace():
                                  countnu=content.count(' ')
                                  
                                  yield "&nbsp;"*countnu
                                  tosave+="&nbsp;"*countnu
                            if '\n' in content:
                                  yield content+"<br>"
                                  tosave+=content+"<br>"
                                 
                            else:
                                yield content
                                tosave+=content
                          
                messages.append({"role": "assistant", "content": datatoshow})
                if request.user.is_authenticated:
                    wef=messagekaro.objects.create(user=request.user,toai=message,name=request.session.get('current'),fromai=tosave)
               response = StreamingHttpResponse(
                            generate_data(),
                            content_type="text/html"
                        )
               return response


@csrf_exempt  
def stopcode(request):
   

    if request.method == 'POST':
   
            set_cancel_flag()
            return JsonResponse({'status':"done"})

    return JsonResponse({'error': 'Invalid HTTP method. Use POST.'}, status=405)