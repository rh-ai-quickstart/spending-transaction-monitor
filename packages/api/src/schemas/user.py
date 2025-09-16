from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone_number: str | None = None
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None
    credit_cards_count: int
    transactions_count: int

    # Location fields
    location_consent_given: bool | None = None
    last_app_location_latitude: float | None = None
    last_app_location_longitude: float | None = None
    last_app_location_timestamp: str | None = None
    last_app_location_accuracy: float | None = None
    last_transaction_latitude: float | None = None
    last_transaction_longitude: float | None = None
    last_transaction_timestamp: str | None = None
    last_transaction_city: str | None = None
    last_transaction_state: str | None = None
    last_transaction_country: str | None = None
