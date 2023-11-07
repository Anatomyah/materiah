from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class NumberAndLetterValidator:
    def validate(self, password, user=None):
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
    def validate(self, password, user=None):
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
    def validate(self, password, user=None):
        if not (any(c.isupper() for c in password)):
            raise ValidationError(
                _("Password must contain an uppercase letter."),
                code='password_uppercase_character',
            )

    def get_help_text(self):
        return _(
            "Password must contain an uppercase letter"
        )
