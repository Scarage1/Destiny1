# Data Quality Report

Profiling-based quality report for raw SAP O2C dataset.

## Executive Summary

- Entities scanned: 19
- Records scanned: 21393

## Issues to Monitor

### High-null Columns (>=30%)

| Entity | Column | Null % |
|---|---|---:|
| billing_document_cancellations | cancelledBillingDocument | 100.0 |
| business_partner_addresses | poBox | 100.0 |
| business_partner_addresses | poBoxDeviatingCityName | 100.0 |
| business_partner_addresses | poBoxDeviatingCountry | 100.0 |
| business_partner_addresses | poBoxDeviatingRegion | 100.0 |
| business_partner_addresses | poBoxLobbyName | 100.0 |
| business_partner_addresses | poBoxPostalCode | 100.0 |
| business_partner_addresses | taxJurisdiction | 100.0 |
| business_partner_addresses | transportZone | 100.0 |
| business_partners | correspondenceLanguage | 100.0 |
| business_partners | firstName | 100.0 |
| business_partners | industry | 100.0 |
| business_partners | lastName | 100.0 |
| customer_company_assignments | accountingClerk | 100.0 |
| customer_company_assignments | accountingClerkFaxNumber | 100.0 |
| customer_company_assignments | accountingClerkInternetAddress | 100.0 |
| customer_company_assignments | accountingClerkPhoneNumber | 100.0 |
| customer_company_assignments | alternativePayerAccount | 100.0 |
| customer_company_assignments | paymentBlockingReason | 100.0 |
| customer_company_assignments | paymentMethodsList | 100.0 |
| customer_sales_area_assignments | billingIsBlockedForCustomer | 100.0 |
| customer_sales_area_assignments | creditControlArea | 100.0 |
| customer_sales_area_assignments | salesDistrict | 100.0 |
| customer_sales_area_assignments | salesGroup | 100.0 |
| customer_sales_area_assignments | salesOffice | 100.0 |
| customer_sales_area_assignments | supplyingPlant | 100.0 |
| journal_entry_items_accounts_receivable | assignmentReference | 100.0 |
| journal_entry_items_accounts_receivable | costCenter | 100.0 |
| outbound_delivery_headers | deliveryBlockReason | 100.0 |
| outbound_delivery_headers | headerBillingBlockReason | 100.0 |
| outbound_delivery_headers | overallProofOfDeliveryStatus | 100.0 |
| outbound_delivery_items | itemBillingBlockReason | 100.0 |
| outbound_delivery_items | lastChangeDate | 100.0 |
| payments_accounts_receivable | assignmentReference | 100.0 |
| payments_accounts_receivable | costCenter | 100.0 |
| payments_accounts_receivable | invoiceReference | 100.0 |
| payments_accounts_receivable | invoiceReferenceFiscalYear | 100.0 |
| payments_accounts_receivable | salesDocument | 100.0 |
| payments_accounts_receivable | salesDocumentItem | 100.0 |
| plants | defaultPurchasingOrganization | 100.0 |

## Ingestion Risk Notes

- Two entities are present in raw data but not yet mapped in current ingestion code: `product_plants`, `product_storage_locations`.
- Relationship integrity must be validated during graph load (missing source/target IDs should be reported).
- Use deterministic canonical IDs and idempotent load semantics.