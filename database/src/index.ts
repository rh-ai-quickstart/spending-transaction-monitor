import prisma from './database';

async function main() {
  try {
    // Test database connection
    await prisma.$connect();
    console.log('🚀 Connected to database successfully!');
    
    // You can add your application logic here
    console.log('💰 Spending Transaction Monitor Database Ready');
    
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main(); 