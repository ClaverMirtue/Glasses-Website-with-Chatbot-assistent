from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Address, ProductImage
from django.db.models import Q, Prefetch
from django.http import JsonResponse

class CustomLoginView(LoginView):
    template_name = 'glassesapp/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, 'You have been successfully logged in!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('profile')

def home(request):
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_available=True)[:8]
    return render(request, 'glassesapp/home.html', {
        'categories': categories,
        'featured_products': featured_products
    })

def product_list(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search')
    
    products = Product.objects.filter(is_available=True)
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    categories = Category.objects.all()
    return render(request, 'glassesapp/product_list.html', {
        'products': products,
        'categories': categories
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(id=product.id)[:4]
    
    return render(request, 'glassesapp/product_detail.html', {
        'product': product,
        'related_products': related_products
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'glassesapp/signup.html', {'form': form})

@login_required
def cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'glassesapp/cart.html', {'cart': cart})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('cart')

@login_required
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()
    
    return redirect('cart')

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty. Add some products before checkout.')
        return redirect('cart')
    
    return render(request, 'glassesapp/checkout.html', {
        'cart': cart
    })

@login_required
def process_order(request):
    if request.method == 'POST':
        cart = get_object_or_404(Cart, user=request.user)
        
        if not cart.items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            shipping_address=request.POST.get('address'),
            shipping_city=request.POST.get('city'),
            shipping_state=request.POST.get('state'),
            shipping_zip=request.POST.get('zip_code'),
            shipping_country=request.POST.get('country'),
            total_price=cart.total_price
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            
            # Update product stock
            product = cart_item.product
            product.stock -= cart_item.quantity
            product.save()
        
        # Clear cart
        cart.items.all().delete()
        
        # Save address if requested
        if request.POST.get('save_address'):
            Address.objects.create(
                user=request.user,
                name=f"{request.POST.get('first_name')} {request.POST.get('last_name')}",
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                zip_code=request.POST.get('zip_code'),
                country=request.POST.get('country')
            )
        
        return redirect('order_confirmation', order_id=order.id)
    
    return redirect('checkout')

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'glassesapp/order_confirmation.html', {
        'order': order
    })

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'glassesapp/profile.html', {
        'orders': orders,
        'addresses': addresses
    })

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.profile.phone = request.POST.get('phone')
        user.save()
        user.profile.save()
        messages.success(request, 'Profile updated successfully.')
    return redirect('profile')

@login_required
def add_address(request):
    if request.method == 'POST':
        Address.objects.create(
            user=request.user,
            name=request.POST.get('name'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            zip_code=request.POST.get('zip_code'),
            country=request.POST.get('country')
        )
        messages.success(request, 'Address added successfully.')
    return redirect('profile')

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'glassesapp/order_detail.html', {
        'order': order
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

def chatbot_api(request):
    """API endpoint for the chatbot to get product and category data"""
    query_type = request.GET.get('type', '')
    query = request.GET.get('query', '').lower()
    
    if query_type == 'categories':
        # Return all categories
        categories = Category.objects.all()
        return JsonResponse({
            'categories': [
                {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description
                } for category in categories
            ]
        })
    
    elif query_type == 'products':
        # Get products, optionally filtered by category name
        products = Product.objects.filter(is_available=True)
        category_id = request.GET.get('category_id')
        
        if category_id:
            products = products.filter(category_id=category_id)
        elif query:
            products = products.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        # No longer limiting the results - show all products
        # products = products[:8]
        
        # Prefetch the primary image for each product
        products = products.prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
        )
        
        result = []
        for product in products:
            product_data = {
                'id': product.id,
                'name': product.name,
                'price': float(product.price),
                'description': product.description[:100] + '...' if len(product.description) > 100 else product.description,
                'category': product.category.name,
                'slug': product.slug,
            }
            
            # Add image URL if available
            primary_image = product.primary_images[0] if hasattr(product, 'primary_images') and product.primary_images else None
            if primary_image:
                product_data['image_url'] = primary_image.image.url
            else:
                # Try to get any image
                any_image = product.images.first()
                if any_image:
                    product_data['image_url'] = any_image.image.url
                else:
                    product_data['image_url'] = '/static/images/no-image.jpg'
            
            result.append(product_data)
        
        return JsonResponse({'products': result})
    
    # Default response
    return JsonResponse({'error': 'Invalid query type'})

def about(request):
    """
    About Us page showcasing the company story, mission, vision and team
    """
    return render(request, 'glassesapp/about.html')

def contact(request):
    """
    Contact page with contact form and location details for DG Khan
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Here you would typically send an email or save to database
        # For now, we'll just show a success message
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
        return redirect('contact')
        
    return render(request, 'glassesapp/contact.html')
