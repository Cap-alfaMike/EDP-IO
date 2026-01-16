# ============================================================================
# EDP-IO - Mock Data Generator for Retail Domain
# ============================================================================
"""
Realistic mock data generator for retail domain testing and demonstration.

PURPOSE:
-------
- Enable full platform testing without database connections
- Generate realistic Brazilian retail data
- Support deterministic generation for reproducible tests

ARCHITECTURAL NOTE:
This module is ONLY used when ENABLE_REAL_DATABASE_CONNECTIONS is False.
In production, this is bypassed entirely in favor of real JDBC connections.

DATA GENERATED:
- Customers (Brazilian PII patterns)
- Products (Retail categories)
- Orders (E-commerce transactions)
- Order Items
- Stores (Brazilian geography)
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from faker import Faker

# Brazilian locale for realistic data
fake = Faker("pt_BR")
Faker.seed(42)  # Reproducibility


@dataclass
class GeneratorConfig:
    """Configuration for mock data generation."""

    num_customers: int = 1000
    num_products: int = 500
    num_stores: int = 50
    num_orders: int = 5000
    avg_items_per_order: int = 3
    seed: int = 42


class RetailMockDataGenerator:
    """
    Mock data generator for retail domain.

    DESIGN DECISIONS:
    -----------------
    1. Deterministic: Same seed produces same data (testability)
    2. Realistic: Uses Brazilian patterns (addresses, CPF format, etc.)
    3. Referential: Maintains foreign key relationships
    4. Timestamped: Generates realistic date ranges

    USAGE:
        generator = RetailMockDataGenerator(seed=42)
        customers = generator.generate_customers(1000)
        products = generator.generate_products(500)
        orders = generator.generate_orders(5000, customers, products)

    PRODUCTION NOTE:
    In production, this class is never instantiated. Data flows directly
    from source systems via JDBC. This exists purely for:
    - Local development
    - CI/CD pipeline testing
    - Demonstration and training
    """

    # Retail product categories and their structure
    CATEGORIES = {
        "Electronics": {
            "subcategories": ["Smartphones", "Laptops", "Tablets", "Accessories", "TVs"],
            "price_range": (99.99, 9999.99),
            "margin": 0.25,
        },
        "Fashion": {
            "subcategories": [
                "Men's Clothing",
                "Women's Clothing",
                "Shoes",
                "Accessories",
                "Sportswear",
            ],
            "price_range": (29.99, 799.99),
            "margin": 0.45,
        },
        "Home & Garden": {
            "subcategories": ["Furniture", "Decor", "Kitchen", "Bedding", "Garden"],
            "price_range": (19.99, 2999.99),
            "margin": 0.35,
        },
        "Beauty": {
            "subcategories": ["Skincare", "Makeup", "Haircare", "Fragrances", "Personal Care"],
            "price_range": (14.99, 499.99),
            "margin": 0.55,
        },
        "Grocery": {
            "subcategories": ["Fresh", "Pantry", "Beverages", "Frozen", "Organic"],
            "price_range": (2.99, 199.99),
            "margin": 0.20,
        },
    }

    BRANDS = [
        "TechMax",
        "StyleCo",
        "HomeEssentials",
        "BeautyPro",
        "FreshMarket",
        "ElectroPrime",
        "FashionForward",
        "ComfortZone",
        "GlowUp",
        "NaturalChoice",
        "SmartLife",
        "UrbanStyle",
        "CasaFeliz",
        "BelezaPura",
        "SaborNatural",
    ]

    CUSTOMER_SEGMENTS = ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
    SEGMENT_WEIGHTS = [0.50, 0.30, 0.15, 0.05]  # Distribution

    ORDER_STATUSES = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
    STATUS_WEIGHTS = [0.05, 0.10, 0.15, 0.60, 0.05, 0.05]  # Most are delivered

    PAYMENT_METHODS = ["CREDIT_CARD", "DEBIT_CARD", "PIX", "BOLETO", "WALLET"]
    PAYMENT_WEIGHTS = [0.35, 0.15, 0.30, 0.10, 0.10]  # PIX popular in Brazil

    STORE_TYPES = ["FLAGSHIP", "STANDARD", "OUTLET", "POPUP", "WAREHOUSE"]

    BRAZILIAN_REGIONS = {
        "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
        "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
        "Centro-Oeste": ["DF", "GO", "MT", "MS"],
        "Sudeste": ["ES", "MG", "RJ", "SP"],
        "Sul": ["PR", "RS", "SC"],
    }

    def __init__(self, seed: int = 42):
        """
        Initialize the generator with a seed for reproducibility.

        Args:
            seed: Random seed for deterministic generation
        """
        self.seed = seed
        random.seed(seed)
        Faker.seed(seed)
        self._product_cache: Dict[str, Dict] = {}
        self._customer_cache: Dict[str, Dict] = {}

    def generate_customers(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate realistic Brazilian customer records.

        IMPLEMENTATION NOTE:
        - Uses Brazilian Faker locale for realistic names/addresses
        - Applies realistic segment distribution
        - Generates valid-looking (but fake) CPF patterns
        """
        customers = []

        for i in range(count):
            customer_id = f"CUST-{str(i+1).zfill(8)}"
            registration_date = fake.date_between(start_date="-5y", end_date="-30d")

            # Realistic timestamp: registration + random time for creation
            created_at = datetime.combine(registration_date, fake.time_object())
            updated_at = fake.date_time_between(start_date=created_at, end_date="now")

            customer = {
                "customer_id": customer_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.email(),
                "phone": fake.phone_number(),
                "address_line1": fake.street_address(),
                "city": fake.city(),
                "state": fake.estado_sigla(),
                "postal_code": fake.postcode(),
                "country_code": "BR",
                "customer_segment": random.choices(
                    self.CUSTOMER_SEGMENTS, weights=self.SEGMENT_WEIGHTS
                )[0],
                "registration_date": registration_date,
                "is_active": random.random() > 0.05,  # 95% active
                "created_at": created_at,
                "updated_at": updated_at,
            }

            customers.append(customer)
            self._customer_cache[customer_id] = customer

        return customers

    def generate_products(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate realistic retail product catalog.

        IMPLEMENTATION NOTE:
        - Distributes products across categories
        - Applies realistic pricing with category-specific margins
        - Generates realistic stock levels
        """
        products = []

        for i in range(count):
            product_id = f"SKU-{str(i+1).zfill(6)}"

            # Select category and subcategory
            category_name = random.choice(list(self.CATEGORIES.keys()))
            category_info = self.CATEGORIES[category_name]
            subcategory = random.choice(category_info["subcategories"])

            # Generate realistic pricing
            price_min, price_max = category_info["price_range"]
            unit_price = round(random.uniform(price_min, price_max), 2)
            margin = category_info["margin"]
            unit_cost = round(unit_price * (1 - margin), 2)

            created_at = fake.date_time_between(start_date="-3y", end_date="-6m")
            updated_at = fake.date_time_between(start_date=created_at, end_date="now")

            product = {
                "product_id": product_id,
                "product_name": f"{random.choice(self.BRANDS)} {subcategory} {fake.word().title()}",
                "category_id": f"CAT-{list(self.CATEGORIES.keys()).index(category_name) + 1:03d}",
                "category_name": category_name,
                "subcategory_name": subcategory,
                "brand": random.choice(self.BRANDS),
                "unit_price": Decimal(str(unit_price)),
                "unit_cost": Decimal(str(unit_cost)),
                "stock_quantity": random.randint(0, 1000),
                "is_active": random.random() > 0.1,  # 90% active
                "created_at": created_at,
                "updated_at": updated_at,
            }

            products.append(product)
            self._product_cache[product_id] = product

        return products

    def generate_stores(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate Brazilian retail store locations.

        IMPLEMENTATION NOTE:
        - Distributes stores across Brazilian regions
        - Biases toward Southeast (most populous region)
        """
        stores = []

        # Weight regions by population (approximate)
        region_weights = {
            "Norte": 0.08,
            "Nordeste": 0.27,
            "Centro-Oeste": 0.08,
            "Sudeste": 0.42,
            "Sul": 0.15,
        }

        for i in range(count):
            store_id = f"STORE-{str(i+1).zfill(4)}"

            # Select region and state
            region = random.choices(
                list(region_weights.keys()), weights=list(region_weights.values())
            )[0]
            state = random.choice(self.BRAZILIAN_REGIONS[region])

            open_date = fake.date_between(start_date="-10y", end_date="-1y")
            created_at = datetime.combine(open_date, fake.time_object())
            updated_at = fake.date_time_between(start_date=created_at, end_date="now")

            store = {
                "store_id": store_id,
                "store_name": f"Loja {fake.city()} - {state}",
                "store_type": random.choices(
                    self.STORE_TYPES, weights=[0.05, 0.70, 0.15, 0.05, 0.05]
                )[0],
                "region": region,
                "city": fake.city(),
                "state": state,
                "manager_name": fake.name(),
                "open_date": open_date,
                "is_active": random.random() > 0.05,
                "created_at": created_at,
                "updated_at": updated_at,
            }

            stores.append(store)

        return stores

    def generate_orders(
        self,
        count: int,
        customer_ids: Optional[List[str]] = None,
        product_ids: Optional[List[str]] = None,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generate orders and order items.

        IMPLEMENTATION NOTE:
        - Creates realistic order patterns
        - Generates consistent total calculations
        - Returns both orders and order_items

        Args:
            count: Number of orders to generate
            customer_ids: List of valid customer IDs (uses cache if not provided)
            product_ids: List of valid product IDs (uses cache if not provided)

        Returns:
            Tuple of (orders, order_items)
        """
        if customer_ids is None:
            customer_ids = list(self._customer_cache.keys())
        if product_ids is None:
            product_ids = list(self._product_cache.keys())

        if not customer_ids or not product_ids:
            raise ValueError("Must provide customer and product IDs, or generate them first")

        orders = []
        order_items = []

        for i in range(count):
            order_id = f"ORD-{str(i+1).zfill(10)}"
            customer_id = random.choice(customer_ids)

            # Order date within last 2 years
            order_date = fake.date_time_between(start_date="-2y", end_date="now")

            # Generate items for this order
            num_items = max(1, int(random.gauss(3, 1.5)))  # Average 3 items
            num_items = min(num_items, 10)  # Cap at 10

            items = []
            subtotal = Decimal("0")

            for j in range(num_items):
                product_id = random.choice(product_ids)
                product = self._product_cache.get(product_id, {})

                quantity = random.randint(1, 5)
                unit_price = product.get("unit_price", Decimal(str(random.uniform(10, 500))))
                discount_percent = Decimal(str(random.choice([0, 0, 0, 5, 10, 15, 20])))

                line_total = quantity * unit_price * (1 - discount_percent / 100)
                line_total = line_total.quantize(Decimal("0.01"))

                item = {
                    "order_item_id": f"{order_id}-{j+1:03d}",
                    "order_id": order_id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": discount_percent,
                    "line_total": line_total,
                    "created_at": order_date,
                }

                items.append(item)
                subtotal += line_total

            order_items.extend(items)

            # Order-level calculations
            discount_amount = subtotal * Decimal(str(random.choice([0, 0, 0.05, 0.10])))
            discount_amount = discount_amount.quantize(Decimal("0.01"))

            shipping_cost = Decimal(str(random.choice([0, 9.99, 14.99, 19.99, 29.99])))
            total_amount = subtotal - discount_amount + shipping_cost

            order = {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": order_date,
                "order_status": random.choices(self.ORDER_STATUSES, weights=self.STATUS_WEIGHTS)[0],
                "shipping_address": fake.address().replace("\n", ", "),
                "payment_method": random.choices(
                    self.PAYMENT_METHODS, weights=self.PAYMENT_WEIGHTS
                )[0],
                "subtotal": subtotal,
                "discount_amount": discount_amount,
                "shipping_cost": shipping_cost,
                "total_amount": total_amount,
                "created_at": order_date,
                "updated_at": fake.date_time_between(start_date=order_date, end_date="now"),
            }

            orders.append(order)

        return orders, order_items

    def generate_all(self, config: Optional[GeneratorConfig] = None) -> Dict[str, List[Dict]]:
        """
        Generate complete retail dataset.

        USAGE:
            generator = RetailMockDataGenerator()
            data = generator.generate_all()

            # Access:
            data["customers"]
            data["products"]
            data["stores"]
            data["orders"]
            data["order_items"]
        """
        if config is None:
            config = GeneratorConfig()

        # Reset seed for reproducibility
        random.seed(config.seed)
        Faker.seed(config.seed)

        # Generate in dependency order
        customers = self.generate_customers(config.num_customers)
        products = self.generate_products(config.num_products)
        stores = self.generate_stores(config.num_stores)
        orders, order_items = self.generate_orders(config.num_orders)

        return {
            "customers": customers,
            "products": products,
            "stores": stores,
            "orders": orders,
            "order_items": order_items,
        }


# ============================================================================
# Convenience function for quick data generation
# ============================================================================


def generate_sample_data(
    customers: int = 100,
    products: int = 50,
    orders: int = 500,
    stores: int = 10,
    seed: int = 42,
) -> Dict[str, List[Dict]]:
    """
    Quick function to generate sample data for testing.

    This is a convenience wrapper for rapid prototyping and testing.

    Args:
        customers: Number of customers to generate
        products: Number of products
        orders: Number of orders
        stores: Number of stores
        seed: Random seed for reproducibility

    Returns:
        Dictionary with all generated data
    """
    generator = RetailMockDataGenerator(seed=seed)
    config = GeneratorConfig(
        num_customers=customers,
        num_products=products,
        num_stores=stores,
        num_orders=orders,
        seed=seed,
    )
    return generator.generate_all(config)
