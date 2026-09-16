# FIX: Priority 3 / Bug 22 - one checksum/normalization rule for identity write requests.
from pydantic import BaseModel, field_validator


_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def validate_iranian_national_code(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("کد ملی باید یک رشتهٔ ۱۰ رقمی معتبر باشد")
    code = value.strip().translate(_DIGITS)
    if len(code) != 10 or any(c not in "0123456789" for c in code) or len(set(code)) == 1:
        raise ValueError("کد ملی وارد شده معتبر نیست")
    remainder = sum(int(code[i]) * (10 - i) for i in range(9)) % 11
    expected = remainder if remainder < 2 else 11 - remainder
    if int(code[-1]) != expected:
        raise ValueError("رقم کنترل کد ملی معتبر نیست")
    return code


def is_valid_iranian_national_code(value: str) -> bool:
    try:
        validate_iranian_national_code(value)
        return True
    except ValueError:
        return False


class NationalCodeRequest(BaseModel):
    # FIX: Bug 22 - omitted update fields remain optional; an explicitly invalid/null identity is rejected.
    @field_validator("national_code", mode="before", check_fields=False)
    @classmethod
    def validate_national_code(cls, value):
        return validate_iranian_national_code(value)

