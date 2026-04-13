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
from chatting.knowledge import search_knowledge, KNOWLEDGE_BASE
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
                results = search_knowledge(message)
                tosave = ""

                if results:
                    # Show the top 3 matching help articles
                    shown = results[:3]
                    intro = f"I found <b>{len(shown)}</b> help topic{'s' if len(shown) > 1 else ''} for your question:<br><br>"
                    yield intro
                    tosave += intro

                    for i, entry in enumerate(shown, 1):
                        header = f"<b>{i}. {entry['title']}</b><br>"
                        yield header
                        tosave += header

                        body = entry['answer'] + "<br><br>"
                        yield body
                        tosave += body

                        if is_cancel_flag_set():
                            break

                    if len(results) > 3:
                        more = f"<i>...and {len(results) - 3} more related topic(s). Try a more specific question to narrow down.</i><br>"
                        yield more
                        tosave += more
                else:
                    # No match — show available topics
                    no_match = (
                        "I couldn't find a specific answer for that. Here are the topics I can help with:<br><br>"
                    )
                    yield no_match
                    tosave += no_match

                    topics = sorted(set(e['title'] for e in KNOWLEDGE_BASE))
                    for t in topics:
                        line = f"• {t}<br>"
                        yield line
                        tosave += line

                    hint = "<br><i>Try asking about any of these topics!</i><br>"
                    yield hint
                    tosave += hint

                if request.user.is_authenticated:
                    messagekaro.objects.create(
                        user=request.user,
                        toai=message,
                        name=request.session.get('current'),
                        fromai=tosave,
                    )

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