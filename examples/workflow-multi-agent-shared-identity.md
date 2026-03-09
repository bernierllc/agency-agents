# Multi-Agent Workflow: Shared Identity Resolution

> What happens when three agents all encounter the same customer from different sources - and how to prevent duplicate records, conflicting actions, and cascading errors.

## The Problem

You're running a customer support system with three agents:
- **Support Responder** processes incoming tickets
- **Backend Architect** maintains the customer database
- **Analytics Reporter** generates weekly customer reports

A customer named "Bill Smith" (wsmith@acme.com) contacts you through email support, then calls your phone line, then submits a web form. Each channel uses a different source system. Without shared identity, you get three separate customer records and three separate responses.

## Agent Team

| Agent | Role in this workflow |
|-------|---------------------|
| Identity Graph Operator | Resolves all records to canonical entities before other agents act |
| Support Responder | Handles customer tickets (only after identity is resolved) |
| Backend Architect | Designs the data model with identity-first architecture |
| Analytics Reporter | Reports on unique customers, not duplicate records |
| Reality Checker | Verifies merge decisions meet quality gates |

## The Workflow

### Step 1 - Set Up the Identity Layer

**Activate Identity Graph Operator**

```
Activate Identity Graph Operator.

We have 3 data sources for customer records:
- "email_support" - tickets from email (fields: email, name, subject)
- "phone_support" - call logs (fields: phone, caller_name, call_date)
- "web_forms" - web submissions (fields: email, full_name, phone, message)

Set up the shared identity graph so all agents resolve to the same customer.
```

The Identity Graph Operator runs:

```
register_agent with capabilities: ["identity_resolution", "entity_matching", "merge_review"]

# Then resolves incoming records as they arrive
```

### Step 2 - First Record Arrives (Email)

The Support Responder receives a ticket from email_support:

```json
{
  "source": "email_support",
  "external_id": "ticket-9201",
  "email": "wsmith@acme.com",
  "name": "Bill Smith",
  "subject": "Can't reset my password"
}
```

**Before responding, the Support Responder asks the Identity Graph Operator to resolve:**

```
resolve with source_name: "email_support", external_id: "ticket-9201",
  data: { "email": "wsmith@acme.com", "first_name": "Bill", "last_name": "Smith" }
```

Result: New entity created (first time seeing this person).

```json
{
  "entity_id": "ent-a1b2c3",
  "is_new": true,
  "confidence": 1.0,
  "canonical_data": { "email": "wsmith@acme.com", "first_name": "bill", "last_name": "smith" }
}
```

Support Responder now handles the ticket, tagged with `entity_id: ent-a1b2c3`.

### Step 3 - Second Record Arrives (Phone)

A call comes in through phone_support:

```json
{
  "source": "phone_support",
  "external_id": "call-7744",
  "phone": "+1-555-014-2",
  "caller_name": "William Smith"
}
```

**Identity Graph Operator resolves:**

```
resolve with source_name: "phone_support", external_id: "call-7744",
  data: { "phone": "+15550142", "first_name": "William", "last_name": "Smith" }
```

The engine doesn't have a phone match yet (the email record didn't include a phone). This creates a new entity:

```json
{
  "entity_id": "ent-d4e5f6",
  "is_new": true,
  "confidence": 1.0
}
```

Two entities now exist. Are they the same person? The Identity Graph Operator isn't sure yet - no overlapping fields to match on.

### Step 4 - Third Record Arrives (Web Form)

A web form submission comes in with BOTH email and phone:

```json
{
  "source": "web_forms",
  "external_id": "form-3388",
  "email": "wsmith@acme.com",
  "full_name": "William Smith",
  "phone": "555-0142",
  "message": "Still can't reset my password, tried calling too"
}
```

**Identity Graph Operator resolves:**

```
resolve with source_name: "web_forms", external_id: "form-3388",
  data: { "email": "wsmith@acme.com", "first_name": "William", "last_name": "Smith", "phone": "+15550142" }
```

Now it gets interesting. The engine:
1. Matches email to `ent-a1b2c3` (exact email match)
2. Matches phone to `ent-d4e5f6` (exact phone match after normalization)
3. Realizes both entities should be one person

```json
{
  "entity_id": "ent-a1b2c3",
  "is_new": false,
  "confidence": 0.96,
  "canonical_data": {
    "email": "wsmith@acme.com",
    "first_name": "william",
    "last_name": "smith",
    "phone": "+15550142"
  }
}
```

The engine auto-merged `ent-d4e5f6` into `ent-a1b2c3` (the email entity had more members). The phone record is now linked to the same entity.

### Step 5 - Verify the Merge

**Activate Reality Checker to verify:**

```
Activate Reality Checker.

The identity graph just auto-merged two entities:
- ent-a1b2c3 (email: wsmith@acme.com, name: Bill Smith)
- ent-d4e5f6 (phone: +15550142, name: William Smith)

Review the merge evidence and verify this is correct.
```

The Reality Checker asks the Identity Graph Operator:

```
explain with entity_id: "ent-a1b2c3"
```

Gets back the full audit: merge chain, per-field scores, nickname mapping (Bill -> William), timeline of events. Confirms the merge is valid.

### Step 6 - Analytics Gets Clean Data

**Activate Analytics Reporter:**

```
Activate Analytics Reporter.

Generate a report on customer support volume this week.
Use the identity graph to count unique customers, not duplicate records.
```

The Analytics Reporter queries the identity graph:

```
search with q: "smith"
```

Gets back one entity with three linked source records, not three separate customers. The report shows 1 customer with 3 touchpoints, not 3 customers with 1 touchpoint each.

## What Would Have Happened Without Shared Identity

| With shared identity | Without shared identity |
|---|---|
| 1 customer record | 3 separate customer records |
| Support agent sees full history across channels | Support agent only sees the email ticket |
| Analytics reports 1 customer, 3 touchpoints | Analytics reports 3 customers |
| One password reset | Three separate password reset workflows |
| Customer gets one follow-up | Customer gets three follow-ups |

## Key Patterns

1. **Resolve before acting.** Every agent resolves incoming records through the identity graph BEFORE taking action. This is the single most important pattern.

2. **The bridge record.** The web form submission (Step 4) was the bridge - it had both email AND phone, connecting two previously separate entities. This is why multi-source ingestion matters.

3. **Propose, don't merge.** For lower confidence matches, the Identity Graph Operator creates proposals. The Reality Checker reviews them. Direct auto-merge only happens at high confidence.

4. **Memory compounds.** After this workflow, the identity graph remembers that "Bill" and "William" at the same phone number are the same person. Future agents benefit from this learned association.

## Scaling This Pattern

This 3-agent example works the same way with 30 agents or 300. The identity graph is the shared substrate:

- Sales agents resolve leads before adding to CRM
- Billing agents resolve customers before charging
- Shipping agents resolve addresses before dispatching
- Marketing agents resolve contacts before emailing
- Compliance agents resolve entities before flagging

Every agent resolves first. Every agent gets the same answer. That's the pattern.

---

**Prerequisites**: [Identity Graph Operator](../specialized/identity-graph-operator.md) agent must be activated first. Uses [Kanoniv](https://github.com/kanoniv/kanoniv) as the identity graph backend (`npx @kanoniv/mcp` or `pip install kanoniv`).
