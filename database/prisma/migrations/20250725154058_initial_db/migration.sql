-- CreateEnum
CREATE TYPE "TransactionType" AS ENUM ('PURCHASE', 'REFUND', 'CASHBACK', 'FEE', 'INTEREST', 'PAYMENT');

-- CreateEnum
CREATE TYPE "TransactionStatus" AS ENUM ('PENDING', 'APPROVED', 'DECLINED', 'CANCELLED', 'SETTLED');

-- CreateEnum
CREATE TYPE "AlertType" AS ENUM ('AMOUNT_THRESHOLD', 'MERCHANT_CATEGORY', 'MERCHANT_NAME', 'LOCATION_BASED', 'FREQUENCY_BASED', 'PATTERN_BASED', 'CUSTOM_QUERY');

-- CreateEnum
CREATE TYPE "NotificationMethod" AS ENUM ('EMAIL', 'SMS', 'PUSH', 'WEBHOOK');

-- CreateEnum
CREATE TYPE "NotificationStatus" AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'READ');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "firstName" TEXT NOT NULL,
    "lastName" TEXT NOT NULL,
    "phoneNumber" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "addressStreet" TEXT,
    "addressCity" TEXT,
    "addressState" TEXT,
    "addressZipCode" TEXT,
    "addressCountry" TEXT DEFAULT 'US',
    "creditLimit" DECIMAL(12,2),
    "currentBalance" DECIMAL(12,2) DEFAULT 0.00,
    "locationConsentGiven" BOOLEAN NOT NULL DEFAULT false,
    "lastAppLocationLatitude" DOUBLE PRECISION,
    "lastAppLocationLongitude" DOUBLE PRECISION,
    "lastAppLocationTimestamp" TIMESTAMP(3),
    "lastAppLocationAccuracy" DOUBLE PRECISION,
    "lastTransactionLatitude" DOUBLE PRECISION,
    "lastTransactionLongitude" DOUBLE PRECISION,
    "lastTransactionTimestamp" TIMESTAMP(3),
    "lastTransactionCity" TEXT,
    "lastTransactionState" TEXT,
    "lastTransactionCountry" TEXT,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "credit_cards" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "cardNumber" TEXT NOT NULL,
    "cardType" TEXT NOT NULL,
    "bankName" TEXT NOT NULL,
    "cardHolderName" TEXT NOT NULL,
    "expiryMonth" INTEGER NOT NULL,
    "expiryYear" INTEGER NOT NULL,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "credit_cards_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "transactions" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "creditCardId" TEXT NOT NULL,
    "amount" DECIMAL(10,2) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "description" TEXT NOT NULL,
    "merchantName" TEXT NOT NULL,
    "merchantCategory" TEXT NOT NULL,
    "transactionDate" TIMESTAMP(3) NOT NULL,
    "transactionType" "TransactionType" NOT NULL DEFAULT 'PURCHASE',
    "merchantLocation" TEXT,
    "merchantCity" TEXT,
    "merchantState" TEXT,
    "merchantCountry" TEXT,
    "status" "TransactionStatus" NOT NULL DEFAULT 'PENDING',
    "authorizationCode" TEXT,
    "referenceNumber" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "transactions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "alert_rules" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "alertType" "AlertType" NOT NULL,
    "amountThreshold" DECIMAL(10,2),
    "merchantCategory" TEXT,
    "merchantName" TEXT,
    "location" TEXT,
    "timeframe" TEXT,
    "naturalLanguageQuery" TEXT,
    "notificationMethods" "NotificationMethod"[] DEFAULT ARRAY['EMAIL']::"NotificationMethod"[],
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "lastTriggered" TIMESTAMP(3),
    "triggerCount" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "alert_rules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "alert_notifications" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "alertRuleId" TEXT NOT NULL,
    "transactionId" TEXT,
    "title" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "notificationMethod" "NotificationMethod" NOT NULL,
    "status" "NotificationStatus" NOT NULL DEFAULT 'PENDING',
    "sentAt" TIMESTAMP(3),
    "deliveredAt" TIMESTAMP(3),
    "readAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "alert_notifications_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_addressCity_addressState_idx" ON "users"("addressCity", "addressState");

-- CreateIndex
CREATE INDEX "users_locationConsentGiven_idx" ON "users"("locationConsentGiven");

-- CreateIndex
CREATE INDEX "transactions_userId_transactionDate_idx" ON "transactions"("userId", "transactionDate");

-- CreateIndex
CREATE INDEX "transactions_merchantCategory_idx" ON "transactions"("merchantCategory");

-- CreateIndex
CREATE INDEX "transactions_amount_idx" ON "transactions"("amount");

-- CreateIndex
CREATE INDEX "alert_rules_userId_isActive_idx" ON "alert_rules"("userId", "isActive");

-- CreateIndex
CREATE INDEX "alert_notifications_userId_createdAt_idx" ON "alert_notifications"("userId", "createdAt");

-- AddForeignKey
ALTER TABLE "credit_cards" ADD CONSTRAINT "credit_cards_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_creditCardId_fkey" FOREIGN KEY ("creditCardId") REFERENCES "credit_cards"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alert_rules" ADD CONSTRAINT "alert_rules_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alert_notifications" ADD CONSTRAINT "alert_notifications_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alert_notifications" ADD CONSTRAINT "alert_notifications_alertRuleId_fkey" FOREIGN KEY ("alertRuleId") REFERENCES "alert_rules"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alert_notifications" ADD CONSTRAINT "alert_notifications_transactionId_fkey" FOREIGN KEY ("transactionId") REFERENCES "transactions"("id") ON DELETE SET NULL ON UPDATE CASCADE;
