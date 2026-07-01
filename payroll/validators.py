import re
from django.core.exceptions import ValidationError


class PayMePasswordValidator:
    def validate(self, password, user=None):
        # 1. Check minimum length
        if len(password) < 6:
            raise ValidationError(
                "The password must be at least 6 characters long.",
                code='password_too_short',
            )

        # 2. Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                "The password must contain at least one uppercase letter (A-Z).",
                code='password_no_upper',
            )

        # 3. Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                "The password must contain at least one lowercase letter (a-z).",
                code='password_no_lower',
            )

        # 4. Check for at least one number
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                "The password must contain at least one numeric digit (0-9).",
                code='password_no_digit',
            )

    def get_help_text(self):
        return "Your password must be at least 6 characters long and contain at least 1 uppercase letter, 1 lowercase letter, and 1 number."