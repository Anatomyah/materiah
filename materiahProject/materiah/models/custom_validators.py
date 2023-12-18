from django.core.exceptions import ValidationError


def validate_phone_suffix(value):
    """
           Validates the suffix part of a phone number.

           This function checks if the given value for a phone number's suffix is valid.
           A valid phone suffix must meet two criteria:
           1. It should only contain digits.
           2. It should be exactly 7 digits long.

           Parameters:
           - value (str): The phone number suffix to validate.

           Raises:
           - ValidationError: If the suffix does not meet the criteria.
               - If the suffix contains non-digit characters, it raises a ValidationError with the message "The phone suffix should only contain digits."
               - If the suffix is not exactly 7 digits long, it raises a ValidationError with the message "The phone suffix should be exactly 7 digits long."

           Example:
           >>> validate_phone_suffix("1234567")
           None
           >>> validate_phone_suffix("123456")
           ValidationError: "The phone suffix should be exactly 7 digits long."
           >>> validate_phone_suffix("abc1234")
           ValidationError: "The phone suffix should only contain digits."
           """
    if not value.isdigit():
        raise ValidationError("The phone suffix should only contain digits.")
    if len(value) != 7:
        raise ValidationError("The phone suffix should be exactly 7 digits long.")
