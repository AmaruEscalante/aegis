# Payments API Reference

## Base URL

```
https://api.example-payments.com/v2
```

All endpoints require the `Authorization: Bearer <token>` header.

---

## POST /charges

Creates a new charge against a payment method.

### Request Body

| Field         | Type   | Required | Description                                    |
|---------------|--------|----------|------------------------------------------------|
| amount        | int    | Yes      | Amount in cents (e.g., 1000 = $10.00)          |
| currency      | string | Yes      | ISO 4217 currency code (e.g., "usd")           |
| source        | string | Yes      | Payment method token (from client-side SDK)    |
| description   | string | No       | Free-text description shown on statements      |
| metadata      | object | No       | Key-value pairs for your internal bookkeeping  |
| capture       | bool   | No       | Default `true`. Set `false` to authorize only. |

### Example Request

```json
{
  "amount": 2500,
  "currency": "usd",
  "source": "tok_visa",
  "description": "Order #1023 — Blue Widget (x2)",
  "capture": true
}
```

### Example Response (200 OK)

```json
{
  "id": "ch_3Ob9Rk2eZvKYlo2C0TmgLPXn",
  "object": "charge",
  "amount": 2500,
  "amount_captured": 2500,
  "currency": "usd",
  "status": "succeeded",
  "created": 1713000000,
  "description": "Order #1023 — Blue Widget (x2)",
  "receipt_url": "https://pay.example-payments.com/receipts/ch_3Ob9Rk"
}
```

### Error Codes

| Code                  | HTTP | Description                                      |
|-----------------------|------|--------------------------------------------------|
| card_declined         | 402  | Card was declined by the issuer                  |
| insufficient_funds    | 402  | Card has insufficient funds                      |
| invalid_expiry_month  | 400  | The card expiration month is invalid             |
| invalid_cvc           | 400  | The CVC number is incorrect                      |
| rate_limit_exceeded   | 429  | Too many requests; back off and retry            |

---

## GET /charges/:id

Retrieves a previously created charge.

### Path Parameters

| Parameter | Description          |
|-----------|----------------------|
| id        | The charge ID string |

### Example Response (200 OK)

```json
{
  "id": "ch_3Ob9Rk2eZvKYlo2C0TmgLPXn",
  "object": "charge",
  "amount": 2500,
  "status": "succeeded"
}
```
