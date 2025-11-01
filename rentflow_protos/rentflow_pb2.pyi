from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Tenant(_message.Message):
    __slots__ = ("id", "first_name", "last_name", "email", "phone")
    ID_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    PHONE_FIELD_NUMBER: _ClassVar[int]
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    def __init__(self, id: _Optional[int] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., email: _Optional[str] = ..., phone: _Optional[str] = ...) -> None: ...

class Property(_message.Message):
    __slots__ = ("id", "address", "city", "country")
    ID_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    id: int
    address: str
    city: str
    country: str
    def __init__(self, id: _Optional[int] = ..., address: _Optional[str] = ..., city: _Optional[str] = ..., country: _Optional[str] = ...) -> None: ...

class Lease(_message.Message):
    __slots__ = ("id", "property", "tenant", "start_date", "end_date", "monthly_rent", "payment_day")
    ID_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_RENT_FIELD_NUMBER: _ClassVar[int]
    PAYMENT_DAY_FIELD_NUMBER: _ClassVar[int]
    id: int
    property: Property
    tenant: Tenant
    start_date: str
    end_date: str
    monthly_rent: float
    payment_day: int
    def __init__(self, id: _Optional[int] = ..., property: _Optional[_Union[Property, _Mapping]] = ..., tenant: _Optional[_Union[Tenant, _Mapping]] = ..., start_date: _Optional[str] = ..., end_date: _Optional[str] = ..., monthly_rent: _Optional[float] = ..., payment_day: _Optional[int] = ...) -> None: ...

class CreateLeaseRequest(_message.Message):
    __slots__ = ("property", "tenant", "start_date", "end_date", "monthly_rent", "django_lease_id", "payment_day")
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_RENT_FIELD_NUMBER: _ClassVar[int]
    DJANGO_LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    PAYMENT_DAY_FIELD_NUMBER: _ClassVar[int]
    property: Property
    tenant: Tenant
    start_date: str
    end_date: str
    monthly_rent: float
    django_lease_id: int
    payment_day: int
    def __init__(self, property: _Optional[_Union[Property, _Mapping]] = ..., tenant: _Optional[_Union[Tenant, _Mapping]] = ..., start_date: _Optional[str] = ..., end_date: _Optional[str] = ..., monthly_rent: _Optional[float] = ..., django_lease_id: _Optional[int] = ..., payment_day: _Optional[int] = ...) -> None: ...

class CreateLeaseResponse(_message.Message):
    __slots__ = ("success", "lease", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    LEASE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    lease: Lease
    message: str
    def __init__(self, success: bool = ..., lease: _Optional[_Union[Lease, _Mapping]] = ..., message: _Optional[str] = ...) -> None: ...

class GetLeaseRequest(_message.Message):
    __slots__ = ("lease_id",)
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    lease_id: int
    def __init__(self, lease_id: _Optional[int] = ...) -> None: ...

class GetLeaseResponse(_message.Message):
    __slots__ = ("found", "lease")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    LEASE_FIELD_NUMBER: _ClassVar[int]
    found: bool
    lease: Lease
    def __init__(self, found: bool = ..., lease: _Optional[_Union[Lease, _Mapping]] = ...) -> None: ...

class UpdateLeaseRequest(_message.Message):
    __slots__ = ("lease_id", "monthly_rent", "end_date")
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    MONTHLY_RENT_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    lease_id: int
    monthly_rent: float
    end_date: str
    def __init__(self, lease_id: _Optional[int] = ..., monthly_rent: _Optional[float] = ..., end_date: _Optional[str] = ...) -> None: ...

class UpdateLeaseResponse(_message.Message):
    __slots__ = ("success", "lease")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    LEASE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    lease: Lease
    def __init__(self, success: bool = ..., lease: _Optional[_Union[Lease, _Mapping]] = ...) -> None: ...

class ListLeasesRequest(_message.Message):
    __slots__ = ("page", "page_size")
    PAGE_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    page: int
    page_size: int
    def __init__(self, page: _Optional[int] = ..., page_size: _Optional[int] = ...) -> None: ...

class ListLeasesResponse(_message.Message):
    __slots__ = ("leases", "total_count")
    LEASES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    leases: _containers.RepeatedCompositeFieldContainer[Lease]
    total_count: int
    def __init__(self, leases: _Optional[_Iterable[_Union[Lease, _Mapping]]] = ..., total_count: _Optional[int] = ...) -> None: ...
