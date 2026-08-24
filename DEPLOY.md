# Deploy to Render

## Quick Deploy (One-Click)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/dutchkemsystems/dutchkem-commerce-agent)

## Manual Deploy

### Step 1: Connect GitHub to Render
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Blueprint**
3. Connect your GitHub account (dutchkemsystems)
4. Select the `dutchkem-commerce-agent` repo

### Step 2: Configure Environment Variables
After the Blueprint creates the services, set these secrets in the Render Dashboard:

**For `whatsapp-commerce-agent` service:**
- `STRIPE_SECRET_KEY` — Your Stripe secret key
- `STRIPE_WEBHOOK_SECRET` — Your Stripe webhook secret
- `FEDEX_API_KEY` — FedEx API key
- `FEDEX_SECRET_KEY` — FedEx secret key
- `FEDEX_ACCOUNT_NUMBER` — FedEx account number
- `FEDEX_METER_NUMBER` — FedEx meter number
- `OPENROUTER_API_KEY` — OpenRouter API key for LLM

### Step 3: Deploy
Render will automatically deploy when you push to the `main` branch.

### Step 4: Seed Products
After deployment, seed sample products:
```bash
# In Render Shell (or via SSH)
python main.py --seed
```

### Step 5: Configure WhatsApp
1. Set `WHATSAPP_PROVIDER=cloud_api` in Render Dashboard
2. Configure your Meta app with the webhook URL:
   - Webhook URL: `https://whatsapp-commerce-agent.onrender.com/webhook/whatsapp`
   - Verify Token: `commerce-verify-token`

## Service URLs
After deployment:
- **Commerce API**: `https://whatsapp-commerce-agent.onrender.com`
- **Admin Dashboard**: `https://whatsapp-commerce-agent.onrender.com/`
- **Health Check**: `https://whatsapp-commerce-agent.onrender.com/health`
- **API Status**: `https://whatsapp-commerce-agent.onrender.com/api/status`
