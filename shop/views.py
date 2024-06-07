import stripe
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Order, Cart, CartItem
from django.http import JsonResponse

stripe.api_key = settings.STRIPE_SECRET_KEY

def product_list(request):
    """
    Display a list of available products.
    """
    products = Product.objects.all()
    cart_items_count = CartItem.objects.filter(cart_id=request.session.get('cart_id')).count()
    return render(request, 'shop/product_list.html', {'products': products, 'cart_items_count': cart_items_count})

def product_detail(request, product_id):
    """
    Display the details of a specific product.
    """
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'shop/product_detail.html', {'product': product})

def cart_detail(request):
    """
    Display the shopping cart and its contents.
    """
    cart_id = request.session.get('cart_id')
    if cart_id:
        cart = get_object_or_404(Cart, id=cart_id)
        cart_items = CartItem.objects.filter(cart=cart)
    else:
        cart_items = []
    return render(request, 'shop/cart_detail.html', {'cart_items': cart_items})

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(id=request.session.get('cart_id'))
    if created:
        request.session['cart_id'] = cart.id
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return JsonResponse({'cart_items': CartItem.objects.filter(cart=cart).count()})

def remove_from_cart(request, item_id):
    """
    Remove an item from the shopping cart.
    """
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    return redirect('cart_detail')

def create_checkout_session(request):
    """
    Create a Stripe checkout session for the items in the cart.
    """
    cart_id = request.session.get('cart_id')
    if not cart_id:
        return redirect('product_list')
    
    cart = get_object_or_404(Cart, id=cart_id)
    cart_items = CartItem.objects.filter(cart=cart)

    if not cart_items:
        return redirect('product_list')

    line_items = []
    for item in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item.product.name,
                },
                'unit_amount': int(item.product.price * 100),
            },
            'quantity': item.quantity,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url='http://localhost:8000/success/',
        cancel_url='http://localhost:8000/cancel/',
    )

    # Save the order with payment intent ID
    for item in cart_items:
        Order.objects.create(
            product=item.product,
            quantity=item.quantity,
            payment_intent_id=session.payment_intent
        )

    return redirect(session.url, code=303)

def payment_success(request):
    """
    Handle successful payment.
    """
    return render(request, 'shop/payment_success.html')

def payment_cancel(request):
    """
    Handle canceled payment.
    """
    return render(request, 'shop/payment_cancel.html')
