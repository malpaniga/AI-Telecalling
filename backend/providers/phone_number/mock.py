import uuid
from backend.providers.base import PhoneNumberProvider
class MockPhoneNumberProvider(PhoneNumberProvider):
    provider_name="mock"
    async def provision_number(self, country_code, **kwargs): return {"provider_resource_id": f"mock-number-{uuid.uuid4()}", "country_code": country_code}
