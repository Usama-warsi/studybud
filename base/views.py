from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import Room,Message,Topic
from .forms import RoomForm,UserForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
import re
from email.utils import parseaddr


def loginpage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        try:
            user = User.objects.get(username = username)
        except:
            messages.error(request, "Userame And Password Does Not Match.")
        user = authenticate(request,username=username,password=password)
        if user is not None:
            login(request,user)
            return redirect('home')
        else:
            messages.error(request, "Userame And Password Does Not Match.")


    context = {'page':page}
    return render(request,'base/login_register.html',context)

def logoutUser(request):
    logout(request)
    return redirect('home')

def registerUser(request):
    form = UserCreationForm()
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        # if form.is_valid():
        if re.match(r"^\S+@\S+\.\S+$", request.POST.get('email')) is not None:
            if re.match("^[a-zA-Z0-9_.-]+$", request.POST.get('username')) is not None:
                if re.fullmatch("^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{8,}$", request.POST.get('password1')) is not None:
                    if request.POST.get('password1') == request.POST.get('password2'):
                        user = form.save(commit=False)
                        user.email = request.POST.get('email')
                        user.username = user.username.lower()
                        form.save()
                        login(request,user)
                        return redirect('home')
                    else:
                        messages.error(request,'Passwords do not match')
                else:
                    messages.error(request,'Password is not strong')
            else:
                messages.error(request,'Username is not valid')
        else:
            messages.error(request,'Email is not valid')

    context = {'form':form}
    return render(request,'base/login_register.html',context)

def home(request):
    # q = None
    t = request.GET.get('t') if request.GET.get('t') != None else False
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    if t != False:
        rooms = Room.objects.filter(Q(topic=t))
    else:    
        rooms = Room.objects.filter(Q(topic__name__icontains=q)|
        Q(name__icontains=q)
        |Q(description__icontains=q)
        |Q(host__username__icontains=q)
        )
    room_count = rooms.count()
    topics = Topic.objects.all()
    chat = Message.objects.filter(Q(room__topic__name__icontains=q))
    context = {'rooms':rooms,'topics':topics,'chat':chat,'room_count':room_count}

    return render(request,'base/home.html',context)

def room(request,pk):
    room = Room.objects.get(id = pk)
    chat = room.message_set.all().order_by('-created')
    if request.method == 'POST':
        if request.POST.get('body') != '':
            message = Message.objects.create(
                user=request.user,
                room=room,
                body=request.POST.get('body')
            ) 
            return redirect('room',pk=room.id)
        else:
            pass

    context = {'room':room,'chat':chat,'participants':room.participants.all()}
    return render(request,'base/room.html',context)

def profile(request,pk):
    user = User.objects.get(id = pk)
    rooms = user.room_set.all()
    chat = user.message_set.order_by('-created')[:5]
    topics = Topic.objects.all()
    room_count = Room.objects.all().count()
    context = {'user':user.username,'rooms':rooms,'chat':chat,'topics':topics,'room_count':room_count}
    return render(request,'base/profile.html',context)


@login_required(login_url='login')
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic,created = Topic.objects.get_or_create(name=topic_name)
        Room.objects.create(   
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description')
        )
        return redirect('home')
    context = {'form':form,'topics':topics}
    return render(request,'base/room_form.html',context)

@login_required(login_url='login')
def updateRoom(request,pk):
    room = Room.objects.get(id = pk)
    if request.user != room.host:
        return HttpResponse('You Are Not Allowed Here!!!!   ')
    
    topics = Topic.objects.all()
    form = RoomForm(instance=room)
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic,created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')
        # room.ed
        # print(request.POST) 
        # form = RoomForm(request.POST,instance=room)
        # if form.is_valid():

    context = { 'form' : form,'topics':topics,'room':room}
    return render(request,'base/room_form.html',context)

@login_required(login_url='login')
def deleteRoom(request,pk):
    room = Room.objects.get(id = pk)
    if request.user != room.host:
        return HttpResponse('You Are Not Allowed Here!!!!')
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request,'base/delete.html',{'obj':room})

@login_required(login_url='login')
def deleteMessage(request,pk):

    try:
        message = Message.objects.get(id = pk)
        room = message.room.id
        if request.user != message.user:
            return HttpResponse('You Are Not Allowed Here!!!!')
        if request.method == 'POST':
            message.delete()
            return redirect('room',room)
        return render(request,'base/delete.html',{'obj':message})
    except Exception as e:
        return HttpResponse(e)

def addParticipant(request,pk):
    # user = User.objects.get(id = pk)
    room = Room.objects.get(id = pk)
    # if request.user == room.participants:
    room.participants.add(request.user.id)
    return redirect('room',room.id)

@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)
    if request.method == 'POST':
        form = UserForm(request.POST,instance=user)
        if form.is_valid():
            form.save(commit=False)
            user.username = user.username.lower()
            user.email = user.email.lower()
            form.save()
            return redirect('profile',user.id)
    return render(request,'base/update-user.html',{'form':form})

def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Room.objects.filter(Q(name__icontains=q))
    # topics = Topic.objects.all()
    rooms = Room.objects.all()
    room_count = rooms.count()
    context = {'topics':topics,'room_count':room_count}
    return render(request,'base/topics.html',context)