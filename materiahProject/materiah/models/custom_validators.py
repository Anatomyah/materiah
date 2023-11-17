from django.core.exceptions import ValidationError

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


def validate_phone_suffix(value):
    if not value.isdigit():
        raise ValidationError("The phone suffix should only contain digits.")
    if len(value) != 7:
        raise ValidationError("The phone suffix should be exactly 7 digits long.")


def luhn_checksum(id_num):
    digits = [int(digit) for digit in id_num]
    checksum = sum(
        (digit * ((i % 2) + 1) - 9) if (digit * ((i % 2) + 1) > 9) else (digit * ((i % 2) + 1))
        for i, digit in enumerate(digits)
    )
    return checksum % 10 == 0


def validate_digits_length_and_luhn(id_num):
    id_num = ('00000000' + id_num)[-9:] if len(id_num) < 9 else id_num

    if not id_num.isdigit():
        raise ValidationError(f"The value should only contain digits.")

    if not luhn_checksum(id_num):
        raise ValidationError(f"{id_num} is not a valid ID number.")
