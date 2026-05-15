# Source Workbook Notes

The supplied `seller-buyer-churn.xlsx` was inspected as representative schema context. It is not treated as sufficient model-training data. Several sheets include SQL snippets and small samples, so the platform design uses the fields to infer entity patterns and then generates a larger synthetic ecosystem.

## Sheets

| Sheet | Observed Purpose | Normalized Target |
| --- | --- | --- |
| `cb` | Contactbook relationship records between two GL user ids. | `contactbook` |
| `cust_to_serv` | Customer-to-service/subscription mapping with start/validity/sales fields. | `subscriptions`, `subscription_risk` |
| `mcd` | Message center details for a small user pair. | `messages`, `inquiries` |
| `mcd all txn` | Broader message-center transaction history. | `messages`, `inquiries` |
| `txn` | Transaction/ref code meaning. | code mappings for transaction types |
| `Subscription dates` | GL user id, hosted date, expiry date, days before expiry, service id. | `subscriptions` |

## Important Source Fields

### Contactbook (`cb`)

| Source Field | Platform Use |
| --- | --- |
| `fk_glusr_usr_id` | seller/user id |
| `contacts_glid` | connected buyer/seller id |
| `contact_last_modified` | recency feature |
| `contacts_add_date` | relationship age |
| `last_contact_date` | contact recency |
| `latest_txn_date` | latest relationship activity |
| `unread_message_cnt` | communication friction |
| `contact_starred_flag` | relationship strength signal |
| `last_message` | retrieval context for AI summary |

### Customer To Service (`cust_to_serv`)

| Source Field | Platform Use |
| --- | --- |
| `cust_to_serv_startdate` | subscription start |
| `cust_to_serv_validupto` | renewal/expiry date |
| `fk_cust_to_serv_glusr_id` | seller id |
| `fk_service_id` | plan/service |
| `service_grace_period` | renewal friction |
| `serv_upgraded_type` | upgrade/downgrade signal |
| `payment_plan` | plan/payment metadata |
| `download_sales_exec_id` | sales owner |

### Message Center (`mcd`, `mcd all txn`)

| Source Field | Platform Use |
| --- | --- |
| `message_receiver_glusr_id` | receiver entity id |
| `message_sender_glusr_id` | sender entity id |
| `message_ref_type` | event type such as ENQ, REPLY, SYSTEM |
| `message_txn_ref_type` | transaction bucket |
| `message_ref_date` | business event timestamp |
| `message_date` | message timestamp |
| `message_read_date` | read latency |
| `message_read_status` | engagement/read feature |
| `message_ref_prod_name` | product/category context |
| `message_text` / `message_text_json` | retrieval evidence and sentiment source |
| `message_ref_call_status` | call/contact outcome |
| `fk_rfq_source_id` | lead source proxy |

### Transaction Code Dictionary (`txn`)

| Code | Observed Meaning |
| --- | --- |
| `W` | Enquiry parent bucket. |
| `X` | Waiting/pending enquiry state. |
| `Y` | Rejected enquiry state. |
| `B` | Buylead parent bucket. |
| `ENQ` | Enquiry row/event. |
| `BL` | Buylead row/event. |
| `PNS` | Pay n Show row/event. |
| `C2C` | Click-to-call row/event. |

### Subscription Dates

| Source Field | Platform Use |
| --- | --- |
| `GLUSR_USR_ID` | seller id |
| `paidshowroom_url` | premium presence/profile context |
| `Date Hosted` | subscription activation |
| `Expiry Date` | renewal date |
| `Days before Expiry` | renewal urgency |
| `Service Id` | plan/service metadata |

## Design Decisions From Workbook

| Observation | Design Decision |
| --- | --- |
| Message center stores enquiry, reply, system, and call-like events together. | Normalize into `inquiries` plus `messages`, while preserving event types. |
| Contactbook captures relationship and unread-message state. | Use as graph and repeat-business feature source. |
| Subscription fields include validity, grace, upgrade, and sales owner metadata. | Add 90-day renewal engine and routed owner alerts. |
| Many operational values are codes. | Maintain code dictionary and translate to readable reason codes for demos. |
| Sample size is tiny. | Generate synthetic data at realistic scale with labels, seasonality, and decline patterns. |

