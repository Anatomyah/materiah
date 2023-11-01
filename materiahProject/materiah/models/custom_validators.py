from django.core.exceptions import ValidationError


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
