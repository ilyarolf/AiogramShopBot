# Test Suite

Comprehensive testing infrastructure for the Aiogram Shop Bot.

## Directory Structure

Tests are organized by feature domain:

```
tests/
├── payment/                    # Payment & Invoice Tests
│   ├── manual/                # Manual testing tools
│   │   ├── simulate_payment_webhook.py
│   │   ├── run_payment_scenarios.sh
│   │   └── requirements.txt
│   └── unit/                  # Automated unit tests
│       ├── test_payment_validation.py
│       └── test_e2e_payment_flow.py
│
├── shipment/                  # Shipping & Address Tests
│   └── manual/
│       ├── payment-shipment-test-guide.md
│       ├── test_shop_data.json
│       └── requirements.txt
│
├── cart/                      # Cart & Stock Tests
│   └── manual/
│       └── simulate_stock_race_condition.py
│
├── data-retention/            # Data Cleanup Tests
│   └── unit/
│       └── test_data_retention_cleanup.py
│
├── security/                  # Security & Encryption Tests
│   └── unit/
│       └── (future tests)
│
├── conftest.py               # Pytest fixtures (shared)
└── README.md                 # This file
```

## Test Categories

### Unit Tests (`unit/`)
Automated tests using pytest. Run with:
```bash
pytest tests/
```

### Manual Tests (`manual/`)
Interactive testing tools for scenarios requiring bot runtime or external services:
- **Payment Webhook Simulator**: Simulates KryptoExpress payment callbacks
- **Stock Race Condition Simulator**: Tests concurrent order creation
- **Payment Scenarios Runner**: Automated manual test suite

## Running Tests

### All Automated Tests
```bash
# From project root
pytest tests/

# Specific feature
pytest tests/payment/unit/
pytest tests/data-retention/unit/
```

### Manual Payment Testing
```bash
# 1. Start bot in separate terminal
python run.py

# 2. Simulate payment webhook
cd tests/payment/manual
python simulate_payment_webhook.py 2025-ABC123

# 3. Or run full scenario suite
./run_payment_scenarios.sh
```

### Manual Stock Race Condition Testing
```bash
cd tests/cart/manual
python simulate_stock_race_condition.py
```

## Test Data

- `shipment/manual/test_shop_data.json`: Sample product catalog for testing
- `payment/manual/`: Payment webhook simulation data
- Test fixtures defined in `conftest.py`

## Requirements

Install test dependencies:
```bash
pip install -r tests/payment/manual/requirements.txt
pip install -r tests/shipment/manual/requirements.txt
```

Or install all:
```bash
pip install pytest pytest-asyncio requests
```

## Documentation

- **Payment/Shipment Testing Guide**: `shipment/manual/payment-shipment-test-guide.md`
- **Test Checklist**: `../TEST_CHECKLIST.md` (project root)
- **Manual Test Scenarios**: `../tests/manual/TESTING_GUIDE.md`

## Adding New Tests

### Unit Test (Automated)
1. Create file in appropriate `unit/` directory
2. Name file `test_*.py`
3. Use pytest fixtures from `conftest.py`
4. Run with `pytest tests/`

### Manual Test Tool
1. Create file in appropriate `manual/` directory
2. Add usage documentation to file docstring
3. Update this README with usage instructions

## Best Practices

- **Feature Isolation**: Keep tests in their respective feature directories
- **Naming Convention**:
  - Unit tests: `test_*.py`
  - Manual tools: `simulate_*.py`, `run_*.sh`
- **Dependencies**: Each manual test directory has its own `requirements.txt`
- **Shared Fixtures**: Use `conftest.py` for shared pytest fixtures
- **Documentation**: Update test guides when adding new manual tools

## CI/CD Integration

Unit tests run automatically on:
- Pull requests
- Commits to `develop` and `master`
- Manual test tools require bot runtime and are not automated

## Status

- ✅ Payment validation tests
- ✅ Payment webhook simulation
- ✅ Data retention cleanup tests
- ✅ Stock race condition simulation
- ⏳ Shipment address validation (TODO)
- ⏳ Cart cleanup tests (TODO)
- ⏳ Security/encryption tests (TODO)

---

**Last Updated**: 2025-10-26
