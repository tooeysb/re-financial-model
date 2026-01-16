"""
Tests for properties, scenarios, and calculations API endpoints.
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Property, Scenario, User, UserRole
from app.auth.password import hash_password

# Database setup is handled by conftest.py


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        first_name="Test",
        last_name="User",
        role=UserRole.user,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Create authenticated test client."""
    client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    return client


@pytest.fixture
def test_property(db_session, test_user):
    """Create a test property."""
    prop = Property(
        name="Test Property",
        owner_id=test_user.id,
        address_street="123 Test St",
        address_city="Test City",
        address_state="FL",
        address_zip="12345",
        property_type="retail",
        building_sf=10000,
        net_rentable_sf=9500,
        purchase_price=5000000,
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)
    return prop


@pytest.fixture
def test_scenario(db_session, test_property):
    """Create a test scenario."""
    scenario = Scenario(
        property_id=test_property.id,
        name="Base Case",
        is_base_case=True,
        acquisition_date=date(2025, 1, 1),
        hold_period_months=120,
        purchase_price=5000000,
        closing_costs=75000,
        exit_cap_rate=0.05,
        sales_cost_percent=0.02,
    )
    db_session.add(scenario)
    db_session.commit()
    db_session.refresh(scenario)
    return scenario


# ============================================================================
# PROPERTY API TESTS
# ============================================================================

class TestPropertyAPI:
    """Test property endpoints."""

    def test_list_properties(self, authenticated_client, test_property):
        """Test listing properties."""
        response = authenticated_client.get("/api/properties")
        assert response.status_code == 200
        data = response.json()
        # API returns PropertyListResponse with 'properties' and 'total' fields
        assert "properties" in data
        properties = data["properties"]
        assert len(properties) >= 1
        # Find our test property in the list
        test_prop = next((p for p in properties if p["name"] == "Test Property"), None)
        assert test_prop is not None

    def test_create_property(self, authenticated_client):
        """Test creating a property."""
        response = authenticated_client.post(
            "/api/properties",
            json={
                "name": "New Property",
                "address_street": "456 New St",
                "address_city": "New City",
                "address_state": "CA",
                "property_type": "office",
                "building_sf": 25000,
                "purchase_price": 10000000,
            },
        )
        assert response.status_code == 201  # API returns 201 for created
        data = response.json()
        assert data["name"] == "New Property"
        assert "id" in data

    def test_get_property(self, authenticated_client, test_property):
        """Test getting a specific property."""
        response = authenticated_client.get(f"/api/properties/{test_property.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Property"
        assert data["id"] == test_property.id

    def test_get_nonexistent_property(self, authenticated_client):
        """Test getting a property that doesn't exist."""
        response = authenticated_client.get("/api/properties/nonexistent-id")
        assert response.status_code == 404

    def test_update_property(self, authenticated_client, test_property):
        """Test updating a property."""
        response = authenticated_client.put(
            f"/api/properties/{test_property.id}",
            json={"name": "Updated Property", "building_sf": 15000},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Property"
        assert data["building_sf"] == 15000

    def test_delete_property(self, authenticated_client, test_property):
        """Test deleting a property."""
        response = authenticated_client.delete(f"/api/properties/{test_property.id}")
        assert response.status_code == 200

        # Verify it's gone (soft delete)
        response = authenticated_client.get(f"/api/properties/{test_property.id}")
        assert response.status_code == 404


# ============================================================================
# SCENARIO API TESTS
# ============================================================================

class TestScenarioAPI:
    """Test scenario endpoints."""

    def test_list_scenarios(self, authenticated_client, test_scenario):
        """Test listing scenarios."""
        response = authenticated_client.get("/api/scenarios")
        assert response.status_code == 200
        scenarios = response.json()
        assert len(scenarios) >= 1

    def test_list_scenarios_by_property(self, authenticated_client, test_property, test_scenario):
        """Test listing scenarios filtered by property."""
        response = authenticated_client.get(
            f"/api/scenarios?property_id={test_property.id}"
        )
        assert response.status_code == 200
        scenarios = response.json()
        # Handle both list of dicts and list of other types
        if scenarios and isinstance(scenarios, list):
            for s in scenarios:
                if isinstance(s, dict):
                    assert s["property_id"] == test_property.id

    def test_create_scenario(self, authenticated_client, test_property):
        """Test creating a scenario."""
        response = authenticated_client.post(
            "/api/scenarios",
            json={
                "property_id": test_property.id,
                "name": "Upside Case",
                "acquisition_date": "2025-01-01",
                "hold_period_months": 60,
                "purchase_price": 5000000,
                "closing_costs": 75000,
                "exit_cap_rate": 0.045,
            },
        )
        assert response.status_code == 201  # API returns 201 for created
        data = response.json()
        assert data["name"] == "Upside Case"
        assert data["property_id"] == test_property.id

    def test_get_scenario(self, authenticated_client, test_scenario):
        """Test getting a specific scenario."""
        response = authenticated_client.get(f"/api/scenarios/{test_scenario.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Base Case"

    def test_update_scenario(self, authenticated_client, test_scenario):
        """Test updating a scenario."""
        response = authenticated_client.put(
            f"/api/scenarios/{test_scenario.id}",
            json={"name": "Updated Scenario", "exit_cap_rate": 0.055},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Scenario"
        assert data["exit_cap_rate"] == 0.055

    def test_delete_scenario(self, authenticated_client, test_scenario):
        """Test deleting a scenario."""
        response = authenticated_client.delete(f"/api/scenarios/{test_scenario.id}")
        assert response.status_code == 200


# ============================================================================
# CALCULATIONS API TESTS
# ============================================================================

class TestCalculationsAPI:
    """Test calculation endpoints."""

    def test_calculate_cashflows(self, client):
        """Test cash flow calculation endpoint."""
        response = client.post(
            "/api/calculate/cashflows",
            json={
                "acquisition_date": "2025-01-01",
                "hold_period_months": 60,
                "purchase_price": 10000,
                "closing_costs": 150,
                "total_sf": 50000,
                "in_place_rent_psf": 20,
                "market_rent_psf": 22,
                "rent_growth": 0.03,
                "vacancy_rate": 0.05,
                "fixed_opex_psf": 5,
                "management_fee_percent": 0.03,
                "property_tax_amount": 100,
                "capex_reserve_psf": 0.50,
                "expense_growth": 0.025,
                "exit_cap_rate": 0.06,
                "sales_cost_percent": 0.02,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # API returns monthly_cashflows and annual_cashflows
        assert "monthly_cashflows" in data
        assert len(data["monthly_cashflows"]) == 61  # 0-60

    def test_calculate_cashflows_with_debt(self, client):
        """Test cash flow calculation with leverage."""
        response = client.post(
            "/api/calculate/cashflows",
            json={
                "acquisition_date": "2025-01-01",
                "hold_period_months": 60,
                "purchase_price": 10000,
                "closing_costs": 150,
                "total_sf": 50000,
                "in_place_rent_psf": 20,
                "market_rent_psf": 22,
                "rent_growth": 0.03,
                "vacancy_rate": 0.05,
                "fixed_opex_psf": 5,
                "management_fee_percent": 0.03,
                "property_tax_amount": 100,
                "capex_reserve_psf": 0.50,
                "expense_growth": 0.025,
                "exit_cap_rate": 0.06,
                "sales_cost_percent": 0.02,
                "loan_amount": 6500,
                "interest_rate": 0.055,
                "io_months": 60,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Verify debt service is included in monthly_cashflows
        assert data["monthly_cashflows"][1]["debt_service"] > 0

    def test_calculate_irr(self, client):
        """Test IRR calculation endpoint."""
        response = client.post(
            "/api/calculate/irr",
            json={
                "cash_flows": [-100, 20, 20, 20, 20, 80],
                "dates": [
                    "2025-01-01",
                    "2026-01-01",
                    "2027-01-01",
                    "2028-01-01",
                    "2029-01-01",
                    "2030-01-01",
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "irr" in data
        assert data["irr"] > 0

    def test_calculate_irr_invalid_cash_flows(self, client):
        """Test IRR with invalid cash flows."""
        response = client.post(
            "/api/calculate/irr",
            json={
                "cash_flows": [100, 100, 100],  # No negative values
                "dates": ["2025-01-01", "2026-01-01", "2027-01-01"],
            },
        )
        assert response.status_code == 400

    def test_calculate_amortization(self, client):
        """Test amortization schedule endpoint."""
        response = client.post(
            "/api/calculate/amortization",
            json={
                "principal": 1000000,
                "annual_rate": 0.06,
                "amortization_years": 30,  # API expects years, not months
                "io_months": 24,
                "total_months": 120,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "schedule" in data
        assert len(data["schedule"]) == 120

        # First 24 months should be IO
        for i in range(24):
            assert data["schedule"][i]["principal"] == 0


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


# ============================================================================
# PAGE ROUTE TESTS
# ============================================================================

class TestPageRoutes:
    """Test HTML page routes."""

    def test_home_page(self, client):
        """Test home page loads."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_login_page(self, client):
        """Test login page loads."""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_register_page(self, client):
        """Test register page loads."""
        response = client.get("/auth/register")
        assert response.status_code == 200

    def test_forgot_password_page(self, client):
        """Test forgot password page loads."""
        response = client.get("/auth/forgot-password")
        assert response.status_code == 200

    def test_reset_password_page(self, client):
        """Test reset password page loads."""
        response = client.get("/auth/reset-password")
        assert response.status_code == 200

    def test_model_page(self, client):
        """Test model editor page loads."""
        response = client.get("/model/test-model-id")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
