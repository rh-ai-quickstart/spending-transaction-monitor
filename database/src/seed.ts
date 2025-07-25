import prisma from './database';

async function seed() {
  try {
    console.log('🌱 Starting database seed...');

    // Create sample user
    const user = await prisma.user.create({
      data: {
        email: 'john.doe@example.com',
        firstName: 'John',
        lastName: 'Doe',
        phoneNumber: '+1-555-0123',
        
        // Address information
        addressStreet: '123 Main Street, Apt 4B',
        addressCity: 'San Francisco',
        addressState: 'CA',
        addressZipCode: '94102',
        addressCountry: 'US',
        
        // Financial information
        creditLimit: 15000.00,
        currentBalance: 2347.85,
        
        // Location consent and last app location
        locationConsentGiven: true,
        lastAppLocationLatitude: 37.7749,
        lastAppLocationLongitude: -122.4194,
        lastAppLocationTimestamp: new Date('2024-01-17T18:30:00Z'),
        lastAppLocationAccuracy: 5.0,
        
        // Last transaction location (from most recent transaction)
        lastTransactionLatitude: 37.7849,
        lastTransactionLongitude: -122.4094,
        lastTransactionTimestamp: new Date('2024-01-17T19:20:00Z'),
        lastTransactionCity: 'San Francisco',
        lastTransactionState: 'CA',
        lastTransactionCountry: 'US',
      },
    });

    console.log('👤 Created user:', user.email);

    // Create sample credit card
    const creditCard = await prisma.creditCard.create({
      data: {
        userId: user.id,
        cardNumber: '1234', // Last 4 digits only
        cardType: 'Visa',
        bankName: 'Example Bank',
        cardHolderName: 'John Doe',
        expiryMonth: 12,
        expiryYear: 2027,
      },
    });

    console.log('💳 Created credit card for user');

    // Create sample transactions
    const transactions = await Promise.all([
      prisma.transaction.create({
        data: {
          userId: user.id,
          creditCardId: creditCard.id,
          amount: 89.99,
          description: 'Grocery shopping',
          merchantName: 'Whole Foods Market',
          merchantCategory: 'Grocery',
          transactionDate: new Date('2024-01-15T10:30:00Z'),
          merchantCity: 'San Francisco',
          merchantState: 'CA',
          merchantCountry: 'US',
          status: 'APPROVED',
        },
      }),
      prisma.transaction.create({
        data: {
          userId: user.id,
          creditCardId: creditCard.id,
          amount: 1299.99,
          description: 'Laptop purchase',
          merchantName: 'Apple Store',
          merchantCategory: 'Electronics',
          transactionDate: new Date('2024-01-16T14:45:00Z'),
          merchantCity: 'San Francisco',
          merchantState: 'CA',
          merchantCountry: 'US',
          status: 'APPROVED',
        },
      }),
      prisma.transaction.create({
        data: {
          userId: user.id,
          creditCardId: creditCard.id,
          amount: 45.50,
          description: 'Dinner',
          merchantName: 'Restaurant ABC',
          merchantCategory: 'Dining',
          transactionDate: new Date('2024-01-17T19:20:00Z'),
          merchantCity: 'San Francisco',
          merchantState: 'CA',
          merchantCountry: 'US',
          status: 'APPROVED',
        },
      }),
    ]);

    console.log(`💰 Created ${transactions.length} sample transactions`);

    // Create sample alert rules
    const alertRules = await Promise.all([
      prisma.alertRule.create({
        data: {
          userId: user.id,
          name: 'High Amount Alert',
          description: 'Alert for transactions over $1000',
          alertType: 'AMOUNT_THRESHOLD',
          amountThreshold: 1000.00,
          notificationMethods: ['EMAIL', 'SMS'],
        },
      }),
      prisma.alertRule.create({
        data: {
          userId: user.id,
          name: 'Electronics Purchase Alert',
          description: 'Alert for all electronics purchases',
          alertType: 'MERCHANT_CATEGORY',
          merchantCategory: 'Electronics',
          notificationMethods: ['EMAIL'],
        },
      }),
      prisma.alertRule.create({
        data: {
          userId: user.id,
          name: 'AI Smart Alert',
          description: 'Smart pattern-based alerts using AI',
          alertType: 'PATTERN_BASED',
          naturalLanguageQuery: 'Alert me when I spend more than usual on dining in a week',
          notificationMethods: ['PUSH'],
        },
      }),
    ]);

    console.log(`🚨 Created ${alertRules.length} sample alert rules`);

    console.log('✅ Database seeded successfully!');
  } catch (error) {
    console.error('❌ Error seeding database:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

seed(); 