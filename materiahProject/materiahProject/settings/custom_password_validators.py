from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NumberAndLetterValidator:
    """
    Validates that a password contains both letters and numbers.

    Attributes:
        None

    Methods:
        validate: Validates the password.
        get_help_text: Returns the help text for the validator.

    """

    def validate(self, password, user=None):
        """
        :param password: The password to be validated. It should be a string.
        :param user: Optional parameter that represents the user for whom the password is being validated. It should be a string. Default value is None.
        :return: None

        This method validates the password by checking if it contains both letters and numbers. If the password does not meet this requirement, a ValidationError is raised with an error message
        * and error code.
        """
        if not (any(c.isdigit() for c in password) and any(c.isalpha() for c in password)):
            raise ValidationError(
                _("Password must contain both letters and numbers"),
                code='password_letter_and_digit',
            )

    def get_help_text(self):
        return _(
            "Password must contain both letters and numbers"
        )


class SpecialCharacterValidator:
    """
    A class for validating the presence of special characters in a password.

    Attributes:
        None

    Methods:
        validate(password, user=None):
            Validates if the given password contains at least one special character.
            Raises a ValidationError if the password is invalid.

        get_help_text():
            Retrieves the help text associated with the validator.

    """

    def validate(self, password, user=None):
        """
        :param password: the password to be validated
        :param user: optional user information (default value is None)
        :return: None

        This method validates the given password by checking if it contains at least one special character. If no special character is found, it raises a ValidationError with a corresponding
        * error message.
        """
        special_characters = r"!\"#$%&'()*+,-./:;<>=?@[]^_`{}|~"
        if not (any(c in special_characters for c in password)):
            raise ValidationError(
                _(r"Password must contain a special character: !\"#$%&'()*+,-./:;<>=?@[]^_`{}|~"),
                code='password_special_character',
            )

    def get_help_text(self):
        return _(
            r"Password must contain a special character: !\"#$%&'()*+,-./:;<>=?@[]^_`{}|~"
        )


class UppercaseLetterValidator:
    """
    Represents a validator for checking if a password contains at least one uppercase letter.

    Methods:
        - validate(password: str, user=None) -> None
        - get_help_text() -> str
    """

    def validate(self, password, user=None):
        """
        Validate the password.

        :param password: The password to be validated.
        :param user: An optional user object. Default is None.
        :raises: ValidationError, if the password does not meet the validation requirements.
        """
        if not (any(c.isupper() for c in password)):
            raise ValidationError(
                _("Password must contain an uppercase letter."),
                code='password_uppercase_character',
            )

    def get_help_text(self):
        return _(
            "Password must contain an uppercase letter"
        )
