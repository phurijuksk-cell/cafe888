from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image_url = models.URLField(max_length=500, blank=True, null=True)
    def __str__(self): return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    points = models.IntegerField(default=0)
    
    def __str__(self):
        return f"โปรไฟล์ของ {self.user.username}"

class OrderQueue(models.Model):
    STATUS_CHOICES = (
        ('cooking', 'กำลังเตรียมเมนู'),
        ('ready', 'เสร็จสิ้น (รอรับสินค้า)'),
        ('completed', 'รับสินค้าแล้ว (จบออเดอร์)'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'ยังไม่ชำระเงิน'),
        ('paid', 'ชำระเงินแล้ว'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    queue_number = models.CharField(max_length=10)
    dining_option = models.CharField(max_length=50) 
    table_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cooking')
    
    payment_method = models.CharField(max_length=50, default='cash')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    discount_used = models.CharField(max_length=50, default='none')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"คิว {self.queue_number} - {self.get_status_display()}"

    @property
    def get_net_total(self):
        subtotal = sum(item.price * item.qty for item in self.items.all())
        if self.discount_used == '20_percent':
            return subtotal * Decimal('0.8')
        elif self.discount_used == 'free_drink':
            drink_prices = [item.price for item in self.items.all() if item.drink_type]
            if drink_prices:
                return subtotal - max(drink_prices)
        return subtotal

class OrderItem(models.Model):
    queue = models.ForeignKey(OrderQueue, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    qty = models.IntegerField(default=1)
    
    sweetness = models.CharField(max_length=20, blank=True, null=True)
    drink_type = models.CharField(max_length=20, blank=True, null=True)
    # เพิ่มใหม่: เก็บขนาดแก้ว (ปกติ, ใหญ่, ใหญ่พิเศษ)
    size = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.qty}x {self.product_name} (คิว {self.queue.queue_number})"