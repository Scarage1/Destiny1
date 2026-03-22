# Data Dictionary

Generated from raw JSONL dataset profiling.

- Total entities: 19
- Total rows: 21393

## Entity Inventory

| Entity | Files | Rows | Parse Errors | Columns | Candidate Keys |
|---|---:|---:|---:|---:|---|
| billing_document_cancellations | 1 | 80 | 0 | 14 | accountingDocument, billingDocument, lastChangeDateTime |
| billing_document_headers | 2 | 163 | 0 | 14 | accountingDocument, billingDocument, cancelledBillingDocument |
| billing_document_items | 2 | 245 | 0 | 9 | - |
| business_partner_addresses | 1 | 8 | 0 | 20 | addressId, addressUuid, businessPartner, cityName |
| business_partners | 1 | 8 | 0 | 19 | businessPartner, businessPartnerFullName, businessPartnerName, customer |
| customer_company_assignments | 1 | 8 | 0 | 13 | customer |
| customer_sales_area_assignments | 1 | 28 | 0 | 19 | - |
| journal_entry_items_accounts_receivable | 4 | 123 | 0 | 22 | accountingDocument, referenceDocument |
| outbound_delivery_headers | 1 | 86 | 0 | 13 | deliveryDocument |
| outbound_delivery_items | 2 | 137 | 0 | 11 | - |
| payments_accounts_receivable | 1 | 120 | 0 | 23 | accountingDocument |
| plants | 1 | 44 | 0 | 14 | addressId, plant, plantCustomer, plantName |
| product_descriptions | 2 | 69 | 0 | 3 | product, productDescription |
| product_plants | 4 | 3036 | 0 | 9 | - |
| product_storage_locations | 18 | 16723 | 0 | 5 | - |
| products | 2 | 69 | 0 | 17 | product, productOldId |
| sales_order_headers | 1 | 100 | 0 | 24 | lastChangeDateTime, salesOrder |
| sales_order_items | 2 | 167 | 0 | 13 | - |
| sales_order_schedule_lines | 2 | 179 | 0 | 6 | - |

## Join Key Candidates

| Source | Target | Relationship |
|---|---|---|
| sales_order_headers.salesOrder | sales_order_items.salesOrder | header-to-item |
| sales_order_items.salesOrder | outbound_delivery_items.referenceSdDocument | order-to-delivery |
| outbound_delivery_headers.deliveryDocument | outbound_delivery_items.deliveryDocument | header-to-item |
| outbound_delivery_headers.deliveryDocument | billing_document_items.referenceSdDocument | delivery-to-billing |
| billing_document_headers.billingDocument | billing_document_items.billingDocument | header-to-item |
| billing_document_headers.accountingDocument | journal_entry_items_accounts_receivable.accountingDocument | billing-to-journal |
| journal_entry_items_accounts_receivable.clearingAccountingDocument | payments_accounts_receivable.accountingDocument | journal-to-payment |
| billing_document_headers.soldToParty | business_partners.businessPartner | billing-to-customer |
| sales_order_headers.soldToParty | business_partners.businessPartner | sales-to-customer |
| sales_order_items.material | products.product | item-to-product |
| billing_document_items.material | products.product | billing-item-to-product |
| sales_order_items.productionPlant | plants.plant | item-to-plant |
| outbound_delivery_items.plant | plants.plant | delivery-item-to-plant |

## Column-level Details

### billing_document_cancellations

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| accountingDocument | 80 | 0 | 0.0 | 80 |
| billingDocument | 80 | 0 | 0.0 | 80 |
| billingDocumentDate | 80 | 0 | 0.0 | 2 |
| billingDocumentIsCancelled | 80 | 0 | 0.0 | 1 |
| billingDocumentType | 80 | 0 | 0.0 | 1 |
| cancelledBillingDocument | 0 | 80 | 100.0 | 0 |
| companyCode | 80 | 0 | 0.0 | 1 |
| creationDate | 80 | 0 | 0.0 | 2 |
| creationTime | 80 | 0 | 0.0 | 4 |
| fiscalYear | 80 | 0 | 0.0 | 1 |
| lastChangeDateTime | 80 | 0 | 0.0 | 80 |
| soldToParty | 80 | 0 | 0.0 | 4 |
| totalNetAmount | 80 | 0 | 0.0 | 46 |
| transactionCurrency | 80 | 0 | 0.0 | 1 |

### billing_document_headers

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| accountingDocument | 163 | 0 | 0.0 | 163 |
| billingDocument | 163 | 0 | 0.0 | 163 |
| billingDocumentDate | 163 | 0 | 0.0 | 3 |
| billingDocumentIsCancelled | 163 | 0 | 0.0 | 2 |
| billingDocumentType | 163 | 0 | 0.0 | 2 |
| cancelledBillingDocument | 80 | 83 | 50.92 | 80 |
| companyCode | 163 | 0 | 0.0 | 1 |
| creationDate | 163 | 0 | 0.0 | 4 |
| creationTime | 163 | 0 | 0.0 | 6 |
| fiscalYear | 163 | 0 | 0.0 | 1 |
| lastChangeDateTime | 163 | 0 | 0.0 | 84 |
| soldToParty | 163 | 0 | 0.0 | 4 |
| totalNetAmount | 163 | 0 | 0.0 | 47 |
| transactionCurrency | 163 | 0 | 0.0 | 1 |

### billing_document_items

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| billingDocument | 245 | 0 | 0.0 | 163 |
| billingDocumentItem | 245 | 0 | 0.0 | 12 |
| billingQuantity | 245 | 0 | 0.0 | 2 |
| billingQuantityUnit | 245 | 0 | 0.0 | 1 |
| material | 245 | 0 | 0.0 | 55 |
| netAmount | 245 | 0 | 0.0 | 53 |
| referenceSdDocument | 245 | 0 | 0.0 | 83 |
| referenceSdDocumentItem | 245 | 0 | 0.0 | 12 |
| transactionCurrency | 245 | 0 | 0.0 | 1 |

### business_partner_addresses

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| addressId | 8 | 0 | 0.0 | 8 |
| addressTimeZone | 8 | 0 | 0.0 | 1 |
| addressUuid | 8 | 0 | 0.0 | 8 |
| businessPartner | 8 | 0 | 0.0 | 8 |
| cityName | 2 | 6 | 75.0 | 2 |
| country | 8 | 0 | 0.0 | 1 |
| poBox | 0 | 8 | 100.0 | 0 |
| poBoxDeviatingCityName | 0 | 8 | 100.0 | 0 |
| poBoxDeviatingCountry | 0 | 8 | 100.0 | 0 |
| poBoxDeviatingRegion | 0 | 8 | 100.0 | 0 |
| poBoxIsWithoutNumber | 8 | 0 | 0.0 | 1 |
| poBoxLobbyName | 0 | 8 | 100.0 | 0 |
| poBoxPostalCode | 0 | 8 | 100.0 | 0 |
| postalCode | 3 | 5 | 62.5 | 3 |
| region | 8 | 0 | 0.0 | 7 |
| streetName | 2 | 6 | 75.0 | 2 |
| taxJurisdiction | 0 | 8 | 100.0 | 0 |
| transportZone | 0 | 8 | 100.0 | 0 |
| validityEndDate | 8 | 0 | 0.0 | 1 |
| validityStartDate | 8 | 0 | 0.0 | 2 |

### business_partners

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| businessPartner | 8 | 0 | 0.0 | 8 |
| businessPartnerCategory | 8 | 0 | 0.0 | 1 |
| businessPartnerFullName | 8 | 0 | 0.0 | 8 |
| businessPartnerGrouping | 8 | 0 | 0.0 | 2 |
| businessPartnerIsBlocked | 8 | 0 | 0.0 | 2 |
| businessPartnerName | 8 | 0 | 0.0 | 8 |
| correspondenceLanguage | 0 | 8 | 100.0 | 0 |
| createdByUser | 8 | 0 | 0.0 | 2 |
| creationDate | 8 | 0 | 0.0 | 2 |
| creationTime | 8 | 0 | 0.0 | 4 |
| customer | 8 | 0 | 0.0 | 8 |
| firstName | 0 | 8 | 100.0 | 0 |
| formOfAddress | 8 | 0 | 0.0 | 1 |
| industry | 0 | 8 | 100.0 | 0 |
| isMarkedForArchiving | 8 | 0 | 0.0 | 2 |
| lastChangeDate | 8 | 0 | 0.0 | 4 |
| lastName | 0 | 8 | 100.0 | 0 |
| organizationBpName1 | 8 | 0 | 0.0 | 8 |
| organizationBpName2 | 1 | 7 | 87.5 | 1 |

### customer_company_assignments

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| accountingClerk | 0 | 8 | 100.0 | 0 |
| accountingClerkFaxNumber | 0 | 8 | 100.0 | 0 |
| accountingClerkInternetAddress | 0 | 8 | 100.0 | 0 |
| accountingClerkPhoneNumber | 0 | 8 | 100.0 | 0 |
| alternativePayerAccount | 0 | 8 | 100.0 | 0 |
| companyCode | 8 | 0 | 0.0 | 1 |
| customer | 8 | 0 | 0.0 | 8 |
| customerAccountGroup | 8 | 0 | 0.0 | 2 |
| deletionIndicator | 8 | 0 | 0.0 | 2 |
| paymentBlockingReason | 0 | 8 | 100.0 | 0 |
| paymentMethodsList | 0 | 8 | 100.0 | 0 |
| paymentTerms | 2 | 6 | 75.0 | 1 |
| reconciliationAccount | 8 | 0 | 0.0 | 2 |

### customer_sales_area_assignments

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| billingIsBlockedForCustomer | 0 | 28 | 100.0 | 0 |
| completeDeliveryIsDefined | 28 | 0 | 0.0 | 1 |
| creditControlArea | 0 | 28 | 100.0 | 0 |
| currency | 28 | 0 | 0.0 | 1 |
| customer | 28 | 0 | 0.0 | 8 |
| customerPaymentTerms | 28 | 0 | 0.0 | 2 |
| deliveryPriority | 28 | 0 | 0.0 | 1 |
| distributionChannel | 28 | 0 | 0.0 | 5 |
| division | 28 | 0 | 0.0 | 1 |
| exchangeRateType | 2 | 26 | 92.86 | 1 |
| incotermsClassification | 23 | 5 | 17.86 | 1 |
| incotermsLocation1 | 23 | 5 | 17.86 | 3 |
| salesDistrict | 0 | 28 | 100.0 | 0 |
| salesGroup | 0 | 28 | 100.0 | 0 |
| salesOffice | 0 | 28 | 100.0 | 0 |
| salesOrganization | 28 | 0 | 0.0 | 1 |
| shippingCondition | 22 | 6 | 21.43 | 1 |
| slsUnlmtdOvrdelivIsAllwd | 28 | 0 | 0.0 | 1 |
| supplyingPlant | 0 | 28 | 100.0 | 0 |

### journal_entry_items_accounts_receivable

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| accountingDocument | 123 | 0 | 0.0 | 123 |
| accountingDocumentItem | 123 | 0 | 0.0 | 1 |
| accountingDocumentType | 123 | 0 | 0.0 | 1 |
| amountInCompanyCodeCurrency | 123 | 0 | 0.0 | 79 |
| amountInTransactionCurrency | 123 | 0 | 0.0 | 79 |
| assignmentReference | 0 | 123 | 100.0 | 0 |
| clearingAccountingDocument | 120 | 3 | 2.44 | 76 |
| clearingDate | 120 | 3 | 2.44 | 2 |
| clearingDocFiscalYear | 123 | 0 | 0.0 | 2 |
| companyCode | 123 | 0 | 0.0 | 1 |
| companyCodeCurrency | 123 | 0 | 0.0 | 1 |
| costCenter | 0 | 123 | 100.0 | 0 |
| customer | 123 | 0 | 0.0 | 2 |
| documentDate | 123 | 0 | 0.0 | 3 |
| financialAccountType | 123 | 0 | 0.0 | 1 |
| fiscalYear | 123 | 0 | 0.0 | 1 |
| glAccount | 123 | 0 | 0.0 | 1 |
| lastChangeDateTime | 123 | 0 | 0.0 | 3 |
| postingDate | 123 | 0 | 0.0 | 3 |
| profitCenter | 123 | 0 | 0.0 | 1 |
| referenceDocument | 123 | 0 | 0.0 | 123 |
| transactionCurrency | 123 | 0 | 0.0 | 1 |

### outbound_delivery_headers

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| actualGoodsMovementDate | 3 | 83 | 96.51 | 2 |
| actualGoodsMovementTime | 86 | 0 | 0.0 | 3 |
| creationDate | 86 | 0 | 0.0 | 3 |
| creationTime | 86 | 0 | 0.0 | 7 |
| deliveryBlockReason | 0 | 86 | 100.0 | 0 |
| deliveryDocument | 86 | 0 | 0.0 | 86 |
| hdrGeneralIncompletionStatus | 86 | 0 | 0.0 | 1 |
| headerBillingBlockReason | 0 | 86 | 100.0 | 0 |
| lastChangeDate | 83 | 3 | 3.49 | 3 |
| overallGoodsMovementStatus | 86 | 0 | 0.0 | 2 |
| overallPickingStatus | 86 | 0 | 0.0 | 1 |
| overallProofOfDeliveryStatus | 0 | 86 | 100.0 | 0 |
| shippingPoint | 86 | 0 | 0.0 | 5 |

### outbound_delivery_items

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| actualDeliveryQuantity | 137 | 0 | 0.0 | 11 |
| batch | 113 | 24 | 17.52 | 1 |
| deliveryDocument | 137 | 0 | 0.0 | 86 |
| deliveryDocumentItem | 137 | 0 | 0.0 | 12 |
| deliveryQuantityUnit | 137 | 0 | 0.0 | 1 |
| itemBillingBlockReason | 0 | 137 | 100.0 | 0 |
| lastChangeDate | 0 | 137 | 100.0 | 0 |
| plant | 137 | 0 | 0.0 | 5 |
| referenceSdDocument | 137 | 0 | 0.0 | 86 |
| referenceSdDocumentItem | 137 | 0 | 0.0 | 12 |
| storageLocation | 137 | 0 | 0.0 | 6 |

### payments_accounts_receivable

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| accountingDocument | 120 | 0 | 0.0 | 120 |
| accountingDocumentItem | 120 | 0 | 0.0 | 1 |
| amountInCompanyCodeCurrency | 120 | 0 | 0.0 | 78 |
| amountInTransactionCurrency | 120 | 0 | 0.0 | 78 |
| assignmentReference | 0 | 120 | 100.0 | 0 |
| clearingAccountingDocument | 120 | 0 | 0.0 | 76 |
| clearingDate | 120 | 0 | 0.0 | 2 |
| clearingDocFiscalYear | 120 | 0 | 0.0 | 1 |
| companyCode | 120 | 0 | 0.0 | 1 |
| companyCodeCurrency | 120 | 0 | 0.0 | 1 |
| costCenter | 0 | 120 | 100.0 | 0 |
| customer | 120 | 0 | 0.0 | 2 |
| documentDate | 120 | 0 | 0.0 | 2 |
| financialAccountType | 120 | 0 | 0.0 | 1 |
| fiscalYear | 120 | 0 | 0.0 | 1 |
| glAccount | 120 | 0 | 0.0 | 1 |
| invoiceReference | 0 | 120 | 100.0 | 0 |
| invoiceReferenceFiscalYear | 0 | 120 | 100.0 | 0 |
| postingDate | 120 | 0 | 0.0 | 2 |
| profitCenter | 120 | 0 | 0.0 | 1 |
| salesDocument | 0 | 120 | 100.0 | 0 |
| salesDocumentItem | 0 | 120 | 100.0 | 0 |
| transactionCurrency | 120 | 0 | 0.0 | 1 |

### plants

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| addressId | 44 | 0 | 0.0 | 44 |
| defaultPurchasingOrganization | 0 | 44 | 100.0 | 0 |
| distributionChannel | 44 | 0 | 0.0 | 1 |
| division | 44 | 0 | 0.0 | 1 |
| factoryCalendar | 44 | 0 | 0.0 | 1 |
| isMarkedForArchiving | 44 | 0 | 0.0 | 1 |
| language | 44 | 0 | 0.0 | 1 |
| plant | 44 | 0 | 0.0 | 44 |
| plantCategory | 0 | 44 | 100.0 | 0 |
| plantCustomer | 44 | 0 | 0.0 | 44 |
| plantName | 44 | 0 | 0.0 | 44 |
| plantSupplier | 35 | 9 | 20.45 | 35 |
| salesOrganization | 44 | 0 | 0.0 | 1 |
| valuationArea | 44 | 0 | 0.0 | 44 |

### product_descriptions

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| language | 69 | 0 | 0.0 | 1 |
| product | 69 | 0 | 0.0 | 69 |
| productDescription | 69 | 0 | 0.0 | 69 |

### product_plants

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| availabilityCheckType | 3036 | 0 | 0.0 | 1 |
| countryOfOrigin | 0 | 3036 | 100.0 | 0 |
| fiscalYearVariant | 0 | 3036 | 100.0 | 0 |
| mrpType | 3036 | 0 | 0.0 | 1 |
| plant | 3036 | 0 | 0.0 | 44 |
| product | 3036 | 0 | 0.0 | 69 |
| productionInvtryManagedLoc | 0 | 3036 | 100.0 | 0 |
| profitCenter | 3036 | 0 | 0.0 | 2 |
| regionOfOrigin | 0 | 3036 | 100.0 | 0 |

### product_storage_locations

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| dateOfLastPostedCntUnRstrcdStk | 0 | 16723 | 100.0 | 0 |
| physicalInventoryBlockInd | 0 | 16723 | 100.0 | 0 |
| plant | 16723 | 0 | 0.0 | 44 |
| product | 16723 | 0 | 0.0 | 69 |
| storageLocation | 16723 | 0 | 0.0 | 225 |

### products

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| baseUnit | 69 | 0 | 0.0 | 1 |
| createdByUser | 69 | 0 | 0.0 | 1 |
| creationDate | 69 | 0 | 0.0 | 2 |
| crossPlantStatus | 0 | 69 | 100.0 | 0 |
| crossPlantStatusValidityDate | 0 | 69 | 100.0 | 0 |
| division | 69 | 0 | 0.0 | 2 |
| grossWeight | 69 | 0 | 0.0 | 2 |
| industrySector | 69 | 0 | 0.0 | 1 |
| isMarkedForDeletion | 69 | 0 | 0.0 | 1 |
| lastChangeDate | 69 | 0 | 0.0 | 5 |
| lastChangeDateTime | 69 | 0 | 0.0 | 24 |
| netWeight | 69 | 0 | 0.0 | 2 |
| product | 69 | 0 | 0.0 | 69 |
| productGroup | 69 | 0 | 0.0 | 2 |
| productOldId | 69 | 0 | 0.0 | 69 |
| productType | 69 | 0 | 0.0 | 3 |
| weightUnit | 69 | 0 | 0.0 | 1 |

### sales_order_headers

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| createdByUser | 100 | 0 | 0.0 | 2 |
| creationDate | 100 | 0 | 0.0 | 2 |
| customerPaymentTerms | 100 | 0 | 0.0 | 2 |
| deliveryBlockReason | 0 | 100 | 100.0 | 0 |
| distributionChannel | 100 | 0 | 0.0 | 2 |
| headerBillingBlockReason | 0 | 100 | 100.0 | 0 |
| incotermsClassification | 100 | 0 | 0.0 | 1 |
| incotermsLocation1 | 100 | 0 | 0.0 | 2 |
| lastChangeDateTime | 100 | 0 | 0.0 | 100 |
| organizationDivision | 100 | 0 | 0.0 | 1 |
| overallDeliveryStatus | 100 | 0 | 0.0 | 2 |
| overallOrdReltdBillgStatus | 0 | 100 | 100.0 | 0 |
| overallSdDocReferenceStatus | 0 | 100 | 100.0 | 0 |
| pricingDate | 100 | 0 | 0.0 | 2 |
| requestedDeliveryDate | 100 | 0 | 0.0 | 2 |
| salesGroup | 0 | 100 | 100.0 | 0 |
| salesOffice | 0 | 100 | 100.0 | 0 |
| salesOrder | 100 | 0 | 0.0 | 100 |
| salesOrderType | 100 | 0 | 0.0 | 1 |
| salesOrganization | 100 | 0 | 0.0 | 1 |
| soldToParty | 100 | 0 | 0.0 | 8 |
| totalCreditCheckStatus | 0 | 100 | 100.0 | 0 |
| totalNetAmount | 100 | 0 | 0.0 | 63 |
| transactionCurrency | 100 | 0 | 0.0 | 1 |

### sales_order_items

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| itemBillingBlockReason | 0 | 167 | 100.0 | 0 |
| material | 167 | 0 | 0.0 | 69 |
| materialGroup | 167 | 0 | 0.0 | 2 |
| netAmount | 167 | 0 | 0.0 | 79 |
| productionPlant | 167 | 0 | 0.0 | 7 |
| requestedQuantity | 167 | 0 | 0.0 | 11 |
| requestedQuantityUnit | 167 | 0 | 0.0 | 1 |
| salesDocumentRjcnReason | 30 | 137 | 82.04 | 1 |
| salesOrder | 167 | 0 | 0.0 | 100 |
| salesOrderItem | 167 | 0 | 0.0 | 12 |
| salesOrderItemCategory | 167 | 0 | 0.0 | 1 |
| storageLocation | 167 | 0 | 0.0 | 8 |
| transactionCurrency | 167 | 0 | 0.0 | 1 |

### sales_order_schedule_lines

| Column | Non-null | Nulls | Null % | Unique (non-null) |
|---|---:|---:|---:|---:|
| confdOrderQtyByMatlAvailCheck | 179 | 0 | 0.0 | 12 |
| confirmedDeliveryDate | 167 | 12 | 6.7 | 3 |
| orderQuantityUnit | 179 | 0 | 0.0 | 1 |
| salesOrder | 179 | 0 | 0.0 | 100 |
| salesOrderItem | 179 | 0 | 0.0 | 12 |
| scheduleLine | 179 | 0 | 0.0 | 2 |
