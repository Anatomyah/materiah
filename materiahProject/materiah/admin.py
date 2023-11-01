from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User

from materiah.models import UserProfile, SupplierUserProfile, Product, Manufacturer, Supplier, Order, OrderItem, Quote, \
    QuoteItem, ManufacturerSupplier
from materiah.models.product import ProductImage


class ManufacturerSupplierInline(admin.TabularInline):  # or admin.StackedInline
    model = ManufacturerSupplier
    extra = 0


class ManufacturerAdmin(admin.ModelAdmin):
    inlines = [ManufacturerSupplierInline]


class SupplierAdmin(admin.ModelAdmin):
    inlines = [ManufacturerSupplierInline]


class QuoteItemInline(admin.StackedInline):
    model = QuoteItem
    extra = 0


class QuoteAdmin(admin.ModelAdmin):
    inlines = [QuoteItemInline]


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        if self.instance.order_id:
            self.fields['quote_item'].queryset = QuoteItem.objects.filter(quote=self.instance.order.quote)


class OrderItemAdmin(admin.ModelAdmin):
    form = OrderItemForm


class ImagesInline(admin.StackedInline):
    model = ProductImage
    extra = 0


class ProductAdmin(admin.ModelAdmin):
    inlines = [ImagesInline]


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0


class SupplierUserProfileInline(admin.StackedInline):
    model = SupplierUserProfile
    extra = 0


class UserAdmin(DefaultUserAdmin):
    inlines = [UserProfileInline, SupplierUserProfileInline]

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email')}
         ),
    )


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
admin.site.register(SupplierUserProfile)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(ManufacturerSupplier)
admin.site.register(Supplier, SupplierAdmin)
admin.site.register(Order)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Quote, QuoteAdmin)
admin.site.register(QuoteItem)
