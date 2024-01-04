import json
import uuid
from django.db import transaction
from rest_framework import serializers

from ..models import Manufacturer, Supplier
from ..models.file import FileUploadStatus
from ..models.product import Product, ProductImage
from ..s3 import create_presigned_post, delete_s3_object


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
        Serializer for the Product model.

        The serializer defines the fields that get serialized/deserialized. The 'images' field is defined as a many-to-many
        relationship with the ProductImage model, where the source is from the 'productimage_set'. Moreover, 'manufacturer'
        and 'supplier' fields are defined using a SerializerMethodField.

        The `create()` method overrides the default implementation to handle creation of the product instance as well as
        its related images in the context of a transaction.

        The `update()` method overrides the default implementation to handle updating of the product instance as well as
        its related images in the context of a transaction.

        The `get_manufacturer()` and `get_supplier()` serializer methods define how to transform the outgoing native Python
        datatype into primitive datatypes that can then be rendered into JSON.

        The `to_representation()` method alters the default representation by popping out 'images' from the representation
        and replacing it with an empty list if it does not exist.

        The `check_and_delete_images()`, `handle_images()`, and `generate_s3_key()` methods are helper methods that deal
        with managing S3 image uploads related to the product.
        """
    images = ProductImageSerializer(source='productimage_set', many=True, read_only=True)

    manufacturer = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'cat_num', 'name', 'category', 'unit', 'unit_quantity', 'stock',
            'storage', 'price', 'url', 'manufacturer', 'supplier', 'images', 'supplier_cat_item'
        ]

    @staticmethod
    def get_manufacturer(obj):
        """
            This method retrieves a dictionary containing id and name of the Manufacturer for a Product instance.

            Args:
                obj (Product): A Product instance.

            Returns:
                dict: A dictionary containing 'id' and 'name' of the associated Manufacturer.
            """
        return {
            'id': obj.manufacturer.id,
            'name': obj.manufacturer.name,
        }

    @staticmethod
    def get_supplier(obj):
        """
            This method retrieves a dictionary containing id and name of the Supplier for a Product instance.

            Args:
                obj (Product): A Product instance.

            Returns:
                dict: A dictionary containing 'id' and 'name' of the associated Supplier.
            """
        return {
            'id': obj.supplier.id,
            'name': obj.supplier.name,
        }

    def to_representation(self, instance):
        """
           This method formats the representation of a Product instance.

           Args:
               instance (Product): A Product instance.

           Returns:
               dict: The representation of the Product instance.

           In the representation of the Product instance, if 'images' does not exist, it pops and replaces with an empty list.
           """
        representation = super(ProductSerializer, self).to_representation(instance)
        representation['images'] = representation.pop('images', [])
        return representation

    @transaction.atomic
    def create(self, validated_data):
        """
        :param validated_data: A dictionary containing the validated data for creating a new product.
        :return: The created product object.

        This method is used to create a new product object. It takes in the validated data as a parameter and returns the created product object.

        The method first extracts the manufacturer_id and supplier_id from the request data in the serializer context. It then converts the 'supplier_cat_item' field in the request data to a
        * boolean value and adds it to the validated_data.

        Next, it tries to get the Manufacturer instance using the manufacturer_id. If the Manufacturer instance does not exist, it raises a validation error.

        Similarly, it tries to get the Supplier instance using the supplier_id. If the Supplier instance does not exist, it raises a validation error.

        After that, it creates the product object using the Manufacturer and Supplier instances and the validated data.

        If images exist in the request data, the method handles the images and generates presigned URLs for them. The presigned URLs are then added to the serializer context.

        Finally, the method returns the created product object.
        """
        # Extract manufacturer_id and supplier_id from the request data in the serializer context
        manufacturer_id = self.context.get('view').request.data.get('manufacturer')
        supplier_id = self.context.get('view').request.data.get('supplier')
        # Convert the 'supplier_cat_item' field in the request data to boolean and add it to the validated_data
        validated_data['supplier_cat_item'] = self.context.get('view').request.data.get('supplier_cat_item') == 'true'

        try:
            # Try to get the Manufacturer instance using the manufacturer_id
            manufacturer = Manufacturer.objects.get(id=manufacturer_id)
        except Manufacturer.DoesNotExist:
            # If the Manufacturer instance does not exist, raise a validation error
            raise serializers.ValidationError("Manufacturer does not exist")
        try:
            # Try to get the Supplier instance using the supplier_id
            supplier = Supplier.objects.get(id=supplier_id)
        except Supplier.DoesNotExist:
            # If the Supplier instance does not exist, raise a validation error
            raise serializers.ValidationError("Supplier does not exist")

        # Create the product object using the Manufacturer and Supplier instances and validated data
        product = Product.objects.create(manufacturer=manufacturer,
                                         supplier=supplier, **validated_data)

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
        # Create a list of image ids to delete by splitting the comma-separated string of image ids and converting them to integers
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
