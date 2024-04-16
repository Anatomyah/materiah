import json
import uuid
from django.db import transaction
from rest_framework import serializers

from ..models import Manufacturer, Supplier
from ..models.file import FileUploadStatus
from ..models import Product, ProductImage, ProductItem
from ..s3 import create_presigned_post, delete_s3_object


class ProductItemSerializer(serializers.ModelSerializer):
    """
    Class: ProductItemSerializer

    This class is a serializer for the ProductItem model. It is used to serialize ProductItem instances into JSON
    format.

    Attributes:
        - order (serializers.SerializerMethodField): A method field that retrieves the related Order information.

    Methods: - get_order(obj: ProductItem) -> dict: Returns a dictionary with Order ID and arrival date for
    ProductItem's related Order.
    """
    order = serializers.SerializerMethodField()

    class Meta:
        model = ProductItem
        fields = ['id', 'batch', 'in_use', 'expiry', 'order']

    @staticmethod
    def get_order(obj):
        """Returns a dictionary with Order ID and arrival date for ProductItem's related Order.

        Args:
            obj (ProductItem): Instance of ProductItem model.

        Returns:
            dict: Dictionary containing Order ID and arrival date, or None if no related Order.
        """
        if hasattr(obj, 'order_item'):
            # Return the desired information if a related Order exists
            return {"id": obj.order_item.order.id, "arrival_date": obj.order_item.order.arrival_date}

        # Return None if no related Order
        return None

    def to_representation(self, instance):
        """
        :param instance: The instance of the object that needs to be represented.

        :return: The representation of the object.
        """
        representation = super(ProductItemSerializer, self).to_representation(instance)
        if representation.get('order') is None:
            # If 'order' key exist and its value is None, remove 'order' from dictionary
            representation.pop('order')

        return representation


class ProductImageSerializer(serializers.ModelSerializer):
    """
       Serializer for the ProductImage model.

       The serializer defines the fields that get serialized/deserialized.

       The 'id', 'image_url', and 's3_image_key' fields from the ProductImage model are included.

       The ProductImageSerializer is a child serializer of the ProductSerializer, used in serializing/deserializing
       the 'images' field of the parent serializer.
       """

    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 's3_image_key']


class ProductSerializer(serializers.ModelSerializer):
    """
       A serializer for the Product model. It includes serializer fields for associated models like images, items,
       manufacturer, and supplier.

       The serializer fields include:
       - images: A serializer for the associated Product image set
       - items: A serializer for the associated Product item set
       - manufacturer: A PrimaryKeyRelatedField for the related Manufacturer
       - supplier: A PrimaryKeyRelatedField for the related Supplier

       This serializer has additional methods for handling image uploads including presigned url generation and image deletion.
       """
    images = ProductImageSerializer(source='productimage_set', many=True, read_only=True)
    items = ProductItemSerializer(source='productitem_set', many=True, read_only=True)
    manufacturer = serializers.PrimaryKeyRelatedField(
        queryset=Manufacturer.objects.all(), required=False, allow_null=True
    )
    supplier = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'cat_num', 'name', 'category', 'unit', 'unit_quantity', 'stock',
            'storage', 'location', 'price', 'currency', 'url', 'manufacturer', 'supplier', 'images', 'items',
            'supplier_cat_item'
        ]

    # def get_supplier(self, obj):
    #     # Assuming 'supplier' is a ForeignKey relation to a Supplier model on the Product model
    #     # and that the Supplier model has 'id' and 'name' fields.
    #     supplier = obj.supplier
    #     if supplier:  # Check if the product has a supplier
    #         return {'id': supplier.id, 'name': supplier.name}
    #     return None

    def to_representation(self, instance):
        """
           This method formats the representation of a Product instance.

           Args:
               instance (Product): A Product instance.

           Returns:
               dict: The representation of the Product instance.

           In the representation of the Product instance, if 'images' does not exist, it pops and replaces with an
           empty list.
        """
        representation = super(ProductSerializer, self).to_representation(instance)
        representation['images'] = representation.pop('images', [])
        representation['items'] = representation.pop('items', [])
        return representation

    @transaction.atomic
    def create(self, validated_data):
        """
           Create a new Product instance using validated data.

           This method extends the default create method to include additional logic for handling images
           and generating presigned URLs for them.
           """
        # Call the superclass's create method to handle the creation of the Product instance
        product = super().create(validated_data)

        try:
            # Try to load images from the request data as a JSON format
            images = json.loads(self.context.get('view').request.data.get('images') or '[]')
        except json.JSONDecodeError:
            # If the images cannot be loaded as JSON, assign an empty list to images
            images = []

        # If images exist, handle the images and generate presigned urls fo them
        # and add them to the serializer context
        if images:
            presigned_urls = self.handle_images(images, product)

            self.context['presigned_urls'] = presigned_urls

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Method to update an instance.

        :param instance: The instance to be updated.
        :param validated_data: The validated data to update the instance.
        :return: The updated instance.
        """
        instance = super().update(instance, validated_data)

        # Get the image details that are to be deleted from the request data
        images_to_delete = self.context.get('view').request.data.get('images_to_delete')

        # If there are any images to be deleted, check and delete them
        if images_to_delete:
            self.check_and_delete_images(images_to_delete)

        try:
            # Try to load images from the request data as JSON
            images = json.loads(self.context.get('view').request.data.get('images') or '[]')
        except json.JSONDecodeError:
            # If JSON loading fails, assign an empty list to images
            images = []

        # If images exist, handle the images and generate presigned URLs
        if images:
            presigned_urls = self.handle_images(images, instance)
            # Store these presigned URLs in the serializer context for use in the response
            self.context['presigned_urls'] = presigned_urls

        # Return the updated product instance
        return instance

    @staticmethod
    def check_and_delete_images(image_ids):
        """
        Check and delete the images with the given image IDs.

        :param image_ids: A string representing a comma-separated list of image IDs.
        :type image_ids: str
        :return: None
        :rtype: None
        """
        # Create a list of image ids to delete by splitting the comma-separated string of image ids and converting
        # them to integers
        images_to_delete_ids = [int(id_) for id_ in image_ids.split(',')]

        # Iterate over each id in the list
        for image_id in images_to_delete_ids:
            # Get the image object using the id
            image = ProductImage.objects.get(id=image_id)

            # Delete the image from the S3 bucket
            # If the deletion from the S3 bucket is successful, delete the image object from the database
            if delete_s3_object(object_key=image.s3_image_key):
                image.delete()

    def handle_images(self, images, product_instance):
        """
        :param images: List of images to be processed
        :type images: list
        :param product_instance: The product instance for which the images are being handled
        :type product_instance: YourProductClass
        :return: List of dictionaries containing presigned URLs and image IDs
        :rtype: list
        :raises serializers.ValidationError: if failed to generate presigned POST data for S3 upload
        """
        # Initialize a list to hold presigned URLs and image IDs data
        presigned_urls_and_image_ids = []

        # Iterating over each image
        for image in images:
            # Generate a unique S3 key for the image
            s3_object_key = self.generate_s3_key(product_instance, image['type'])

            # Generate presigned POST data for S3 upload using the created S3 object key
            presigned_post_data = create_presigned_post(object_name=s3_object_key, file_type=image['type'])

            # If presigned POST data was successfully generated
            if presigned_post_data:
                # Create a new ProductImage instance with the created S3 object key and associated product instance
                product_image = ProductImage.objects.create(product=product_instance, s3_image_key=s3_object_key)

                # Create a FileUploadStatus instance with the status set to 'uploading' and associated product image
                upload_status = FileUploadStatus.objects.create(status='uploading', product_image=product_image)

                # Append the presigned post data, keys, and image ids to the list
                presigned_urls_and_image_ids.append({
                    'url': presigned_post_data['url'],  # The url to which the upload request must be sent
                    'fields': presigned_post_data['fields'],  # additional fields to include in the upload request
                    'key': s3_object_key,  # the key to be used for the uploaded object
                    'frontend_id': image['id'],  # the id from the frontend to match the response with the request
                    'image_id': product_image.id  # the id of the created Image instance in database
                })
            else:
                # If the generation of presigned POST data failed, raise a validation error
                raise serializers.ValidationError("Failed to generate presigned POST data for S3 upload.")

        # Return the list of presigned URLs and image ids
        return presigned_urls_and_image_ids

    @staticmethod
    def generate_s3_key(product, image_type):
        """
        Generate the S3 object key for a product image.

        :param product: The product object for which the S3 key is generated.
        :type product: Any
        :param image_type: The file type of the image.
        :type image_type: str
        :return: The S3 object key.
        :rtype: str
        """
        # Calculate how many images the product already has and increment by one, which will be used in naming the
        # image to be added
        product_image_count = (product.productimage_set.count()) + 1

        # Split the image type on '/' and get the last part, this is generally done to convert types like 'image/png'
        # to 'png'
        image_type = image_type.split('/')[-1]

        # Create a unique UUID to ensure that image name is unique
        unique_uuid = uuid.uuid4()

        # Form the S3 object key using product details and image details, it's the filename that will be used in S3
        # bucket
        s3_object_key = f"products/product_{product.id}_image_{product_image_count}_{unique_uuid}.{image_type}"

        # Return the created S3 object key
        return s3_object_key
