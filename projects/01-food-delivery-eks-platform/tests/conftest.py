import os
import sys
import pytest
import pytest_asyncio

# Allow importing service modules directly for unit tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/user-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/restaurant-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/order-service"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/delivery-service"))

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
RESTAURANT_SERVICE_URL = os.getenv("RESTAURANT_SERVICE_URL", "http://localhost:8002")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8003")
DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://localhost:8004")


@pytest.fixture(scope="session")
def user_service_url():
    return USER_SERVICE_URL


@pytest.fixture(scope="session")
def restaurant_service_url():
    return RESTAURANT_SERVICE_URL


@pytest.fixture(scope="session")
def order_service_url():
    return ORDER_SERVICE_URL


@pytest.fixture(scope="session")
def delivery_service_url():
    return DELIVERY_SERVICE_URL


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
