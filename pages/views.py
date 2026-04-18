from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse 
from .models import Category, Product, UserProfile, OrderQueue, OrderItem 
import random
import json 

def index(request):
    selected_category = request.GET.get('category', 'All')
    categories = Category.objects.all()
    if selected_category == 'All':
        products = Product.objects.all()
    else:
        products = Product.objects.filter(category__name=selected_category)

    if 'banner_product_ids' in request.session:
        banner_ids = request.session['banner_product_ids']
        products_qs = Product.objects.filter(id__in=banner_ids)
        product_dict = {p.id: p for p in products_qs}
        banner_products = [product_dict[i] for i in banner_ids if i in product_dict]
    else:
        banner_products = []
        for cat in categories:
            cat_products = list(Product.objects.filter(category=cat).order_by('?')[:3])
            banner_products.extend(cat_products)
        random.shuffle(banner_products) 
        request.session['banner_product_ids'] = [p.id for p in banner_products]
   
    has_active_queue = False
    queue_status = '' 
    past_orders = [] 
    
    if request.user.is_authenticated:
        active_q = OrderQueue.objects.filter(user=request.user).exclude(status='completed').first()
        if active_q:
            has_active_queue = True
            queue_status = active_q.status
            
        if not hasattr(request.user, 'profile'):
            UserProfile.objects.create(user=request.user)

        completed_queues = OrderQueue.objects.filter(user=request.user, status='completed')
        purchased_names = OrderItem.objects.filter(queue__in=completed_queues).values_list('product_name', flat=True).distinct()
        past_orders = Product.objects.filter(name__in=purchased_names)[:10]

    elif 'active_queue_id' in request.session:
        active_q = OrderQueue.objects.filter(id=request.session['active_queue_id']).exclude(status='completed').first()
        if active_q:
            has_active_queue = True
            queue_status = active_q.status

    context = {
        'categories': categories, 'products': products,
        'selected_category': selected_category, 'banner_products': banner_products,
        'has_active_queue': has_active_queue,
        'queue_status': queue_status, 
        'past_orders': past_orders,
    }
    return render(request, 'pages/index.html', context)

def checkout(request): 
    if request.user.is_authenticated:
        if OrderQueue.objects.filter(user=request.user).exclude(status='completed').exists():
            return redirect('index')
    elif 'active_queue_id' in request.session:
        if OrderQueue.objects.filter(id=request.session['active_queue_id']).exclude(status='completed').exists():
            return redirect('index')
            
    return render(request, 'pages/checkout.html')

def queue(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            if OrderQueue.objects.filter(user=request.user).exclude(status='completed').exists():
                return redirect('index')
        elif 'active_queue_id' in request.session:
            if OrderQueue.objects.filter(id=request.session['active_queue_id']).exclude(status='completed').exists():
                return redirect('index')

        dining_option = request.POST.get('dining_option')
        table_number = request.POST.get('table_number', '')
        
        last_queue = OrderQueue.objects.exclude(status='completed').order_by('-created_at').first()
        if last_queue and last_queue.queue_number.isdigit():
            next_num = int(last_queue.queue_number) + 1
            if next_num > 999:
                next_num = 1
        else:
            next_num = 1
            
        queue_number = f"{next_num:03d}"
        
        payment_method = request.POST.get('payment_method', 'cash')
        payment_status = 'paid' if payment_method == 'promptpay' else 'pending'
        
        discount_used = request.POST.get('discount_used', 'none')
        if request.user.is_authenticated:
            profile = request.user.profile
            if discount_used == '20_percent' and profile.points >= 100:
                profile.points -= 100
                profile.save()
            elif discount_used == 'free_drink' and profile.points >= 150:
                profile.points -= 150
                profile.save()
            else:
                discount_used = 'none' 
        else:
            discount_used = 'none'
        
        new_queue = OrderQueue.objects.create(
            user=request.user if request.user.is_authenticated else None,
            queue_number=queue_number,
            dining_option=dining_option,
            table_number=table_number,
            status='cooking',
            payment_method=payment_method, 
            payment_status=payment_status,
            discount_used=discount_used 
        )

        cart_data = request.POST.get('cart_data', '[]')
        try:
            items = json.loads(cart_data)
            for item in items:
                OrderItem.objects.create(
                    queue=new_queue,
                    product_name=item.get('name', 'ไม่ระบุ'),
                    price=item.get('price', 0),
                    qty=item.get('qty', 1),
                    sweetness=item.get('sweetness', ''), 
                    drink_type=item.get('drink_type', ''),
                    size=item.get('size', ''),
                    boba=item.get('boba', ''),
                    flavor=item.get('flavor', ''),
                    meat=item.get('meat', '')
                )
        except json.JSONDecodeError:
            pass 

        if request.user.is_authenticated:
            request.user.profile.points += 10
            request.user.profile.save()
        else:
            request.session['active_queue_id'] = new_queue.id
            
        messages.success(request, 'order_placed', extra_tags='order_placed')
        return redirect('index') 
    
    return redirect('index')

def clear_queue(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            OrderQueue.objects.filter(user=request.user).update(status='completed')
        elif 'active_queue_id' in request.session:
            OrderQueue.objects.filter(id=request.session['active_queue_id']).update(status='completed')
            del request.session['active_queue_id']
    return redirect('index')

def profile(request): 
    return render(request, 'pages/profile.html')

def edit_profile(request):
    if request.method == 'POST' and request.user.is_authenticated:
        request.user.username = request.POST.get('username', request.user.username)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        
        if 'profile_pic' in request.FILES:
            request.user.profile.profile_pic = request.FILES['profile_pic']
            request.user.profile.save()
            
        return redirect('index')
        
    return render(request, 'pages/edit_profile.html')

def staff_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'เฉพาะพนักงานเท่านั้นที่สามารถเข้าถึงหน้านี้ได้', extra_tags='login')
        return redirect('index')
        
    active_queues = OrderQueue.objects.exclude(status='completed').order_by('created_at')
    return render(request, 'pages/staff_dashboard.html', {'queues': active_queues})

def update_queue_status(request, queue_id, new_status):
    if request.user.is_staff:
        queue = get_object_or_404(OrderQueue, id=queue_id)
        queue.status = new_status
        queue.save()
    return redirect('staff_dashboard')

def update_payment_status(request, queue_id, new_status):
    if request.user.is_staff:
        queue = get_object_or_404(OrderQueue, id=queue_id)
        queue.payment_status = new_status
        queue.save()
    return redirect('staff_dashboard')

def custom_login(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            auth_login(request, user)
            
            if 'active_queue_id' in request.session:
                guest_queue = OrderQueue.objects.filter(id=request.session['active_queue_id']).first()
                if guest_queue and guest_queue.user is None:
                    guest_queue.user = user
                    guest_queue.save()
                del request.session['active_queue_id'] 
                
            if user.is_staff:
                return redirect('staff_dashboard')
        else:
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่', extra_tags='login')
    return redirect('index')

def custom_register(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        if User.objects.filter(username=u).exists():
            messages.error(request, 'ชื่อผู้ใช้นี้มีคนใช้แล้ว กรุณาใช้ชื่ออื่น', extra_tags='register')
        elif len(p) < 6:
            messages.error(request, 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', extra_tags='register')
        else:
            user = User.objects.create_user(username=u, password=p)
            UserProfile.objects.create(user=user)
            auth_login(request, user)
            
            if 'active_queue_id' in request.session:
                guest_queue = OrderQueue.objects.filter(id=request.session['active_queue_id']).first()
                if guest_queue and guest_queue.user is None:
                    guest_queue.user = user
                    guest_queue.save()
                del request.session['active_queue_id']
                
    return redirect('index')

def custom_logout(request):
    if request.method == 'POST':
        auth_logout(request)
    return redirect('index')

def delete_account(request):
    if request.method == 'POST' and request.user.is_authenticated:
        user = request.user
        auth_logout(request)
        user.delete()
    return redirect('index')

def api_check_queue(request):
    status = 'none'
    queue_number = ''
    if request.user.is_authenticated:
        active_q = OrderQueue.objects.filter(user=request.user).exclude(status='completed').first()
        if active_q:
            status = active_q.status
            queue_number = active_q.queue_number
    elif 'active_queue_id' in request.session:
        active_q = OrderQueue.objects.filter(id=request.session['active_queue_id']).exclude(status='completed').first()
        if active_q:
            status = active_q.status
            queue_number = active_q.queue_number
    return JsonResponse({'status': status, 'queue_number': queue_number})

def add_staff(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, 'เฉพาะเจ้าของร้าน (Admin) เท่านั้นที่สามารถเพิ่มพนักงานได้', extra_tags='login')
        return redirect('index')
        
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        
        if User.objects.filter(username=u).exists():
            messages.error(request, 'ชื่อผู้ใช้นี้มีในระบบแล้ว กรุณาใช้ชื่ออื่น', extra_tags='add_staff_error')
        elif len(p) < 6:
            messages.error(request, 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', extra_tags='add_staff_error')
        else:
            new_staff = User.objects.create_user(username=u, password=p)
            new_staff.is_staff = True 
            new_staff.save()
            
            UserProfile.objects.create(user=new_staff)
            
            messages.success(request, f'เพิ่มบัญชีพนักงาน "{u}" เรียบร้อยแล้ว!', extra_tags='add_staff_success')
            return redirect('add_staff')
            
    return render(request, 'pages/add_staff.html')