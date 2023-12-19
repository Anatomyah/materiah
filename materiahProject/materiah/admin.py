from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, SupplierUserProfile, Product, Manufacturer, Supplier, Order, OrderItem, Quote, \
    QuoteItem, ManufacturerSupplier, ProductImage, OrderImage, OrderNotifications, ProductOrderStatistics, \
    FileUploadStatus


class ManufacturerSupplierInline(admin.TabularInline):
    """
    ManufacturerSupplierInline

        This class represents a tabular inline for the ManufacturerSupplier model in the Django admin.

    Attributes:
        model (Model): The ManufacturerSupplier model that this inline corresponds to.
        extra (int): The number of extra form instances to display when rendering the inline.

    """
    model = ManufacturerSupplier
    extra = 0


class ManufacturerAdmin(admin.ModelAdmin):
    """Admin class for managing manufacturers."""
    inlines = [ManufacturerSupplierInline]


class SupplierAdmin(admin.ModelAdmin):
    """A class representing the admin interface for managing suppliers.

    This class extends the `admin.ModelAdmin` class, which is provided by Django's admin site.
    It is used to customize the behavior and appearance of the admin interface for the Supplier model.

    Attributes:
        inlines (list): A list of inline classes to be displayed on the supplier admin page.

    """
    inlines = [ManufacturerSupplierInline]


class QuoteItemInline(admin.StackedInline):
    """
    A class representing an inline quote item in the admin interface.

    :class:`QuoteItemInline` is a subclass of `admin.StackedInline` and is used to display quote items in a stacked format within a quote object in the admin interface.

    Attributes:
        model (Model): The model class that represents the quote item.
        extra (int): The number of empty quote item forms to display.

    """
    model = QuoteItem
    extra = 0


class QuoteAdmin(admin.ModelAdmin):
    """
    Admin class for managing quotes in the Django admin interface.

    :ivar inlines: A list of inline classes to use in the admin interface.
    :vartype inlines: list

    Usage:
        - Register the QuoteAdmin class in the admin.py file of your Django app.

    Example:
        ```
        from django.contrib import admin

        class QuoteAdmin(admin.ModelAdmin):
            inlines = [QuoteItemInline]
        admin.site.register(Quote, QuoteAdmin)
        ```
    """
    inlines = [QuoteItemInline]


class OrderItemForm(forms.ModelForm):
    """

    OrderItemForm Class

    This class is a form used for creating and updating instances of the OrderItem model.

    """

    class Meta:
        model = OrderItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """
        Initialize the OrderItemForm object.

        :param args: Variable length arguments.
        :param kwargs: Keyword arguments.

        """
        super(OrderItemForm, self).__init__(*args, **kwargs)
        if self.instance.order_id:
            self.fields['quote_item'].queryset = QuoteItem.objects.filter(quote=self.instance.order.quote)


class OrderItemAdmin(admin.ModelAdmin):
    """
    The `OrderItemAdmin` class is a subclass of `admin.ModelAdmin` and is used for managing the order items in the admin interface.

    :class:`OrderItemAdmin` Attributes:

        - ``form``: An instance of the `OrderItemForm` class, used for customizing the form for creating or updating order items.

    """
    form = OrderItemForm


class ImagesInline(admin.StackedInline):
    """
    A class that defines an inline administration interface for ProductImage model.

    Attributes:
        model (Model): The model object to be managed by the inline interface.
        extra (int): The number of extra inline forms to display.
    """
    model = ProductImage
    extra = 0


class ProductAdmin(admin.ModelAdmin):
    """
    A class representing an admin for managing products in the system.

    Attributes:
        inlines (list): A list of inlines to be displayed when editing a product.
    """
    inlines = [ImagesInline]


class UserProfileInline(admin.StackedInline):
    """
    This class represents a stacked inline for the UserProfile model in the admin interface.

    Attributes:
        model (Model): The UserProfile model that will be used for the stacked inline.
        extra (int): The number of additional forms that should be displayed in the stacked inline.

    """
    model = UserProfile
    extra = 0


class SupplierUserProfileInline(admin.StackedInline):
    """
    This class represents an inline form for the SupplierUserProfile model in the Django admin site.

    :ivar model: The model associated with this inline form (SupplierUserProfile).
    :type model: Model
    :ivar extra: The number of extra empty forms to display when editing a SupplierUserProfile instance.
    :type extra: int
    """
    model = SupplierUserProfile
    extra = 0


class UserAdmin(DefaultUserAdmin):
    """
    Class UserAdmin

    This class extends the DefaultUserAdmin class and is responsible for managing user administration.

    Attributes:
        inlines (list): A list of inline model classes to be displayed on the UserAdmin page.
        add_fieldsets (tuple): A tuple of fieldsets to be displayed on the add user page.

    Usage:

        # Import UserAdmin
        from django.contrib import admin

        # Define your custom inline model classes
        class UserProfileInline(admin.StackedInline):
            model = UserProfile

        class SupplierUserProfileInline(admin.StackedInline):
            model = SupplierUserProfile

        # Define your custom UserAdmin class
        class UserAdmin(admin.ModelAdmin):
            inlines = [UserProfileInline, SupplierUserProfileInline]

            add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email')}
                 ),
            )

        # Register the UserAdmin class
        admin.site.register(User, UserAdmin)
    """
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
admin.site.register(OrderNotifications)
admin.site.register(ProductOrderStatistics)
admin.site.register(OrderImage)
admin.site.register(FileUploadStatus)
