# Revenue Pipeline Schema

Use a persistent table when a connected spreadsheet/database is available.

## Columns

| Field | Meaning |
|---|---|
| `id` | Stable opportunity identifier |
| `created_at` | First discovery timestamp |
| `updated_at` | Last meaningful update |
| `opportunity` | Short name |
| `lane` | asset, service, bounty, product, retainer, content/affiliate, other |
| `buyer_platform` | Buyer, client, marketplace, or program |
| `source` | URL, repository, message, or connected source |
| `stage` | discovered, qualified, building, ready, contacted, negotiating, committed, delivered, collected, lost |
| `score` | Current 0-100 opportunity score |
| `expected_value` | Estimated gross revenue if converted |
| `probability` | Estimated conversion probability from 0 to 1 |
| `expected_time_to_cash_days` | Estimated days to payment |
| `cost` | Expected cash cost |
| `actions_completed` | Concise executed actions |
| `next_action` | Single next best action |
| `last_contact` | Last outbound/inbound contact timestamp |
| `evidence` | Evidence URL/reference |
| `committed_revenue` | Revenue with external commitment evidence |
| `collected_revenue` | Revenue with payment/settlement evidence |
| `notes` | Material context only |

## Stage rules

- `discovered`: candidate exists, not yet validated.
- `qualified`: buyer/demand and payment path are credible.
- `building`: deliverable or offer is actively being prepared.
- `ready`: deliverable/offer is ready to sell or submit.
- `contacted`: a real buyer/program submission has been contacted.
- `negotiating`: active two-way commercial discussion exists.
- `committed`: accepted order/agreement/award exists.
- `delivered`: promised deliverable has been provided.
- `collected`: payment/settlement evidence exists.
- `lost`: opportunity ended or failed kill criteria.

Never use `committed` or `collected` based on forecasts, sent proposals, pending invoices, or optimistic interpretation.
