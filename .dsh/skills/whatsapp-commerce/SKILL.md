# WhatsApp AI Commerce Agent

## Overview
A fully autonomous, AI-powered WhatsApp agent that handles customer support, e-commerce, payments, shipping, and logistics.

## Architecture
- **Orchestrator**: Routes messages to specialized agents based on intent classification
- **E-commerce Engine**: Product catalog, shopping cart, orders, recommendations
- **Payment Engine**: Stripe integration with webhooks, refunds, and transaction recording
- **Shipping Engine**: FedEx/UPS integration with rate shopping, label generation, and tracking
- **Support Agent**: Intent detection, sentiment analysis, FAQ matching, and ticket creation
- **WhatsApp Bridge**: Bidirectional communication via Meta Cloud API or whatsapp-web.js

## Agents
| Agent | Responsibility |
|-------|---------------|
| `CatalogAgent` | Product browsing, search, recommendations |
| `SalesAgent` | Cart management, checkout, order placement |
| `PaymentAgent` | Payment processing, refunds |
| `ShippingAgent` | Rate calculation, tracking, label generation |
| `SupportAgent` | Customer support, ticketing, FAQ |
| `AccountAgent` | Profile management, loyalty points |
| `InventoryAgent` | Stock monitoring, alerts |
| `AnalyticsAgent` | Business intelligence, metrics |

## Intent Classification
Messages are classified into intents based on keyword matching:
- `catalog` — product search, browsing
- `sales` — cart, checkout, orders
- `payment` — payments, refunds
- `shipping` — tracking, delivery
- `support` — help, complaints, returns
- `account` — profile, loyalty
- `greeting` — hello, menu

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/status` | GET | System status |
| `/api/products` | GET/POST | List/create products |
| `/api/products/<id>` | GET/PUT | Get/update product |
| `/api/orders` | GET | List orders |
| `/api/orders/<id>` | GET | Get order details |
| `/api/orders/<id>/status` | PUT | Update order status |
| `/api/payments/create-intent` | POST | Create payment intent |
| `/api/payments/webhook` | POST | Stripe webhook |
| `/api/shipping/rates` | POST | Get shipping rates |
| `/api/shipping/track/<tn>` | GET | Track shipment |
| `/api/tickets` | GET | List support tickets |
| `/api/analytics` | GET | Analytics overview |
| `/webhook/whatsapp` | GET/POST | WhatsApp webhook |

## Quick Start
```bash
# 1. Copy and configure environment
cp commerce/.env.example .env

# 2. Start services
docker-compose up -d

# 3. Seed sample products
docker-compose exec commerce python main.py --seed

# 4. Check status
docker-compose exec commerce python main.py --status
```

## WhatsApp Integration
Set `WHATSAPP_PROVIDER=cloud_api` and configure your Meta app credentials.
For development, use `WHATSAPP_PROVIDER=mock` to test without a real WhatsApp account.

## Webhook URLs
Configure these in your Meta app dashboard:
- **Webhook URL**: `https://your-domain.com/webhook/whatsapp`
- **Verify Token**: Match `WHATSAPP_VERIFY_TOKEN` in your `.env`
