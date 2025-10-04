from django.contrib import admin
from .models import Category, Product, ProductImage, Cart, CartItem
from .admin_site import admin_site

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_available', 'created_at')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    list_editable = ('price', 'stock', 'is_available')

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'total_price')

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'total_price')
    readonly_fields = ('user', 'created_at', 'updated_at')
    inlines = [CartItemInline]

    def total_price(self, obj):
        return f"Rs. {obj.total_price}"
    total_price.short_description = 'Total Price'

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart__user',)
    search_fields = ('product__name', 'cart__user__username')

    def total_price(self, obj):
        return f"Rs. {obj.total_price}"
    total_price.short_description = 'Total Price'

# Register models with custom admin site
admin_site.register(Category, CategoryAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(Cart, CartAdmin)
admin_site.register(CartItem, CartItemAdmin)
