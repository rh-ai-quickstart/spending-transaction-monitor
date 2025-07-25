import prisma from './database';

async function verifyUserData() {
  try {
    console.log('🔍 Verifying updated user data...\n');

    const user = await prisma.user.findFirst({
      where: { email: 'john.doe@example.com' },
      include: {
        creditCards: true,
        transactions: {
          take: 3,
          orderBy: { transactionDate: 'desc' }
        },
        alertRules: true
      }
    });

    if (!user) {
      console.log('❌ User not found');
      return;
    }

    console.log('👤 USER PROFILE:');
    console.log(`   Name: ${user.firstName} ${user.lastName}`);
    console.log(`   Email: ${user.email}`);
    console.log(`   Phone: ${user.phoneNumber}`);
    console.log(`   Active: ${user.isActive}\n`);

    console.log('📍 ADDRESS:');
    console.log(`   Street: ${user.addressStreet}`);
    console.log(`   City: ${user.addressCity}, ${user.addressState} ${user.addressZipCode}`);
    console.log(`   Country: ${user.addressCountry}\n`);

    console.log('💰 FINANCIAL INFO:');
    console.log(`   Credit Limit: $${user.creditLimit?.toString()}`);
    console.log(`   Current Balance: $${user.currentBalance?.toString()}\n`);

    console.log('📱 MOBILE APP LOCATION (Privacy Consented):');
    console.log(`   Consent Given: ${user.locationConsentGiven}`);
    if (user.locationConsentGiven) {
      console.log(`   Last Location: ${user.lastAppLocationLatitude}, ${user.lastAppLocationLongitude}`);
      console.log(`   Timestamp: ${user.lastAppLocationTimestamp?.toISOString()}`);
      console.log(`   Accuracy: ${user.lastAppLocationAccuracy}m\n`);
    }

    console.log('🛒 LAST TRANSACTION LOCATION:');
    console.log(`   Coordinates: ${user.lastTransactionLatitude}, ${user.lastTransactionLongitude}`);
    console.log(`   Location: ${user.lastTransactionCity}, ${user.lastTransactionState}, ${user.lastTransactionCountry}`);
    console.log(`   Timestamp: ${user.lastTransactionTimestamp?.toISOString()}\n`);

    console.log('💳 RELATED DATA:');
    console.log(`   Credit Cards: ${user.creditCards.length}`);
    console.log(`   Recent Transactions: ${user.transactions.length}`);
    console.log(`   Alert Rules: ${user.alertRules.length}`);

    console.log('\n✅ User data verification complete!');

  } catch (error) {
    console.error('❌ Error verifying user data:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

verifyUserData(); 