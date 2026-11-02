from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    delivery_address: str = Field(min_length=1, max_length=255)


class CustomerUpdate(CustomerCreate):
    pass


class CustomerRead(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
